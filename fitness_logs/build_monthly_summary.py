#!/usr/bin/env python3
"""Create month-end JSON summaries from per-day fitness JSON records."""

from __future__ import annotations

import argparse
import calendar
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
from record_tools import validate, save_json, load_records, rolling_review, strength_progress


ROOT = Path(__file__).resolve().parent
DAILY_ROOT = ROOT / "daily"
MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")
DAY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")


def normalized_exercise_type(value: Any) -> str:
    exercise_type = str(value or "未分类运动")
    if exercise_type in {"力量训练", "传统力量训练"}:
        return "strength"
    if exercise_type in {"骑行", "室内骑行", "室内单车"}:
        return "indoor_cycling"
    return exercise_type


def rounded(value: float, digits: int = 1) -> int | float:
    result = round(value, digits)
    return int(result) if result.is_integer() else result


def first_present(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if mapping.get(key) is not None:
            return mapping[key]
    return None


def bounds(exact: Any, value_range: Any) -> tuple[float | None, float | None]:
    if isinstance(value_range, list) and len(value_range) == 2:
        if all(isinstance(item, (int, float)) for item in value_range):
            return float(value_range[0]), float(value_range[1])
    if isinstance(exact, (int, float)):
        return float(exact), float(exact)
    return None, None


def parse_duration_minutes(entry: dict[str, Any]) -> float | None:
    duration_min = entry.get("duration_min")
    if isinstance(duration_min, (int, float)):
        return float(duration_min)
    duration_seconds = entry.get("duration_seconds")
    if isinstance(duration_seconds, (int, float)):
        return float(duration_seconds) / 60
    duration = entry.get("duration")
    if not isinstance(duration, str):
        return None
    duration = duration.strip().removeprefix("约").strip().removesuffix("钟").strip()
    chinese = re.fullmatch(r"(?:(\d+)小时)?(?:(\d+)分)?(?:(\d+)秒)?", duration)
    if chinese and any(chinese.groups()):
        hours, minutes, seconds = (int(value or 0) for value in chinese.groups())
        return hours * 60 + minutes + seconds / 60
    parts = duration.split(":")
    try:
        if len(parts) == 3:
            hours, minutes, seconds = (int(part) for part in parts)
            return hours * 60 + minutes + seconds / 60
        if len(parts) == 2:
            minutes, seconds = (int(part) for part in parts)
            return minutes + seconds / 60
    except ValueError:
        return None
    return None


def metric_source(record: dict[str, Any]) -> dict[str, Any]:
    return record.get("daily_summary") or record.get("daily_totals") or {}


def daily_metrics(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("date", "") > "2026-09-08" and record.get("schema_version") != 3:
        raise ValueError("新日记录必须采用schema_version 3，避免漏写算法后静默回退旧口径")
    if record.get("schema_version") == 3:
        validate(record)
    source = metric_source(record)
    method = record.get("energy_method") or {}
    algorithm = method.get("algorithm", "legacy_bmr_plus_exercise")
    if algorithm not in {"legacy_bmr_plus_exercise", "tdee_v1"}:
        raise ValueError(f"未知热量算法：{algorithm}")
    intake = source.get("intake_kcal_estimate")
    if algorithm == "tdee_v1":
        intake = source.get("intake_kcal_booked")
        if not isinstance(intake, (int, float)):
            raise ValueError("tdee_v1 必须提供 intake_kcal_booked")
    intake_low, intake_high = bounds(intake, source.get("intake_kcal_range"))

    protein = source.get("protein_g_estimate")
    protein_range = source.get("protein_g_range")
    protein_low, protein_high = bounds(protein, protein_range)

    exercise = first_present(
        source,
        "exercise_active_kcal",
        "exercise_kcal_estimate",
    )
    if not isinstance(exercise, (int, float)):
        exercise = sum(
            value
            for entry in record.get("exercise_entries", [])
            if isinstance(
                (value := first_present(entry, "active_kcal", "kcal_estimate")),
                (int, float),
            )
        )

    bmr = (record.get("profile_snapshot") or {}).get("bmr_kcal")
    conservative_deficit = None
    if all(isinstance(value, (int, float)) for value in (bmr, intake, exercise)):
        conservative_deficit = round(float(bmr) + float(exercise) - float(intake))

    tdee = adjusted_exercise = estimated_deficit = None
    if algorithm == "tdee_v1":
        activity_factor = method.get("activity_factor")
        training_factor = method.get("training_factor")
        if not all(isinstance(value, (int, float)) and value > 0
                   for value in (bmr, activity_factor, training_factor)):
            raise ValueError("tdee_v1 必须记录有效 BMR、activity_factor 和 training_factor")
        adjusted_exercise = float(exercise) * training_factor
        tdee = float(bmr) * activity_factor + adjusted_exercise
        estimated_deficit = tdee - float(intake)
        conservative_deficit = None

    if record.get("schema_version") == 3:
        # New records have already passed the shared daily calculator validation.
        tdee = source["tdee_kcal_estimate"]
        adjusted_exercise = source["exercise_adjusted_kcal"]
        estimated_deficit = source["completed_day_estimated_deficit_kcal"]

    return {
        "provisional_recorded_balance_kcal": source.get("estimated_deficit_kcal") if source.get("energy_estimate_provisional") else None,
        "protein_range_available": isinstance(source.get("protein_g_range"), list),
        "algorithm": algorithm,
        "energy_method": method,
        "intake_kcal_base_estimate": source.get("intake_kcal_base_estimate"),
        "exercise_adjusted_kcal": adjusted_exercise,
        "tdee_kcal_estimate": tdee,
        "estimated_deficit_kcal": estimated_deficit,
        "intake_target_kcal_range": source.get("intake_target_kcal_range") or (record.get("targets") or {}).get("intake_kcal_range"),
        "date": record.get("date"),
        "record_status": record.get("record_status", "unknown"),
        "missing_sections": record.get("missing_sections", []),
        "morning_weight_kg": record.get("morning_weight_kg"),
        "bmr_kcal": bmr,
        "intake_kcal_estimate": intake,
        "intake_kcal_range": (
            [rounded(intake_low), rounded(intake_high)]
            if intake_low is not None and intake_low != intake_high
            else None
        ),
        "base_macro_estimates": source.get("base_macro_estimates"),
        "fat_g_estimate": source.get("fat_g_estimate"),
        "carbs_g_estimate": source.get("carbs_g_estimate"),
        "food_coverage": record.get("food_coverage", "unknown"),
        "energy_estimate_provisional": source.get("energy_estimate_provisional", True),
        "training_status": record.get("training_status", "unknown"),
        "protein_g_estimate": protein,
        "protein_g_range": (
            [rounded(protein_low), rounded(protein_high)]
            if protein_low is not None and protein_low != protein_high
            else None
        ),
        "exercise_active_or_estimated_kcal": rounded(float(exercise)),
        "conservative_deficit_kcal": conservative_deficit,
        "intake_limit_kcal": (record.get("targets") or {}).get("intake_kcal"),
        "protein_target_g": (record.get("targets") or {}).get("protein_target_g"),
        "deficit_target_range_kcal": [
            (record.get("targets") or {}).get("deficit_min_kcal"),
            (record.get("targets") or {}).get("deficit_max_kcal"),
        ],
        "meal_entries": sum(record.get("schema_version") != 3 or e.get("status") in ("consumed", "consumed_estimated") for e in record.get("intake_entries", [])),
        "exercise_sessions": len(record.get("exercise_entries") or []),
        "source_summary_status": source.get("status") or source.get("deficit_status"),
    }


def extreme_day(
    daily: list[dict[str, Any]], key: str, *, highest: bool
) -> dict[str, Any] | None:
    candidates = [item for item in daily if isinstance(item.get(key), (int, float))]
    if not candidates:
        return None
    selected = (max if highest else min)(candidates, key=lambda item: item[key])
    return {"date": selected["date"], "value": selected[key]}


def weight_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    values = [
        {"date": record.get("date"), "weight_kg": record.get("morning_weight_kg")}
        for record in records
        if isinstance(record.get("morning_weight_kg"), (int, float))
    ]
    if not values:
        return {"recorded_days": 0}
    weights = [float(item["weight_kg"]) for item in values]
    minimum = min(values, key=lambda item: item["weight_kg"])
    maximum = max(values, key=lambda item: item["weight_kg"])
    return {
        "recorded_days": len(values),
        "first": values[0],
        "last": values[-1],
        "first_to_last_change_kg": rounded(weights[-1] - weights[0], 2),
        "average_kg": rounded(sum(weights) / len(weights), 2),
        "minimum": minimum,
        "maximum": maximum,
    }


def nutrition_summary(
    records: list[dict[str, Any]], daily: list[dict[str, Any]]
) -> dict[str, Any]:
    intake_days = [
        item for item in daily if isinstance(item.get("intake_kcal_estimate"), (int, float))
    ]
    protein_days = [
        item
        for item in daily
        if isinstance(item.get("protein_g_estimate"), (int, float))
        or isinstance(item.get("protein_g_range"), list)
    ]
    intake_total = sum(float(item["intake_kcal_estimate"]) for item in intake_days)

    protein_bounds: list[tuple[float, float]] = []
    for item in protein_days:
        protein_bounds.append(
            bounds(item.get("protein_g_estimate"), item.get("protein_g_range"))  # type: ignore[arg-type]
        )
    ranged = [(low, high) for item, (low, high) in zip(protein_days, protein_bounds) if item["protein_range_available"]]
    protein_low_total = sum(low for low, _ in ranged)
    protein_high_total = sum(high for _, high in ranged)

    definite_met = 0
    midpoint_met = 0
    possible_met = 0
    definite_below = 0
    for item, (low, high) in zip(protein_days, protein_bounds):
        target = item.get("protein_target_g")
        if not isinstance(target, (int, float)) or low is None or high is None:
            continue
        range_available = item["protein_range_available"]
        if range_available and low >= target:
            definite_met += 1
        point = item.get("protein_g_estimate")
        if (point if isinstance(point, (int, float)) else (low + high) / 2) >= target:
            midpoint_met += 1
        if range_available and high >= target:
            possible_met += 1
        if range_available and high < target:
            definite_below += 1

    intake_with_limit = [
        item
        for item in intake_days
        if item["algorithm"] == "legacy_bmr_plus_exercise" and isinstance(item.get("intake_limit_kcal"), (int, float))
    ]
    definite_within_intake_limit = 0
    estimate_within_intake_limit = 0
    possible_within_intake_limit = 0
    definite_above_intake_limit = 0
    for item in intake_with_limit:
        low, high = bounds(
            item.get("intake_kcal_estimate"), item.get("intake_kcal_range")
        )
        limit = item["intake_limit_kcal"]
        if low is None or high is None:
            continue
        definite_within_intake_limit += high <= limit
        estimate_within_intake_limit += item["intake_kcal_estimate"] <= limit
        possible_within_intake_limit += low <= limit
        definite_above_intake_limit += low > limit
    meal_categories = Counter(
        str(entry.get("meal", "未分类"))
        for record in records
        for entry in record.get("intake_entries", [])
        if record.get("schema_version") != 3 or entry.get("status") in ("consumed", "consumed_estimated")
    )

    result: dict[str, Any] = {
        "days_with_intake_summary": len(intake_days),
        "total_intake_kcal_estimate": rounded(intake_total),
        "average_intake_kcal_per_recorded_day": (
            rounded(intake_total / len(intake_days)) if intake_days else None
        ),
        "lowest_intake_day": extreme_day(
            intake_days, "intake_kcal_estimate", highest=False
        ),
        "highest_intake_day": extreme_day(
            intake_days, "intake_kcal_estimate", highest=True
        ),
        "intake_limit_adherence": {
            "days_recorded_range_at_or_below_legacy_limit": definite_within_intake_limit,
            "days_estimate_at_or_below_limit": estimate_within_intake_limit,
            "days_possibly_at_or_below_limit": possible_within_intake_limit,
            "days_recorded_range_above_legacy_limit": definite_above_intake_limit,
        },
        "total_meal_entries": sum(item["meal_entries"] for item in daily),
        "meal_category_counts": dict(sorted(meal_categories.items())),
        "protein_days_with_summary": len(protein_days),
        "protein_days_with_explicit_range": sum(item["protein_range_available"] for item in protein_days),
        "protein_range_note": "无范围日仅提供点估算，不当作确定上下限；以下区间合计仅含有明确区间的日",
        "total_protein_g_range": [rounded(protein_low_total), rounded(protein_high_total)] if ranged else None,
        "average_protein_g_range_per_recorded_day": (
            [
                rounded(protein_low_total / len(ranged)),
                rounded(protein_high_total / len(ranged)),
            ]
            if ranged
            else None
        ),
        "protein_target_days_range_lower_bound_met": definite_met,
        "protein_target_days_point_estimate_met": midpoint_met,
        "protein_target_days_possibly_met": possible_met,
        "protein_target_days_range_upper_bound_below": definite_below,
    }
    for macro in ("protein_g", "fat_g", "carbs_g"):
        values = [item[macro + "_estimate"] for item in daily if isinstance(item.get(macro + "_estimate"), (int, float))]
        result[macro + "_point_summary"] = {
            "days_with_data": len(values), "total": rounded(sum(values)) if values else None,
            "average_per_recorded_day": rounded(sum(values)/len(values)) if values else None,
            "note": "仅已报告数据；缺失不按零处理"}
    comparison = {"below": 0, "within": 0, "above": 0, "excluded_incomplete_days": 0}
    for item in intake_days:
        if item["algorithm"] != "tdee_v1": continue
        target = item.get("intake_target_kcal_range")
        if not target or item["food_coverage"] != "confirmed_complete" or item["record_status"] != "final" or item["training_status"] == "unknown" or item["missing_sections"]:
            comparison["excluded_incomplete_days"] += 1; continue
        value = item["intake_kcal_estimate"]
        comparison["below" if value < target[0] else "above" if value > target[1] else "within"] += 1
    comparison["interpretation"] = "相对初始摄入安排的描述，不是合格评分；低于区间不自动代表更好"
    result["new_intake_target_comparison"] = comparison
    result["base_macro_summaries"] = {}
    for macro in ("protein_g", "fat_g", "carbs_g"):
        values=[item["base_macro_estimates"][macro] for item in daily if item.get("base_macro_estimates")]
        result["base_macro_summaries"][macro] = {"days_with_data":len(values),
            "total": rounded(sum(values)) if values else None,
            "mean": rounded(sum(values)/len(values)) if values else None}
    result["macro_basis_note"] = "原有宏量合计含记账余量；base_macro_summaries仅汇总明确保存的基础宏量，不反推旧日数据"
    return result


def exercise_summary(
    records: list[dict[str, Any]], daily: list[dict[str, Any]]
) -> dict[str, Any]:
    by_type: dict[str, dict[str, float]] = defaultdict(
        lambda: {"sessions": 0, "duration_min": 0, "kcal": 0}
    )
    total_sessions = 0
    sessions_with_duration = 0
    sessions_with_kcal = 0

    for record in records:
        for entry in record.get("exercise_entries") or []:
            total_sessions += 1
            exercise_type = normalized_exercise_type(entry.get("type"))
            bucket = by_type[exercise_type]
            bucket["sessions"] += 1
            duration = parse_duration_minutes(entry)
            if duration is not None:
                bucket["duration_min"] += duration
                sessions_with_duration += 1
            kcal = first_present(entry, "active_kcal", "kcal_estimate")
            if isinstance(kcal, (int, float)):
                bucket["kcal"] += float(kcal)
                sessions_with_kcal += 1

    type_output = {
        name: {
            "sessions": int(values["sessions"]),
            "recorded_duration_min": rounded(values["duration_min"]),
            "active_or_estimated_kcal": rounded(values["kcal"]),
        }
        for name, values in sorted(by_type.items())
    }
    daily_exercise_total = sum(
        float(item["exercise_active_or_estimated_kcal"]) for item in daily
    )
    return {
        "exercise_days": sum(item["exercise_sessions"] > 0 for item in daily),
        "days_without_exercise_entries": sum(
            item["exercise_sessions"] == 0 for item in daily
        ),
        "total_sessions": total_sessions,
        "sessions_with_duration": sessions_with_duration,
        "sessions_with_kcal": sessions_with_kcal,
        "total_active_or_estimated_kcal_from_daily_summaries": rounded(
            daily_exercise_total
        ),
        "highest_exercise_kcal_day": extreme_day(
            daily, "exercise_active_or_estimated_kcal", highest=True
        ),
        "by_normalized_type": type_output,
        "type_aliases": {
            "strength": ["力量训练", "传统力量训练"],
            "indoor_cycling": ["骑行", "室内骑行", "室内单车"],
        },
        "energy_basis": "每次运动优先采用 active_kcal；没有该字段时沿用 kcal_estimate。Apple Watch 总千卡不计入。",
    }


def deficit_summary(daily: list[dict[str, Any]]) -> dict[str, Any]:
    days = [
        item
        for item in daily
        if isinstance(item.get("conservative_deficit_kcal"), (int, float))
    ]
    within = below = above = 0
    for item in days:
        target = item.get("deficit_target_range_kcal")
        if not (
            isinstance(target, list)
            and len(target) == 2
            and all(isinstance(value, (int, float)) for value in target)
        ):
            continue
        value = item["conservative_deficit_kcal"]
        if value < target[0]:
            below += 1
        elif value > target[1]:
            above += 1
        else:
            within += 1
    total = sum(float(item["conservative_deficit_kcal"]) for item in days)
    return {
        "days_with_calculable_deficit": len(days),
        "total_conservative_deficit_kcal": rounded(total),
        "average_conservative_deficit_kcal_per_recorded_day": (
            rounded(total / len(days)) if days else None
        ),
        "days_within_that_days_recorded_target": within,
        "days_below_that_days_recorded_target": below,
        "days_above_that_days_recorded_target": above,
        "surplus_days": sum(item["conservative_deficit_kcal"] < 0 for item in days),
        "lowest_deficit_day": extreme_day(days, "conservative_deficit_kcal", highest=False),
        "highest_deficit_day": extreme_day(days, "conservative_deficit_kcal", highest=True),
        "formula": "当日基础代谢 + 已记录运动动态或估算千卡 - 当日摄入估算",
    }


def assessment(
    month: str,
    expected_days: int,
    records: list[dict[str, Any]],
    weights: dict[str, Any],
    nutrition: dict[str, Any],
    exercise: dict[str, Any],
    deficits: dict[str, Any],
) -> list[str]:
    notes: list[str] = []
    if len(records) < expected_days:
        notes.append(
            f"本月只保存 {len(records)}/{expected_days} 天日记录，月度均值和总量不能代表完整月份。"
        )
    partial_dates = [
        str(record.get("date"))
        for record in records
        if record.get("record_status") == "partial"
    ]
    open_dates = [
        str(record.get("date"))
        for record in records
        if record.get("record_status") == "open"
    ]
    if partial_dates:
        notes.append(
            f"明确不完整的日记录：{', '.join(partial_dates)}；其已报告数值仍保留，但不能视为完整全天。"
        )
    if open_dates:
        notes.append(
            f"缺少当日结束确认的记录：{', '.join(open_dates)}；月度统计按已报告内容计算。"
        )
    if weights.get("first_to_last_change_kg") is not None:
        change = weights["first_to_last_change_kg"]
        notes.append(f"本月首次至末次有记录体重变化 {change:+.2f} 千克。")
    protein_days = nutrition.get("protein_days_with_summary", 0)
    protein_met = nutrition.get("protein_target_days_range_lower_bound_met", 0)
    if protein_days:
        notes.append(
            f"有蛋白质汇总的 {protein_days} 天中，按记录区间下限达到参考目标 {protein_met} 天；另列点估算统计，均非确定测量或饮食质量评分。"
        )
    notes.append(
        f"记录到 {exercise.get('exercise_days', 0)} 个运动日、{exercise.get('total_sessions', 0)} 次训练。"
    )
    if deficits.get("days_with_calculable_deficit"):
        notes.append(
            "旧算法记账差额仅汇总旧记录；新算法另列，不将两者合并为月度缺口。"
        )
    return notes


def load_month(month: str) -> list[dict[str, Any]]:
    month_dir = DAILY_ROOT / month
    if not month_dir.is_dir():
        raise FileNotFoundError(f"月份目录不存在：{month_dir}")
    records: list[dict[str, Any]] = []
    for path in sorted(month_dir.iterdir()):
        if not path.is_file() or not DAY_PATTERN.fullmatch(path.name):
            continue
        if not path.name.startswith(f"{month}-"):
            continue
        with path.open("r", encoding="utf-8") as handle:
            record = json.load(handle)
        if record.get("date") != path.stem:
            raise ValueError(f"文件名与 JSON 日期不一致：{path}")
        records.append(record)
    if not records:
        raise ValueError(f"月份目录没有每日记录：{month_dir}")
    return records


def energy_summary_by_algorithm(daily: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    for algorithm in sorted({item["algorithm"] for item in daily}):
        items = [item for item in daily if item["algorithm"] == algorithm]
        if algorithm == "legacy_bmr_plus_exercise":
            result = deficit_summary(items)
            result["interpretation"] = "旧算法记账差额，不代表真实缺口或盈余。"
        else:
            values = [item["estimated_deficit_kcal"] for item in items if isinstance(item.get("estimated_deficit_kcal"), (int, float))]
            result = {
                "total_estimated_deficit_kcal": rounded(sum(values)) if values else None,
                "days_with_completed_day_estimate": len(values),
                "excluded_provisional_days": len(items)-len(values),
                "average_estimated_deficit_kcal": rounded(sum(values) / len(values)) if values else None,
                "total_estimated_tdee_kcal": rounded(sum(item["tdee_kcal_estimate"] for item in items)),
                "total_adjusted_training_kcal": rounded(sum(item["exercise_adjusted_kcal"] for item in items)),
                "formula": "BMR × activity_factor + 原始训练动态消耗 × training_factor − 偏高记账摄入",
                "interpretation": "按偏高摄入估算的缺口，不是真实缺口下限；系数未经个人验证。",
            }
        base_values = [item["intake_kcal_base_estimate"] for item in items if isinstance(item.get("intake_kcal_base_estimate"), (int, float))]
        result["base_intake_summary"] = {"days_with_data": len(base_values),
            "total_kcal": rounded(sum(base_values)) if base_values else None,
            "average_kcal": rounded(sum(base_values)/len(base_values)) if base_values else None}
        result["booked_or_legacy_intake_total_kcal"] = rounded(sum(item["intake_kcal_estimate"] for item in items if isinstance(item.get("intake_kcal_estimate"), (int, float))))
        if algorithm == "tdee_v1":
            complete = [item for item in items if not item["energy_estimate_provisional"] and item["record_status"] == "final" and not item["missing_sections"]]
            result["complete_data_subset"] = {"dates": [item["date"] for item in complete],
                "recorded_days": len(complete),
                "average_estimated_deficit_kcal": rounded(sum(item["estimated_deficit_kcal"] for item in complete)/len(complete)) if complete else None,
                "note": "完整资料子集，仍是估算；未完成日的暂算差额不计入缺口合计"}
        result["provisional_or_unconfirmed_dates"] = [item["date"] for item in items if item["energy_estimate_provisional"] or item["record_status"] != "final"]
        result["coefficient_variants"] = list({json.dumps(item["energy_method"], sort_keys=True): item["energy_method"] for item in items}.values())
        result["dates"] = [item["date"] for item in items]
        result["recorded_days"] = len(items)
        result["average_booked_or_legacy_intake_kcal"] = rounded(
            sum(item["intake_kcal_estimate"] for item in items if isinstance(item["intake_kcal_estimate"], (int, float)))
            / max(1, sum(isinstance(item["intake_kcal_estimate"], (int, float)) for item in items)))
        groups[algorithm] = result
    return groups


def weekly_weight_summary(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    weeks: dict[str, list[float]] = defaultdict(list)
    for record in records:
        value = record.get("morning_weight_kg")
        if isinstance(value, (int, float)):
            day = date.fromisoformat(record["date"])
            year, week, _ = day.isocalendar()
            weeks[f"{year}-W{week:02d}"].append(float(value))
    return [{"iso_week": week, "valid_measurements": len(values),
             "average_kg": rounded(sum(values) / len(values), 2),
             "scope": "仅当前月内有效测量，月边界周可能不完整；缺测不插补"}
            for week, values in sorted(weeks.items())]


def build_summary(month: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    year, month_number = (int(part) for part in month.split("-"))
    expected_days = calendar.monthrange(year, month_number)[1]
    expected_dates = {
        f"{month}-{day:02d}" for day in range(1, expected_days + 1)
    }
    recorded_dates = {str(record["date"]) for record in records}
    daily = [daily_metrics(record) for record in records]
    weights = weight_summary(records)
    nutrition = nutrition_summary(records, daily)
    exercise = exercise_summary(records, daily)
    deficits = deficit_summary([item for item in daily if item["algorithm"] == "legacy_bmr_plus_exercise"])
    missing_dates = sorted(expected_dates - recorded_dates)
    partial_dates = sorted(
        str(record["date"])
        for record in records
        if record.get("record_status") == "partial"
    )
    open_dates = sorted(
        str(record["date"])
        for record in records
        if record.get("record_status") == "open"
    )
    final_dates = sorted(
        str(record["date"])
        for record in records
        if record.get("record_status") == "final"
    )
    unknown_dates = sorted(
        str(record["date"])
        for record in records
        if record.get("record_status") not in {"partial", "open", "final"}
    )
    weight_missing_dates = sorted(
        str(record["date"])
        for record in records
        if not isinstance(record.get("morning_weight_kg"), (int, float))
    )
    last_day = f"{month}-{expected_days:02d}"

    return {
        "schema_version": 3,
        "record_type": "monthly_summary",
        "month": month,
        "summary_type": "月度饮食与运动总结",
        "period": {
            "start_date": f"{month}-01",
            "end_date": last_day,
            "timezone": "亚洲/上海",
        },
        "month_end_date": last_day,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "finalized": month_is_finished(month, datetime.now(ZoneInfo("Asia/Shanghai")).date()) and len(records) == expected_days and all(r.get("record_status") == "final" for r in records),
        "coverage": {
            "calendar_days": expected_days,
            "recorded_days": len(records),
            "is_complete_calendar_coverage": not missing_dates,
            "missing_dates": missing_dates,
            "final_dates": final_dates,
            "partial_dates": partial_dates,
            "open_dates": open_dates,
            "unknown_completion_dates": unknown_dates,
            "weight_missing_dates": weight_missing_dates,
        },
        "aggregation_policy": {
            "daily_summary_precedence": ["daily_summary", "daily_totals"],
            "reported_data_policy": "月度总量包含所有日文件中已报告的数据；partial/open 日期会单独标出，不能视为完整全天。",
            "range_central_value": "新日摄入采用intake_kcal_booked，旧日采用intake_kcal_estimate；宏量点估算单列，区间不是置信区间。",
            "exercise_kcal": "优先 active_kcal，否则使用 kcal_estimate；不使用 total_kcal。",
            "energy_balance_formula": "按 energy_summary_by_algorithm 分组，不合并新旧算法缺口",
            "target_evaluation": "按每个日文件自身 targets 判断，不使用单一月度目标。",
        },
        "energy_summary_by_algorithm": energy_summary_by_algorithm(daily),
        "weekly_weight_summary": weekly_weight_summary(records),
        "recovery_reports": [{"date": r["date"], **r["recovery"]} for r in records if any(v is not None for v in (r.get("recovery") or {}).values())],
        "unresolved_data": [{"date": r["date"], "missing_sections": r.get("missing_sections", []),
                             "food_coverage": r.get("food_coverage", "unknown")}
                            for r in records if r.get("missing_sections") or r.get("food_coverage", "unknown") != "confirmed_complete"],
        "weight_summary": weights,
        "nutrition_summary": nutrition,
        "exercise_summary": exercise,
        "strength_progress": strength_progress(records),
        "conservative_deficit_summary": deficits,
        "notable_days": {
            "highest_intake": nutrition.get("highest_intake_day"),
            "lowest_intake": nutrition.get("lowest_intake_day"),
            "highest_exercise": exercise.get("highest_exercise_kcal_day"),
            "highest_conservative_deficit": deficits.get("highest_deficit_day"),
            "lowest_conservative_deficit": deficits.get("lowest_deficit_day"),
        },
        "assessment": assessment(
            month,
            expected_days,
            records,
            weights,
            nutrition,
            exercise,
            deficits,
        ),
        "daily_metrics": daily,
        "source_files": [
            f"daily/{month}/{record['date']}.json" for record in records
        ],
        "methodology_notes": [
            "月度总量和均值只按现有每日 JSON 计算；缺失日期不按零摄入或零运动处理。",
            "每日摄入使用该日算法对应记账值；新口径基础估算另外保留。",
            "蛋白质范围仅汇总显式区间，只有点估算不当作零宽范围；注明范围覆盖天数。",
            "运动总消耗优先采用 Apple Watch 动态千卡；没有动态千卡时沿用设备或人工估算。",
            "conservative_deficit_summary 仅含旧算法；新口径见 energy_summary_by_algorithm。",
            "跨口径摄入合计仅为记录值合计，不能视为同一估算标准下的精确摄入；校准优先使用连续3–4周同口径记录。",
            "蛋白质目标为参考，不以达标天数单独评价饮食质量；同时观察完整正餐、饥饿及训练恢复。",
            "没有运动条目的日期仅表示无运动记录；若当日记录不完整，不能据此确认是休息日。",
        ],
    }


def month_is_finished(month: str, today: date) -> bool:
    year, month_number = (int(part) for part in month.split("-"))
    last_day = date(year, month_number, calendar.monthrange(year, month_number)[1])
    return today > last_day


def discover_finished_months(today: date) -> list[str]:
    months = [
        path.name
        for path in DAILY_ROOT.iterdir()
        if path.is_dir() and MONTH_PATTERN.fullmatch(path.name)
    ]
    return sorted(month for month in months if month_is_finished(month, today))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="在已到月末的月份目录内生成 YYYY-MM-summary.json。"
    )
    parser.add_argument(
        "months",
        nargs="*",
        help="要汇总的月份（YYYY-MM）；省略时处理所有已经到月末的月份。",
    )
    parser.add_argument("--overwrite", action="store_true", help="明确重生成指定月份的已有总结；需同时指定月份")
    args = parser.parse_args()
    if args.overwrite and not args.months: raise SystemExit("--overwrite需明确指定月份，避免批量覆盖历史")
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    months = args.months or discover_finished_months(today)
    if not months:
        raise SystemExit("没有已经到月末且包含日记录的月份。")

    for month in months:
        if not MONTH_PATTERN.fullmatch(month):
            raise SystemExit(f"月份格式错误：{month}")
        if not month_is_finished(month, today):
            raise SystemExit(f"月份尚未结束，不能生成最终月总结：{month}")
        records = load_month(month)
        output = DAILY_ROOT / month / f"{month}-summary.json"
        if output.exists() and not args.overwrite:
            print(f"已存在，保留原总结：{output}；明确重生成时加--overwrite")
            continue
        summary = build_summary(month, records)
        summary["rolling_28_day_review"] = rolling_review(load_records(), summary["month_end_date"])
        save_json(output, summary)
        print(output)


if __name__ == "__main__":
    main()
