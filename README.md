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

Mac 通过 LaunchAgent `com.wangjie.health.daily-review` 每天本地时间 00:00 运行 `fitness_logs/automation/daily_review.sh`，复核刚结束的前一上海自然日，并每15分钟检查失败补跑。任务先同步 `origin/main`，执行确定性重算与校验，再调用本机 Codex CLI 做受限语义复核；只有产生合法实际修改时才提交并非强制推送。脚本会在launchd未继承交互式代理变量时读取已启用的macOS系统HTTP/HTTPS代理。网络操作单次运行内有限重试，失败日期保存在仓库外并跨重启优先补跑；已成功日期在目标记录和复核规则未变化时跳过重复Codex调用。运行日志保存在 `~/Library/Logs/health/`，不进入仓库。

由于 macOS 不允许普通 LaunchAgent 后台读取用户的 `Documents` 目录，实际定时任务使用 `~/Library/Application Support/health-daily-review/repo` 作为专用 checkout；它与本目录共享同一个 GitHub `main`。交互式 Codex 继续使用本目录，并在写入前同步 `main`。
