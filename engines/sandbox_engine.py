from datetime import datetime

def create_sandbox_session(property_data, findings, cost_matrix):
    items = []
    for finding in findings:
        matching_cost = None
        for item in cost_matrix.get("line_items", []):
            if item.get("finding", "")[:40] in finding.get("description", "")[:40]:
                matching_cost = item
                break
        if not matching_cost:
            matching_cost = cost_matrix.get("line_items", [{}])[0] if cost_matrix.get("line_items") else {}
        items.append({
            "finding_id": finding.get("id"),
            "description": finding.get("description", "")[:120],
            "system": finding.get("system_category", "OTHER"),
            "severity": finding.get("severity", "MEDIUM"),
            "selected": finding.get("severity", "MEDIUM") in ["CRITICAL", "HIGH"],
            "repair_type": "seller_credit",
            "estimated_cost": matching_cost.get("total_avg", 0),
            "estimated_low": matching_cost.get("total_low", 0),
            "estimated_high": matching_cost.get("total_high", 0),
            "notes": "",
            "override_amount": None,
        })
    return {
        "property": property_data,
        "items": items,
        "created_at": datetime.now().isoformat(),
    }

def calculate_sandbox_totals(items, market_profile=None):
    selected_items = [i for i in items if i.get("selected", False)]
    total_requested = 0
    total_low = 0
    total_high = 0
    by_repair_type = {"seller_credit": 0, "seller_repair": 0, "price_reduction": 0, "waived": 0}
    by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for item in selected_items:
        override = item.get("override_amount")
        amount = override if override is not None else item.get("estimated_cost", 0)
        total_requested += amount
        total_low += item.get("estimated_low", 0)
        total_high += item.get("estimated_high", 0)
        repair_type = item.get("repair_type", "seller_credit")
        by_repair_type[repair_type] = by_repair_type.get(repair_type, 0) + amount
        severity = item.get("severity", "MEDIUM")
        by_severity[severity] = by_severity.get(severity, 0) + amount
    leverage = market_profile.get("leverage_score", 50) if market_profile else 50
    if leverage < 35:
        expected_concession = total_requested * 0.45
    elif leverage < 55:
        expected_concession = total_requested * 0.65
    else:
        expected_concession = total_requested * 0.82
    return {
        "total_items": len(items),
        "selected_items": len(selected_items),
        "total_requested": round(total_requested, 0),
        "total_low_range": round(total_low, 0),
        "total_high_range": round(total_high, 0),
        "by_repair_type": by_repair_type,
        "by_severity": by_severity,
        "expected_concession": round(expected_concession, 0),
        "expected_concession_pct": round((expected_concession / max(total_requested, 1)) * 100, 0),
        "market_leverage": leverage,
    }

def update_item_selection(items, item_index, selected, repair_type=None, override_amount=None, notes=None):
    if 0 <= item_index < len(items):
        items[item_index]["selected"] = selected
        if repair_type:
            items[item_index]["repair_type"] = repair_type
        if override_amount is not None:
            items[item_index]["override_amount"] = override_amount
        if notes is not None:
            items[item_index]["notes"] = notes
    return items

def generate_scenario_comparison(items, scenarios, market_profile=None):
    results = []
    for scenario in scenarios:
        modified_items = []
        for item in items:
            mod_item = item.copy()
            for change in scenario.get("changes", []):
                if change.get("system", "").upper() == item.get("system", "").upper():
                    if "selected" in change:
                        mod_item["selected"] = change["selected"]
                    if "repair_type" in change:
                        mod_item["repair_type"] = change["repair_type"]
                    if "override_amount" in change:
                        mod_item["override_amount"] = change["override_amount"]
            modified_items.append(mod_item)
        totals = calculate_sandbox_totals(modified_items, market_profile)
        results.append({
            "scenario_name": scenario.get("name", "Unnamed"),
            "scenario_description": scenario.get("description", ""),
            "totals": totals,
        })
    return results
