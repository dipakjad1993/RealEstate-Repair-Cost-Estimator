import random
from datetime import datetime
from config import INSURANCE_RED_FLAGS

def analyze_insurance_risk(findings, property_data):
    state = property_data.get("state", "")
    year_built = property_data.get("year_built", 2000)
    current_year = datetime.now().year
    prop_age = current_year - year_built if year_built else 30
    red_flags = []
    all_findings_text = " ".join(f.get("description", "") for f in findings)
    all_findings_lower = all_findings_text.lower()
    for flag in INSURANCE_RED_FLAGS:
        patterns = flag["pattern"].split("|")
        for pattern in patterns:
            pattern_clean = pattern.strip().lower()
            if pattern_clean in all_findings_lower:
                red_flags.append({
                    "red_flag_type": flag["description"],
                    "system": flag["system"],
                    "risk_score": flag["risk_score"],
                    "denial_probability": flag["denial_prob"],
                    "annual_premium_impact": flag["annual_penalty"],
                    "replacement_cost": flag["replacement_cost"],
                    "matched_pattern": pattern_clean,
                    "description": flag["description"],
                    "recommendation": _get_insurance_recommendation(flag),
                    "severity": "CRITICAL" if flag["risk_score"] >= 90 else "HIGH" if flag["risk_score"] >= 80 else "MEDIUM",
                })
                break
    if prop_age > 25:
        roof_risk = any("roof" in f.get("description", "").lower() for f in findings)
        if roof_risk:
            existing_roof_flag = any(r["system"] == "roof" for r in red_flags)
            if not existing_roof_flag:
                red_flags.append({
                    "red_flag_type": "Aging Roof (25+ years)",
                    "system": "roof",
                    "risk_score": 70,
                    "denial_probability": 0.50,
                    "annual_premium_impact": 1800,
                    "replacement_cost": 12000,
                    "matched_pattern": "aging_roof",
                    "description": "Roof exceeding 25 years poses elevated insurance risk",
                    "recommendation": "Roof certification may be required for insurance. Budget for replacement.",
                    "severity": "HIGH",
                })
    if prop_age > 30:
        electric_findings = [f for f in findings if f.get("system_category") == "ELECTRICAL"]
        if electric_findings:
            red_flags.append({
                "red_flag_type": "Aging Electrical System (30+ years)",
                "system": "electrical",
                "risk_score": 65,
                "denial_probability": 0.40,
                "annual_premium_impact": 1200,
                "replacement_cost": 8000,
                "matched_pattern": "aging_electrical",
                "description": "Electrical system over 30 years may require panel upgrade for insurance",
                "recommendation": "Electrical inspection and possible panel upgrade may be required.",
                "severity": "MEDIUM",
            })
    if any(r["system"] == "environmental" and "mold" in r["matched_pattern"] for r in red_flags):
        for flag in red_flags:
            if flag["system"] == "environmental":
                flag["annual_premium_impact"] = int(flag["annual_premium_impact"] * 1.3)
    total_annual_impact = sum(r["annual_premium_impact"] for r in red_flags)
    max_denial_prob = max((r["denial_probability"] for r in red_flags), default=0)
    total_replacement = sum(r["replacement_cost"] for r in red_flags)
    base_premium = _estimate_base_premium(state, prop_age)
    inflated_premium = base_premium + total_annual_impact
    insurability_score = max(10, 100 - (sum(r["risk_score"] for r in red_flags) // len(red_flags)) if red_flags else 100)
    risk_level = "HIGH" if insurability_score < 40 else "MEDIUM" if insurability_score < 70 else "LOW"
    return {
        "red_flags": sorted(red_flags, key=lambda x: x["risk_score"], reverse=True),
        "summary": {
            "total_red_flags": len(red_flags),
            "critical_flags": len([r for r in red_flags if r["severity"] == "CRITICAL"]),
            "high_flags": len([r for r in red_flags if r["severity"] == "HIGH"]),
            "medium_flags": len([r for r in red_flags if r["severity"] == "MEDIUM"]),
            "max_denial_probability": round(max_denial_prob * 100, 0),
            "total_annual_premium_impact": round(total_annual_impact, 0),
            "total_replacement_cost": round(total_replacement, 0),
            "insurability_score": insurability_score,
            "risk_level": risk_level,
            "estimated_base_annual_premium": round(base_premium, 0),
            "estimated_inflated_annual_premium": round(inflated_premium, 0),
            "annual_premium_increase": round(total_annual_impact, 0),
            "five_year_cost_impact": round(total_annual_impact * 5, 0),
        },
        "market_context": {
            "state": state,
            "property_age": prop_age,
            "market_year": current_year,
            "note": "P&C insurance market is volatile in 2026. High-risk properties face non-renewal risk.",
        },
    }

def _estimate_base_premium(state, prop_age):
    base_premiums = {
        "FL": 4500, "TX": 3800, "LA": 3500, "CA": 3200, "NY": 2800,
        "NJ": 2600, "MA": 2400, "CT": 2200, "RI": 2100,
        "default": 2000,
    }
    base = base_premiums.get(state, base_premiums["default"])
    if prop_age > 30:
        base *= 1.20
    elif prop_age > 20:
        base *= 1.10
    return base

def _get_insurance_recommendation(flag):
    system = flag["system"]
    risk_score = flag["risk_score"]
    if risk_score >= 90:
        return f"URGENT: Replace or remediate {system} immediately. High probability of carrier denial or non-renewal. Estimated savings: ${flag['annual_penalty']:,}/year in avoided premium penalties."
    elif risk_score >= 80:
        return f"Address {system} issue before policy renewal. Document repairs with licensed contractor for insurance carrier."
    else:
        return f"Monitor {system} condition. Consider proactive repair to prevent future premium increases."

def calculate_insurance_scorecard(findings, property_data):
    analysis = analyze_insurance_risk(findings, property_data)
    score = analysis["summary"]["insurability_score"]
    return {
        "insurability_score": score,
        "grade": _score_to_grade(score),
        "red_flags": analysis["summary"]["total_red_flags"],
        "max_denial_prob": analysis["summary"]["max_denial_probability"],
        "annual_impact": analysis["summary"]["total_annual_premium_impact"],
        "five_year_impact": analysis["summary"]["five_year_cost_impact"],
        "verdict": _get_verdict(score),
        "recommendations": [
            r["recommendation"] for r in analysis["red_flags"][:5]
        ],
    }

def _score_to_grade(score):
    if score >= 90: return "A"
    elif score >= 80: return "B+"
    elif score >= 70: return "B"
    elif score >= 60: return "C+"
    elif score >= 50: return "C"
    elif score >= 40: return "D"
    else: return "F"

def _get_verdict(score):
    if score >= 80:
        return "Property is likely insurable at standard or near-standard rates. Minor repairs recommended."
    elif score >= 60:
        return "Property may face elevated premiums or specific exclusions. Proactive repairs strongly recommended."
    elif score >= 40:
        return "Property faces significant insurance challenges. Multiple red flags may trigger higher premiums, exclusions, or non-renewal."
    else:
        return "Property may be uninsurable or require specialty/Lloyd's market coverage. Immediate remediation of critical issues is essential."
