# ChatGPT × Codex × GitHub 健身记录工作流

## 目标

本项目使用 GitHub 作为 ChatGPT 与 Codex 之间的共享事实源，实现：

- 白天在 iPhone 上直接向 ChatGPT 发送饮食、体重、训练、照片和更正；
- ChatGPT 立即根据仓库规则、常用食物库和当天记录给出热量/蛋白质等即时反馈；
- ChatGPT 将结构化结果写回 GitHub `main`；
- 晚上 Mac 上的 Codex 通过 `git pull` 读取白天记录，负责正式复核、重算、校验和复杂维护；
- 不要求用户晚上重新口述白天已经记录过的信息。

GitHub `main` 是 ChatGPT 与 Codex 的共享同步层；Mac 本地仓库是 Codex 的工作副本。所有正式规则与历史记录以仓库文件为准，不依赖单个聊天会话记忆。

## 角色分工

### ChatGPT：白天实时记录端

ChatGPT 负责：

1. 读取最新 `main`；
2. 按规则读取必要上下文；
3. 接收用户即时输入：食物、照片、体重、训练、更正；
4. 判断是新增、重复消息还是更正；
5. 使用现有同款、标签、照片或一般估算规则计算；
6. 立即向用户反馈本次与当天截至目前的关键结果；
7. 将结构化记录写入当天 daily JSON；
8. 保留稳定 id、估算依据、不确定性和 corrections；
9. 修改后提交并推送到 GitHub。

ChatGPT 不应要求用户重复提供仓库中已有的常用食物数据、历史同款或已经持久化的更正。

### Codex：Mac 端复核与维护端

Codex 负责：

1. `git pull --rebase origin main` 获取 ChatGPT 白天写入的最新记录；
2. 按项目规则重新读取 README、AGENTS、handoff、计划、food catalog 与目标日 JSON；
3. 对当天数据运行正式的 `recalculate`、`validate`、`report` 与 `jq empty`；
4. 发现问题时修正源条目并保留 corrections/basis/uncertainty；
5. 处理复杂规则、schema、模板、工具代码、测试与历史维护；
6. 有实际修改时 commit 并 push；
7. 不要求用户重新口述已存在于 GitHub 的白天记录。

### GitHub：共享事实源与同步层

GitHub 负责：

- 保存规则、计划、food catalog、daily JSON、handoff 和工具；
- 让 ChatGPT 与 Codex 读取同一份最新状态；
- 提供版本历史、diff 与回滚能力；
- 避免依赖聊天历史作为唯一信息来源。

## 开始任何记录前的读取顺序

无论由 ChatGPT 还是 Codex 操作，先按顺序读取：

1. 根目录 `README.md`
2. `fitness_logs/AGENTS.md`
3. `fitness_logs/README.md`
4. `fitness_logs/handoff_summary.md`
5. `fitness_logs/current_plan.json`
6. `fitness_logs/food_catalog.json`
7. 目标日 `fitness_logs/daily/YYYY-MM/YYYY-MM-DD.json`（若已存在）

日期按 `Asia/Shanghai` 处理；用户明确指定补报日期时使用用户指定日期。

## 白天 ChatGPT 实时记录流程

用户可以自然输入，例如：

> 午饭芥兰牛肉饭，全部吃完。

或：

> 刚才那顿米饭其实剩了三分之一，而且油比较多。

或直接发照片。

ChatGPT 应执行：

1. 读取最新 `main` 与当天 JSON；
2. 检查相关同款是否在 `food_catalog.json` 或历史已确认口径中；
3. 按资料优先级处理：
   - 本次实际食用说明和清晰标签；
   - 已确认同款；
   - 匹配食物数据；
   - 照片与一般估算；
4. 判断本次输入属于：
   - 新增真实条目；
   - 重复消息；
   - 对已有条目的更正；
5. 仅记录实际吃下部分；剩饭、骨头、未喝汤等应扣除，入口附着油、糖、酱汁按规则合理计入；
6. 更新当天 JSON；
7. 保证稳定且唯一的 `id` / `event_id`；
8. 更正时修改原条目，并将旧值、新值、时间与原因记录在 `corrections`；
9. 不把计划/未吃内容计入总量；
10. 向用户立即反馈：
    - 本次基础/记账 kcal（适用时）；
    - 蛋白质等主要宏量；
    - 当天截至目前累计；
    - 重要不确定项；
11. 提交并推送 GitHub。

即时反馈不应假装具有不存在的精度。照片估算、用油余量和缺口均需遵守现有 README 口径。

## 更正规则

用户后续补充应优先视为对原条目的更正，而不是新增一份。

例如：

> 汤没喝，只吃了水饺。

应修改原有水饺/调味相关条目，保留 corrections，而不是额外添加一份“未喝汤”。

重复发送同一信息不新增；只有用户明确表示“又吃了一份”才创建新 id。

## 常用食物与配料知识

`fitness_logs/food_catalog.json` 是机器可读常用食物库。

ChatGPT 与 Codex 应优先复用已确认同款，避免用户反复解释：

- 固定规格；
- 份量；
- 标签热量；
- 蛋白质/脂肪/碳水；
- 已存在的余量与估算依据。

实际本次标签或实际食用量始终优先于 catalog 默认值。

Catalog 更新不能反向改写历史已封账记录。

## 当天累计与正式计算

`daily_summary` 不应靠记忆手写。

ChatGPT 可以在白天根据当天源条目给出即时累计，但正式结构仍遵循项目 schema。

Codex 晚上必须运行：

```bash
python3 fitness_logs/record_tools.py recalculate fitness_logs/daily/YYYY-MM/YYYY-MM-DD.json
python3 fitness_logs/record_tools.py validate fitness_logs/daily/YYYY-MM/YYYY-MM-DD.json
python3 fitness_logs/record_tools.py report fitness_logs/daily/YYYY-MM/YYYY-MM-DD.json
jq empty fitness_logs/daily/YYYY-MM/YYYY-MM-DD.json
```

如果 ChatGPT 白天即时估算与 `record_tools.py` 正式结果不同，以：

1. 用户明确更正；
2. 源条目真实数据；
3. 当前仓库规则；
4. `record_tools.py` 重算结果

为准。

不要为了匹配 ChatGPT 之前口头回复的数字而篡改源数据。

## Codex 晚间接手流程

在 Mac 本地仓库执行：

```bash
git status
```

如果没有需要用户确认的未提交本地修改：

```bash
git pull --rebase origin main
```

然后按本文“开始任何记录前的读取顺序”读取文件，并检查当天 JSON：

- `intake_entries`
- `exercise_entries`
- `morning_weight_kg`
- `corrections`
- `food_coverage`
- `training_coverage`
- `record_status`
- `missing_sections`
- `daily_summary`

重点检查：

- 重复食物；
- 更正是否误记成新增；
- stable id / event_id；
- food catalog 使用是否正确；
- 标签、照片与用户说明的优先级；
- 剩饭、骨头、未喝汤是否已扣除；
- 辣椒油、酱汁是否只计算入口部分；
- 油、调味或子成分是否重复计入；
- 当天累计是否正确。

完成 `recalculate`、`validate`、`report`、`jq empty` 后，如有实际修改：

```bash
git add fitness_logs/
git commit -m "fitness: review YYYY-MM-DD logs"
git push origin main
```

若无修改，不创建空提交。

## 每日自动复核

Mac 上的统一入口是 `fitness_logs/automation/daily_review.sh`，由 LaunchAgent `com.wangjie.health.daily-review` 每天本地时间 00:00 启动。脚本用 `Asia/Shanghai` 计算刚结束的前一自然日；例如 09-18 00:00 处理 09-17，不处理刚开始的 09-18。

自动任务分两层：

1. 阶段A确定性维护：要求干净 `main`，执行 `fetch`、`pull --rebase`、目标文件存在性检查、`recalculate`、`validate`、`report` 和 `jq empty`。
2. 阶段B语义复核：使用本机实际安装的 Codex CLI 非交互命令 `codex exec --ephemeral --sandbox workspace-write --ask-for-approval never`，按 `automation/daily_codex_prompt.md` 读取规则和目标日。它可修正已有事实能证明的重复、累计、状态和更正应用错误，不得补造用户事实。阶段B结束后再次运行阶段A校验。

任务以原子目录锁避免并发，完整日志位于 `~/Library/Logs/health/`。工作区已有修改、pull冲突、Codex失败、验证失败或远端竞态都会停止任务。只有 `fitness_logs/` 下存在合法实际修改时才提交 `fitness: automated review YYYY-MM-DD` 并普通推送；无变化时不产生空提交。

若 macOS 隐私保护阻止普通 LaunchAgent 读取 `Documents`，本机安装使用 `~/Library/Application Support/health-daily-review/repo` 专用 checkout，并通过 `HEALTH_REPO_ROOT` 传给同一版本化脚本。两个本地工作副本只通过 GitHub `main` 交换已提交事实；自动任务不会复制、覆盖或暂存交互工作副本的未提交内容。

## 并发与冲突处理

为了避免 ChatGPT 与 Codex 同时修改同一文件：

- 每次写之前都读取最新 `main`；
- ChatGPT 写入后立即 push；
- Codex 开始复核前先 pull；
- 如果发现远端在本次操作期间发生变化，先重新读取目标文件并合并真实源条目，再写入；
- 不用旧副本覆盖远端较新记录；
- 冲突时优先保留用户最新明确更正与已有 corrections 历史。

## 规则、schema 与工具变更

若 Codex 修改：

- 计算逻辑；
- schema；
- 模板；
- food catalog 规则；
- 记录口径；

必须同步更新相关：

- `fitness_logs/README.md`
- `fitness_logs/AGENTS.md`
- `fitness_logs/handoff_summary.md`
- templates
- `record_tools.py`
- tests

并运行回归测试。

ChatGPT 白天记录端一般不修改 schema 或核心计算工具；复杂维护交给 Codex。

## 用户体验原则

用户不需要理解 JSON 或重复做人工交接。

理想交互是：

1. 用户在 iPhone 发一顿饭、照片、训练或更正；
2. ChatGPT 立即给出合理的 kcal / 蛋白质 / 当天累计反馈；
3. 同一轮将记录持久化到 GitHub；
4. 晚上 Codex 直接从 GitHub 读取并复核；
5. 用户不再重复告诉 Codex 白天吃过什么。

## 给 Codex 的最短接手指令

以后用户可以直接对 Codex 说：

> 读取 health 仓库最新 main，按 `fitness_logs/CHATGPT_CODEX_WORKFLOW.md` 接手今天的记录。不要让我重新口述白天已经写入 GitHub 的内容。完成 recalculate、validate、report 和 jq 校验；有问题直接修正并保留 corrections；有实际修改再 commit/push，最后简洁汇报今天累计、修正项和校验结果。
