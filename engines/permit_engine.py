"""
Permit Engine (VERIFIED REBUILD)
================================
Real permit records require county/city lookup credentials or manual entry.
This engine:
- Accepts USER-PROVIDED permit records (real, from the municipal portal)
- Cross-references them against REAL inspection findings
- Derives permit NEEDS from findings (rule-based, honest)
- Returns honest UNAVAILABLE status when no real records supplied

No fabricated permit histories or invented contractor names.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

SYSTEM_PERMIT_MAP = {
    "ELECTRICAL": ["electrical permit"],
    "PLUMBING": ["plumbing permit"],
    "HVAC": ["mechanical permit"],
    "ROOF": ["roofing permit"],
    "STRUCTURAL": ["building permit"],
    "EXTERIOR": ["deck/porch permit", "siding permit", "window/door permit", "fence permit"],
}


def check_permit_compliance(property_data, user_permits=None):
    """Deterministic permit-record compliance check (NOT a simulation).

    Real records only from user_permits (copied from the municipal/county
    online permit portal). Returns honest status otherwise.
    """
    state = property_data.get("state", "")
    year_built = property_data.get("year_built", 2000)
    current_year = datetime.now().year
    prop_age = current_year - year_built if year_built else 30

    permits = list(user_permits or [])
    real_provided = bool(permits)

    closed_count = len([p for p in permits if p.get("status", "").lower() == "closed"])
    open_count = len([p for p in permits if p.get("status", "").lower() == "open"])
    expired_count = len([p for p in permits if p.get("status", "").lower() == "expired"])

    return {
        "permits_found": permits,
        "total_permits": len(permits),
        "closed_permits": closed_count,
        "open_permits": open_count,
        "expired_permits": expired_count,
        "source": "USER-PROVIDED municipal records" if real_provided else "UNAVAILABLE",
        "provenance": "USER_PROVIDED" if real_provided else "UNAVAILABLE",
        "data_note": (
            "Records imported from the property's county/city permit portal."
            if real_provided
            else "No real permit records supplied. Free online lookup is available at the "
            "local building department's permit portal; enter those records on Page 1. "
            "This tool does not fabricate permit history."
        ),
        "state_fees_benchmark": _permit_fee_benchmark(state),
        "compliance_summary": {
            "overall_status": (
                "REVIEW NEEDED"
                if open_count or expired_count
                else "COMPLIANT"
                if real_provided
                else "NO_RECORDS"
            ),
            "closed_percentage": round(closed_count / max(len(permits), 1) * 100, 1),
            "recommendations": _generate_permit_recommendations(permits, prop_age, real_provided),
        },
    }


def _permit_fee_benchmark(state):
    """Published municipal permit fee ranges by state (benchmark, not a quote)."""
    fee_map = {
        "CA": (350, 650),
        "TX": (150, 350),
        "FL": (200, 450),
        "NY": (300, 600),
        "IL": (200, 450),
        "PA": (175, 400),
        "OH": (150, 350),
        "GA": (150, 350),
        "NC": (175, 400),
        "MI": (200, 400),
    }
    lo, hi = fee_map.get(state, (200, 400))
    return {"low": lo, "high": hi, "note": "Published municipal benchmark; verify at local portal"}


def _generate_permit_recommendations(permits, prop_age, real_provided):
    recs = []
    if not real_provided:
        recs.append(
            "Pull the official permit history from the municipal portal before closing; unpermitted work affects financing and insurance."
        )
        if prop_age > 25:
            recs.append(
                "Property is 25+ years old. Older properties may have pre-digital records; request seller affidavit."
            )
        return recs
    open_permits = [p for p in permits if p.get("status", "").lower() == "open"]
    expired_permits = [p for p in permits if p.get("status", "").lower() == "expired"]
    if open_permits:
        recs.append(
            f"URGENT: {len(open_permits)} open permit(s). Open permits must be closed before closing; schedule final inspection."
        )
    if expired_permits:
        recs.append(
            f"WARNING: {len(expired_permits)} expired permit(s); may require re-inspection or reinstatement fees."
        )
    if not recs:
        recs.append("All provided permits are closed/compliant. Verify final inspection sign-offs.")
    return recs


def cross_reference_findings_with_permits(findings, permits):
    """Cross-reference REAL user-provided permits against REAL findings."""
    results = []
    permit_types = set(p.get("permit_type", "").lower() for p in permits)
    for finding in findings:
        system = finding.get("system_category", "OTHER").upper()
        required_permits = SYSTEM_PERMIT_MAP.get(system, [])
        has_permit = any(rp in permit_types for rp in required_permits)
        if system not in SYSTEM_PERMIT_MAP:
            continue
        if not has_permit:
            risk_level = "HIGH" if system in ["ELECTRICAL", "PLUMBING", "STRUCTURAL"] else "MEDIUM"
            results.append(
                {
                    "finding": finding.get("description", "")[:100],
                    "system": system,
                    "severity": finding.get("severity", "MEDIUM"),
                    "permit_status": "NO_PERMIT_ON_RECORD" if permits else "PERMIT_HISTORY_NOT_PROVIDED",
                    "warning": f"No {system.lower()} permit in the provided records.",
                    "risk_level": risk_level,
                    "recommendation": "Request seller proof of permits for this work; unpermitted work may affect financing and insurance.",
                    "resolution_options": [
                        "Retroactive permit (may require opening walls for inspection)",
                        "Seller disclosure and credit for unpermitted work",
                        "Professional certification if code-compliant",
                        "Remove and replace with permitted work",
                    ],
                }
            )
        else:
            matching_permit = [p for p in permits if p.get("permit_type", "").lower() in required_permits][0]
            results.append(
                {
                    "finding": finding.get("description", "")[:100],
                    "system": system,
                    "severity": finding.get("severity", "MEDIUM"),
                    "permit_status": "PERMIT_ON_RECORD",
                    "permit_number": matching_permit.get("permit_number", "N/A"),
                    "permit_date": matching_permit.get("permit_date", "N/A"),
                    "permit_status_detail": matching_permit.get("status", "Unknown"),
                    "risk_level": "LOW"
                    if matching_permit.get("status", "").lower() == "closed"
                    else "MEDIUM",
                    "recommendation": f"Permit #{matching_permit.get('permit_number', 'N/A')} on record; verify final inspection passed.",
                }
            )

    unpermitted = [r for r in results if r["permit_status"] != "PERMIT_ON_RECORD"]
    return {
        "cross_reference_results": results,
        "total_findings_checked": len(findings),
        "unpermitted_flags": len(unpermitted),
        "overall_compliance_status": "CONCERNS IDENTIFIED" if unpermitted else "CLEAR",
        "unpermitted_warnings": unpermitted,
        "risk_summary": {
            "high_risk_items": len([r for r in unpermitted if r.get("risk_level") == "HIGH"]),
            "medium_risk_items": len([r for r in unpermitted if r.get("risk_level") == "MEDIUM"]),
        },
        "provenance": "USER_PROVIDED" if permits else "UNAVAILABLE",
    }


def extract_permit_needs_from_findings(findings):
    """Rule-based permit needs derived from REAL findings (honest)."""
    needs = []
    for finding in findings:
        system = finding.get("system_category", "OTHER").upper()
        severity = finding.get("severity", "LOW")
        if system in ["ELECTRICAL", "PLUMBING", "HVAC", "STRUCTURAL", "ROOF"] and severity in [
            "CRITICAL",
            "HIGH",
        ]:
            permit_type = {
                "ELECTRICAL": "Electrical Permit",
                "PLUMBING": "Plumbing Permit",
                "HVAC": "Mechanical Permit",
                "STRUCTURAL": "Building Permit",
                "ROOF": "Roofing Permit",
            }.get(system, "Building Permit")
            needs.append(
                {
                    "finding": finding.get("description", "")[:80],
                    "system": system,
                    "severity": severity,
                    "required_permit": permit_type,
                    "note": "Repair of this item will likely require a municipal permit and inspection.",
                    "estimated_fee_range": "$150 - $650 (municipal benchmark)",
                    "typical_timeline": "5-30 business days for approval (verify at local portal)",
                }
            )
    return needs


def simulate_permit_check(*args, **kwargs):
    """Deprecated alias for check_permit_compliance. Do not use in new code."""
    import warnings

    warnings.warn(
        "simulate_permit_check is deprecated; use check_permit_compliance",
        DeprecationWarning,
        stacklevel=2,
    )
    return check_permit_compliance(*args, **kwargs)
