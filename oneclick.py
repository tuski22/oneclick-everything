#!/usr/bin/env python3
"""Standard library only installer. Python 3.9+."""
import argparse
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

TUNA = "https://mirrors.tuna.tsinghua.edu.cn"
DOCKER_KEY = "9DC858229FC7DD38854AE2D88D81803C0EBFCD88"
APT_RELEASES = {"ubuntu": {"22.04": "jammy", "24.04": "noble", "26.04": "resolute"},
                "debian": {"11": "bullseye", "12": "bookworm", "13": "trixie"}}
# tuple: macOS Homebrew, Windows WinGet, Debian/Ubuntu APT, Fedora DNF
TOOLS = {
    "git": ("git", "Git.Git", "git", "git"),
    "python": ("python@3.12", "Python.Python.3.12", "python3", "python3"),
    "nodejs": ("node", "OpenJS.NodeJS.LTS", "nodejs", "nodejs"),
    "java": ("openjdk", "EclipseAdoptium.Temurin.21.JDK", "default-jdk", "java-latest-openjdk-devel"),
    "ffmpeg": ("ffmpeg", "Gyan.FFmpeg", "ffmpeg", "ffmpeg-free"),
    "nginx": ("nginx", None, "nginx", "nginx"),
    "gh": ("gh", "GitHub.cli", "gh", "gh"),
    "jq": ("jq", "jqlang.jq", "jq", "jq"),
}
MODULES = ("docker", "compose", *TOOLS)
# docker-library/repo-info, repos/hello-world/remote/latest.md (multi-platform index).
HELLO_WORLD = "library/hello-world@sha256:c567b231f65614688711a75f31518a064258a51d442117a3e771a3a8fdba78ef"


class Failure(Exception):
    pass


def capture(*args):
    return subprocess.check_output(args, stderr=subprocess.STDOUT, text=True, timeout=30).strip()


def optional(*args):
    try:
        return capture(*args)
    except (OSError, subprocess.SubprocessError):
        return ""


def os_release(content):
    data = {}
    for line in content.splitlines():
        match = re.fullmatch(r"(ID|VERSION_ID|VERSION_CODENAME)=(.*)", line)
        if match:
            parts = shlex.split(match[2], comments=True)
            if len(parts) == 1:
                data[match[1]] = parts[0]
    return data


@dataclass(frozen=True)
class Host:
    system: str
    arch: str
    version: str
    distro: str = ""
    codename: str = ""
    wsl: bool = False
    server: bool = False


def detect():
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Darwin" and optional("sysctl", "-n", "hw.optional.arm64") == "1":
        machine = "arm64"
    if system == "Windows":
        machine = os.getenv("PROCESSOR_ARCHITEW6432", machine).lower()
    arch = {"aarch64": "arm64", "x86_64": "amd64", "amd64": "amd64"}.get(machine, machine)
    if system == "Linux":
        release = Path("/etc/os-release")
        data = os_release(release.read_text() if release.exists() else "")
        return Host(system, arch, data.get("VERSION_ID", ""), data.get("ID", ""),
                    data.get("VERSION_CODENAME", ""), "microsoft" in platform.release().lower())
    if system == "Windows":
        version = sys.getwindowsversion()
        return Host(system, arch, str(version.build), server=version.product_type != 1)
    return Host(system, arch, platform.mac_ver()[0] if system == "Darwin" else platform.release())


def backend(host, requested):
    if host.arch not in ("amd64", "arm64"):
        raise Failure("安装目前仅支持 64 位 x86 和 ARM。")
    if host.system == "Linux":
        if host.wsl:
            raise Failure("WSL 内请使用 Windows Docker Desktop 的 WSL 集成。")
        if host.version in APT_RELEASES.get(host.distro, {}):
            expected = APT_RELEASES[host.distro][host.version]
            if host.codename and host.codename != expected:
                raise Failure("发行版代号与支持矩阵不符。")
            choice = "apt"
        elif host.distro == "fedora" and host.version in ("43", "44"):
            choice = "dnf"
        else:
            raise Failure("Linux 发行版或版本未列入支持矩阵。")
    elif host.system == "Darwin":
        major = int(host.version.split(".")[0] or 0)
        if major < 14:
            raise Failure("macOS 低于 14；当前方案不自动下载停更的旧版本。")
        choice = "desktop" if requested == "desktop" else "colima"
        if choice == "desktop" and major < 15:
            raise Failure("本项目仅在 macOS 15+ 提供 Docker Desktop 路径；可尝试 Colima。")
    elif host.system == "Windows":
        if host.server or int(host.version) < 22631:
            raise Failure("需要受支持的 Windows 11 客户端（至少 23H2）；不支持 Windows Server。")
        choice = "winget"
    else:
        raise Failure("此操作系统未列入支持矩阵。")
    if requested != "auto" and requested != choice and not (requested == "desktop" and choice == "winget"):
        raise Failure("所选后端与系统不兼容。")
    return choice


class Runner:
    def __init__(self, args):
        self.args = args
        self.env = os.environ.copy()

    def run(self, *argv, env=None, timeout=None):
        print("+", subprocess.list2cmdline(argv), flush=True)
        if not self.args.dry_run:
            subprocess.run(argv, check=True, env=env or self.env, timeout=timeout)

    def root(self, *argv):
        self.run(*(() if getattr(os, "geteuid", lambda: -1)() == 0 else ("sudo",)), *argv)

    def brew(self, *argv, fallback=True):
        clean = {k: v for k, v in self.env.items() if k not in
                 {"HOMEBREW_API_DOMAIN", "HOMEBREW_BOTTLE_DOMAIN", "HOMEBREW_ARTIFACT_DOMAIN",
                  "HOMEBREW_NO_INSTALL_FROM_API", "HOMEBREW_ARTIFACT_DOMAIN_NO_FALLBACK"}}
        clean.update(HOMEBREW_NO_AUTO_UPDATE="1", HOMEBREW_NO_INSTALL_UPGRADE="1")
        mirror = dict(clean, HOMEBREW_API_DOMAIN=TUNA + "/homebrew-bottles/api",
                      HOMEBREW_BOTTLE_DOMAIN=TUNA + "/homebrew-bottles")
        binary = shutil.which("brew") or next((p for p in
                  ("/opt/homebrew/bin/brew", "/usr/local/bin/brew") if Path(p).is_file()), "brew")
        if not self.args.dry_run and binary == "brew":
            script = Path(__file__).resolve().parent / "scripts/install-homebrew.sh"
            self.run("/bin/sh", str(script), self.args.source)
            binary = "/opt/homebrew/bin/brew" if detect().arch == "arm64" else "/usr/local/bin/brew"
            if not Path(binary).is_file():
                raise Failure("Homebrew 安装后仍未找到 brew。")
        if binary != "brew":
            self.env["PATH"] = str(Path(binary).parent) + os.pathsep + self.env.get("PATH", "")
            clean["PATH"] = mirror["PATH"] = self.env["PATH"]
        order = (("清华", mirror), ("官方", clean)) if self.args.source == "auto" else (("官方", clean),)
        for i, (name, env) in enumerate(order):
            print(f"Homebrew 来源：{name}")
            try:
                self.run(binary, *argv, env=env)
                return
            except subprocess.CalledProcessError:
                if not fallback or i == len(order) - 1:
                    raise

    def winget(self, package):
        argv = ["winget", "install", "--exact", "--id", package, "--source", "winget"]
        if self.args.yes:
            argv += ["--silent", "--disable-interactivity", "--accept-package-agreements",
                     "--accept-source-agreements"]
        self.run(*argv)


def download_key(url, dest):
    with urllib.request.urlopen(url, timeout=15) as response:
        if not response.geturl().startswith("https://"):
            raise Failure("拒绝非 HTTPS 下载。")
        data = response.read(65537)
    if not data or len(data) > 65536:
        raise Failure("签名公钥文件大小异常。")
    dest.write_bytes(data)
    output = capture("gpg", "--batch", "--no-options", "--homedir", str(dest.parent),
                     "--with-colons", "--show-keys", str(dest))
    records = [line.split(":") for line in output.splitlines()]
    primary = [row for row in records if row[0] == "pub"]
    fingerprints = [row[9] for row in records if row[0] == "fpr"]
    if len(primary) != 1 or not fingerprints or fingerprints[0] != DOCKER_KEY:
        raise Failure("Docker 公钥指纹不匹配。")


def apt_docker(runner, host, packages, apt_dir=Path("/etc/apt")):
    release = APT_RELEASES[host.distro][host.version]
    bases = [f"https://download.docker.com/linux/{host.distro}"]
    if runner.args.source == "auto":
        bases.insert(0, f"{TUNA}/docker-ce/linux/{host.distro}")
    if runner.args.dry_run:
        for base in bases:
            print(f"APT 候选：{base} {release}/{host.arch}；验证公钥、签名索引及包哈希")
        runner.root("apt-get", "install", *packages)
        return
    if capture("dpkg", "--print-architecture") != host.arch:
        raise Failure("系统架构与 APT 主架构不一致。")
    source_dir = apt_dir / "sources.list.d"
    target = source_dir / "oneclick-docker.sources"
    keyring = str(apt_dir / "keyrings/oneclick-docker.asc")
    original = apt_dir / "sources.list"
    source_files = [original, *source_dir.glob("*.list"), *source_dir.glob("*.sources")]
    for path in source_files:
        if path != target and path.exists() and re.search(
                r"^\s*(?:deb\s|URIs:).*?(?:download\.docker\.com|/docker-ce/linux/)",
                path.read_text(), re.M):
            raise Failure(f"已配置 Docker 源：{path}；请沿用现有包管理方式，避免重复源。")
    if not shutil.which("gpg") or not Path("/etc/ssl/certs/ca-certificates.crt").is_file():
        runner.root("apt-get", "-o", "APT::Update::Error-Mode=any", "update")
        runner.root("apt-get", "install", "-y", "ca-certificates", "gnupg")
    with tempfile.TemporaryDirectory(prefix="oneclick-") as tmp:
        # APT's sandbox user needs read access to the public source and key.
        folder = Path(tmp)
        folder.chmod(0o755)
        keys = folder / "keys"
        keys.mkdir(mode=0o700)
        key = keys / "docker.asc"
        public = folder / "docker.asc"
        source = folder / "docker.sources"
        parts = folder / "parts"
        parts.mkdir()
        for path in source_files:
            if path.exists() and path != target and path.name != "sources.list":
                (parts / path.name).symlink_to(path)
        # Use dedicated lists so candidate probing never changes system APT indexes.
        lists = folder / "lists"
        lists.mkdir()
        lists_opt = ("-o", f"Dir::State::lists={lists}")
        keep_lists = ("-o", "APT::Get::List-Cleanup=false")
        runner.root("apt-get", *lists_opt, "-o", f"Dir::Etc::sourceparts={parts}",
                    "-o", f"Dir::Etc::sourcelist={original}",
                    "-o", "APT::Update::Error-Mode=any", "update")
        if original.is_file():
            (parts / "base.list").symlink_to(original)
        for base in bases:
            print(f"检查 Docker APT 源：{base}", flush=True)
            try:
                download_key(base + "/gpg", key)
                public.write_bytes(key.read_bytes())
                entry = (f"Types: deb\nURIs: {base}\nSuites: {release}\n"
                         f"Components: stable\nArchitectures: {host.arch}\nSigned-By: ")
                source.write_text(entry + str(public) + "\n")
                # Probe the candidate alone. Install dependencies using configured OS repositories.
                runner.root("apt-get", *lists_opt, *keep_lists, "-o", f"Dir::Etc::sourcelist={source}",
                            "-o", "Dir::Etc::sourceparts=-", "-o", "Acquire::Retries=0",
                            "-o", "Acquire::https::Timeout=15",
                            "-o", "APT::Update::Error-Mode=any", "update")
                cache = folder / "archives"
                cache.mkdir(exist_ok=True)
                opts = (*lists_opt, "-o", f"Dir::Cache::archives={cache}",
                        "-o", "Acquire::https::Timeout=20", "-o", f"Dir::Etc::sourcelist={source}",
                        "-o", f"Dir::Etc::sourceparts={parts}")
                runner.root("apt-get", *opts, "install", "--download-only", "--no-remove", "-y", *packages)
            except (OSError, subprocess.SubprocessError, Failure) as exc:
                print(f"此源不可用或未通过验证：{exc}", file=sys.stderr)
                continue
            runner.root("apt-get", *opts, "install", "--no-download", "--no-remove", "-y", *packages)
            source.write_text(entry + keyring + "\n")
            runner.root("install", "-d", "-m", "0755", str(apt_dir / "keyrings"))
            runner.root("install", "-m", "0644", str(public), keyring)
            runner.root("install", "-m", "0644", str(source), str(target))
            return
    raise Failure("所有 Docker APT 候选均失败；检查上方网络、签名或依赖错误。")


def docker_ok(args, env=None, attempts=1, verify_only_compose=False):
    env = dict(env or os.environ)
    env.pop("DOCKER_HOST", None)
    env.pop("DOCKER_CONTEXT", None)
    for index in range(attempts):
        try:
            base = ["docker", "--context", args.context]
            compose = subprocess.run([*base, "compose", "version", "--short"], check=True,
                                     env=env, timeout=15, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            major = re.match(rb"v?(\d+)\.", compose.stdout.strip())
            if not major or int(major[1]) < 2:
                return False
            if not verify_only_compose:
                subprocess.run([*base, "info", "--format", "{{.ServerVersion}}"], check=True,
                               env=env, timeout=15, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except (OSError, subprocess.SubprocessError):
            if index + 1 < attempts:
                time.sleep(3)
    return False


def install_docker(r, host, choice, compose_only):
    a = r.args
    if not a.dry_run and docker_ok(a, verify_only_compose=compose_only):
        print("Docker 检查已通过，跳过安装。")
        return
    if choice in ("colima", "desktop") and not compose_only and not a.dry_run:
        if optional("/usr/sbin/sysctl", "-n", "kern.hv_support") == "0":
            raise Failure("此 Mac 环境未向 Docker 提供硬件虚拟化。")
        if shutil.disk_usage(Path.home()).free < 10 * 1024**3:
            raise Failure("Docker 初次安装需要至少 10 GiB 可用空间。")
    if choice in ("apt", "dnf") and not compose_only and not a.dry_run:
        if not Path("/run/systemd/system").is_dir():
            raise Failure("Docker Engine 自动安装要求 systemd 主机。")
    if choice == "apt":
        packages = ("docker-compose-plugin",) if compose_only else (
            "docker-ce", "docker-ce-cli", "containerd.io", "docker-buildx-plugin",
            "docker-compose-plugin")
        apt_docker(r, host, packages)
    elif choice == "dnf":
        r.root("dnf", "install", "-y", *(("docker-compose",) if compose_only else
                                        ("moby-engine", "docker-compose")))
    elif choice == "colima":
        r.brew("install", "docker", "docker-compose", *(() if compose_only else ("colima",)))
        if not a.dry_run:
            prefix = subprocess.check_output(["brew", "--prefix", "docker-compose"], env=r.env,
                                             text=True, timeout=20).strip()
            # Compose discovery without rewriting config.json.
            directory = Path(os.getenv("DOCKER_CONFIG") or str(Path.home() / ".docker")) / "cli-plugins"
            directory.mkdir(parents=True, exist_ok=True)
            link = directory / "docker-compose"
            try:
                link.symlink_to(Path(prefix) / "bin/docker-compose")
            except FileExistsError:
                if link.is_symlink() and not link.exists():
                    raise Failure(f"Compose 插件链接已失效：{link}。请检查并修复链接后重试。")
        if not compose_only:
            options = ("colima", "start", "--runtime", "docker")
            help_text = "" if a.dry_run else optional("colima", "start", "--help")
            if "--downloader" in help_text:
                options += ("--downloader", "curl")
            mirror = os.getenv("ONECLICK_COLIMA_IMAGE_MIRROR") if a.source == "auto" else None
            if mirror and not mirror.startswith("https://"):
                raise Failure("ONECLICK_COLIMA_IMAGE_MIRROR 必须是 HTTPS 地址。")
            supports_mirror = a.dry_run or "--disk-image-mirror" in help_text
            if mirror and not supports_mirror:
                print("当前 Colima 版本不支持虚拟机镜像代理，将使用上游地址。", file=sys.stderr)
            if mirror and supports_mirror:
                try:
                    r.run(*options, "--disk-image-mirror", mirror)
                except subprocess.CalledProcessError:
                    print("Colima 镜像启动失败，改用官方地址。", file=sys.stderr)
                    r.run(*options, "--disk-image-mirror", "")
            else:
                if a.source == "official" and supports_mirror:
                    options += ("--disk-image-mirror", "")
                r.run(*options)
    elif choice == "desktop":
        if a.dry_run or not Path("/Applications/Docker.app/Contents/Resources/bin/docker").is_file():
            r.brew("install", "--cask", "docker-desktop")
        if not compose_only:
            r.run("open", "-a", "Docker")
        r.env["PATH"] += os.pathsep + "/Applications/Docker.app/Contents/Resources/bin"
    else:
        if not a.dry_run:
            try:
                version = subprocess.check_output(["wsl.exe", "--version"], timeout=30,
                                                  stderr=subprocess.STDOUT)
            except (OSError, subprocess.SubprocessError):
                version = b""
            version = version.replace(b"\x00", b"").decode("ascii", errors="ignore")
            match = re.search(r"\d+\.\d+\.\d+", version)
            if not match or tuple(map(int, match[0].split("."))) < (2, 1, 5):
                raise Failure("需要 WSL 2.1.5+。请以管理员运行 wsl --install 或 wsl --update，重启后重试。")
        r.winget("Docker.DockerDesktop")
        for var in ("ProgramFiles", "LOCALAPPDATA"):
            if os.getenv(var):
                base = Path(os.environ[var])
                app = base / ("Docker/Docker" if var == "ProgramFiles" else "Programs/DockerDesktop")
                exe = app / "Docker Desktop.exe"
                if not a.dry_run and exe.exists():
                    r.env["PATH"] += os.pathsep + str(app / "resources/bin")
                    if not compose_only:
                        subprocess.Popen([str(exe)], env=r.env)
                    break
    if not compose_only and choice in ("apt", "dnf"):
        r.root("systemctl", "enable", "--now", "docker")
    if a.dry_run:
        print(f"验证：docker --context {a.context} compose version；Docker 安装另检查 Engine")
    elif not docker_ok(a, r.env, attempts=6, verify_only_compose=compose_only):
        raise Failure("安装命令已执行，但验证未通过。请检查首次启动提示、PATH、Docker context 或 Linux socket 权限，再运行 verify。")
    else:
        print("验证通过：Compose" + ("" if compose_only else " 与 Docker Engine"))


def repair_colima_dns(r):
    if r.args.dry_run or not shutil.which("colima", path=r.env.get("PATH")):
        return
    # A Colima Ubuntu minimal image can ship a dangling systemd-resolved stub.
    # Limit the repair to that exact state and use the VM's DHCP resolver.
    script = r"""
if [ "$(readlink /etc/resolv.conf)" != "../run/systemd/resolve/stub-resolv.conf" ] ||
   [ -e /etc/resolv.conf ] || command -v resolvectl >/dev/null; then
    exit 0
fi
tmp=$(mktemp /etc/oneclick-resolv.XXXXXX)
trap 'rm -f "$tmp"' EXIT
awk -F= '$1 == "DNS" {
    n = split($2, servers, " ")
    for (i = 1; i <= n; i++)
        if (servers[i] ~ /^[0-9a-fA-F:.]+$/) print "nameserver " servers[i]
}' /run/systemd/netif/leases/* > "$tmp"
test -s "$tmp"
chmod 644 "$tmp"
mv -T "$tmp" /etc/resolv.conf
echo '已修复 Colima 虚拟机失效的 DNS 配置。'
"""
    subprocess.run(("colima", "ssh", "--", "sudo", "sh", "-eu", "-c", script),
                   env=r.env, check=True, timeout=30)


def docker_smoke(r, mirror_first=False):
    env = {k: v for k, v in r.env.items() if k not in ("DOCKER_HOST", "DOCKER_CONTEXT")}
    base = ("docker", "--context", r.args.context)
    r.run(*base, "version", env=env, timeout=20)
    r.run(*base, "compose", "version", env=env, timeout=20)
    registries = ("docker.m.daocloud.io", "docker.io") if mirror_first else ("docker.io",)
    for registry in registries:
        image = f"{registry}/{HELLO_WORLD}"
        try:
            r.run(*base, "pull", image, env=env, timeout=60)
        except subprocess.SubprocessError:
            print(f"测试镜像拉取失败：{registry}", file=sys.stderr)
            continue
        r.run(*base, "run", "--rm", "--pull=never", image, env=env, timeout=30)
        return
    raise Failure("无法拉取固定摘要的 hello-world。请检查 Docker 虚拟机 DNS 和镜像仓库网络。")


def install_tool(r, choice, name):
    index = {"desktop": 0, "colima": 0, "winget": 1, "apt": 2, "dnf": 3}[choice]
    package = TOOLS[name][index]
    if not package:
        raise Failure(f"{name} 暂无此平台安装方案。")
    if index == 0:
        r.brew("install", package)
    elif index == 1:
        r.winget(package)
    elif index == 2:
        r.root("apt-get", "-o", "APT::Update::Error-Mode=any", "update")
        r.root("apt-get", "install", "-y", package)
    else:
        r.root("dnf", "install", "-y", package)


def read_batch(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"modules"}:
        raise Failure("配置须为仅含 modules 数组的 JSON 对象。")
    names = payload["modules"]
    if not isinstance(names, list) or not names or any(
            not isinstance(n, str) or n not in MODULES for n in names):
        raise Failure("配置包含未知模块或空数组。")
    return list(dict.fromkeys(names))


def main(argv=None):
    parser = argparse.ArgumentParser(description="跨平台安装 Docker 和常用软件")
    parser.add_argument("action", nargs="?", choices=("list", "doctor", "install", "verify", "menu", "batch"))
    parser.add_argument("modules", nargs="*")
    parser.add_argument("--backend", default="auto", choices=("auto", "desktop", "colima", "apt", "dnf", "winget"))
    parser.add_argument("--source", default="auto", choices=("auto", "official"),
                        help="APT Docker / Homebrew 使用国内优先或官方源")
    parser.add_argument("--context", help="覆盖 Docker 验证上下文")
    parser.add_argument("--smoke", action="store_true",
                        help="验证时拉取并运行 Docker Hub 的 hello-world")
    parser.add_argument("--dry-run", action="store_true", help="仅输出安装计划")
    parser.add_argument("--yes", action="store_true", help="确认执行；系统仍可能要求提权或重启")
    a = parser.parse_args(argv)
    try:
        if a.action == "list":
            print("\n".join(MODULES))
            return 0
        h = detect()
        if a.smoke and (a.action not in ("verify", "install") or
                        (a.action == "install" and "docker" not in a.modules) or
                        (a.action == "verify" and a.modules == ["compose"])):
            raise Failure("--smoke 需要 verify 或 install docker。")
        if a.action == "doctor":
            print(json.dumps(asdict(h), ensure_ascii=False, indent=2))
            for exe in ("docker", "docker-compose", "colima", "brew", "apt-get", "dnf", "winget", "wsl.exe"):
                if shutil.which(exe):
                    print(exe, shutil.which(exe))
            if h.system == "Darwin":
                print("硬件虚拟化：", optional("/usr/sbin/sysctl", "-n", "kern.hv_support") or "未知")
                print("可用磁盘 GiB：", shutil.disk_usage(Path.home()).free // 1024**3)
                if shutil.which("docker"):
                    print(optional("docker", "context", "ls"))
            try:
                print("推荐安装后端：", backend(h, a.backend))
            except Failure as exc:
                print("兼容性：", exc)
            return 0
        if not a.action or a.action == "menu":
            if not sys.stdin.isatty():
                raise Failure("菜单需要终端；无人值守请使用 install 模块 --yes。")
            for i, name in enumerate(MODULES, 1):
                print(f"{i:2}. {name}")
            picks = input("输入编号（空格分隔，回车退出）：").split()
            if not picks:
                return 0
            if any(not p.isdecimal() or not 1 <= int(p) <= len(MODULES) for p in picks):
                raise Failure("菜单编号无效。")
            a.modules = [MODULES[int(p) - 1] for p in picks]
        if a.action == "batch":
            if len(a.modules) != 1:
                raise Failure("用法：batch 文件.json")
            a.modules = read_batch(a.modules[0])
        if a.action == "verify":
            a.context = a.context or ("colima" if h.system == "Darwin" and a.backend != "desktop"
                                     else "desktop-linux" if h.system in ("Darwin", "Windows") else "default")
            if a.modules not in ([], ["docker"], ["compose"]):
                raise Failure("verify 仅接受 docker 或 compose。")
            if not a.dry_run and not docker_ok(a, verify_only_compose=a.modules == ["compose"]):
                raise Failure(f"验证失败：检查 Docker、Compose、服务状态和上下文 {a.context}。")
            if a.smoke:
                docker_smoke(Runner(a), h.system == "Darwin" and a.source == "auto")
            print("验证计划已输出。" if a.dry_run else "验证通过。")
            return 0
        if not a.modules or any(n not in MODULES for n in a.modules):
            raise Failure("请提供有效模块；用 list 查看。")
        choice = backend(h, a.backend)
        a.context = a.context or {"colima": "colima", "desktop": "desktop-linux",
                                  "winget": "desktop-linux"}.get(choice, "default")
        names = list(dict.fromkeys(n for n in a.modules if n != "compose" or "docker" not in a.modules))
        if choice == "winget" and "nginx" in names:
            raise Failure("nginx 暂未提供 Windows 安装模块。")
        if not (a.dry_run or a.yes):
            if not sys.stdin.isatty() or input(f"使用 {choice} 安装 {', '.join(names)}？[y/N] ").lower() != "y":
                raise Failure("安装未执行；无人值守请显式传入 --yes。")
        r = Runner(a)
        for n in names:
            if n in ("docker", "compose"):
                install_docker(r, h, choice, n == "compose")
                if n == "docker" and choice == "colima" and a.context == "colima":
                    repair_colima_dns(r)
                if a.smoke and n == "docker":
                    docker_smoke(r, h.system == "Darwin" and a.source == "auto")
            else:
                install_tool(r, choice, n)
        return 0
    except (Failure, OSError, ValueError, subprocess.SubprocessError, EOFError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    if os.name == "nt":
        sys.stdout.reconfigure(errors="backslashreplace")
        sys.stderr.reconfigure(errors="backslashreplace")
    sys.exit(main())
