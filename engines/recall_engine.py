import json
from config import MANUFACTURER_RECALLS

def check_recalls_for_findings(findings):
    results = []
    for finding in findings:
        desc = finding.get("description", "").lower()
        subsystem = finding.get("subsystem", "").lower()
        for recall in MANUFACTURER_RECALLS:
            model_pattern = recall.get("model_pattern", "").lower()
            manufacturer = recall.get("manufacturer", "").lower()
            product = recall.get("product", "").lower()
            matched = False
            if manufacturer in desc:
                matched = True
            if any(part in desc for part in model_pattern.split("|")):
                matched = True
            if product in desc and manufacturer in desc:
                matched = True
            if any(kw in desc for kw in [manufacturer, product]) and any(kw in desc for kw in model_pattern.split("|")):
                matched = True
            if matched:
                results.append({
                    "finding_id": finding.get("id"),
                    "finding_description": finding.get("description", "")[:100],
                    "system": finding.get("system_category", "OTHER"),
                    "manufacturer": recall["manufacturer"],
                    "model_pattern": recall.get("model_pattern", ""),
                    "product_type": recall.get("product", ""),
                    "recall_type": recall.get("recall_type", "Unknown"),
                    "recall_status": recall.get("status", "Check"),
                    "claim_url": recall.get("claim_url", ""),
                    "description": recall.get("description", ""),
                    "remedy": recall.get("remedy", ""),
                    "cost_savings": _estimate_recall_savings(finding),
                    "action_required": _get_recall_action(recall),
                })
                break
    total_savings = sum(r["cost_savings"] for r in results)
    recalls_found = len(results)
    return {
        "recall_results": results,
        "summary": {
            "total_recalls_checked": len(MANUFACTURER_RECALLS),
            "matches_found": recalls_found,
            "total_potential_savings": round(total_savings, 0),
            "active_recalls": len([r for r in results if r["recall_status"] == "Active"]),
            "check_required": len([r for r in results if r["recall_status"] == "Check"]),
        },
    }

def _estimate_recall_savings(finding):
    severity = finding.get("severity", "MEDIUM")
    savings_map = {
        "CRITICAL": 2500,
        "HIGH": 1800,
        "MEDIUM": 1200,
        "LOW": 600,
    }
    return savings_map.get(severity, 800)

def _get_recall_action(recall):
    status = recall.get("status", "Check")
    if status == "Active":
        return "ACTIVE RECALL: File claim immediately. Replacement may be free under recall program."
    else:
        return "CHECK ELIGIBILITY: Verify serial number against recall database before proceeding with repair."
