# AI 自动化轻量灾难恢复手册

适用场景：更换 AI、ChatGPT 账号不可用、Mac mini 迁移或需要重新连接授权。目标是恢复必要记忆与既有自动化，不恢复所有聊天。

## 0. 准备

你需要：GitHub 访问权、Notion 访问权、Mac mini 本机管理员密码、原来的密码管理器或 macOS 钥匙串访问权。不要把任何密钥贴进聊天或仓库。

## 1. 让新的 AI 接管

把仓库根目录的 `START_HERE.md` 提供给新 AI，并允许它访问本仓库、Notion 和需要检查的 Mac mini。要求它：

1. 先阅读 START_HERE、项目恢复档案和日志。
2. 读取 Notion「AI跨平台记忆中枢｜总入口」，再按任务打开相关原始项目页。
3. 先盘点 Mac mini 现状，确认服务是否仍在运行。
4. 只修复失效项目，逐项记录实际验证结果。

可直接使用这段指令：

```text
请接管我的既有自动化。先完整阅读 START_HERE.md、RESTORE_GUIDE.md 和 recovery/PROJECT_REGISTRY.md；再读取 Notion「AI跨平台记忆中枢｜总入口」。先检查现有 Mac mini 服务与调度，正常项目不得重复安装。缺少凭据时只定位其安全保存位置或要求我在官方授权界面重新连接，绝不索要或写入明文密钥。每项修复必须验证并记录，未经验证标为待确认。
```

## 2. 恢复代码与工具安装器

在 Mac mini「终端」中执行：

```sh
git clone https://github.com/tuski22/oneclick-everything.git
cd oneclick-everything
./install.sh doctor
./install.sh list
```

只有在需要安装缺失工具时，先预览：

```sh
./install.sh install docker --dry-run
```

确认后才执行带 `--yes` 的安装。已安装的 Docker、Colima 或 Docker Desktop 不要盲目重装。安装后以仓库 README 的 `verify` 命令验证。

## 3. 重新连接授权

按“最少授权”原则逐项重新连接。

| 服务 | 重新连接方式 | 验证 |
|---|---|---|
| GitHub | 在浏览器或 GitHub CLI 完成登录；确认可访问仓库 | `git ls-remote` 或仓库网页可读 |
| Notion | 在新 AI 中连接 Notion，并授权目标页面 | 能打开总入口和相关项目页 |
| 第三方 API / 社媒 | 进入该服务官方开发者或登录页面重新授权；将凭据放回原来的密码管理器、钥匙串或本机安全文件 | 运行该项目提供的只读健康检查 |
| ChatGPT 定时任务 | 不视为可自动迁移 | 在新账户中按原任务内容手动重建；先确认不会与 Mac mini 调度重复 |

若旧密钥已失效，应在服务商后台撤销并新建，不要尝试从仓库或聊天里找明文。

## 4. 恢复或检查每个项目

打开 `recovery/PROJECT_REGISTRY.md`，从“当前证据”最完整的项目开始。每项遵循：

1. 记录本机实际项目路径、启动方式和最近运行日志。
2. 检查进程 / launchd 状态，确认是否已正常运行。
3. 仅在未运行或验证失败时按档案中的恢复步骤操作。
4. 运行无副作用的健康检查或一次受控测试。
5. 将结果、日期、问题写入 `recovery/IMPLEMENTATION_LOG.md`。

## 5. 配置每日 22:15 轻量备份

仓库已经提供备份脚本与 launchd 模板；它只备份本仓库的恢复资料和你手动放入的 Notion 核心导出，不抓取全部聊天或秘密。请按 [Mac mini 备份说明](recovery/MAC_MINI_LIGHT_BACKUP.md) 在 Mac mini 上安装。首次运行完成后，检查当天的日志和备份目录。

## 6. 常见故障

| 问题 | 处理 |
|---|---|
| 新 AI 看不到 Notion | 在新 AI 的连接设置中重新授权；确认它至少有总入口与相关原始页面的访问权 |
| Git clone 被拒绝 | 检查 GitHub 登录、网络与仓库权限；公共仓库也要确认 URL 未被替换 |
| launchd 未按时执行 | 用 `launchctl print gui/$(id -u)/com.tuski.ai-recovery-backup` 查看状态；检查 plist 的路径和日志 |
| 备份缺少 Notion 内容 | Notion 导出是用户手动放入指定目录的核心副本；检查导出目录与文件权限，不要假设能从聊天自动读取 |
| 自动化重复运行 | 先停下新增调度；比较 ChatGPT 定时任务、launchd 与其他平台的触发器，只保留一个执行源 |
| API 认证失败 | 在官方页面重新授权 / 轮换密钥；密钥保存在密码管理器或钥匙串，仓库只保存模板与说明 |
