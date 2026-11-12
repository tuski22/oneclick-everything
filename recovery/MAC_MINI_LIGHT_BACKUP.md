# Mac mini 每日 22:15 轻量备份

此方案不会安装模型、数据库或常驻服务。它使用 macOS 自带的 `launchd`，每天 22:15 将本仓库的恢复资料和一个可选的 Notion 核心导出打包到本机备份目录。

## 备份范围

- 本仓库中的 `START_HERE.md`、`RESTORE_GUIDE.md`、`recovery/` 与版本库状态。
- 可选目录 `~/AI-Recovery-Notion-Export`：由你从 Notion 手动导出的关键页面 / CSV。只放必要核心记忆，不放全部聊天。
- 不备份：密钥、Token、Cookie、.env、macOS 钥匙串内容、全部聊天、缓存。

## 在 Mac mini 上一次性安装

1. 克隆或更新本仓库，并进入根目录。
2. 先预览脚本（不需要填写任何密钥）：
   ```sh
   sed -n '1,240p' recovery/macos/backup-ai-recovery.sh
   ```
3. 创建目录并复制模板：
   ```sh
   mkdir -p "$HOME/AI-Recovery-Backups" "$HOME/AI-Recovery-Notion-Export" "$HOME/Library/LaunchAgents"
   cp recovery/macos/com.tuski.ai-recovery-backup.plist "$HOME/Library/LaunchAgents/"
   ```
4. 在复制前，将 plist 中的 `__REPOSITORY_PATH__` 替换成该仓库的**绝对路径**，例如 `/Users/你的用户名/oneclick-everything`。不要使用 `~`。
5. 加载并立即验证：
   ```sh
   launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.tuski.ai-recovery-backup.plist" 2>/dev/null || true
   launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.tuski.ai-recovery-backup.plist"
   launchctl kickstart -k "gui/$(id -u)/com.tuski.ai-recovery-backup"
   launchctl print "gui/$(id -u)/com.tuski.ai-recovery-backup"
   ```
6. 查看 `$HOME/Library/Logs/ai-recovery-backup.log` 与 `$HOME/AI-Recovery-Backups`。确认出现一个 `.tar.gz` 文件和对应 `.sha256` 文件。

## 恢复或停用

- 立即执行一次：`/bin/sh /绝对路径/oneclick-everything/recovery/macos/backup-ai-recovery.sh /绝对路径/oneclick-everything`
- 停用：`launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.tuski.ai-recovery-backup.plist"`
- 恢复某次备份：先执行 `shasum -a 256 -c 文件名.sha256`，成功后解压到空目录，阅读其中的 START_HERE.md。

注意：此电脑当前不是 Mac mini，因此本次实施只能提供并核对该配置文件；加载、执行和验证必须在 Mac mini 登录用户会话中完成。
