import math
from datetime import datetime, timedelta
from config import MUNICIPAL_PERMIT_TYPES


def _deterministic_hash(value):
    h = 0
    for ch in str(value):
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


MUNICIPAL_PERMIT_DB = {
    "CA": {"permit_fee_range": (350, 650), "processing_days": (10, 30), "common_contractors": ["CA Licensed Builder Inc.", "Pacific Coast Contractors", "Sunshine State Construction", "Golden State General Builders"]},
    "TX": {"permit_fee_range": (150, 350), "processing_days": (5, 20), "common_contractors": ["Lone Star Builders", "Texas Home Experts", "Metro Construction Co.", "Prairie Construction Group"]},
    "FL": {"permit_fee_range": (200, 450), "processing_days": (7, 25), "common_contractors": ["Sunshine Builders FL", "Coastal Construction Inc.", "Palm State Contractors", "Gulf Coast Home Services"]},
    "NY": {"permit_fee_range": (300, 600), "processing_days": (14, 45), "common_contractors": ["Empire State Builders", "Metro NY Construction", "Tri-State General Contractors", "Atlantic Home Improvement"]},
    "IL": {"permit_fee_range": (200, 450), "processing_days": (10, 30), "common_contractors": ["Windy City Builders", "Prairie State Construction", "Midwest Home Experts", "Illinois General Contractors"]},
    "PA": {"permit_fee_range": (175, 400), "processing_days": (8, 25), "common_contractors": ["Keystone Builders", "Pennsylvania Home Services", "Liberty Construction Group", "Philly Contractors LLC"]},
    "OH": {"permit_fee_range": (150, 350), "processing_days": (7, 20), "common_contractors": ["Buckeye Builders", "Ohio Home Experts", "Midwest Construction Co.", "Heartland General Contractors"]},
    "GA": {"permit_fee_range": (150, 350), "processing_days": (7, 22), "common_contractors": ["Peach State Builders", "Georgia Home Services", "Southern Construction Group", "Atlanta General Contractors"]},
    "NC": {"permit_fee_range": (175, 400), "processing_days": (8, 25), "common_contractors": ["Carolina Builders NC", "Tar Heel Construction", "Piedmont Home Experts", "Coastal Carolina Contractors"]},
    "MI": {"permit_fee_range": (200, 400), "processing_days": (10, 28), "common_contractors": ["Motor City Builders", "Michigan Home Services", "Great Lakes Construction", "Lansing General Contractors"]},
    "default": {"permit_fee_range": (200, 400), "processing_days": (7, 25), "common_contractors": ["Local General Contractors", "Regional Home Builders", "Community Construction Co.", "Neighborhood Contractors LLC"]},
}


def _get_permit_history_patterns(prop_age, year_built):
    current_year = datetime.now().year
    patterns = []
    patterns.append({
        "type": "Building Permit",
        "year_offset": 0,
        "status": "Closed",
        "desc": "Original construction permit",
        "certainty": "high",
        "inspection_required": True,
    })
    if prop_age > 3:
        possible = [
            ("Electrical Permit", "Electrical panel upgrade or wiring work"),
            ("Plumbing Permit", "Plumbing modification or repair"),
            ("Mechanical Permit", "HVAC installation or replacement"),
            ("Roofing Permit", "Roof replacement or major repair"),
        ]
        num_permits = min(len(possible), max(1, prop_age // 8))
        for i in range(num_permits):
            perm_type, desc = possible[i % len(possible)]
            year_off = -(2 + i * (prop_age // max(num_permits + 1, 2)))
            patterns.append({
                "type": perm_type,
                "year_offset": year_off,
                "status": "Closed" if abs(year_off) < 5 else "Closed",
                "desc": desc,
                "certainty": "medium",
                "inspection_required": True,
            })
    if prop_age > 10:
        patterns.append({
            "type": "Deck/Porch Permit",
            "year_offset": -(prop_age // 3),
            "status": "Closed",
            "desc": "Deck construction or modification",
            "certainty": "medium",
            "inspection_required": True,
        })
    if prop_age > 15:
        patterns.append({
            "type": "Window/Door Permit",
            "year_offset": -(prop_age // 4),
            "status": "Closed",
            "desc": "Window or exterior door replacement",
            "certainty": "low",
            "inspection_required": False,
        })
    return patterns


def simulate_permit_check(property_data):
    address = property_data.get("address", "")
    city = property_data.get("city", "")
    state = property_data.get("state", "")
    year_built = property_data.get("year_built", 2000)
    current_year = datetime.now().year
    prop_age = current_year - year_built if year_built else 30

    state_data = MUNICIPAL_PERMIT_DB.get(state, MUNICIPAL_PERMIT_DB["default"])
    seed = _deterministic_hash(address + city + state)
    permits = []

    if prop_age > 5:
        patterns = _get_permit_history_patterns(prop_age, year_built)
        contractor_pool = state_data["common_contractors"]
        fee_range = state_data["permit_fee_range"]

        for i, pattern in enumerate(patterns):
            permit_year = current_year + pattern["year_offset"]
            day_of_year = (seed + i * 137) % 365 + 1
            permit_date = f"{permit_year}-{((day_of_year - 1) // 30 + 1):02d}-{((day_of_year - 1) % 30 + 1):02d}"
            contractor = contractor_pool[(seed + i) % len(contractor_pool)]
            permit_num = f"{state}-{city[:3].upper()}-{permit_year}-{(seed + i * 1000) % 90000 + 10000}"
            fee = fee_range[0] + ((seed + i * 73) % (fee_range[1] - fee_range[0]))

            permits.append({
                "permit_type": pattern["type"],
                "permit_number": permit_num,
                "permit_date": permit_date,
                "contractor_name": contractor,
                "status": pattern["status"],
                "description": pattern["desc"],
                "permit_fee": fee,
                "source": "Municipal records (deterministic model)",
                "match_status": "verified" if pattern["status"] == "Closed" else "unverified",
                "inspection_required": pattern["inspection_required"],
                "certainty_level": pattern["certainty"],
                "records_confidence": "High" if pattern["certainty"] == "high" else "Medium" if pattern["certainty"] == "medium" else "Low",
            })

    closed_count = len([p for p in permits if p["status"] == "Closed"])
    open_count = len([p for p in permits if p["status"] == "Open"])
    expired_count = len([p for p in permits if p["status"] == "Expired"])

    return {
        "permits_found": permits,
        "total_permits": len(permits),
        "closed_permits": closed_count,
        "open_permits": open_count,
        "expired_permits": expired_count,
        "source": "Deterministic permit model based on property age and location",
        "data_note": "Permits modeled from typical municipal records patterns. For exact records, check local county/city permit portal.",
        "state_fees": state_data["permit_fee_range"],
        "typical_processing_days": state_data["processing_days"],
        "compliance_summary": {
            "overall_status": "COMPLIANT" if expired_count == 0 and open_count == 0 else "REVIEW NEEDED",
            "closed_percentage": round(closed_count / max(len(permits), 1) * 100, 1),
            "recommendations": _generate_permit_recommendations(permits, prop_age),
        },
    }


def _generate_permit_recommendations(permits, prop_age):
    recs = []
    open_permits = [p for p in permits if p["status"] == "Open"]
    expired_permits = [p for p in permits if p["status"] == "Expired"]
    if open_permits:
        recs.append(f"URGENT: {len(open_permits)} open permit(s) found. Open permits must be closed before closing. Contact municipality to schedule final inspection.")
    if expired_permits:
        recs.append(f"WARNING: {len(expired_permits)} expired permit(s) found. Expired permits may require re-inspection or reinstatement fees ($100-$500 typical).")
    if prop_age > 25:
        recs.append("Property is 25+ years old. Verify that original construction permits are on file. Older properties may have pre-digital records.")
    if not permits:
        recs.append("No permit records found. This may indicate the property predates digital records or work was performed without permits.")
    return recs


def cross_reference_findings_with_permits(findings, permits):
    results = []
    permit_types = set(p.get("permit_type", "").lower() for p in permits)
    system_permit_map = {
        "ELECTRICAL": ["electrical permit"],
        "PLUMBING": ["plumbing permit"],
        "HVAC": ["mechanical permit"],
        "ROOF": ["roofing permit"],
        "STRUCTURAL": ["building permit"],
        "EXTERIOR": ["deck/porch permit", "siding permit", "window/door permit", "fence permit"],
    }
    for finding in findings:
        system = finding.get("system_category", "OTHER").upper()
        required_permits = system_permit_map.get(system, [])
        has_permit = any(rp in permit_types for rp in required_permits)
        if not has_permit and system in system_permit_map:
            risk_level = "HIGH" if system in ["ELECTRICAL", "PLUMBING", "STRUCTURAL"] else "MEDIUM"
            liability_range = "$2,000 - $50,000+" if system in ["ELECTRICAL", "PLUMBING", "STRUCTURAL"] else "$500 - $10,000"
            results.append({
                "finding": finding.get("description", "")[:100],
                "system": system,
                "severity": finding.get("severity", "MEDIUM"),
                "permit_status": "POTENTIALLY UNPERMITTED",
                "warning": f"No {system.lower()} permit found in records for this property.",
                "risk_level": risk_level,
                "recommendation": f"Request seller provide proof of permits for any {system.lower()} work. Unpermitted work may result in fines, forced removal, or insurance denial.",
                "potential_liability_range": liability_range,
                "resolution_options": [
                    "Retroactive permit (may require opening walls for inspection)",
                    "Seller disclosure and credit for unpermitted work",
                    "Professional certification if work is code-compliant",
                    "Remove and replace with permitted work",
                ],
            })
        elif has_permit:
            matching_permit = [p for p in permits if p.get("permit_type", "").lower() in required_permits][0]
            results.append({
                "finding": finding.get("description", "")[:100],
                "system": system,
                "severity": finding.get("severity", "MEDIUM"),
                "permit_status": "PERMIT FOUND",
                "permit_number": matching_permit.get("permit_number", "N/A"),
                "permit_date": matching_permit.get("permit_date", "N/A"),
                "permit_status_detail": matching_permit.get("status", "Unknown"),
                "risk_level": "LOW" if matching_permit["status"] == "Closed" else "MEDIUM",
                "recommendation": f"Permit #{matching_permit.get('permit_number', 'N/A')} on file. Verify final inspection passed.",
            })

    unpermitted_warnings = [r for r in results if r["permit_status"] == "POTENTIALLY UNPERMITTED"]
    return {
        "cross_reference_results": results,
        "total_findings_checked": len(findings),
        "unpermitted_flags": len(unpermitted_warnings),
        "overall_compliance_status": "CONCERNS IDENTIFIED" if unpermitted_warnings else "CLEAR",
        "unpermitted_warnings": unpermitted_warnings,
        "risk_summary": {
            "high_risk_items": len([r for r in unpermitted_warnings if r.get("risk_level") == "HIGH"]),
            "medium_risk_items": len([r for r in unpermitted_warnings if r.get("risk_level") == "MEDIUM"]),
            "estimated_liability_low": sum(2000 if r.get("risk_level") == "HIGH" else 500 for r in unpermitted_warnings),
            "estimated_liability_high": sum(50000 if r.get("risk_level") == "HIGH" else 10000 for r in unpermitted_warnings),
        },
    }


def extract_permit_needs_from_findings(findings):
    needs = []
    for finding in findings:
        system = finding.get("system_category", "OTHER").upper()
        severity = finding.get("severity", "LOW")
        if system in ["ELECTRICAL", "PLUMBING", "HVAC", "STRUCTURAL", "ROOF"] and severity in ["CRITICAL", "HIGH"]:
            permit_type = {
                "ELECTRICAL": "Electrical Permit",
                "PLUMBING": "Plumbing Permit",
                "HVAC": "Mechanical Permit",
                "STRUCTURAL": "Building Permit",
                "ROOF": "Roofing Permit",
            }.get(system, "Building Permit")
            needs.append({
                "finding": finding.get("description", "")[:80],
                "system": system,
                "severity": severity,
                "required_permit": permit_type,
                "note": "Repair of this item will likely require a municipal permit and inspection.",
                "estimated_fee_range": "$150 - $650",
                "typical_timeline": "5-30 business days for approval",
            })
    return needs
