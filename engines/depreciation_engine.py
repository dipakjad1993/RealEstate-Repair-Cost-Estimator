import math
from datetime import datetime
from config import DEPRECIATION_TABLES

def parse_appliance_metadata(text):
    assets = []
    import re
    asset_indicators = {
        "hvac": ["hvac", "furnace", "air conditioner", "heat pump", "air handler", "condenser", "compressor", "carrier", "lennox", "trane", "goodman"],
        "water_heater": ["water heater", "hot water", "rheem", "a.o. smith", "bradford white", "ge water"],
        "roof_asphalt": ["asphalt shingle", "composition shingle", "roof shingle", "3-tab", "architectural shingle"],
        "roof_tile": ["tile roof", "concrete tile", "clay tile", "slate"],
        "electrical_panel": ["electrical panel", "breaker panel", "service panel", "subpanel", "200 amp", "100 amp"],
        "plumbing_main": ["main sewer", "main line", "supply line", "cast iron", "copper pipe main"],
        "foundation": ["foundation", "slab", "basement wall", "footing", "stem wall"],
        "windows": ["window", "dual pane", "double pane", "single pane", "vinyl window"],
        "insulation": ["insulation", "spray foam", "fiberglass", "cellulose", "blown-in"],
        "appliance_stove": ["stove", "range", "oven", "cooktop"],
        "appliance_refrigerator": ["refrigerator", "fridge", "freezer"],
        "appliance_dishwasher": ["dishwasher"],
        "appliance_washer": ["washing machine", "washer"],
        "appliance_dryer": ["dryer", "clothes dryer"],
        "garage_door": ["garage door", "garage opener"],
        "deck": ["deck", "wood deck", "composite deck"],
        "chimney": ["chimney", "flue", "firebox"],
    }
    text_lower = text.lower()
    for asset_type, keywords in asset_indicators.items():
        for kw in keywords:
            if kw in text_lower:
                asset = {"asset_type": asset_type, "detected_from": kw}
                make_patterns = [
                    r"(?:brand|make|manufacturer)[:\s]+([A-Za-z\s&.]+?)(?:\n|\.|,)",
                    r"(Carrier|Lennox|Trane|Goodman|Rheem|A\.?O\.?\s*Smith|Bradford\s*White|GE|Samsung|LG|Whirlpool|Maytag|Kenmore|Bosch|Ruud|York|Coleman|Bryant|Armstrong)",
                ]
                for pat in make_patterns:
                    match = re.search(pat, text, re.IGNORECASE)
                    if match:
                        asset["make"] = match.group(1).strip()
                        break
                model_match = re.search(r"model[:\s]+([A-Za-z0-9\-]+)", text, re.IGNORECASE)
                if model_match:
                    asset["model"] = model_match.group(1).strip()
                serial_match = re.search(r"serial(?:\s*(?:no|number|#))?\s*[:\s]+\s*([A-Za-z0-9]+)", text, re.IGNORECASE)
                if serial_match:
                    asset["serial_number"] = serial_match.group(1).strip()
                year_match = re.search(r"(?:manufactured|mfg|built|installed|year)\s*(?:in\s*)?(\d{4})", text, re.IGNORECASE)
                if year_match:
                    asset["year_manufactured"] = int(year_match.group(1))
                age_match = re.search(r"(?:age|approximately|about|~)\s*(\d{1,2})\s*years?", text, re.IGNORECASE)
                if age_match:
                    asset["age_years"] = int(age_match.group(1))
                break
        if asset.get("asset_type"):
            assets.append(asset)
    return assets

def calculate_depreciation_curve(asset_type, age_years, current_condition=None):
    table = DEPRECIATION_TABLES.get(asset_type)
    if not table:
        for key in DEPRECIATION_TABLES:
            if key in asset_type.lower():
                table = DEPRECIATION_TABLES[key]
                break
    if not table:
        table = {"useful_life": 20, "salvage_pct": 0.10, "replacement_avg": 3000, "replacement_range": (1500, 6000)}
    useful_life = table["useful_life"]
    salvage_pct = table["salvage_pct"]
    replacement_avg = table["replacement_avg"]
    replacement_low, replacement_high = table["replacement_range"]
    straight_line_dep = max(0, (1 - salvage_pct)) / useful_life
    annual_dep = straight_line_dep
    depreciation_pct = min(1.0, age_years * annual_dep)
    remaining_value_pct = max(0, 1.0 - depreciation_pct)
    remaining_life = max(0, useful_life - age_years)
    if age_years > useful_life:
        failure_prob = min(0.98, 0.70 + (age_years - useful_life) * 0.05)
    elif age_years > useful_life * 0.8:
        failure_prob = 0.15 + (age_years / useful_life - 0.8) * 2.5
    else:
        failure_prob = max(0.02, (age_years / useful_life) ** 3 * 0.15)
    condition_mults = {
        "excellent": 0.7, "good": 0.85, "fair": 1.0, "poor": 1.25,
        "terrible": 1.5, "rust": 1.3, "leaking": 1.4, "broken": 1.5,
        "noisy": 1.1, "corroded": 1.35, "damaged": 1.3,
    }
    cond_mult = 1.0
    if current_condition:
        cond_lower = current_condition.lower()
        for condition, mult in condition_mults.items():
            if condition in cond_lower:
                cond_mult = mult
                break
    adjusted_failure_prob = min(0.99, failure_prob * cond_mult)
    if adjusted_failure_prob > 0.75:
        urgency = "IMMEDIATE REPLACEMENT - High failure risk"
    elif adjusted_failure_prob > 0.50:
        urgency = "PLAN REPLACEMENT - Likely within 12 months"
    elif adjusted_failure_prob > 0.25:
        urgency = "MONITOR CLOSELY - Replacement within 24 months probable"
    elif remaining_life <= 3:
        urgency = "BUDGET FOR REPLACEMENT - Approaching end of useful life"
    elif remaining_life <= 5:
        urgency = "BEGIN PLANNING - Approaching end of useful life"
    else:
        urgency = "ADEQUATE REMAINING LIFE"
    failure_horizon_months = int(remaining_life * 12 * (1 - adjusted_failure_prob))
    depreciation_value = replacement_avg * depreciation_pct
    return {
        "asset_type": asset_type,
        "age_years": age_years,
        "useful_life": useful_life,
        "remaining_life": round(remaining_life, 1),
        "depreciation_pct": round(depreciation_pct * 100, 1),
        "remaining_value_pct": round(remaining_value_pct * 100, 1),
        "annual_depreciation_rate": round(annual_dep * 100, 2),
        "replacement_cost_avg": replacement_avg,
        "replacement_cost_low": replacement_low,
        "replacement_cost_high": replacement_high,
        "current_depreciated_value": round(replacement_avg * remaining_value_pct, 0),
        "depreciation_loss": round(depreciation_value, 0),
        "failure_probability_24mo": round(adjusted_failure_prob * 100, 1),
        "failure_horizon_months": max(0, failure_horizon_months),
        "replacement_urgency": urgency,
        "salvage_value": round(replacement_avg * salvage_pct, 0),
        "depreciation_curve": _generate_depreciation_timeline(useful_life, salvage_pct),
    }

def _generate_depreciation_timeline(useful_life, salvage_pct):
    timeline = []
    annual_dep = (1 - salvage_pct) / useful_life
    for year in range(0, useful_life + 10):
        dep = min(1.0, year * annual_dep)
        remaining = max(0, 1.0 - dep)
        if year <= useful_life:
            prob = min(0.95, (year / useful_life) ** 3 * 0.15)
        else:
            prob = min(0.98, 0.70 + (year - useful_life) * 0.06)
        timeline.append({
            "year": year,
            "depreciation_pct": round(dep * 100, 1),
            "remaining_value_pct": round(remaining * 100, 1),
            "failure_probability": round(prob * 100, 1),
        })
    return timeline

def analyze_all_capex(findings, property_data):
    current_year = datetime.now().year
    year_built = property_data.get("year_built", current_year - 20)
    prop_age = current_year - year_built if year_built else 20
    capex_items = []
    system_estimates = {
        "HVAC": {"type": "hvac", "avg_replacement_age": 15},
        "ROOF": {"type": "roof_asphalt", "avg_replacement_age": 25},
        "PLUMBING": {"type": "plumbing_main", "avg_replacement_age": 35},
        "ELECTRICAL": {"type": "electrical_panel", "avg_replacement_age": 30},
        "STRUCTURAL": {"type": "foundation", "avg_replacement_age": 50},
        "EXTERIOR": {"type": "deck", "avg_replacement_age": 20},
    }
    systems_with_findings = set()
    for finding in findings:
        system = finding.get("system_category", "OTHER")
        severity = finding.get("severity", "LOW")
        if system in system_estimates:
            systems_with_findings.add(system)
            sys_info = system_estimates[system]
            estimated_age = _estimate_system_age(system, finding, prop_age)
            dep = calculate_depreciation_curve(sys_info["type"], estimated_age, finding.get("description", ""))
            failure_month = dep["failure_horizon_months"]
            failure_year = current_year + (failure_month // 12)
            priority = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4}.get(severity, 5)
            capex_items.append({
                "system": system,
                "finding": finding.get("description", "")[:100],
                "severity": severity,
                "estimated_age": estimated_age,
                "asset_type": sys_info["type"],
                "useful_life": sys_info["avg_replacement_age"],
                "replacement_cost_avg": dep["replacement_cost_avg"],
                "replacement_cost_low": dep["replacement_cost_low"],
                "replacement_cost_high": dep["replacement_cost_high"],
                "remaining_life": dep["remaining_life"],
                "failure_probability_24mo": dep["failure_probability_24mo"],
                "failure_horizon_months": dep["failure_horizon_months"],
                "projected_failure_year": failure_year,
                "replacement_urgency": dep["replacement_urgency"],
                "priority": priority,
            })
    for system, info in system_estimates.items():
        if system not in systems_with_findings:
            estimated_age = _estimate_system_age(system, None, prop_age)
            dep = calculate_depreciation_curve(info["type"], estimated_age)
            if dep["failure_probability_24mo"] > 15:
                failure_month = dep["failure_horizon_months"]
                failure_year = current_year + (failure_month // 12)
                capex_items.append({
                    "system": system,
                    "finding": f"Age-based assessment for {system} (property age: {prop_age} years)",
                    "severity": "MEDIUM" if dep["remaining_life"] > 3 else "HIGH",
                    "estimated_age": estimated_age,
                    "asset_type": info["type"],
                    "useful_life": info["avg_replacement_age"],
                    "replacement_cost_avg": dep["replacement_cost_avg"],
                    "replacement_cost_low": dep["replacement_cost_low"],
                    "replacement_cost_high": dep["replacement_cost_high"],
                    "remaining_life": dep["remaining_life"],
                    "failure_probability_24mo": dep["failure_probability_24mo"],
                    "failure_horizon_months": dep["failure_horizon_months"],
                    "projected_failure_year": failure_year,
                    "replacement_urgency": dep["replacement_urgency"],
                    "priority": 3,
                })
    capex_items.sort(key=lambda x: (x["priority"], x["projected_failure_year"]))
    total_capex_risk_24mo = sum(
        item["replacement_cost_avg"] * (item["failure_probability_24mo"] / 100)
        for item in capex_items
    )
    total_replacement_if_all = sum(item["replacement_cost_avg"] for item in capex_items)
    return {
        "capex_items": capex_items,
        "summary": {
            "total_systems_assessed": len(capex_items),
            "total_replacement_value": round(total_replacement_if_all, 0),
            "weighted_24mo_risk": round(total_capex_risk_24mo, 0),
            "highest_risk_system": capex_items[0]["system"] if capex_items else "N/A",
            "property_age": prop_age,
            "generated_at": datetime.now().isoformat()
        }
    }

def _estimate_system_age(system, finding, prop_age):
    desc = (finding.get("description", "") if finding else "").lower()
    import re
    year_match = re.search(r"(?:20[0-2]\d|19[89]\d)", desc)
    if year_match:
        return datetime.now().year - int(year_match.group())
    age_match = re.search(r"(\d{1,2})\s*years?\s*old", desc)
    if age_match:
        return int(age_match.group(1))
    age_ranges = {
        "HVAC": (10, min(prop_age, 15)),
        "ROOF": (min(prop_age, 15), min(prop_age, 25)),
        "PLUMBING": (min(prop_age, 20), min(prop_age, 40)),
        "ELECTRICAL": (min(prop_age, 15), min(prop_age, 30)),
        "STRUCTURAL": (0, prop_age),
        "EXTERIOR": (5, min(prop_age, 20)),
    }
    low, high = age_ranges.get(system, (5, min(prop_age, 20)))
    return (low + high) // 2
