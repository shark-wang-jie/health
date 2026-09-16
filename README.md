# health

记录日常饮食、体重和训练，用于 ChatGPT 与 Codex 共享同一份数据。

## 入口

- `fitness_logs/README.md`：记录规则和计算口径
- `fitness_logs/handoff_summary.md`：当前交接摘要
- `fitness_logs/current_plan.json`：当前饮食与训练计划
- `fitness_logs/daily/`：每日源数据
- `fitness_logs/record_tools.py`：日志新建、重算、校验和回顾工具
- `handoffs/`：按日期保存的交接快照

## 协作约定

修改记录前先阅读 `fitness_logs/AGENTS.md`、`fitness_logs/README.md`和当前交接摘要。每次修改前同步最新的 `main`，修改后提交并推送，避免 ChatGPT 和 Codex 同时改动同一文件。

项目中的部分历史文件保留了本机绝对路径 `/Users/wangjie/Documents/health/fitness_logs/`。在本仓库中阅读时，将该前缀对应为 `fitness_logs/`。
