# 健身记录交接摘要
更新时间：2026-11-07 下午（两段训练已完成，练后4项新增，全天饮食未封账）

## 2026-11-07 进行中
- 用户今日空腹88.65kg，较11月6日86.90kg上升1.75kg；前日自由饮食与训练后短期变化可能包含水分和糖原，不能当作脂肪变化。上午早餐三项：南瓜子6.1g、无油烤熟土豆155g（原报140g已更正，不重复）、鸡小胸一包暂按100g。
- **练后新增4项实际食物**：带皮火龙果433g（65%出肉率估281.45g可食果肉，约154.80kcal）；烤土豆170g（暂按无油熟重158.10kcal）；荞麦薄皮素包荠菜鸡蛋一袋（包装图确认每100g855kJ/P7.3/F10.6/C19.9/钠420，市场同名野人日记500g15只装，**本袋规格未实物确认，暂按500g估1021.75kcal**）；野人日记鸡肉脆骨丸一包（沿2026-10-21已核验200g整袋530kJ/100g，估253.35kcal）。
- **截至练后累计7项：1895.70kcal、蛋白质104.34g、脂肪68.96g、碳水214.68g**；素包袋重是最重要待确认项，需按实际包装规格/实吃数量原位更正；无其它餐食可自行补造。今日record_status=open、food_coverage=partial，不计算最终热量缺口。
- **今天训练结束，Apple Health恰好两段**：传统力量训练13:31–14:35，约64分35秒，workout原始total_energy_kcal442.17；室内步行14:38–15:43，约64分59秒、约4.09km，原始total_energy_kcal711.16。两段原始估值合计1153.33kcal；**未与Fitness截图的动态千卡核实**，两条exercise_entries保留active_kcal=null，不拿总千卡或全天活动圆环直接乘0.75。training_status=reported_training、training_coverage=confirmed_complete，训练已经报完。
- BMR1837.75kcal，现有TDEE模型按BMR×1.2＋已核实动态×0.75；当前训练动态值缺失，日模型只含基础部分，不等于全天实测消耗。昨天较大训练与自由饮食不要求惩罚性节食或额外训练。

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
