# 健身记录交接摘要
更新时间：2026-11-07 上午（空腹88.65kg；早餐已记录3项，今日未封账）

## 2026-11-07 进行中
- 今日新建日JSON：record_status=open、food_log_closed=false、food_coverage=partial、training_status=unknown、training_coverage=unknown；不能把未报告的训练或其余餐食记为0，当前不能计算全天最终热量缺口。
- **晨起空腹88.65kg**，较昨天86.90kg上升1.75kg。昨天自由饮食且力量＋室内步行两段训练，短期变化可能包含糖原、水分、钠和胃肠内容物，不直接解释成脂肪增加或要求补偿运动。
- **早餐真实吃下3项**：南瓜子6.1g（历史标签2579kJ/100g，37.60kcal/P1.90）；烤土豆**155g**（用户最初报140g，随后明确更正为155g，只记155g，沿历史无油烤熟熟重每100g93kcal，144.15kcal/P3.88）；鸡小胸一包暂沿历史100g/包及相近产品每100g527kJ/P28.6，125.96kcal/P28.60。
- **早餐累计307.71kcal、P34.38g/F4.23g/C33.37g**；烤土豆是否烤后熟重、是否额外用油尚未明确，鸡小胸本包规格及标签未核实。后续有当次营养表或实际情况按原id更正，不重复新增140g土豆。
- 按今天体重估BMR**1837.75kcal**，保留历史动态运动×0.75算法；今天仅早餐已报告，全天其他食物和训练待实际报告，不自行断定休息日。

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
