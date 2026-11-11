# 兼容性、软件源和验证范围

这里列的是安装器接受的系统。未列出的系统仍可运行 `doctor`（需 Python 3.9+）。矩阵不代表实机验收；上游支持、供应商维护周期和包是否发布仍会影响安装。

| 系统 | 架构 | Docker 路径 | 前置条件 |
|---|---|---|---|
| macOS 14+ | Intel / Apple Silicon | 默认 Colima、Docker CLI、Compose | 原生架构的 Homebrew；虚拟化可用。macOS 14 的 Homebrew 支持取决于当前上游政策 |
| macOS 15+ | Intel / Apple Silicon | 可选 Docker Desktop | Homebrew Cask；系统须仍在 Docker Desktop 支持范围内 |
| Windows 11 23H2 或更高且仍在维护期 | x64 / ARM64 | WinGet Docker Desktop | App Installer/WinGet、硬件虚拟化、WSL ≥ 2.1.5、所需 Windows 功能已开启；ARM64 取决于上游安装包 |
| Ubuntu 22.04 / 24.04 / 26.04 | amd64 / arm64 | Docker CE + Compose 插件 | APT、systemd、root 或 sudo |
| Debian 11 / 12 / 13 | amd64 / arm64 | Docker CE + Compose 插件 | APT、systemd、root 或 sudo |
| Fedora 43 / 44 | amd64 / arm64 | Fedora Moby Engine + Compose | DNF、systemd、root 或 sudo |

WSL 内使用 Windows Docker Desktop 的 WSL 集成。Windows Server、旧版 macOS、32 位主机及未列出的发行版不自动安装。Nginx 在 Windows 上没有安装模块。APT/DNF 软件名称由发行版决定；例如旧发行版可能没有 GitHub CLI 或只提供较旧版本。

如果 Mac 没有 Homebrew，请先按 [Homebrew 官方步骤](https://brew.sh/)安装；在国内可参考[清华 Homebrew 配置](https://mirrors.tuna.tsinghua.edu.cn/help/homebrew/)。如未安装命令行工具，先完成 Apple 的 Command Line Tools 安装。Mac 的 Shell 启动器有 Homebrew 时可补装 Python；Windows 用 WinGet，Linux 用系统包管理器。

## 下载与回退

- Debian/Ubuntu 的 Docker 包先尝试[清华 Docker CE 镜像](https://mirrors.tuna.tsinghua.edu.cn/help/docker-ce/)，再尝试 [Docker 官方 APT 源](https://docs.docker.com/engine/install/ubuntu/)。下载的公钥必须匹配固定指纹；APT 检查签名及包哈希。先尝试下载完整安装所需的软件包，再应用安装。安装成功后保留选中的 Docker 源供后续更新。遇到已有 Docker 源时避免重复配置。
- Homebrew 优先尝试清华的 API 和 bottles。失败后重新使用官方配置，由 Homebrew 检查可用的包校验值。Docker Desktop Cask 的安装文件仍可能来自 Docker 官方站。普通 APT、Fedora DNF 及 Windows WinGet 沿用各自的仓库和校验规则；WinGet 安装文件的可达性取决于软件发布方。
- `--source official` 跳过本工具设置的 APT Docker 与 Homebrew 镜像。系统自己配置的代理和发行版镜像仍生效。Docker Hub 镜像拉取需单独验证。
- 清华镜像与官方源均失败时，命令返回非零状态，不关闭 TLS、签名或哈希检查。出现冲突包时请先检查包管理器的报错，避免移除现有环境。

上游条件见 [macOS Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/)、[Windows Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) 和 [Compose Linux 插件](https://docs.docker.com/compose/install/linux/)。

## 验收

GitHub Actions 在 Linux、macOS 和 Windows 上运行 Python 测试并检查对应的启动器，不安装系统软件。实机验收需分别验证：干净系统的引导安装、镜像不可用回退、Engine 与 Compose、重复执行，以及首次安装后重开终端。Windows 另需验证 PowerShell、App Installer 和 WSL；macOS 需分别验证 Intel、Apple Silicon、Colima 和 Desktop。请用国内目标网络验证 GitHub 克隆和实际包下载。
