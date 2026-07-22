import math
from datetime import datetime
from config import MATERIAL_COSTS_2026, ZIP_COST_MODIFIERS

REAL_CONTRACTOR_PROFILES = [
    {"name": "Precision Home Services", "specialty": "General", "years_active": 18, "rating": 4.8, "warranty_standard": "2 years parts & labor", "license_prefix": "GH"},
    {"name": "Elite Contracting Solutions", "specialty": "General", "years_active": 22, "rating": 4.7, "warranty_standard": "1 year parts & labor", "license_prefix": "GC"},
    {"name": "ProBuild Construction Group", "specialty": "General", "years_active": 15, "rating": 4.6, "warranty_standard": "2 year parts & labor", "license_prefix": "GC"},
    {"name": "Master Craft Remodeling", "specialty": "Remodeling", "years_active": 12, "rating": 4.5, "warranty_standard": "1 year warranty", "license_prefix": "RC"},
    {"name": "Premier Property Solutions", "specialty": "General", "years_active": 20, "rating": 4.9, "warranty_standard": "5 year structural", "license_prefix": "GC"},
    {"name": "Summit Construction Group", "specialty": "Roofing", "years_active": 25, "rating": 4.7, "warranty_standard": "10 year manufacturer + 2 year labor", "license_prefix": "RF"},
    {"name": "All Star Home Experts", "specialty": "HVAC", "years_active": 16, "rating": 4.6, "warranty_standard": "1 year parts & labor", "license_prefix": "HV"},
    {"name": "TrustPoint Builders", "specialty": "Electrical", "years_active": 19, "rating": 4.8, "warranty_standard": "2 year parts & labor", "license_prefix": "EL"},
    {"name": "Cornerstone Repairs Inc.", "specialty": "Plumbing", "years_active": 14, "rating": 4.5, "warranty_standard": "1 year parts & labor", "license_prefix": "PL"},
    {"name": "BrightView Construction", "specialty": "Exterior", "years_active": 11, "rating": 4.4, "warranty_standard": "1 year warranty", "license_prefix": "EX"},
    {"name": "Ace Home Maintenance", "specialty": "Handyman", "years_active": 8, "rating": 4.3, "warranty_standard": "90 days workmanship", "license_prefix": "HM"},
    {"name": "Quality First Contracting", "specialty": "General", "years_active": 17, "rating": 4.7, "warranty_standard": "2 year parts & labor", "license_prefix": "GC"},
    {"name": "Reliable Repair Co.", "specialty": "General", "years_active": 13, "rating": 4.4, "warranty_standard": "1 year warranty", "license_prefix": "GC"},
    {"name": "Top Shelf Home Services", "specialty": "Remodeling", "years_active": 9, "rating": 4.5, "warranty_standard": "1 year parts & labor", "license_prefix": "RC"},
    {"name": "ABC General Contractors", "specialty": "General", "years_active": 28, "rating": 4.8, "warranty_standard": "2 year parts & labor", "license_prefix": "GC"},
]

SYSTEM_LABOR_RATES = {
    "HVAC": {"hourly_low": 80, "hourly_high": 130, "markup_pct": 0.25, "complexity_mult": 1.2},
    "ROOF": {"hourly_low": 55, "hourly_high": 90, "markup_pct": 0.20, "complexity_mult": 1.1},
    "ELECTRICAL": {"hourly_low": 75, "hourly_high": 120, "markup_pct": 0.22, "complexity_mult": 1.15},
    "PLUMBING": {"hourly_low": 80, "hourly_high": 135, "markup_pct": 0.22, "complexity_mult": 1.15},
    "STRUCTURAL": {"hourly_low": 65, "hourly_high": 110, "markup_pct": 0.30, "complexity_mult": 1.3},
    "EXTERIOR": {"hourly_low": 50, "hourly_high": 85, "markup_pct": 0.18, "complexity_mult": 1.0},
    "INSULATION": {"hourly_low": 45, "hourly_high": 75, "markup_pct": 0.15, "complexity_mult": 1.0},
    "APPLIANCES": {"hourly_low": 60, "hourly_high": 100, "markup_pct": 0.20, "complexity_mult": 1.0},
    "WINDOWS_DOORS": {"hourly_low": 55, "hourly_high": 95, "markup_pct": 0.18, "complexity_mult": 1.1},
    "FIRE_SAFETY": {"hourly_low": 60, "hourly_high": 95, "markup_pct": 0.20, "complexity_mult": 1.0},
    "MOISTURE": {"hourly_low": 55, "hourly_high": 90, "markup_pct": 0.22, "complexity_mult": 1.1},
    "DEFAULT": {"hourly_low": 50, "hourly_high": 85, "markup_pct": 0.20, "complexity_mult": 1.0},
}

SEVERITY_TIMELINE_MAP = {
    "CRITICAL": {"min_days": 1, "max_days": 5, "rush_available": True},
    "HIGH": {"min_days": 3, "max_days": 10, "rush_available": True},
    "MEDIUM": {"min_days": 5, "max_days": 21, "rush_available": True},
    "LOW": {"min_days": 7, "max_days": 30, "rush_available": False},
    "INFO": {"min_days": 14, "max_days": 45, "rush_available": False},
}


def _deterministic_hash(value):
    h = 0
    for ch in str(value):
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


def _get_labor_rates(system, zip_code):
    rates = ZIP_COST_MODIFIERS.get(zip_code, {})
    local_labor = rates.get("avg_labor_rate", 70)
    sys_rates = SYSTEM_LABOR_RATES.get(system, SYSTEM_LABOR_RATES["DEFAULT"])
    labor_adjusted_low = sys_rates["hourly_low"] * (local_labor / 70)
    labor_adjusted_high = sys_rates["hourly_high"] * (local_labor / 70)
    return {
        "local_hourly_low": round(labor_adjusted_low, 0),
        "local_hourly_high": round(labor_adjusted_high, 0),
        "markup_pct": sys_rates["markup_pct"],
        "complexity_mult": sys_rates["complexity_mult"],
    }


def _estimate_labor_hours(system, severity, description):
    base_hours = {
        "HVAC": {"CRITICAL": 8, "HIGH": 5, "MEDIUM": 3, "LOW": 1.5},
        "ROOF": {"CRITICAL": 12, "HIGH": 6, "MEDIUM": 3, "LOW": 1.5},
        "ELECTRICAL": {"CRITICAL": 6, "HIGH": 4, "MEDIUM": 2, "LOW": 1},
        "PLUMBING": {"CRITICAL": 6, "HIGH": 4, "MEDIUM": 2, "LOW": 1},
        "STRUCTURAL": {"CRITICAL": 16, "HIGH": 10, "MEDIUM": 5, "LOW": 2},
        "EXTERIOR": {"CRITICAL": 10, "HIGH": 6, "MEDIUM": 3, "LOW": 1.5},
    }
    hours = base_hours.get(system, {"CRITICAL": 6, "HIGH": 4, "MEDIUM": 2, "LOW": 1})
    return hours.get(severity, 3)


def _get_warranty_for_profile(profile, severity):
    if severity == "CRITICAL":
        return f"{profile['warranty_standard']} + extended warranty"
    return profile["warranty_standard"]


def _calculate_bid_detail(base_cost, labor_rates, material_mult, severity, system, finding_desc):
    material_cost = base_cost * 0.45 * material_mult
    labor_hours = _estimate_labor_hours(system, severity, finding_desc)
    labor_rate_avg = (labor_rates["local_hourly_low"] + labor_rates["local_hourly_high"]) / 2
    labor_cost = labor_hours * labor_rate_avg
    overhead = (material_cost + labor_cost) * labor_rates["markup_pct"]
    profit_margin = (material_cost + labor_cost) * 0.08
    permit_cost = 0
    if severity in ["CRITICAL", "HIGH"] and system in ["ELECTRICAL", "PLUMBING", "HVAC", "STRUCTURAL", "ROOF"]:
        permit_cost = 275
    total = material_cost + labor_cost + overhead + profit_margin + permit_cost
    return {
        "material_cost": round(material_cost, 0),
        "labor_cost": round(labor_cost, 0),
        "labor_hours": round(labor_hours, 1),
        "labor_rate": round(labor_rate_avg, 0),
        "overhead": round(overhead, 0),
        "profit_margin": round(profit_margin, 0),
        "permit_cost": round(permit_cost, 0),
        "total": round(total, 0),
    }


def simulate_contractor_bids(findings, zip_code, cost_matrix):
    all_bids = []
    cost_items = cost_matrix.get("line_items", [])

    for idx, finding in enumerate(findings):
        system = finding.get("system_category", "OTHER")
        severity = finding.get("severity", "MEDIUM")
        description = finding.get("description", "")

        matching_cost = None
        for item in cost_items:
            if item.get("system", "") == system:
                matching_cost = item
                break
        if not matching_cost and cost_items:
            matching_cost = cost_items[min(idx, len(cost_items) - 1)]

        base_low = matching_cost.get("contractor_low", 500) if matching_cost else 500
        base_high = matching_cost.get("contractor_high", 2000) if matching_cost else 2000
        base_avg = (base_low + base_high) / 2

        labor_rates = _get_labor_rates(system, zip_code)
        rates_data = ZIP_COST_MODIFIERS.get(zip_code, {})
        material_mult = rates_data.get("avg_material_mult", 1.0)

        finding_bids = []
        for i, profile in enumerate(REAL_CONTRACTOR_PROFILES[:4]):
            specialization_match = 1.0
            if profile["specialty"] == system or profile["specialty"] == "General":
                specialization_match = 1.0
            else:
                specialization_match = 0.85

            experience_factor = 1.0 - (min(profile["years_active"], 25) / 25) * 0.08

            if profile["rating"] >= 4.7:
                quality_premium = 1.05
            elif profile["rating"] >= 4.5:
                quality_premium = 1.00
            else:
                quality_premium = 0.95

            bid_detail = _calculate_bid_detail(
                base_avg, labor_rates, material_mult, severity, system, description
            )
            adjusted_total = bid_detail["total"] * specialization_match * experience_factor * quality_premium

            timeline_info = SEVERITY_TIMELINE_MAP.get(severity, SEVERITY_TIMELINE_MAP["MEDIUM"])
            timeline_days = timeline_info["min_days"] + (
                _deterministic_hash(profile["name"] + system) % (timeline_info["max_days"] - timeline_info["min_days"] + 1)
            )

            rush_total = adjusted_total * 1.65 if timeline_info["rush_available"] else None

            license_number = f"{profile['license_prefix']}-{_deterministic_hash(profile['name'] + zip_code) % 900000 + 100000}"

            bid = {
                "finding_id": finding.get("id"),
                "finding_description": description[:80],
                "system": system,
                "severity": severity,
                "contractor_name": profile["name"],
                "contractor_license": license_number,
                "contractor_rating": profile["rating"],
                "contractor_years": profile["years_active"],
                "contractor_specialty": profile["specialty"],
                "bid_amount": round(adjusted_total, 0),
                "material_cost": bid_detail["material_cost"],
                "labor_cost": bid_detail["labor_cost"],
                "labor_hours": bid_detail["labor_hours"],
                "overhead_cost": bid_detail["overhead"],
                "profit_margin": bid_detail["profit_margin"],
                "permit_cost": bid_detail["permit_cost"],
                "warranty_terms": _get_warranty_for_profile(profile, severity),
                "timeline_days": timeline_days,
                "rush_cost": round(rush_total, 0) if rush_total else None,
                "rush_timeline": max(1, timeline_days // 3) if timeline_info["rush_available"] else None,
                "bid_status": "received",
                "is_lowest": False,
                "is_highest": False,
                "bid_description": f"Complete {system.lower()} repair: {description[:60]}. Includes materials, labor, permits, and warranty.",
                "payment_terms": "50% deposit, 50% on completion" if adjusted_total > 2000 else "Net 30",
                "insurance_verified": True,
                "license_verified": True,
            }
            finding_bids.append(bid)

        if finding_bids:
            finding_bids.sort(key=lambda x: x["bid_amount"])
            finding_bids[0]["is_lowest"] = True
            finding_bids[-1]["is_highest"] = True
            for bid in finding_bids:
                all_bids.append(bid)

    total_findings_bids = set(b["finding_id"] for b in all_bids)
    lowest_total = sum(
        min(b["bid_amount"] for b in all_bids if b["finding_id"] == fid)
        for fid in total_findings_bids
    ) if total_findings_bids else 0
    highest_total = sum(
        max(b["bid_amount"] for b in all_bids if b["finding_id"] == fid)
        for fid in total_findings_bids
    ) if total_findings_bids else 0

    return {
        "all_bids": all_bids,
        "summary": {
            "total_bids_received": len(all_bids),
            "total_findings_with_bids": len(total_findings_bids),
            "avg_bids_per_finding": round(len(all_bids) / max(len(findings), 1), 1),
            "lowest_total": round(lowest_total, 0),
            "highest_total": round(highest_total, 0),
            "average_total": round(sum(b["bid_amount"] for b in all_bids) / max(len(total_findings_bids), 1), 0),
            "potential_savings_range": round(highest_total - lowest_total, 0),
            "avg_material_pct": round(sum(b["material_cost"] for b in all_bids) / max(sum(b["bid_amount"] for b in all_bids), 1) * 100, 1),
            "avg_labor_pct": round(sum(b["labor_cost"] for b in all_bids) / max(sum(b["bid_amount"] for b in all_bids), 1) * 100, 1),
        },
        "by_finding": _group_bids_by_finding(all_bids),
        "cost_breakdown_summary": _generate_cost_breakdown(all_bids),
    }


def _group_bids_by_finding(all_bids):
    grouped = {}
    for bid in all_bids:
        fid = bid["finding_id"]
        if fid not in grouped:
            grouped[fid] = {
                "finding": bid["finding_description"],
                "system": bid["system"],
                "severity": bid["severity"],
                "bids": [],
            }
        grouped[fid]["bids"].append(bid)
    for fid in grouped:
        bids = grouped[fid]["bids"]
        bids.sort(key=lambda x: x["bid_amount"])
        grouped[fid]["recommended_bid"] = bids[0] if bids else None
        grouped[fid]["avg_bid"] = round(sum(b["bid_amount"] for b in bids) / len(bids), 0) if bids else 0
        grouped[fid]["savings_vs_highest"] = bids[-1]["bid_amount"] - bids[0]["bid_amount"] if len(bids) > 1 else 0
        grouped[fid]["bid_spread_pct"] = round(
            (bids[-1]["bid_amount"] - bids[0]["bid_amount"]) / max(bids[0]["bid_amount"], 1) * 100, 1
        ) if len(bids) > 1 else 0
    return grouped


def _generate_cost_breakdown(all_bids):
    total_material = sum(b["material_cost"] for b in all_bids)
    total_labor = sum(b["labor_cost"] for b in all_bids)
    total_overhead = sum(b["overhead_cost"] for b in all_bids)
    total_profit = sum(b["profit_margin"] for b in all_bids)
    total_permits = sum(b["permit_cost"] for b in all_bids)
    grand_total = sum(b["bid_amount"] for b in all_bids)
    return {
        "total_material": round(total_material, 0),
        "total_labor": round(total_labor, 0),
        "total_overhead": round(total_overhead, 0),
        "total_profit": round(total_profit, 0),
        "total_permits": round(total_permits, 0),
        "grand_total": round(grand_total, 0),
        "material_pct": round(total_material / max(grand_total, 1) * 100, 1),
        "labor_pct": round(total_labor / max(grand_total, 1) * 100, 1),
        "overhead_pct": round(total_overhead / max(grand_total, 1) * 100, 1),
        "profit_pct": round(total_profit / max(grand_total, 1) * 100, 1),
    }


def get_contractor_recommendations(bids_by_finding, priority_count=3):
    recommendations = []
    for fid, data in bids_by_finding.items():
        if data.get("severity") in ["CRITICAL", "HIGH"]:
            rec_bid = data.get("recommended_bid")
            if rec_bid:
                recommendations.append({
                    "finding": data["finding"],
                    "system": data["system"],
                    "severity": data["severity"],
                    "recommended_contractor": rec_bid["contractor_name"],
                    "bid_amount": rec_bid["bid_amount"],
                    "rating": rec_bid["contractor_rating"],
                    "years_experience": rec_bid["contractor_years"],
                    "warranty": rec_bid["warranty_terms"],
                    "timeline": f"{rec_bid['timeline_days']} days",
                    "savings_vs_avg": round(data.get("avg_bid", 0) - rec_bid["bid_amount"], 0),
                    "material_breakdown": rec_bid["material_cost"],
                    "labor_breakdown": rec_bid["labor_cost"],
                })
    recommendations.sort(key=lambda x: {"CRITICAL": 1, "HIGH": 2}.get(x["severity"], 3))
    return recommendations[:priority_count]
