# 健身记录交接摘要
更新时间：2026-11-07 傍晚（剩余素包250g已吃，鸡小胸晚餐计划仍未吃）

## 2026-11-07 进行中
- 空腹88.65kg，较11月6日86.90kg+1.75kg；前一日自由饮食和运动后波动可含水分、糖原、胃肠内容物，不直接视作脂肪增长。
- 早餐已吃南瓜子6.1g、无油烤熟土豆155g（原报140g后更正，仅记155g）、鸡小胸一包暂按历史100g。
- 练后已吃火龙果433g带皮（按65%果肉约281.45g）、无油烤土豆170g、荞麦薄皮素包250g、历史200g鸡肉脆骨丸一包、鸡小胸另1包暂按100g。荞麦薄皮素包包装营养标签每100g855kJ/P7.3/F10.6/C19.9/钠420mg，整袋净含量500g。
- **11月7日17:42用户确认剩余250g素包也吃完**。原计划条目改为consumed，不新增另一条；今天素包500g全袋已吃完，分为练后250g和傍晚250g，每半袋约510.87kcal。
- **当前已确认9项摄入：2021.66kcal、P132.94g/F70.06g/C214.68g**（已含整袋素包500g和早餐、练后各一包鸡小胸）。
- 另一包鸡小胸仍只是晚间计划，status=planned，**尚未确认吃下，不计入当前摄入**。若以后确认实吃，再把现有计划条目转已吃，不重复新增；当日仍open，food_coverage=partial，不封账。
- 用户今天训练已全部结束，Apple Health两段：力量13:31–14:35（接口workout原始442.17kcal），室内步行14:38–15:43约4.09km（接口原始711.16kcal）；未核对截图动态千卡，因此active_kcal=null，不将原始数值冒充动态能量，暂不计算全天最终热量缺口。training_status=reported_training，training_coverage=confirmed_complete。
- 早餐鸡小胸与练后鸡小胸均按历史相近品估值，土豆按历史无油熟重口径，火龙果带皮按65%可食率，均保留相应估算不确定性。

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
