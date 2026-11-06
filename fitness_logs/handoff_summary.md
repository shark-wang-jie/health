# 健身记录交接摘要
更新时间：2026-11-06（北京时间）

## 2026-11-06 进行中
- 空腹体重86.90kg，较11月5日87.45kg下降0.55kg。单日变化不等于脂肪变化。
- 早餐4项：南瓜子6.5g、酸奶165g（暂按历史大桶原味发酵乳）、鸡小胸1包（暂按100g相近产品）、牛奶吐司45g。吐司新标签每100g为1080kJ、P8.8/F5.2/C45.4/钠230mg；已吃45g记116.16kcal、P3.96/F2.34/C20.43，原位替换117kcal普通面包估算，不额外计一片。
- 午餐沙县鸡腿饭按历史同款：两只去皮鸡腿、250g熟米饭、白菜卤蛋、不吃土豆丝；基础837.5kcal，餐馆油脂余量83.75kcal，记921.25kcal、P69.33/F36.14/C77.67。真实份量未称重，暂估。
- 上午、下午各已报告荞麦锅巴约45g，两份共约90g；按食物库历史同款每100g1667kJ/P5.6/F2.8/C83.5，分别约179.29kcal，两份358.58kcal；重量为约数。
- **截至目前累计7项：1699.25kcal、P115.56g、F53.52g、C183.03g。**
- 当天记录开放：record_status=open、food_coverage=partial、training_status=unknown、training_coverage=unknown。未封账、不输出最终缺口。
- 待核实：酸奶与历史款是否相同、鸡小胸本包重量及营养标签、午餐实际份量和用油。当前BMR为1820.25kcal。

## 2026-11-05 已封账
晨起87.45kg，11项摄入2182.60kcal，P187.67/F66.08/C207.61。力量和室内单车训练记录能量合计957.19kcal，×0.75折算717.89kcal；部分能量口径及食品标签仍有不确定性。日JSON是事实来源。

## 记录规则
仓库 shark-wang-jie/health，main分支。每日文件fitness_logs/daily/YYYY-MM/YYYY-MM-DD.json。严格使用Asia/Shanghai日期、实际吃下量，重复消息不重记；标签更正替换原id。当前模型BMR×1.2＋Apple Watch训练动态千卡×0.75，不重复加全天活动圆环。当天未确认结束时不把模型差额称为最终热量缺口。一次业务变更涉及多文件应使用一个原子commit并回读验证。
完整细节参考fitness_logs/README.md、AGENTS.md、current_plan.json、food_catalog.json。旧交接详细历史已保存在fitness_logs/reference/handoff_legacy_2026-11-06.md，同时可通过Git历史追溯。
