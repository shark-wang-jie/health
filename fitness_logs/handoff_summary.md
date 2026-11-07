# 健身记录交接摘要
更新时间：2026-11-07 下午（练后素包实吃半袋250g、鸡小胸1包，晚餐计划未吃）

## 2026-11-07 进行中
- 晨起空腹88.65kg；较11月6日86.90kg增加1.75kg，前日自由饮食及高训练量后的短期波动不能直接视作脂肪增加。
- 早餐已吃三项：南瓜子6.1g、无油烤熟土豆**155g**（原报140g后已更正，不重复）、鸡小胸一包暂按100g。早餐累计307.71kcal。
- 练后确实吃：带皮火龙果433g（按65%出肉率估可食281.45g）、无油烤土豆170g、**荞麦薄皮素包荠菜鸡蛋半袋250g**、历史同款200g魔芋鸡肉脆骨丸一包、**鸡小胸另1包**（暂按100g）。
- **重要更正**：用户确认素包包装规格为500g，但练后只吃一半250g；每100g包装标签855kJ/P7.3/F10.6/C19.9/钠420mg，250g实吃记**510.87kcal、P18.25g/F26.5g/C49.75g**。之前把整袋500g视为练后已吃是错误的，现已原位更正，不重复记。
- **截至目前实际累计8项：1510.78kcal，蛋白质114.69g、脂肪43.56g、碳水164.93g**。早餐鸡小胸1包和练后1包是两包不同的实际摄入。
- **晚餐只是计划**：素包剩余半袋250g（约510.87kcal），另1包鸡小胸（暂按100g，约125.96kcal）；目前都未确认吃下，状态planned，不加入摄入。若之后确认两样都吃完，预计全天2147.61kcal，P161.54g/F71.16g/C214.68g；只在实际确认后改原计划条目的状态，禁止再次新增。
- 训练用户已表示结束：Apple Health两段，传统力量13:31–14:35（原始workout能量442.17kcal），室内步行14:38–15:43约4.09公里（原始workout能量711.16kcal）。尚未核对Apple Fitness动态千卡，原始值不直接当作动态消耗加到模型；training_status=reported_training、training_coverage=confirmed_complete。
- 今天record_status=open、food_coverage=partial，晚餐与全天饮食是否结束待用户实际报告，不封账、不计算全天最终热量缺口。两包鸡小胸的规格均按历史100g参考值暂估，素包标签已核实。

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
