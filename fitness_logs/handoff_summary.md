# 健身记录交接摘要
更新时间：2026-11-08 17:08北京时间（练后实吃蒸饺270g、猪肝100g、鸡小胸66g，今日仍未封账）

## 2026-11-08 进行中
- 空腹体重**88.20kg**，较11月7日88.65kg下降0.45kg；单日变化不能直接认定为脂肪减少。
- 上午实际吃南瓜子5.5g（33.90kcal）、鸡小胸1包（暂按历史100g/包，125.96kcal）和荞麦薄皮素包荠菜鸡蛋1整包500g（1021.75kcal）。早先报告的烤土豆155g实际**没吃**，原条目status=not_eaten，不能计入。
- 加餐酸奶135g暂沿历史大桶原味发酵乳每100g348kJ/P4/F5/C5.6估112.28kcal；具体品牌与标签未核实。
- 练前实吃卤猪肝50g（82.10kcal，P13.15g），按150g原盒装标签换算。
- **练后已吃**小白菜蒸饺1整包270g（按包装每100g745kJ、P7.5/F6.5/C22.2换算，480.76kcal/P20.25g）、此前同一盒**剩余卤猪肝100g**（164.20kcal/P26.30g）、鸡小胸**66g**（按历史相近即食鸡胸肉每100g527kJ/P28.6/F1.1/C0暂估，83.13kcal/P18.88g）。练后合计728.09kcal/P65.43g。卤猪肝全天50g＋100g=150g整盒，**不可再重复计入剩余猪肝**。
- **截至目前8项实吃、1项烤土豆未吃；摄入累计2104.08kcal、蛋白质150.79g、脂肪88.56g、碳水173.91g。** 今日蛋白质已处于实用目标140–180g范围内，酸奶和鸡胸等品牌口径若有新标签仍允许校正。
- 用户说练后已吃，**确认今天已训练**，training_status=reported_training，但目前没有运动项目、训练时长、当次动态千卡或是否全部完成的数据，training_coverage=partial、exercise_entries暂空；不得把没有记录的训练能量当成0，也不得假称运动消耗已核实。
- 当前record_status=open、food_log_closed=false、food_coverage=partial，**今日还未封账、不计算全天最终热量缺口**。今日TDEE模型中因无训练动态千卡而只显示基础活动暂估，不可视为完整全天运动消耗。基础BMR1833.25kcal；坚持BMR×1.2＋核准Apple Watch训练动态×0.75口径。
- 近期用户曾报告仅特定姿势按压髌骨附近轻微疼痛，正常活动无痛；不据此推断今天训练类型或疼痛变化。

## 2026-11-07 已封账
- 用户明确今天饮食结束并要求封账，原计划晚餐鸡小胸1包**实际没吃**，从planned原位更正为not_eaten，不纳入当天总量。早餐及练后分别实吃的另外两包鸡小胸不变。
- **全天已报告实际摄入共9项：2021.66kcal，蛋白质132.94g、脂肪70.06g、碳水214.68g。** 早晨空腹88.65kg，较11月6日86.90kg+1.75kg；前一天自由饮食和训练后单日变化不等于脂肪增长。
- 早餐：南瓜子6.1g、无油烤熟土豆155g（原报140g已更正）、鸡小胸一包暂按100g。练后：火龙果带皮433g（暂按65%可食果肉）、无油烤熟土豆170g、荞麦薄皮素包250g、野人日记历史同款鸡肉脆骨丸一包200g、鸡小胸另1包。傍晚又吃了素包剩余250g。**素包一袋净重500g，全天确实吃完，分两次各250g，合计约1021.75kcal。**
- 训练完成、确认两段：Apple Health力量13:31–14:35，原始workout能量442.17kcal；室内步行14:38–15:43，4.09公里，原始能量711.16kcal。**本次未提供Apple Fitness动态千卡截图，两条运动active_kcal=null**；不可将API原始能量或全天活动圆环直接视为核准动态值。
- **日JSON状态record_status=final，food_log_closed=true，training_status=reported_training，training_coverage=confirmed_complete，food_coverage=partial。** 用户确认当天饮食结束并封账，但先前仅报告早餐及训练后/傍晚进食，未逐餐核实午餐是否存在，按仓库规则不自动宣称所有餐食完整；同时训练动态千卡未核准，**completed_day_estimated_deficit_kcal=null，不计算全天最终热量缺口**。后续若有确切资料可原位更正。
- 鸡小胸单包规格及营养标签沿历史100g参考估算；土豆沿无油熟重，带皮火龙果按65%可食比例，属于已有估算口径。今日记录已结束，不再把没吃的最后一包鸡小胸加回。

## 2026-11-06 最新封账日
- 用户今晚确认训练已结束、下午至晚上饮食不再记录，明确要求封账。record_status=final，food_log_closed=true，food_coverage=partial，training_status=reported_training，training_coverage=confirmed_complete。
- 空腹86.90kg。当天只保留先前确认的6项实际摄入，累计1519.96kcal、P113.04g、F52.26g、C145.45g；这只是部分饮食，不是全天摄入。下午练前荞麦锅巴45g仍为planned，未确认最终吃下，不计入。
- 下午至晚间用户自由进食且不记录具体食物、数量或热量。未记录不等于0，无须追问或补造餐食。
- Apple Watch截图和Apple Health相互印证恰好两段训练：18:21–19:32传统力量70分34秒，动态635/总760kcal，均心126；19:33–20:35室内步行62分16秒、4.08km，动态741/总856kcal，均心143。
- 两段动态合计1376kcal，按0.75折算1032kcal。基础BMR1820.25kcal，模型总消耗3216.30kcal仅作为消耗模型，不可用来减部分饮食1519.96kcal推出全天热量缺口。completed_day_estimated_deficit_kcal=null，energy_balance_scope=provisional_recorded_balance，energy_estimate_provisional=true。
- 今日饮食与训练归档完成，不把自由饮食视作需要补偿的训练原因；明天正常吃、正常休息。

## 2026-11-05 已封账
晨起87.45kg，11项摄入2182.60kcal，P187.67/F66.08/C207.61。力量和室内单车训练记录能量合计957.19kcal，×0.75折算717.89kcal；部分能量口径及食品标签仍有不确定性。日JSON是事实来源。

## 记录规则
仓库 shark-wang-jie/health，main分支。每日文件fitness_logs/daily/YYYY-MM/YYYY-MM-DD.json。严格使用Asia/Shanghai日期、实际吃下量，重复消息不重记；标签更正替换原id。当前模型BMR×1.2＋Apple Watch训练动态千卡×0.75，不重复加全天活动圆环。当天未确认结束时不把模型差额称为最终热量缺口。一次业务变更涉及多文件应使用一个原子commit并回读验证。
完整细节参考fitness_logs/README.md、AGENTS.md、current_plan.json、food_catalog.json。旧交接详细历史已保存在fitness_logs/reference/handoff_legacy_2026-11-06.md，同时可通过Git历史追溯。
