#!/bin/sh
# Lightweight local backup: recovery documentation plus optional Notion core export.
# Usage: backup-ai-recovery.sh /absolute/path/to/oneclick-everything
set -eu

repo_path=${1:?pass the absolute repository path}
backup_root="$HOME/AI-Recovery-Backups"
notion_export="$HOME/AI-Recovery-Notion-Export"
timestamp=$(/bin/date +%Y%m%d-%H%M%S)
stage="$(/usr/bin/mktemp -d "${TMPDIR:-/tmp}/ai-recovery.XXXXXX")"
archive="$backup_root/ai-recovery-$timestamp.tar.gz"

cleanup() { /bin/rm -rf "$stage"; }
trap cleanup EXIT HUP INT TERM

[ -d "$repo_path/.git" ] || { echo "Not a Git repository: $repo_path" >&2; exit 2; }
mkdir -p "$backup_root"
mkdir -p "$stage/repository"

for item in START_HERE.md RESTORE_GUIDE.md recovery; do
  [ -e "$repo_path/$item" ] && /bin/cp -R "$repo_path/$item" "$stage/repository/"
done

(
  cd "$repo_path"
  /usr/bin/git rev-parse HEAD
  /usr/bin/git status --short
) > "$stage/repository/GIT_STATUS.txt"

if [ -d "$notion_export" ]; then
  /bin/cp -R "$notion_export" "$stage/notion-core-export"
fi

/usr/bin/tar -czf "$archive" -C "$stage" .
/usr/bin/shasum -a 256 "$archive" > "$archive.sha256"

# Retain 31 calendar days of lightweight archives.
/usr/bin/find "$backup_root" -type f -name 'ai-recovery-*.tar.gz' -mtime +31 -delete
/usr/bin/find "$backup_root" -type f -name 'ai-recovery-*.tar.gz.sha256' -mtime +31 -delete

echo "Created $archive"
