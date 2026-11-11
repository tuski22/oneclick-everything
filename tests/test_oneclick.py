import argparse
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

import oneclick as o


class Compatibility(unittest.TestCase):
    def test_supported_paths(self):
        cases = [
            (o.Host("Darwin", "arm64", "14.8"), "auto", "colima"),
            (o.Host("Darwin", "amd64", "15.4"), "desktop", "desktop"),
            (o.Host("Windows", "amd64", "26100"), "auto", "winget"),
            (o.Host("Windows", "arm64", "26100"), "desktop", "winget"),
            (o.Host("Linux", "arm64", "24.04", "ubuntu", "noble"), "auto", "apt"),
            (o.Host("Linux", "amd64", "13", "debian", "trixie"), "auto", "apt"),
            (o.Host("Linux", "amd64", "44", "fedora"), "auto", "dnf"),
        ]
        for host, requested, expected in cases:
            with self.subTest(host=host):
                self.assertEqual(o.backend(host, requested), expected)

    def test_unsupported_paths(self):
        for host in (o.Host("Darwin", "amd64", "12.7"),
                     o.Host("Windows", "amd64", "19045"),
                     o.Host("Windows", "amd64", "26100", server=True),
                     o.Host("Linux", "amd64", "24.04", "ubuntu", wsl=True),
                     o.Host("Linux", "arm64", "24.04", "ubuntu", "jammy"),
                     o.Host("Linux", "i686", "13", "debian")):
            with self.subTest(host=host), self.assertRaises(o.Failure):
                o.backend(host, "auto")

    def test_rosetta_reports_physical_arch(self):
        with patch.object(o.platform, "system", return_value="Darwin"), \
             patch.object(o.platform, "machine", return_value="x86_64"), \
             patch.object(o.platform, "mac_ver", return_value=("15.1", (), "")), \
             patch.object(o, "optional", return_value="1"):
            self.assertEqual(o.detect().arch, "arm64")

    def test_os_release_data_is_not_executed(self):
        self.assertEqual(o.os_release('ID=ubuntu\nVERSION_ID="24.04"\nOTHER=$(touch bad)'),
                         {"ID": "ubuntu", "VERSION_ID": "24.04"})


class SourceTests(unittest.TestCase):
    @patch.object(o, "capture")
    @patch.object(o.urllib.request, "urlopen")
    def test_docker_key_rejects_extra_primary_key(self, open_url, capture):
        response = open_url.return_value.__enter__.return_value
        response.geturl.return_value = "https://example.test/gpg"
        response.read.return_value = b"test data"
        capture.return_value = f"pub:::::::::\nfpr:::::::::{o.DOCKER_KEY}:\npub:::::::::"
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(o.Failure):
            o.download_key("https://example.test/gpg", Path(tmp) / "docker.asc")

    @patch.object(o, "capture")
    @patch.object(o.urllib.request, "urlopen")
    def test_docker_key_accepts_only_expected_fingerprint(self, open_url, capture):
        response = open_url.return_value.__enter__.return_value
        response.geturl.return_value = "https://example.test/gpg"
        response.read.return_value = b"test data"
        capture.return_value = f"pub:::::::::\nfpr:::::::::{o.DOCKER_KEY}:"
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "docker.asc"
            o.download_key("https://example.test/gpg", dest)
            self.assertEqual(dest.read_bytes(), b"test data")
            capture.return_value = "pub:::::::::\nfpr:::::::::BAD:"
            with self.assertRaises(o.Failure):
                o.download_key("https://example.test/gpg", dest)

    @patch.object(o.shutil, "which", return_value="/mock/bin/brew")
    def test_brew_falls_back_with_mirror_variables_removed(self, _which):
        runner = o.Runner(argparse.Namespace(source="auto", dry_run=False))
        runner.run = Mock(side_effect=[subprocess.CalledProcessError(1, "brew"), None])
        with redirect_stdout(io.StringIO()):
            runner.brew("install", "docker")
        calls = runner.run.call_args_list
        self.assertIn("tsinghua", calls[0].kwargs["env"]["HOMEBREW_API_DOMAIN"])
        self.assertNotIn("HOMEBREW_API_DOMAIN", calls[1].kwargs["env"])

    @patch.object(o, "capture", return_value="amd64")
    @patch.object(o.shutil, "which", return_value="/mock/bin/gpg")
    @patch.object(o, "download_key")
    def test_apt_retries_verified_official_source_before_install(self, key, _which, _capture):
        def write_key(url, destination):
            if "tsinghua" in url:
                raise o.Failure("invalid key")
            destination.write_text("verified key")
        key.side_effect = write_key
        runner = o.Runner(argparse.Namespace(source="auto", dry_run=False))
        runner.root = Mock()
        host = o.Host("Linux", "amd64", "24.04", "ubuntu", "noble")
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            o.apt_docker(runner, host, ("docker-compose-plugin",), Path(tmp))
        self.assertIn("download.docker.com", key.call_args.args[0])
        calls = [c.args for c in runner.root.call_args_list]
        download = next(i for i, c in enumerate(calls) if "--download-only" in c)
        apply = next(i for i, c in enumerate(calls) if "--no-download" in c)
        self.assertLess(download, apply)

    def test_smoke_falls_back_to_same_digest_on_official_registry(self):
        runner = o.Runner(argparse.Namespace(context="colima", dry_run=False))
        runner.run = Mock(side_effect=[None, None, subprocess.CalledProcessError(1, "docker"), None, None])
        with redirect_stderr(io.StringIO()):
            o.docker_smoke(runner, mirror_first=True)
        commands = [call.args for call in runner.run.call_args_list]
        self.assertEqual(commands[2][-1], f"docker.m.daocloud.io/{o.HELLO_WORLD}")
        self.assertEqual(commands[3][-1], f"docker.io/{o.HELLO_WORLD}")
        self.assertIn("--pull=never", commands[4])
        self.assertEqual(commands[4][-1], commands[3][-1])

    def test_docker_engine_failure_is_not_success(self):
        args = argparse.Namespace(context="colima")
        with patch.object(o.subprocess, "run", side_effect=[Mock(stdout=b"2.40.0"), subprocess.TimeoutExpired("docker", 15)]) as run:
            self.assertFalse(o.docker_ok(args, {"DOCKER_HOST": "tcp://remote:1234"}))
            self.assertNotIn("DOCKER_HOST", run.call_args.kwargs["env"])


class CLI(unittest.TestCase):
    @patch.object(o.subprocess, "run")
    @patch.object(o, "detect", return_value=o.Host("Linux", "arm64", "24.04", "ubuntu", "noble"))
    def test_dry_run_never_invokes_installer(self, _detect, run):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(o.main(["install", "docker", "compose", "--dry-run"]), 0)
        run.assert_not_called()
        self.assertIn("tsinghua", output.getvalue())
        self.assertIn("download.docker.com", output.getvalue())
        self.assertIn("docker-compose-plugin", output.getvalue())
        self.assertEqual(output.getvalue().count("验证："), 1)

    @patch.object(o.subprocess, "run")
    @patch.object(o, "detect", return_value=o.Host("Windows", "amd64", "26100"))
    def test_windows_dry_run_and_agreement(self, _detect, run):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(o.main(["install", "docker", "--dry-run", "--yes"]), 0)
        run.assert_not_called()
        self.assertIn("--accept-package-agreements", output.getvalue())
        self.assertIn("Docker.DockerDesktop", output.getvalue())

    def test_batch_rejects_unknown_names_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "batch.json"
            config.write_text(json.dumps({"modules": ["git", "git", "jq"]}))
            self.assertEqual(o.read_batch(config), ["git", "jq"])
            config.write_text(json.dumps({"modules": ["git", "--bogus"]}))
            with redirect_stderr(io.StringIO()):
                self.assertEqual(o.main(["batch", str(config), "--dry-run"]), 1)

    def test_real_cli_process(self):
        result = subprocess.run([sys.executable, "oneclick.py", "list"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("compose", result.stdout.splitlines())
