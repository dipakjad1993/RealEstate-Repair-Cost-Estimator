from datetime import datetime

from engines.depreciation_engine import calculate_depreciation_curve


def generate_capex_horizon(findings, property_data):
    current_year = datetime.now().year
    current_month = datetime.now().month
    year_built = property_data.get("year_built", current_year - 20)
    prop_age = current_year - year_built if year_built else 20
    timeline_items = []
    for finding in findings:
        system = finding.get("system_category", "OTHER")
        severity = finding.get("severity", "MEDIUM")
        asset_type = _system_to_asset_type(system)
        if not asset_type:
            continue
        age = _estimate_age(finding, prop_age)
        dep = calculate_depreciation_curve(asset_type, age, finding.get("description", ""))
        failure_months = dep["failure_horizon_months"]
        failure_month_abs = current_month + failure_months
        failure_year = current_year + (failure_months // 12)
        failure_month_in_year = ((failure_month_abs - 1) % 12) + 1
        timeline_items.append(
            {
                "finding": finding.get("description", "")[:100],
                "system": system,
                "severity": severity,
                "asset_type": asset_type,
                "current_age": age,
                "useful_life": dep["useful_life"],
                "remaining_life_years": dep["remaining_life"],
                "replacement_cost": dep["replacement_cost_avg"],
                "replacement_low": dep["replacement_cost_low"],
                "replacement_high": dep["replacement_cost_high"],
                "failure_probability_24mo": dep["failure_probability_24mo"],
                "failure_horizon_months": failure_months,
                "projected_failure_date": f"{failure_year}-{failure_month_in_year:02d}",
                "replacement_urgency": dep["replacement_urgency"],
                "urgency_category": _categorize_urgency(failure_months),
                "timeline_position": _timeline_position(failure_months),
            }
        )
    timeline_items.sort(key=lambda x: x["failure_horizon_months"])
    total_risk = sum(
        item["replacement_cost"] * item["failure_probability_24mo"] / 100 for item in timeline_items
    )
    immediate_items = [i for i in timeline_items if i["urgency_category"] == "IMMEDIATE"]
    within_12mo = [i for i in timeline_items if i["urgency_category"] == "WITHIN_12_MONTHS"]
    within_24mo = [i for i in timeline_items if i["urgency_category"] == "WITHIN_24_MONTHS"]
    beyond_24mo = [i for i in timeline_items if i["urgency_category"] == "BEYOND_24_MONTHS"]
    return {
        "timeline_items": timeline_items,
        "summary": {
            "total_capex_items": len(timeline_items),
            "immediate_replacement_count": len(immediate_items),
            "within_12mo_count": len(within_12mo),
            "within_24mo_count": len(within_24mo),
            "beyond_24mo_count": len(beyond_24mo),
            "total_replacement_value": sum(i["replacement_cost"] for i in timeline_items),
            "weighted_risk_exposure": round(total_risk, 0),
            "immediate_cost": sum(i["replacement_cost"] for i in immediate_items),
            "12mo_cost": sum(i["replacement_cost"] for i in within_12mo),
            "24mo_cost": sum(i["replacement_cost"] for i in within_24mo),
        },
        "visual_timeline": _build_visual_timeline(timeline_items),
    }


def _system_to_asset_type(system):
    mapping = {
        "HVAC": "hvac",
        "ROOF": "roof_asphalt",
        "PLUMBING": "water_heater",
        "ELECTRICAL": "electrical_panel",
        "STRUCTURAL": "foundation",
        "EXTERIOR": "deck",
        "INSULATION": "insulation",
        "APPLIANCES": "appliance_stove",
        "WINDOWS_DOORS": "windows",
        "FIRE_SAFETY": "chimney",
    }
    return mapping.get(system)


def _estimate_age(finding, prop_age):
    import re

    desc = finding.get("description", "").lower()
    year_match = re.search(r"(20[0-2]\d|19[89]\d)", desc)
    if year_match:
        return datetime.now().year - int(year_match.group())
    age_match = re.search(r"(\d{1,2})\s*years?\s*old", desc)
    if age_match:
        return int(age_match.group(1))
    system = finding.get("system_category", "OTHER")
    avg_ages = {
        "HVAC": min(12, prop_age),
        "ROOF": min(18, prop_age),
        "PLUMBING": min(25, prop_age),
        "ELECTRICAL": min(20, prop_age),
        "STRUCTURAL": min(prop_age, prop_age),
        "EXTERIOR": min(15, prop_age),
    }
    return avg_ages.get(system, min(15, prop_age))


def _categorize_urgency(failure_months):
    if failure_months <= 0:
        return "IMMEDIATE"
    elif failure_months <= 6:
        return "WITHIN_6_MONTHS"
    elif failure_months <= 12:
        return "WITHIN_12_MONTHS"
    elif failure_months <= 24:
        return "WITHIN_24_MONTHS"
    else:
        return "BEYOND_24_MONTHS"


def _timeline_position(failure_months):
    if failure_months <= 0:
        return "NOW"
    elif failure_months <= 6:
        return "0-6M"
    elif failure_months <= 12:
        return "6-12M"
    elif failure_months <= 18:
        return "12-18M"
    elif failure_months <= 24:
        return "18-24M"
    else:
        return f"24M+ ({failure_months}mo)"


def _build_visual_timeline(items):
    months = list(range(0, 25))
    timeline = {}
    for m in months:
        timeline[m] = []
    for item in items:
        failure_mo = min(24, max(0, item["failure_horizon_months"]))
        if failure_mo in timeline:
            timeline[failure_mo].append(
                {
                    "system": item["system"],
                    "cost": item["replacement_cost"],
                    "severity": item["severity"],
                }
            )
    visual = []
    for m in months:
        entries = timeline.get(m, [])
        if entries:
            visual.append(
                {
                    "month": m,
                    "events": entries,
                    "total_cost": sum(e["cost"] for e in entries),
                }
            )
    return visual
