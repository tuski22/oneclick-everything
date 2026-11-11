#!/bin/sh
set -eu
repo=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
source=auto
source_next=no
for arg in "$@"; do
    if [ "$source_next" = yes ]; then
        source=$arg
        source_next=no
    else
        case "$arg" in
            --source) source_next=yes ;;
            --source=*) source=${arg#--source=} ;;
        esac
    fi
done
if [ "$(uname -s)" = Darwin ]; then
    if [ "$(sysctl -n hw.optional.arm64 2>/dev/null || :)" = 1 ]; then
        if [ "$(uname -m)" != arm64 ]; then
            exec /usr/bin/arch -arm64 /bin/sh "$0" "$@"
        fi
        brew_bin=/opt/homebrew/bin
    else
        brew_bin=/usr/local/bin
    fi
    export PATH="$brew_bin:/Applications/Docker.app/Contents/Resources/bin:$PATH"
fi
valid_python() {
    "$1" -c 'import sys; sys.exit(sys.version_info < (3,9))' >/dev/null 2>&1
}
find_python() {
    for exe in python3 python3.14 python3.13 python3.12 /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12; do
        if command -v "$exe" >/dev/null 2>&1 && valid_python "$exe"; then
            py=$exe
            return 0
        fi
    done
    return 1
}
if ! find_python; then
    allow=no
    for arg in "$@"; do
        case "$arg" in
            --yes) allow=yes ;;
            --dry-run|--help|-h|doctor|list|verify)
                printf '%s\n' "需要 Python 3.9+；预览/诊断不会安装依赖。" >&2
                exit 1 ;;
        esac
    done
    if [ "$allow" != yes ]; then
        if [ ! -t 0 ]; then
            printf '%s\n' "缺少 Python 3.9+。请先安装，或用 --yes 引导安装。" >&2
            exit 1
        fi
        printf '安装 Python 3.9+ 以启动管理器？[y/N] '
        read -r reply
        [ "$reply" = y ] || exit 1
    fi
    admin() {
        if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi
    }
    case "$(uname -s)" in
        Darwin)
            version=$(sw_vers -productVersion)
            [ "${version%%.*}" -ge 14 ] || { echo '需要 macOS 14 或更新版本。' >&2; exit 1; }
            if [ ! -x "$brew_bin/brew" ]; then
                /bin/sh "$repo/scripts/install-homebrew.sh" "$source"
            fi
            if [ "$source" = official ] || ! (
                export HOMEBREW_API_DOMAIN=https://mirrors.tuna.tsinghua.edu.cn/homebrew-bottles/api
                export HOMEBREW_BOTTLE_DOMAIN=https://mirrors.tuna.tsinghua.edu.cn/homebrew-bottles
                export HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_UPGRADE=1
                "$brew_bin/brew" install python@3.12
            ); then
                unset HOMEBREW_API_DOMAIN HOMEBREW_BOTTLE_DOMAIN HOMEBREW_ARTIFACT_DOMAIN
                HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_UPGRADE=1 "$brew_bin/brew" install python@3.12
            fi ;;
        Linux)
            if command -v apt-get >/dev/null 2>&1; then
                admin apt-get update
                admin apt-get install -y python3
            elif command -v dnf >/dev/null 2>&1; then
                admin dnf install -y python3
            else
                printf '%s\n' "请通过发行版安装 Python 3.9+。" >&2
                exit 1
            fi ;;
        *) printf '%s\n' "不支持此 Shell 平台。" >&2; exit 1 ;;
    esac
    find_python || { printf '%s\n' "仍未找到 Python 3.9+。" >&2; exit 1; }
fi
exec "$py" "$repo/oneclick.py" "$@"
