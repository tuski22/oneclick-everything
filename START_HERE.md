# AI 自动化恢复入口

> 目标：新的 AI 或新的账号只需先读本文件，即可按最小必要范围接管已有项目；不复制全部聊天、不重建已正常运行的服务。

## 先做什么

1. 阅读 [恢复手册](RESTORE_GUIDE.md) 和 [恢复档案总表](recovery/PROJECT_REGISTRY.md)。
2. 打开 Notion 中的「AI跨平台记忆中枢｜总入口」：<https://app.notion.com/p/4155ff23843781ca8bd7f9d117e613b7?pvs=204>。
3. 只读取与当前任务有关的 Notion 原始项目页；把摘要和未经验证的信息分开。
4. 检查目标 Mac mini 上的实际状态。运行中的项目不重装、不重复调度。
5. 缺少授权时依照恢复手册重新连接；禁止把密钥、Cookie、令牌、SSH 私钥或 .env 文件提交到仓库。
6. 完成一个项目后，把结果与日期追加到 `recovery/IMPLEMENTATION_LOG.md`；未验证必须标明“待确认”。

## 权威来源与优先级

| 内容 | 权威来源 | 本仓库的作用 |
|---|---|---|
| 长期偏好、决策、项目背景 | Notion 记忆中枢 | 索引、恢复说明和离线关键副本 |
| 可复用安装脚本 | 本 GitHub 仓库 | 代码与版本历史 |
| 当前运行状态、launchd、凭据位置 | Mac mini | 现场核实；本仓库不保存秘密 |
| 运行密钥、登录会话 | 用户控制的密码管理器 / macOS 钥匙串 | 仅记录恢复位置与重新授权步骤 |

## 当前已盘点项目

见 [项目恢复档案](recovery/PROJECT_REGISTRY.md)。其中只有 OneClick 安装器的仓库内容已由本次盘点核实；其他自动化与本机服务必须在 Mac mini 现场核实后才能标为已恢复。

## 新 AI 的工作约束

- 复用已有代码、配置和调度；先检查后操作。
- 不将 ChatGPT 订阅、对话记录或模型内部状态误当作可迁移资产。
- 不安装本地大模型、新数据库或常驻复杂服务。
- 不以“已备份”代替“可恢复”：每次恢复都需要执行验证步骤。
- 发生项目变更时，同时更新对应恢复档案与实施日志。

## 关键路径

- [给用户的恢复手册](RESTORE_GUIDE.md)
- [项目恢复档案总表](recovery/PROJECT_REGISTRY.md)
- [Mac mini 每日轻量备份说明](recovery/MAC_MINI_LIGHT_BACKUP.md)
- [实施与验证日志](recovery/IMPLEMENTATION_LOG.md)
- [敏感信息边界](recovery/SECRETS_AND_ACCESS.md)
