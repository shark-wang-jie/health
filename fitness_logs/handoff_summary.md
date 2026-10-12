# 健身记录交接摘要

更新时间：2026-10-12 晚（Asia/Shanghai）。用于新对话接续体重、饮食及训练记录。**正式数据源是 GitHub 每日 JSON，而非本摘要或聊天里曾给出的暂算值**。日记录、计划、规则若后来有变化，应先读取最新版本。

## 工作位置及操作

- GitHub 仓库：`shark-wang-jie/health`，分支 `main`；每日记录：`fitness_logs/daily/YYYY-MM/YYYY-MM-DD.json`。
- 规则：`fitness_logs/README.md`、`fitness_logs/AGENTS.md`；目标：`fitness_logs/current_plan.json`；常用食物：`fitness_logs/food_catalog.json`；本摘要：`fitness_logs/handoff_summary.md`。
- 用户的 Mac 上曾使用路径 `/Users/wangjie/Documents/health/fitness_logs/handoff_summary.md`，但远端 GitHub 更新不等于本机文件即时更新；本机需要同步。
- 用户报餐食/体重/训练后，优先读目标日 JSON、同款食物口径和最新 SHA，再新增唯一条目或原位更正；不要因重复发图或问热量而重复记账。用户明确说“又吃了”才另增一份。更新 `daily_summary`，确认 GitHub commit 成功后才说“已同步”。
- 日期严格按 Asia/Shanghai。只算**实际吃下**的食物；未报告与没吃不是一回事。用户明确更正优先；照片/本次营养标签优先旧估算。若只询问建议，不把建议的食物算成已吃。

## 当前进行中：2026-10-12

- **状态：open；饮食 coverage=partial；力量训练已报告一段，training_status=reported_training、training_coverage=partial**。用户尚未说“今天饮食/训练全部结束”，所以不得封账或称暂算差额为最终缺口。
- 早上空腹体重 **89.20 kg**（10-11 为 88.85 kg；单日升 0.35 kg 不代表脂肪增加）。男，27岁，173 cm；今日估算 BMR **1843.25 kcal**。
- 已摄入：
  1. 早餐南瓜子 **10g**：**61.64 kcal**，P3.12/F4.88/C0.83。
  2. 早餐六号肠 **1根 150g**：**263.50 kcal**，P20.85/F13.65/C14.25。
  3. 午餐沙县鸡腿饭：暂沿用**两只去皮鸡腿＋米饭＋炒白菜＋卤蛋全吃、不吃土豆丝**，基础 **885**、含餐馆油余量记账 **973.5 kcal**，P70.5/F36.83/C91，**等待确认本次配菜与去皮是否一致**。
  4. 练后海鲜四重奏饭团 **105g**：标签每100g 404kJ、P2.2/F3.8/C13.3；实际 **101.39 kcal**，P2.31/F3.99/C13.97。
  5. 练后外星人电解质饮料 **600mL**：标签每100mL **80kJ、碳水4.7g、糖4.2g、钠55mg**；整瓶 **114.72 kcal**、C28.2g、糖25.2g、钠330mg。**此条已写入当日 GitHub JSON，不要重复新增**。
- **目前已记账摄入：1514.75 kcal；P96.78g／F59.35g／C148.25g**。基础摄入 1426.25 kcal，差额 88.5 kcal 来自午餐油量记账余量。已记录5条摄入。
- 当天力量训练：**17:34–18:42，1:08:38**；Apple Watch **动态556 kcal**、总679 kcal、平均心率123；按规则折算 **417 kcal**。未确认是否还有其他训练。
- 基于**目前一段训练**计算的模型 TDEE **2628.9 kcal**，TDEE 减截至目前摄入约 **1114.15 kcal**，**仅为开放日暂算差额，绝非最终全天缺口**。
- 接下来主要待办：继续记录10-12任何未报/之后吃的正餐与零食；确认沙县鸡腿饭实际配菜、鸡腿去皮情况；确认当天是否还有训练、饮食/训练何时结束。别为凑目标强行限制饮食。

## 最近一天及背景

- **10-11 空腹 88.85kg，已标记 `record_status=final`**；记录摄入约 **1833 kcal**，P162.45/F44.02/C219.61；力量和室内步行 Apple Health 训练动态合计 **1196.30 kcal**，折算 **897.23 kcal**，模型 TDEE **3104.93 kcal**。曾口头提到模型差约1272 kcal，但自动复核后的 JSON 将 `completed_day_estimated_deficit_kcal` 设为 null 且警示资料不确定，因此**不把1272当作已核验的最终全天缺口**。详见该日 JSON。
- **10-10 空腹90.50kg**；已记录摄入约1735 kcal，P151.30/F72.85/C118.55；训练动态约1058.48 kcal，模型 TDEE 约3021 kcal。过去几天估算差额偏大，注意恢复，不鼓励追求过大热量缺口。
- 10-09 有未记录的晚宴：饮食虽结束但覆盖不完整，不输出完整日缺口。历史更正不要由本摘要反向覆盖；查对应日文件。
- 体重正常受水分、盐分、糖原、胃肠内容物、运动后恢复影响，优先看多周同条件趋势。

## 当前计划和计算方法

- `current_plan.json` 版本 **2026-09-08-v3.2**，男27岁、173cm。休息日建议摄入约**1800 kcal**，训练日**1900–2000 kcal**；长期参考日均缺口**400–600 kcal**。若当日训练量较大，不应机械压低摄入来制造超大缺口。
- 蛋白质参考目标170g，实用区间**140–180g**，无需每天硬凑；碳水150–180g仅作旧计划参考，**不是硬上限**。兼顾脂肪、蔬菜、水果与纤维。
- `BMR = 10×体重kg + 6.25×173 − 5×27 + 5`；`TDEE = BMR×1.2 + 已确认的每次训练动态 kcal×0.75`。系数都是模型假设，不是实测。
- Apple Health workout 记录中的 `total_energy_kcal` 已与 Apple Watch **“动态千卡”**截图核对一致（虽字段命名有歧义）；**不要把截图“总千卡数”当动态消耗，也不能叠加活动圆环**。同一次运动来自不同设备不得重复相加。
- 食物分 `kcal_base_estimate`（基础估算）与 `kcal_booked`（含合理余量的记账值）；如沙县饭 885/973.5。宏量不因热量上浮而一律等比例增加。报告保留范围与不确定性。
- `record_status`、`food_log_closed`、`food_coverage`、`training_status`、`training_coverage` 必须与事实一致。`estimated_deficit_kcal` 在开放日只是兼容暂算，**只有关键资料完整时 `completed_day_estimated_deficit_kcal` 才可作为完整日模型差额**。

## 常见食物口径（同款/同规格才沿用）

- 南瓜子每100g 2579kJ，P31.2/F48.8/C8.3；**10g约61.64 kcal**。
- 六号肠1根150g，标签每100g 735kJ、P13.9/F9.1/C9.5；整根 **263.50 kcal，P20.85g**。
- 沙县鸡腿饭：两只去皮鸡腿、饭、炒白菜、卤蛋、不吃土豆丝；**基础885／记账973.5 kcal，P70.5g**。是否同款需确认。
- 无油烤土豆每100g **93 kcal、P2.5/F0.1/C21.2**；若另加油则须另算。
- 馒头100g 1058kJ ≈ **252.87 kcal**，P7.4/F0.9/C52.9。
- 全蛋1个 **72 kcal、P6.3/F4.71/C1.44**；蛋清1个约 **17 kcal、P3.6**。建议吃但未吃不计。
- 盒马卤鸭腿每盒2只共240g（含骨皮）；用户10-11去皮去骨的每只曾**估145 kcal、P20g**，为可食重量估算，不可直接用毛重。
- 盒马卤鸡腿1盒2只、170g：包装满量曾计约249 kcal；若明确去皮再修正。
- 外星人电解质饮料600mL：**114.72 kcal、C28.2g**；非零卡电解质水。

## 自动维护、月总结与规范

- 本机自动化配置以仓库 `README.md` 为准：每日 `automation/daily_review_watchdog.sh` 配合 `daily_review.sh`、本地 Codex 进行前一天记录重算、校验、复核、同步；失败重试并保存状态。**仓库存在配置不等于本次已验证 Mac 服务实时运行**。
- 月总结有 `automation/monthly_review.py` 与 `com.wangjie.health.monthly-review` LaunchAgent，预定**每月1日00:15、每15分钟补查**。只处理已结束、有记录且尚无月总结的月份；不覆盖已有总结，不会凭空补未报数据。
- 本机手动检查指令：`python3 fitness_logs/record_tools.py recalculate fitness_logs/daily/YYYY-MM/YYYY-MM-DD.json`、`validate`、`report`；已结束月份：`python3 fitness_logs/build_monthly_summary.py YYYY-MM`。不要未经请求重生成旧月总结。
- 用户喜欢**简洁中文**日报：先本次新食物/训练，再今日累计 kcal、蛋白质P、脂肪F、碳水C、GitHub commit。未确认的一件重要细节可简短追问；不要要求每天重复所有信息。
- 当天饮食明确结束才关闭日志；后续补报可以按日期更正，**不跨日挪记、不把提议当实际进食**。

如与每日 JSON 或较新的 `README.md/current_plan.json/food_catalog.json` 不一致，以正式数据与用户最新更正为准。
