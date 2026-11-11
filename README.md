# OneClick Everything

macOS 优先的 Docker、Compose 和常用工具安装器。默认使用 Colima，也可选择 Docker Desktop。Windows 和 Linux 路径为实验性。

## macOS 快速开始

下面是一条完整命令。将最后两个参数换成可信发布渠道提供的压缩包 HTTPS 地址和 SHA-256。命令先校验整包，再解压并安装 Docker、Compose，最后运行测试容器。

```sh
/bin/sh -c '
set -eu
tmp=$(mktemp -d)
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT
trap "exit 130" INT
trap "exit 143" TERM
fetch() {
    /usr/bin/curl -qfsSL --proto "=https" --proto-redir "=https" --connect-timeout 10 --max-time 90 --max-filesize 5242880 "$1" -o "$tmp/source.tgz" &&
    printf "%s  %s\n" "$2" "$tmp/source.tgz" | /usr/bin/shasum -a 256 -c -
}
if [ -z "${ONECLICK_ARCHIVE_MIRROR:-}" ] || ! fetch "$ONECLICK_ARCHIVE_MIRROR" "$2"; then
    fetch "$1" "$2"
fi
/usr/bin/tar -xzf "$tmp/source.tgz" --strip-components 1 -C "$tmp"
shift 2
/bin/sh "$tmp/install.sh" install docker --yes --smoke "$@"
' oneclick 'ARCHIVE_URL' 'ARCHIVE_SHA256'
```

如果有国内分发地址，可设置 `ONECLICK_ARCHIVE_MIRROR` 为同一压缩包的 HTTPS 地址。镜像下载或校验失败时，命令改用官方地址。若两处都不可访问，可通过其他渠道取得压缩包，校验后使用下面的源码入口。Homebrew 软件包、Colima 虚拟机镜像和 Docker Hub 容器各自需要可用网络。

## 从源码使用

从 GitHub 克隆仓库。没有 Git 时，可从 GitHub 项目页下载 ZIP，解压后进入目录。生产环境建议签出经过审核的提交。

```sh
git clone https://github.com/tuski22/oneclick-everything.git
cd oneclick-everything
./install.sh doctor
./install.sh install docker --dry-run
./install.sh install docker --yes --smoke
./install.sh verify --smoke
```

Windows PowerShell（先进入仓库目录）：

```powershell
.\install.ps1 doctor
.\install.ps1 install docker --dry-run
.\install.ps1 install docker --yes
.\install.ps1 verify
```

Python 3.9+ 已安装时可直接执行 `python3 oneclick.py`（Windows：`py -3 oneclick.py`）。macOS 启动器在你同意后可补装 Homebrew 和 Python。首次安装如弹出 Apple 命令行工具窗口，完成后重跑原命令。安装前查看[兼容性及前置条件](docs/compatibility.md)，尤其是 Homebrew、WinGet、WSL 与 Docker Desktop 的首次启动步骤。

| 用法 | 示例（macOS/Linux） |
|---|---|
| 单独调用 Docker 安装脚本 | `./scripts/docker/install.sh --yes`（Windows：`.\scripts\docker\install.ps1 --yes`） |
| 交互菜单 | `./install.sh` |
| 查看模块 | `./install.sh list` |
| 安装多个模块 | `./install.sh install git nodejs ffmpeg --yes` |
| 按配置批量安装 | `./install.sh batch docs/example.json --yes` |
| macOS 使用 Docker Desktop | `./install.sh install docker --backend desktop --yes` |
| 仅检查 Compose | `./install.sh verify compose` |
| 使用官方软件源 | `./install.sh install docker --source official --yes` |

`--yes` 表示同意本次安装；系统仍可能要求 sudo、UAC、重启或接受 Docker Desktop 的首次运行条款。批量任务遇到错误会停止，已经成功安装的模块保留。模块包括 Docker、Compose、Git、Python、Node.js、Java、FFmpeg、Nginx、GitHub CLI 和 jq；版本由包管理器提供。安装 `compose` 在 Desktop 路径会安装整个 Desktop，因为它包含 Compose。

## 验证和排错

- 常规 Docker 验证只检查所选上下文的 Engine 和 Compose。加 `--smoke` 后会运行 `docker version`、`docker compose version`，并拉取、运行固定官方摘要的 `hello-world`。macOS 默认先用 DaoCloud，失败时尝试 Docker Hub。默认上下文为 Linux `default`、Colima `colima`、Desktop `desktop-linux`。macOS Desktop 验证时也需传入 `--backend desktop`。如已自行配置，可用 `--context` 指定。
- Linux 若提示 Docker socket 无权访问，可先用 `sudo docker --context default info` 区分权限与服务问题。工具不会自动把用户加入具有高权限的 docker 组，也不会删除冲突软件包。
- Desktop 安装后如需确认条款、开启虚拟化或重启，请完成后重新运行 `verify`。普通软件安装后如命令不在 PATH，请打开新终端。
- [镜像、签名与回退说明](docs/compatibility.md)列出了各平台的覆盖范围。软件下载源和 Docker Hub 容器镜像是两回事；项目不自动改写容器镜像加速器配置。

开发测试：`python3 -m unittest discover -s tests -v`。可用 `sh -n install.sh && sh -n scripts/docker/install.sh` 检查入口（也可分别检查两个文件）。更改包名或支持版本后，请先在干净虚拟机执行安装、重复安装及验证，再更新矩阵。
