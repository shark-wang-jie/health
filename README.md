# health

记录日常饮食、体重和训练，用于 ChatGPT 与 Codex 共享同一份数据。

## 入口

- `fitness_logs/README.md`：记录规则和计算口径
- `fitness_logs/handoff_summary.md`：当前交接摘要
- `fitness_logs/current_plan.json`：当前饮食与训练计划
- `fitness_logs/daily/`：每日源数据
- `fitness_logs/record_tools.py`：日志新建、重算、校验和回顾工具
- `fitness_logs/automation/`：每日确定性维护、Codex 语义复核和 LaunchAgent 模板
- `handoffs/`：按日期保存的交接快照

## 协作约定

修改记录前先阅读 `fitness_logs/AGENTS.md`、`fitness_logs/README.md`和当前交接摘要。每次修改前同步最新的 `main`，修改后提交并推送，避免 ChatGPT 和 Codex 同时改动同一文件。

项目中的部分历史文件保留了本机绝对路径 `/Users/wangjie/Documents/health/fitness_logs/`。在本仓库中阅读时，将该前缀对应为 `fitness_logs/`。

## 每日自动复核

Mac 通过 LaunchAgent `com.wangjie.health.daily-review` 每天本地时间 00:00 运行 `fitness_logs/automation/daily_review_watchdog.sh`，并每15分钟检查失败补跑。看门狗按故障类别退避和熔断，再调用`daily_review.sh`同步`origin/main`、执行确定性重算与校验以及受限Codex语义复核。确定性校验失败时，Codex只可在隔离副本中修复目标日期JSON，重新通过全部检查后才能提交。运行状态保存在仓库外的`state/status/`与`watchdog.json`，日志保存在`~/Library/Logs/health/`。

脚本自动发现当前 ChatGPT 应用内的 Codex CLI，同时兼容旧应用路径和系统 `PATH`；`HEALTH_CODEX_BIN` 可显式覆盖。应用升级改变CLI目录时，不再需要手工修改脚本。

由于 macOS 不允许普通 LaunchAgent 后台读取用户的 `Documents` 目录，实际定时任务使用 `~/Library/Application Support/health-daily-review/repo` 作为专用 checkout；它与本目录共享同一个 GitHub `main`。交互式 Codex 继续使用本目录，并在写入前同步 `main`。

每次重算与AI复核在 state/runs/ 下独立临时clone执行，失败副本保留供审计，下一次从干净主副本重新复核；验证后的提交先快进保存到主副本再推送，以便断网恢复。根据完成状态补齐遗漏日期队列，逐次处理最早未完成日期；不创建虚构日记录。
