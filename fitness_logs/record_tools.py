#!/usr/bin/env python3
"""Daily calculation, validation and rolling review. Standard library only."""
from __future__ import annotations
import argparse
import copy
import json
import math
import os
import subprocess
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
TZ = ZoneInfo('Asia/Shanghai')
MACROS = ('protein_g', 'fat_g', 'carbs_g')


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def nonnegative(value, name):
    if not number(value) or value < 0:
        raise ValueError(f'{name}: 必须是有限非负数')
    return float(value)


def valid_range(value, name):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f'{name}: 必须是两个数的区间')
    low, high = (nonnegative(v, name) for v in value)
    if low > high:
        raise ValueError(f'{name}: 下限大于上限')
    return low, high


def bmr(profile):
    weight = nonnegative(profile['bmr_weight_kg'], 'BMR体重')
    height = nonnegative(profile['height_cm'], '身高')
    age = nonnegative(profile['age'], '年龄')
    if weight == 0 or height == 0 or age < 18:
        raise ValueError('成人BMR参数无效')
    sex = profile['sex']
    if sex not in ('男性', '女性'):
        raise ValueError('BMR公式性别参数需明确')
    return 10 * weight + 6.25 * height - 5 * age + (5 if sex == '男性' else -161)


def calculate(record):
    """Single source for new daily totals. No double application of food margin."""
    day = date.fromisoformat(record['date'])
    if record.get('schema_version') != 3:
        raise ValueError('每日计算仅支持schema_version 3；历史记录不自动迁移')
    if record.get('timezone') != 'Asia/Shanghai':
        raise ValueError('新记录timezone使用Asia/Shanghai')
    status = record.get('record_status')
    if status not in ('open', 'final', 'partial'):
        raise ValueError('record_status无效')
    if record.get('food_log_closed') != (status == 'final'):
        raise ValueError('封账状态不一致')
    if status == 'final' and not record.get('closure_basis'):
        raise ValueError('封账需注明依据')
    if not isinstance(record.get('missing_sections'), list):
        raise ValueError('missing_sections必须为列表')
    food_coverage = record.get('food_coverage')
    training = record.get('training_status')
    training_coverage = record.get('training_coverage', 'unknown')
    if training_coverage not in ('unknown', 'partial', 'confirmed_complete'):
        raise ValueError('training_coverage无效')
    if food_coverage not in ('unknown', 'partial', 'confirmed_complete'):
        raise ValueError('food_coverage无效')
    if training not in ('unknown', 'confirmed_rest', 'reported_training'):
        raise ValueError('training_status无效')
    method = record.get('energy_method', {})
    if method.get('algorithm') != 'tdee_v1':
        raise ValueError('新记录必须明确tdee_v1')
    af = nonnegative(method.get('activity_factor'), 'activity_factor')
    tf = nonnegative(method.get('training_factor'), 'training_factor')
    if not 1 <= af <= 3 or not 0 < tf <= 1:
        raise ValueError('活动系数需在1–3，训练系数需在0–1之间且大于0')
    if not record.get('food_estimation_policy'):
        raise ValueError('缺少食物估算口径标识')
    profile = record['profile_snapshot']
    basis_date = date.fromisoformat(profile['bmr_weight_date'])
    if basis_date > day:
        raise ValueError('BMR不可使用未来体重')
    weight = record.get('morning_weight_kg')
    if weight is not None:
        if nonnegative(weight, '空腹体重') == 0:
            raise ValueError('空腹体重必须大于0')
        if profile['bmr_weight_kg'] != weight or basis_date != day:
            raise ValueError('当天已称重时BMR应采用当天体重')
    basal = bmr(profile)
    if not number(profile.get('bmr_kcal')) or abs(profile['bmr_kcal'] - basal) > 1:
        raise ValueError('BMR与公式参数不一致')
    totals = {'intake_kcal_base_estimate': 0., 'intake_kcal_booked': 0.}
    for macro in MACROS:
        totals[macro + '_estimate'] = 0.
    kcal_bounds = [0., 0.]
    macro_bounds = {key: [0., 0.] for key in MACROS}
    warnings = []
    ids = set()
    actual = []
    added_fat_total = added_carbs_total = 0.
    macro_range_coverage = {m: 0 for m in MACROS}
    for entry in record.get('intake_entries', []):
        identity = entry.get('id')
        if not identity or identity in ids:
            raise ValueError('食物条目id缺失或重复；更正应替换原id')
        ids.add(identity)
        state = entry.get('status')
        if state in ('planned', 'not_eaten'):
            continue
        if state not in ('consumed', 'consumed_estimated'):
            raise ValueError('食物status无效；待确认食用量使用consumed_estimated并写假设')
        actual.append(entry)
        base = nonnegative(entry.get('kcal_base_estimate'), f'{identity}:基础热量')
        booked = nonnegative(entry.get('kcal_booked'), f'{identity}:记账热量')
        low, high = valid_range(entry.get('kcal_range'), f'{identity}:热量范围')
        if not low <= base <= booked <= high:
            raise ValueError(f'{identity}:基础/偏高记账值需在合理范围内，且记账值不低于基础值')
        source = entry.get('source_kind')
        if source not in ('label_known_quantity', 'matched_default', 'photo_estimate', 'database_estimate'):
            raise ValueError(f'{identity}:资料来源类型无效')
        if not entry.get('basis'):
            raise ValueError(f'{identity}:需记录份量和估算依据')
        margin = entry.get('margin', {})
        extra_fat = nonnegative(margin.get('added_fat_g', 0), '额外油脂')
        extra_carbs = nonnegative(margin.get('added_carbs_g', 0), '额外碳水')
        if source == 'label_known_quantity' and (booked != base or extra_fat or extra_carbs):
            raise ValueError('标签和食用量明确时不得额外加成')
        if booked > base:
            if not margin.get('reason') or margin.get('already_in_base'):
                raise ValueError('额外上浮需理由，基础已含同一余量时不可重复加成')
            if abs((booked - base) - (9 * extra_fat + 4 * extra_carbs)) > 2:
                raise ValueError('热量余量与新增油/酱汁宏量假设不一致')
        elif extra_fat or extra_carbs:
            raise ValueError('无热量上浮却填入额外油脂或碳水')
        if entry.get('fat_g_estimate', 0) < extra_fat or entry.get('carbs_g_estimate', 0) < extra_carbs:
            raise ValueError('记账宏量不能小于其中明确附加的油/酱汁余量')
        added_fat_total += extra_fat
        added_carbs_total += extra_carbs
        totals['intake_kcal_base_estimate'] += base
        totals['intake_kcal_booked'] += booked
        kcal_bounds[0] += low; kcal_bounds[1] += high
        for macro in MACROS:
            value = nonnegative(entry.get(macro + '_estimate'), f'{identity}:{macro}')
            explicit_range = entry.get(macro + '_range')
            if explicit_range is not None: macro_range_coverage[macro] += 1
            ml, mh = valid_range(explicit_range if explicit_range is not None else [value, value], macro)
            if not ml <= value <= mh:
                raise ValueError(f'{identity}:{macro}点估算不在范围中')
            totals[macro + '_estimate'] += value
            macro_bounds[macro][0] += ml; macro_bounds[macro][1] += mh
        # Label rounding/fibre can explain modest differences; do not force equality.
        macro_energy = 4 * entry['protein_g_estimate'] + 9 * entry['fat_g_estimate'] + 4 * entry['carbs_g_estimate']
        if abs(macro_energy - booked) > max(30, booked * .2):
            warnings.append(f'{identity}:热量与宏量换算差异较大，请核对标签或估算，勿强行配平')
        if state == 'consumed_estimated' and not entry.get('uncertainty'):
            raise ValueError(f'{identity}:暂估条目需保留不确定项')
    exercises = record.get('exercise_entries', [])
    strength_progress([record])
    if training == 'confirmed_rest' and exercises:
        raise ValueError('确认休息与已有训练条目冲突')
    if exercises and training != 'reported_training':
        raise ValueError('有训练条目应标为reported_training')
    if training == 'reported_training' and not exercises:
        raise ValueError('已报告训练必须保留条目，消耗未知可为null')
    active = 0.
    missing_training_energy = False
    event_ids = set()
    for entry in exercises:
        identity = entry.get('id')
        if not identity or identity in ids:
            raise ValueError('训练条目id缺失或重复')
        ids.add(identity)
        event_id = entry.get('event_id')
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError('训练需稳定event_id，用于识别同一次训练的多设备记录')
        if event_id:
            if event_id in event_ids: raise ValueError('同一训练event_id只能计入一次；多设备读数保存在同一条目内')
            event_ids.add(event_id)
        if entry.get('energy_scope') != 'session_active':
            raise ValueError('仅允许当次训练动态消耗，不可使用全天活动圆环或总千卡')
        if not entry.get('source'):
            raise ValueError('训练需保留来源')
        value = entry.get('active_kcal')
        if value is None:
            missing_training_energy = True
        else:
            active += nonnegative(value, '训练动态消耗')
            if entry.get('total_kcal') is not None and nonnegative(entry['total_kcal'], '总千卡') < value:
                raise ValueError('总千卡小于动态千卡')
    adjusted = active * tf
    tdee = basal * af + adjusted
    saved_targets = record.get('targets', {})
    target_key = 'training_day_intake_kcal_range' if training == 'reported_training' else 'rest_day_intake_kcal_range'
    target_range = list(valid_range(saved_targets.get(target_key, [1900, 2000] if training == 'reported_training' else [1800, 1800]), target_key))
    if saved_targets.get('intake_kcal_range') is not None:
        target_range = list(valid_range(saved_targets['intake_kcal_range'], '摄入目标'))
    if training == 'unknown': warnings.append('训练状态未确认：仅暂按基础活动估算，不等于确认休息')
    if missing_training_energy: warnings.append('已报告训练有消耗缺失：仅计已知训练消耗')
    if food_coverage != 'confirmed_complete': warnings.append('饮食完整性未确认：合计仅含已记录摄入')
    training_complete = training == 'confirmed_rest' or training_coverage == 'confirmed_complete'
    provisional = status != 'final' or training == 'unknown' or not training_complete or missing_training_energy or food_coverage != 'confirmed_complete' or bool(record['missing_sections'])
    if training == 'reported_training' and not training_complete: warnings.append('已报告部分训练，全天训练是否报完尚未确认')
    if status != 'final': warnings.append('尚未封账：全天模型消耗减已记录摄入只是暂算差额')
    if record['missing_sections']: warnings.append('存在影响能量解释或完整性的待确认项')
    totals.update({
        'intake_kcal_estimate': totals['intake_kcal_booked'],
        'food_margin_kcal': totals['intake_kcal_booked'] - totals['intake_kcal_base_estimate'],
        'base_macro_estimates': {'protein_g': totals['protein_g_estimate'], 'fat_g': totals['fat_g_estimate'] - added_fat_total, 'carbs_g': totals['carbs_g_estimate'] - added_carbs_total},
        'completed_day_base_intake_balance_kcal': None if provisional else tdee - totals['intake_kcal_base_estimate'],
        'training_discount_kcal': active - adjusted,
        'assumption_note': '基础宏量与记账宏量区分附加余量；两个摄入口径的能量差额是模型对照，不是可信区间或真实上下界。',
        'intake_kcal_range': kcal_bounds,
        'exercise_active_kcal': active,
        'exercise_adjusted_kcal': adjusted,
        'tdee_kcal_estimate': tdee,
        'estimated_deficit_kcal': tdee - totals['intake_kcal_booked'],
        'completed_day_estimated_deficit_kcal': None if provisional else tdee - totals['intake_kcal_booked'],
        'energy_balance_scope': 'provisional_recorded_balance' if provisional else 'completed_day_estimate',
        'intake_target_kcal_range': target_range,
        'target_is_provisional': training == 'unknown',
        'energy_estimate_provisional': provisional,
        'consumed_entries': len(actual),
        'protein_by_meal_g': {meal: sum(e['protein_g_estimate'] for e in actual if e.get('meal', '未分类') == meal) for meal in sorted({e.get('meal', '未分类') for e in actual})},
        'warnings': warnings,
        'interpretation': '按偏高记账摄入估算的缺口；非实测值或真实缺口下限。食物范围不包含完整消耗误差。',
    })
    for macro in MACROS:
        complete_range = bool(actual) and macro_range_coverage[macro] == len(actual)
        totals[macro + '_range'] = macro_bounds[macro] if complete_range else None
        totals[macro + '_entries_with_range'] = macro_range_coverage[macro]
        totals[macro + '_range_coverage_complete'] = complete_range
    for nutrient in ('fiber_g', 'sodium_mg', 'fruit_vegetable_g'):
        values = [e.get(nutrient + '_estimate') for e in actual]
        known = [nonnegative(v, nutrient) for v in values if v is not None]
        totals[nutrient + '_known_sum'] = sum(known) if known else None
        totals[nutrient + '_entries_with_data'] = len(known)
        totals[nutrient + '_coverage_complete'] = bool(actual) and len(known) == len(actual)
    return totals


def validate(record):
    expected = calculate(record)
    saved = record.get('daily_summary', {})
    errors = []
    for key, value in expected.items():
        current = saved.get(key)
        if number(value):
            match = number(current) and abs(current - value) < .011
        elif isinstance(value, list) and all(number(v) for v in value):
            match = isinstance(current, list) and len(current) == len(value) and all(number(a) and abs(a-b)<.011 for a,b in zip(current,value))
        else: match = current == value
        if not match: errors.append(f'daily_summary.{key}与条目计算不一致')
    if errors: raise ValueError('; '.join(errors))
    return expected['warnings']


def save_json(path, data):
    """Validate JSON with jq before atomically replacing the destination."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, suffix='.json', delete=False) as f:
            name = f.name
            json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False); f.write('\n')
        subprocess.run(['jq', 'empty', name], check=True, capture_output=True)
        os.replace(name, path)
    finally:
        if name and os.path.exists(name): os.unlink(name)


def new_record(day, latest_weight, weight_date, measured_weight=None, plan=None):
    day = date.fromisoformat(day).isoformat()
    plan = copy.deepcopy(plan if plan is not None else json.loads((ROOT/'current_plan.json').read_text()))
    profile = {**plan['profile'], 'bmr_weight_kg': measured_weight if measured_weight is not None else latest_weight,
               'bmr_weight_date': day if measured_weight is not None else weight_date}
    profile['bmr_kcal'] = bmr(profile)
    record = {
        'schema_version': 3, 'date': day, 'timezone': 'Asia/Shanghai',
        'record_status': 'open', 'food_log_closed': False, 'closure_basis': None,
        'food_coverage': 'unknown', 'training_status': 'unknown', 'training_coverage': 'unknown', 'missing_sections': [],
        'non_energy_pending_notes': [], 'trend_context': [], 'weight_measurement_note': None, 'plan_version': plan['version'],
        'morning_weight_kg': measured_weight, 'profile_snapshot': profile,
        'energy_method': plan['energy_method'],
        'food_estimation_policy': plan['food_estimation_policy'],
        'targets': plan['targets'],
        'intake_entries': [], 'exercise_entries': [],
        'recovery': {'hunger': None, 'sleep_hours': None, 'training_performance': None, 'fatigue_or_pain': None},
        'corrections': [], 'notes': []}
    record['daily_summary'] = calculate(record)
    return record


def food_from_catalog(food_id, entry_id, servings=1, status="consumed_estimated"):
    """Copy a versioned default; margin is applied once to the base, never totals."""
    servings = nonnegative(servings, "份数")
    if servings == 0: raise ValueError("份数必须大于0")
    catalog = json.loads((ROOT / "food_catalog.json").read_text())
    default = catalog["foods"][food_id]
    entry = copy.deepcopy(default["entry"])
    entry.update({"id": entry_id, "status": status, "catalog_id": food_id,
                  "catalog_version": catalog["version"], "servings": servings})
    for key in ("kcal_base_estimate", "kcal_booked", *(m+"_estimate" for m in MACROS), 'fiber_g_estimate', 'sodium_mg_estimate', 'fruit_vegetable_g_estimate'):
        if key not in entry: continue
        entry[key] *= servings
    for key in ("kcal_range", *(m+"_range" for m in MACROS)):
        if key in entry: entry[key] = [v*servings for v in entry[key]]
    for key in ("added_fat_g", "added_carbs_g"):
        entry["margin"][key] = entry["margin"].get(key, 0)*servings
    return entry


def load_records(root=ROOT / 'daily'):
    records = []
    for path in sorted(Path(root).glob('*/*.json')):
        try: date.fromisoformat(path.stem)
        except ValueError: continue
        data = json.loads(path.read_text())
        if data['date'] != path.stem: raise ValueError(f'文件日期不一致：{path}')
        records.append(data)
    return records


def fit_weight_trend(measurements):
    """Descriptive only; missing food or exercise data do not hide weight trends."""
    if len(measurements) < 4 or max(x for x,_ in measurements)-min(x for x,_ in measurements) < 7:
        return {"available": False, "reason": "不足4次有效称重或覆盖不足7天，保留原始记录与周均"}
    xs=[x for x,_ in measurements]; ys=[y for _,y in measurements]
    xm=sum(xs)/len(xs); ym=sum(ys)/len(ys)
    slope=sum((x-xm)*(y-ym) for x,y in measurements)/sum((x-xm)**2 for x in xs)
    return {"available": True, "valid_measurements": len(xs), "span_days": max(xs)-min(xs),
            "weekly_weight_loss_kg_approx": -7*slope,
            "interpretation": "实际日期线性趋势，仅描述体重变化，不等于脂肪变化；4次/7天是报告门槛，非医学阈值"}


def select_plan(day, plan_root=ROOT):
    """Choose an effective immutable plan version for backfill as well as new days."""
    day=date.fromisoformat(day).isoformat()
    root=Path(plan_root)
    paths=[root/'current_plan.json', *sorted((root/'plans').glob('*.json'))]
    candidates=[json.loads(path.read_text()) for path in paths if path.exists()]
    candidates=[p for p in candidates if date.fromisoformat(p['effective_from']).isoformat() <= day]
    if not candidates: raise ValueError('此日期没有已生效的新口径计划；读取历史文件，勿套用未来配置')
    return max(candidates,key=lambda p:(p['effective_from'],p.get('revision',0)))


def rolling_review(records, end):
    end = date.fromisoformat(end)
    start = end - timedelta(days=27)
    window = sorted([r for r in records if start <= date.fromisoformat(r['date']) <= end], key=lambda r:r['date'])
    if len({r['date'] for r in window}) != len(window): raise ValueError('日期重复')
    weeks=[]
    for i in range(4):
        a=start+timedelta(days=7*i); b=a+timedelta(days=6)
        values=[(r['date'],r['morning_weight_kg']) for r in window if a.isoformat() <= r['date'] <= b.isoformat() and number(r.get('morning_weight_kg'))]
        weeks.append({'start':a.isoformat(),'end':b.isoformat(),'valid_measurements':len(values),
                      'mean_weight_kg':sum(v for _,v in values)/len(values) if values else None})
    measurements=[((date.fromisoformat(r['date'])-start).days,r['morning_weight_kg']) for r in window if number(r.get('morning_weight_kg'))]
    trend = fit_weight_trend(measurements)
    reasons=[]
    if len(window)!=28: reasons.append('不足28个连续日记录')
    if any(w['valid_measurements']<4 for w in weeks): reasons.append('至少一个7日窗口少于4次有效称重；这是内部数据质量门槛，不是医学标准')
    methods=set()
    trend_flags=[{'date':r['date'],'context':r['trend_context']} for r in window if r.get('trend_context')]
    if trend_flags: reasons.append('存在可能干扰体重解释的情况，需人工复核后再粗校准')
    booked=[]; base=[]
    for r in window:
        if r.get('schema_version')!=3:
            reasons.append('包含旧口径记录'); continue
        validate(r)
        methods.add(r['food_estimation_policy'])
        if r['record_status']!='final' or r['food_coverage']!='confirmed_complete' or r.get('missing_sections'):
            reasons.append('存在未封账、饮食资料不完整或关键待确认日')
        booked.append(r['daily_summary']['intake_kcal_booked']); base.append(r['daily_summary']['intake_kcal_base_estimate'])
    if len(methods)!=1: reasons.append('估算方法不统一或无可用新口径记录')
    result={'start':start.isoformat(),'end':end.isoformat(),'recorded_days':len(window),'weeks':weeks,
            'calibration_eligible':not reasons,'reasons':sorted(set(reasons)), 'trend_context':trend_flags, 'weight_trend':trend,
            'exercise_model_comparison_available': bool(window) and all(r.get('schema_version')==3 and not r['daily_summary']['energy_estimate_provisional'] for r in window),
            'recovery_reports':[{'date':r['date'],**r['recovery']} for r in window if any(v is not None for v in (r.get('recovery') or {}).values())],
            'note':'跨月读取；缺测不插补。趋势用于复核，不自动修改目标。7700换算仅为多周粗估，水分与估餐偏差仍可能显著。'}
    if not reasons:
        measurements=[((date.fromisoformat(r['date'])-start).days,r['morning_weight_kg']) for r in window if number(r.get('morning_weight_kg'))]
        xs=[x for x,_ in measurements]; ys=[y for _,y in measurements]
        xm=sum(xs)/len(xs); ym=sum(ys)/len(ys)
        slope=sum((x-xm)*(y-ym) for x,y in measurements)/sum((x-xm)**2 for x in xs)
        loss=-7*slope
        intake_start=start+timedelta(days=min(xs)); intake_end=start+timedelta(days=max(xs))
        aligned=[r['daily_summary'] for r in window if intake_start.isoformat() <= r['date'] < intake_end.isoformat()]
        mean_booked=sum(s['intake_kcal_booked'] for s in aligned)/len(aligned)
        mean_base=sum(s['intake_kcal_base_estimate'] for s in aligned)/len(aligned)
        result.update({'weekly_weight_loss_kg_approx':loss,'average_booked_intake_kcal':mean_booked,
                       'average_base_intake_kcal':mean_base,
                       'calibration_intake_period':{'start_inclusive':intake_start.isoformat(),'end_exclusive':intake_end.isoformat(),'days':len(aligned)},
                       'trend_method':'全部有效空腹称重按实际日期作线性拟合，不只比较首尾；非脂肪变化测量',
                       'rough_daily_energy_gap_kcal':loss*7700/7,
                       'bookkeeping_implied_tdee_kcal':mean_booked+loss*7700/7,
                       'base_intake_implied_tdee_kcal':mean_base+loss*7700/7,
                       'identifiability_note':'体重与摄入只能粗估该时段平均消耗；无法分别确定BMR、日常活动、训练误差或食物误差。手表训练数据不是此反推的必要输入。',
                       'calibration_note':'摄入采用首次至末次空腹称重之间的日记录（不含末次称重日）。线性趋势及7700仍是粗估，TDEE吸收估餐误差，仅用于同口径计划；结合恢复复核，不自动改目标。'})
    return result


def render_daily_report(record):
    validate(record)
    summary=record['daily_summary']
    macros=summary['base_macro_estimates']
    lines=[f"{record['date']} {'已封账' if record['record_status']=='final' else '截至目前'}",
           f"摄入：基础估算约{summary['intake_kcal_base_estimate']:.0f}千卡；含余量记账约{summary['intake_kcal_booked']:.0f}千卡。",
           f"基础宏量估算：蛋白质{macros['protein_g']:.1f}克、脂肪{macros['fat_g']:.1f}克、碳水{macros['carbs_g']:.1f}克。"]
    if summary['completed_day_estimated_deficit_kcal'] is None:
        lines.append('全天最终缺口暂不报告：当天未结束或关键资料尚不完整。')
    else:
        lines.append(f"模型TDEE约{summary['tdee_kcal_estimate']:.0f}千卡；按含余量摄入估算缺口约{summary['completed_day_estimated_deficit_kcal']:.0f}千卡，非实测。")
    if record.get('missing_sections'):
        lines.append('待确认：'+'；'.join(record['missing_sections']))
    if summary['warnings']: lines.append('记录说明：'+'；'.join(summary['warnings']))
    return '\n'.join(lines)


def strength_progress(records):
    """Summarise only reported working sets with comparable equipment/load basis."""
    groups={}
    for record in records:
        for session in record.get('exercise_entries', []):
            sets=session.get('resistance_sets') or []
            for entry in sets:
                if entry.get('set_type') == 'warmup': continue
                if entry.get('set_type') != 'working': raise ValueError('力量组需区分warmup或working')
                for key in ('exercise_name','equipment','load_basis'):
                    if not isinstance(entry.get(key),str) or not entry[key].strip(): raise ValueError('力量组需动作、器械和重量口径')
                reps=entry.get('reps')
                if not isinstance(reps,int) or isinstance(reps,bool) or reps <= 0: raise ValueError('训练次数需正整数')
                load=entry.get('load_kg')
                if load is not None: nonnegative(load,'训练负重')
                rir=entry.get('rir')
                if rir is not None and (not number(rir) or not 0 <= rir <= 10): raise ValueError('RIR需0–10或null')
                identity=(entry['exercise_name'],entry['equipment'],entry['load_basis'])
                groups.setdefault(identity,[]).append({'date':record['date'],'event_id':session.get('event_id'),
                                                       'reps':reps,'load_kg':load,'rir':rir})
    return {'exercises':[{'exercise_name':key[0],'equipment':key[1],'load_basis':key[2],
                          'reported_working_sets':len(sets),'sets':sets} for key,sets in sorted(groups.items())],
            'interpretation':'仅汇总已报告工作组；不同器械或重量口径不混比。无组数资料不等于没有力量训练，不从热量推断肌肉增长或自动增加训练量。'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('validate','recalculate','report'):
        p=sub.add_parser(name);p.add_argument('path',type=Path)
    p=sub.add_parser('new');p.add_argument('date');p.add_argument('--weight',type=float)
    p=sub.add_parser('review');p.add_argument('--end',default=datetime.now(TZ).date().isoformat());p.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.command=='new':
        day=date.fromisoformat(args.date)
        if day>datetime.now(TZ).date(): raise ValueError('不提前建立未来实际日记录')
        history=[r for r in load_records() if r['date']<=args.date and number(r.get('morning_weight_kg'))]
        if not history: raise ValueError('缺少历史有效体重，需先建立用户档案')
        latest=history[-1]; path=ROOT/'daily'/args.date[:7]/f'{args.date}.json'
        if path.exists(): raise ValueError('日文件已存在，请读取后更新，不覆盖创建')
        record=new_record(args.date, latest['morning_weight_kg'],latest['date'],args.weight,plan=select_plan(args.date))
        save_json(path,record); print(path)
    elif args.command=='review':
        result=rolling_review(load_records(),args.end)
        if args.output: save_json(args.output,result)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        record=json.loads(args.path.read_text())
        if args.path.stem!=record['date']: raise ValueError('文件名与日期不一致')
        if args.command=='report':
            print(render_daily_report(record));return
        if args.command=='recalculate':
            record['daily_summary']=calculate(record);validate(record);save_json(args.path,record)
        else: validate(record)
        print('通过；'+ '；'.join(record['daily_summary']['warnings']))

if __name__=='__main__': main()
