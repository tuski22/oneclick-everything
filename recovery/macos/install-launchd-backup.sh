#!/bin/sh
# Install a per-user launchd job for the AI recovery backup.
set -eu

repo_path=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
template="$repo_path/recovery/macos/com.tuski.ai-recovery-backup.plist"
target="$HOME/Library/LaunchAgents/com.tuski.ai-recovery-backup.plist"

[ "$(uname -s)" = Darwin ] || { echo "This installer runs only on macOS." >&2; exit 2; }
[ -f "$template" ] || { echo "Missing template: $template" >&2; exit 2; }

mkdir -p "$HOME/AI-Recovery-Backups" "$HOME/AI-Recovery-Notion-Export" "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
escaped_repo=$(printf '%s' "$repo_path" | /usr/bin/sed 's/[&|]/\\&/g')
escaped_home=$(printf '%s' "$HOME" | /usr/bin/sed 's/[&|]/\\&/g')
/usr/bin/sed -e "s|__REPOSITORY_PATH__|$escaped_repo|g" -e "s|__HOME__|$escaped_home|g" "$template" > "$target"
/usr/bin/plutil -lint "$target"
launchctl bootout "gui/$(id -u)" "$target" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$target"
launchctl kickstart -k "gui/$(id -u)/com.tuski.ai-recovery-backup"
echo "Installed and started: $target"
echo "Check: launchctl print gui/$(id -u)/com.tuski.ai-recovery-backup"
