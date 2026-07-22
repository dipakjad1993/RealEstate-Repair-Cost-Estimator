from datetime import datetime
from config import SeverityLevels

def generate_legal_addendum(property_data, findings, cost_matrix, selected_items=None):
    address = f"{property_data.get('address', 'N/A')}, {property_data.get('city', 'N/A')}, {property_data.get('state', 'N/A')} {property_data.get('zip_code', 'N/A')}"
    today = datetime.now().strftime("%B %d, %Y")
    if selected_items is None:
        selected_items = [f for f in findings if f.get("severity") in ["CRITICAL", "HIGH"]]
    else:
        selected_items = [item for item in selected_items if item.get("selected", True)]
    seller_repairs = []
    seller_credits = []
    price_reductions = []
    for item in selected_items:
        if isinstance(item, dict):
            system = item.get("system_category", item.get("system", "UNKNOWN"))
            desc = item.get("description", "")
            severity = item.get("severity", "MEDIUM")
            repair_type = item.get("repair_type", "seller_credit")
        else:
            system = "UNKNOWN"
            desc = str(item)[:200]
            severity = "MEDIUM"
            repair_type = "seller_credit"
        cost_est = _get_cost_for_item(item, cost_matrix)
        clause = _generate_repair_clause(system, desc, severity, cost_est, repair_type)
        entry = {
            "system": system,
            "description": desc[:200],
            "severity": severity,
            "repair_type": repair_type,
            "estimated_cost": cost_est,
            "clause_text": clause,
        }
        if repair_type == "seller_repair":
            seller_repairs.append(entry)
        elif repair_type == "seller_credit":
            seller_credits.append(entry)
        else:
            price_reductions.append(entry)
    addendum_text = _assemble_addendum(address, today, seller_repairs, seller_credits, price_reductions, property_data)
    return {
        "addendum_type": "Repair Request Addendum (RR)",
        "addendum_text": addendum_text,
        "address": address,
        "date": today,
        "seller_repairs": seller_repairs,
        "seller_credits": seller_credits,
        "price_reductions": price_reductions,
        "total_repair_items": len(seller_repairs),
        "total_credit_items": len(seller_credits),
        "total_reduction_items": len(price_reductions),
        "total_requested_value": sum(
            e["estimated_cost"] for e in seller_repairs + seller_credits + price_reductions
        ),
    }

def _get_cost_for_item(item, cost_matrix):
    if isinstance(item, dict):
        if item.get("estimated_cost"):
            return item["estimated_cost"]
        if item.get("override_amount"):
            return item["override_amount"]
    desc = item.get("description", "")[:40] if isinstance(item, dict) else ""
    for line in cost_matrix.get("line_items", []):
        if line.get("finding", "")[:40] == desc or line.get("system", "") == item.get("system_category", ""):
            return line.get("total_avg", 0)
    return 0

def _generate_repair_clause(system, description, severity, cost_est, repair_type):
    system_lower = system.lower() if system else "component"
    truncated_desc = description[:150] + "..." if len(description) > 150 else description
    if repair_type == "seller_repair":
        clause = (
            f"Seller shall, prior to the close of escrow, cause the {system_lower} deficiency "
            f"as described in the inspection report ({truncated_desc}) to be repaired by a "
            f"licensed and insured {system_lower} contractor, at Seller's sole cost and expense. "
            f"Seller shall provide Buyer with copies of all receipts, warranties, and proof of "
            f"permits (if applicable) for said repairs within five (5) business days of completion. "
            f"Repair estimates averaged at approximately ${cost_est:,.0f}."
        )
    elif repair_type == "seller_credit":
        clause = (
            f"Seller shall credit Buyer in the amount of ${cost_est:,.0f} at closing for the "
            f"{system_lower} deficiency as described in the inspection report ({truncated_desc}). "
            f"This credit is intended to offset Buyer's cost for future repair or replacement of "
            f"said item. This credit shall be applied as a reduction to the purchase price or as "
            f"a direct credit to Buyer on the closing settlement statement (HUD-1/Closing Disclosure)."
        )
    else:
        clause = (
            f"The parties agree to reduce the purchase price by ${cost_est:,.0f} to account for "
            f"the {system_lower} deficiency as described in the inspection report ({truncated_desc}). "
            f"This reduction shall be reflected on the closing settlement statement."
        )
    return clause

def _assemble_addendum(address, date, repairs, credits, reductions, property_data):
    buyer_name = "[BUYER NAME]"
    seller_name = "[SELLER NAME]"
    text = f"""
{'='*80}
REAL ESTATE REPAIR REQUEST ADDENDUM
Property Address: {address}
Date: {date}
{'='*80}

This Repair Request Addendum ("Addendum") is made part of the Purchase and Sale
Agreement dated ____________ between {buyer_name} ("Buyer") and {seller_name} ("Seller")
for the property located at {address} ("Property").

WHEREAS, a professional home inspection of the Property was conducted and certain
deficiencies were identified; and

WHEREAS, the parties wish to memorialize their agreement regarding the repair,
credit, or price adjustment for said deficiencies;

NOW, THEREFORE, the parties agree as follows:

"""
    if repairs:
        text += f"""
ARTICLE I - SELLER-REPAIRED ITEMS ({len(repairs)} items, Est. Total: ${sum(r["estimated_cost"] for r in repairs):,.0f})
{'─'*80}
Seller agrees to repair the following items at Seller's sole cost and expense prior
to the close of escrow:

"""
        for idx, item in enumerate(repairs, 1):
            text += f"""
  Item {idx}: {item['system'].upper()} - Severity: {item['severity']}
  Description: {item['description'][:200]}
  Estimated Cost: ${item['estimated_cost']:,.0f}

  Contractual Obligation: {item['clause_text']}

"""
        text += """
  Additional Terms for Seller-Repaired Items:
  (a) All repairs must be performed by licensed and insured contractors.
  (b) Seller must obtain all required municipal permits and pass final inspection.
  (c) Seller must provide Buyer with copies of permits, receipts, and warranties.
  (d) Buyer reserves the right to conduct a re-inspection of repaired items at Seller's expense.

"""
    if credits:
        text += f"""
ARTICLE II - SELLER CREDIT ITEMS ({len(credits)} items, Est. Total: ${sum(c["estimated_cost"] for c in credits):,.0f})
{'─'*80}
Seller agrees to provide Buyer with a monetary credit at closing for the following items:

"""
        for idx, item in enumerate(credits, 1):
            text += f"""
  Item {idx}: {item['system'].upper()} - Severity: {item['severity']}
  Description: {item['description'][:200]}
  Credit Amount: ${item['estimated_cost']:,.0f}

  Contractual Obligation: {item['clause_text']}

"""
        total_credit = sum(c["estimated_cost"] for c in credits)
        text += f"""
  Total Seller Credit at Closing: ${total_credit:,.0f}
  Credit Application: Reduction to purchase price on settlement statement.

"""
    if reductions:
        text += f"""
ARTICLE III - PURCHASE PRICE REDUCTIONS ({len(reductions)} items, Est. Total: ${sum(r["estimated_cost"] for r in reductions):,.0f})
{'─'*80}
The parties agree to the following purchase price adjustments:

"""
        for idx, item in enumerate(reductions, 1):
            text += f"""
  Item {idx}: {item['system'].upper()} - Severity: {item['severity']}
  Description: {item['description'][:200]}
  Price Reduction: ${item['estimated_cost']:,.0f}

  Contractual Obligation: {item['clause_text']}

"""
        total_reduction = sum(r["estimated_cost"] for r in reductions)
        text += f"""
  Total Purchase Price Reduction: ${total_reduction:,.0f}

"""
    total_all = sum(r["estimated_cost"] for r in repairs + credits + reductions)
    text += f"""
ARTICLE IV - GENERAL PROVISIONS
{'─'*80}

1. TOTAL FINANCIAL IMPACT: The total estimated financial impact of this Addendum
   is ${total_all:,.0f} (repairs: ${sum(r["estimated_cost"] for r in repairs):,.0f},
   credits: ${sum(c["estimated_cost"] for c in credits):,.0f},
   reductions: ${sum(r["estimated_cost"] for r in reductions):,.0f}).

2. TIME IS OF THE ESSENCE: All repairs must be completed prior to close of escrow
   unless otherwise agreed in writing.

3. FAILURE TO PERFORM: If Seller fails to complete the agreed-upon repairs, Buyer
   may, at Buyer's option: (a) extend the closing date by up to fifteen (15) days;
   (b) accept the equivalent monetary credit; or (c) terminate this Agreement and
   receive a full refund of the earnest money deposit.

4. RE-INSPECTION: Buyer reserves the right to re-inspect the Property after repairs
   are completed, at Buyer's expense, to verify that repairs have been performed
   in a workmanlike manner and in compliance with all applicable codes.

5. WARRANTY: All repairs shall include a minimum one (1) year workmanship warranty.
   Seller shall assign all manufacturer warranties to Buyer where applicable.

6. PERMITS AND CODE COMPLIANCE: All repairs requiring municipal permits shall be
   performed with proper permits and shall pass final municipal inspection.

7. This Addendum is incorporated into and made part of the Purchase and Sale
   Agreement. In the event of a conflict between this Addendum and the original
   Agreement, the terms of this Addendum shall control.


BUYER: _____________________________    DATE: _____________
       {buyer_name}

SELLER: _____________________________   DATE: _____________
        {seller_name}


{'='*80}
DISCLAIMER: This addendum was generated by automated analysis software and is
provided as a template for real estate professionals. It should be reviewed by
a licensed attorney in the applicable jurisdiction before execution. This document
does not constitute legal advice.
{'='*80}
"""
    return text.strip()

def generate_escrow_holdback_agreement(property_data, high_risk_findings, contractor_bids):
    address = f"{property_data.get('address', 'N/A')}, {property_data.get('city', 'N/A')}, {property_data.get('state', 'N/A')} {property_data.get('zip_code', 'N/A')}"
    today = datetime.now().strftime("%B %d, %Y")
    items = []
    total_holdback = 0
    for finding in high_risk_findings:
        bid = _get_best_bid(finding, contractor_bids)
        bid_amount = bid.get("bid_amount", 0) if bid else finding.get("estimated_cost_avg", 0)
        holdback = bid_amount * 1.5
        total_holdback += holdback
        items.append({
            "finding": finding.get("description", "")[:100],
            "system": finding.get("system_category", "OTHER"),
            "severity": finding.get("severity", "HIGH"),
            "contractor_bid": round(bid_amount, 0),
            "holdback_amount": round(holdback, 0),
            "release_conditions": _generate_release_conditions(finding),
            "milestone_1": "50% upon commencement of repairs by licensed contractor",
            "milestone_1_pct": 50,
            "milestone_2": "50% upon completion, final inspection, and Buyer written approval",
            "milestone_2_pct": 50,
        })
    return {
        "property_address": address,
        "date": today,
        "items": items,
        "total_holdback": round(total_holdback, 0),
        "holdback_multiplier": 1.5,
    }

def _get_best_bid(finding, contractor_bids):
    matching = [b for b in contractor_bids if b.get("finding_id") == finding.get("id")]
    if matching:
        matching.sort(key=lambda x: x.get("bid_amount", float("inf")))
        return matching[0]
    return None

def _generate_release_conditions(finding):
    system = finding.get("system_category", "OTHER")
    conditions = {
        "ROOF": "Paid to licensed roofer upon city inspection sign-off and warranty documentation.",
        "PLUMBING": "Paid to licensed plumber upon city sign-off and scope video verification.",
        "ELECTRICAL": "Paid to licensed electrician upon city inspection and permit closure.",
        "HVAC": "Paid to licensed HVAC contractor upon mechanical inspection sign-off.",
        "STRUCTURAL": "Paid upon independent engineer structural certification post-repair.",
        "EXTERIOR": "Paid upon completion and Buyer written inspection approval.",
    }
    return conditions.get(system, "Paid upon completion, inspection, and Buyer written approval.")
