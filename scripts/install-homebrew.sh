#!/bin/sh
set -eu
[ "$(id -u)" -ne 0 ] || { echo '请以普通用户运行安装。' >&2; exit 1; }
if ! /usr/bin/xcode-select -p >/dev/null 2>&1; then
    /usr/bin/xcode-select --install || :
    echo '请完成 macOS 命令行工具安装，再重试原命令。' >&2
    exit 1
fi
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
commit=7986efac25016e41eed7e471666140c06f9d97cf
sha=5f333bbe53bc490e51e7ccb1df8779b3dd6ee73a1a7379efda216edb08ccb148
tuna=https://mirrors.tuna.tsinghua.edu.cn
official=https://raw.githubusercontent.com/Homebrew/install/$commit/install.sh
download() {
    /usr/bin/curl -qfsSL --proto '=https' --proto-redir '=https' --connect-timeout 10 \
        --max-time 45 --max-filesize 262144 "$1" -o "$tmp/install.sh" &&
        printf '%s  %s\n' "$sha" "$tmp/install.sh" | /usr/bin/shasum -a 256 -c -
}
unset HOMEBREW_BREW_GIT_REMOTE HOMEBREW_CORE_GIT_REMOTE HOMEBREW_API_DOMAIN \
    HOMEBREW_BOTTLE_DOMAIN HOMEBREW_ARTIFACT_DOMAIN HOMEBREW_NO_INSTALL_FROM_API
if [ "${1:-auto}" = auto ]; then
    if git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=15 clone --depth=1 \
        "$tuna/git/homebrew/install.git" "$tmp/mirror" &&
        printf '%s  %s\n' "$sha" "$tmp/mirror/install.sh" | /usr/bin/shasum -a 256 -c -; then
        cp "$tmp/mirror/install.sh" "$tmp/install.sh"
    else
        download "$official"
    fi
    if HOMEBREW_BREW_GIT_REMOTE="$tuna/git/homebrew/brew.git" \
        HOMEBREW_CORE_GIT_REMOTE="$tuna/git/homebrew/homebrew-core.git" \
        HOMEBREW_API_DOMAIN="$tuna/homebrew-bottles/api" \
        HOMEBREW_BOTTLE_DOMAIN="$tuna/homebrew-bottles" /bin/bash "$tmp/install.sh"; then
        exit 0
    fi
    echo 'Homebrew 镜像安装失败，改用官方源。' >&2
else
    download "$official"
fi
/bin/bash "$tmp/install.sh"
