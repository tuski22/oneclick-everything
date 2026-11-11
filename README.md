# OneClick Everything

用一套命令在 macOS、Windows、Linux 安装 Docker、Compose 和常用工具。脚本可独立调用，也可从统一入口批量安装。

## 快速开始

从 GitHub 克隆仓库。没有 Git 时，可从 GitHub 项目页下载 ZIP，解压后进入目录。生产环境建议签出经过审核的提交。

```sh
git clone https://github.com/tuski22/oneclick-everything.git
cd oneclick-everything
./install.sh doctor
./install.sh install docker --dry-run
./install.sh install docker --yes
./install.sh verify
```

Windows PowerShell（先进入仓库目录）：

```powershell
.\install.ps1 doctor
.\install.ps1 install docker --dry-run
.\install.ps1 install docker --yes
.\install.ps1 verify
```

Python 3.9+ 已安装时可直接执行 `python3 oneclick.py`（Windows：`py -3 oneclick.py`）。系统有包管理器但缺 Python 时，启动器可在你同意后尝试安装。安装前查看[兼容性及前置条件](docs/compatibility.md)，尤其是 Homebrew、WinGet、WSL 与 Docker Desktop 的首次启动步骤。

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

- Docker 验证检查所选上下文的 Engine 和 `docker compose version`，不会下载测试镜像。默认上下文为 Linux `default`、Colima `colima`、Desktop `desktop-linux`。macOS Desktop 验证时也需传入 `--backend desktop`。如已自行配置，可用 `--context` 指定。
- Linux 若提示 Docker socket 无权访问，可先用 `sudo docker --context default info` 区分权限与服务问题。工具不会自动把用户加入具有高权限的 docker 组，也不会删除冲突软件包。
- Desktop 安装后如需确认条款、开启虚拟化或重启，请完成后重新运行 `verify`。普通软件安装后如命令不在 PATH，请打开新终端。
- [镜像、签名与回退说明](docs/compatibility.md)列出了各平台的覆盖范围。软件下载源和 Docker Hub 容器镜像是两回事；项目不自动改写容器镜像加速器配置。

开发测试：`python3 -m unittest discover -s tests -v`。可用 `sh -n install.sh && sh -n scripts/docker/install.sh` 检查入口（也可分别检查两个文件）。更改包名或支持版本后，请先在干净虚拟机执行安装、重复安装及验证，再更新矩阵。
