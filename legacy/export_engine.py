import csv
import io
from datetime import datetime

from config import SeverityLevels

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def format_currency(amount):
    if amount >= 1000000:
        return f"${amount / 1000000:,.2f}M"
    elif amount >= 1000:
        return f"${amount:,.0f}"
    else:
        return f"${amount:,.2f}"


def _safe_list(data):
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items", data.get("findings", data.get("risks", [])))
    return []


def _safe_dict(data, default=None):
    if data is None:
        return default or {}
    if isinstance(data, dict):
        return data
    return default or {}


def _severity_color(sev):
    mapping = {
        "CRITICAL": "#FF453A",
        "HIGH": "#FF9F0A",
        "MEDIUM": "#FFD60A",
        "LOW": "#30D158",
        "INFO": "#0A84FF",
    }
    return mapping.get(str(sev).upper(), "#8E8E93")


def _severity_sort_key(x):
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    return order.get(str(x).upper(), 5)


# ---------------------------------------------------------------------------
# Comprehensive JSON report builder
# ---------------------------------------------------------------------------


def generate_comprehensive_report(
    property_data,
    findings,
    cost_matrix,
    depreciation_data,
    market_profile,
    capex_analysis,
    negotiation_strategies,
    insurance_analysis=None,
    environmental_data=None,
    escrow_data=None,
    permit_data=None,
    recall_data=None,
):
    return {
        "report_metadata": {
            "generated_at": datetime.now().isoformat(),
            "tool_version": "3.0 Enterprise",
            "report_type": "Comprehensive Repair Cost Estimator Analysis",
            "property_address": property_data.get("address", "N/A"),
            "property_city": property_data.get("city", "N/A"),
            "property_state": property_data.get("state", "N/A"),
            "property_zip": property_data.get("zip_code", "N/A"),
        },
        "property_summary": _build_property_summary(property_data),
        "executive_summary": _build_executive_summary(findings, cost_matrix, market_profile, capex_analysis),
        "findings_matrix": _build_findings_matrix(findings, cost_matrix),
        "cost_analysis": cost_matrix.get("summary", {}),
        "depreciation_timeline": depreciation_data,
        "capex_risk_horizon": capex_analysis,
        "market_context": market_profile,
        "negotiation_playbook": negotiation_strategies,
        "insurance_risk_profile": insurance_analysis or [],
        "environmental_risk_profile": environmental_data or [],
        "escrow_holdback_analysis": escrow_data or [],
        "permit_compliance_status": permit_data or [],
        "manufacturer_recall_status": recall_data or [],
    }


def _build_property_summary(property_data):
    year_built = property_data.get("year_built", 0)
    current_year = datetime.now().year
    age = current_year - year_built if year_built > 0 else "Unknown"
    return {
        "address": f"{property_data.get('address', 'N/A')}, {property_data.get('city', 'N/A')}, {property_data.get('state', 'N/A')} {property_data.get('zip_code', 'N/A')}",
        "property_type": property_data.get("property_type", "Single Family"),
        "year_built": year_built,
        "approximate_age": f"{age} years" if isinstance(age, int) else age,
        "square_footage": property_data.get("square_footage", "N/A"),
        "bedrooms": property_data.get("bedrooms", "N/A"),
        "bathrooms": property_data.get("bathrooms", "N/A"),
        "lot_size": property_data.get("lot_size_sqft", "N/A"),
        "foundation_type": property_data.get("foundation_type", "N/A"),
        "roof_type": property_data.get("roof_type", "N/A"),
        "hvac_type": property_data.get("hvac_type", "N/A"),
        "plumbing_type": property_data.get("plumbing_type", "N/A"),
        "electrical_type": property_data.get("electrical_type", "N/A"),
    }


def _build_executive_summary(findings, cost_matrix, market_profile, capex_analysis):
    summary = cost_matrix.get("summary", {})
    severity_breakdown = summary.get("by_severity", {})
    critical = severity_breakdown.get("CRITICAL", 0)
    high = severity_breakdown.get("HIGH", 0)
    medium = severity_breakdown.get("MEDIUM", 0)
    low = severity_breakdown.get("LOW", 0)
    total_items = summary.get("total_items", 0)
    total_low = summary.get("total_low", 0)
    total_high = summary.get("total_high", 0)
    total_avg = summary.get("total_avg", 0)
    market_type = market_profile.get("market_type", "Unknown")
    leverage = market_profile.get("leverage_score", 50)
    weighted_risk = (
        capex_analysis.get("summary", {}).get("weighted_24mo_risk", 0)
        if isinstance(capex_analysis, dict)
        else 0
    )
    if critical > 0:
        urgency = "IMMEDIATE ACTION REQUIRED"
        urgency_detail = (
            f"{critical} critical safety/structural issues demand immediate attention before closing."
        )
    elif high > 2:
        urgency = "HIGH PRIORITY"
        urgency_detail = f"{high} high-priority items require negotiation before or at closing."
    else:
        urgency = "STANDARD PROCESS"
        urgency_detail = "Findings are consistent with typical inspection results for the property age."
    return {
        "urgency": urgency,
        "lines": [
            f"Total Identified Issues: {total_items} ({critical} Critical, {high} High, {medium} Medium, {low} Low)",
            f"Estimated Repair Cost Range: ${total_low:,.0f} - ${total_high:,.0f} (Average: ${total_avg:,.0f})",
            f"24-Month CapEx Risk Exposure: ${weighted_risk:,.0f} weighted probability estimate",
            f"Market Condition: {market_type} (Buyer Leverage Score: {leverage}/100)",
            f"Urgency Level: {urgency}",
            f"Detail: {urgency_detail}",
        ],
        "total_estimated_cost_avg": total_avg,
        "weighted_24mo_risk": weighted_risk,
    }


def _build_findings_matrix(findings, cost_matrix):
    line_items = cost_matrix.get("line_items", [])
    matrix = []
    for finding in findings:
        matching_cost = None
        for item in line_items:
            if finding.get("description", "")[:50] in item.get("finding", "") or item.get(
                "system", ""
            ) == finding.get("system_category", ""):
                matching_cost = item
                break
        if not matching_cost and line_items:
            idx = findings.index(finding)
            if idx < len(line_items):
                matching_cost = line_items[idx]
        matrix.append(
            {
                "system": finding.get("system_category", "N/A"),
                "sub_component": finding.get("subsystem", "N/A"),
                "severity": finding.get("severity", "MEDIUM"),
                "severity_label": SeverityLevels.get(finding.get("severity", "MEDIUM"), {}).get(
                    "label", "Medium"
                ),
                "severity_color": SeverityLevels.get(finding.get("severity", "MEDIUM"), {}).get(
                    "color", "#CA8A04"
                ),
                "location": finding.get("location", "N/A"),
                "description": finding.get("description", ""),
                "estimated_cost_low": matching_cost.get("total_low", 0) if matching_cost else 0,
                "estimated_cost_high": matching_cost.get("total_high", 0) if matching_cost else 0,
                "estimated_cost_avg": matching_cost.get("total_avg", 0) if matching_cost else 0,
                "confidence": finding.get("confidence_score", 0.85),
            }
        )
    return matrix


# ---------------------------------------------------------------------------
# Summary text (enhanced)
# ---------------------------------------------------------------------------


def generate_summary_text(
    property_data,
    findings,
    cost_matrix,
    market_profile,
    insurance_analysis=None,
    environmental_data=None,
    permit_data=None,
    recall_data=None,
    negotiation_strategies=None,
    capex_analysis=None,
    depreciation_data=None,
    escrow_data=None,
    contractor_bids=None,
    spatial_data=None,
    investor_analysis=None,
):
    summary = cost_matrix.get("summary", {})
    line_items = cost_matrix.get("line_items", [])
    address = f"{property_data.get('address', 'N/A')}, {property_data.get('city', 'N/A')}, {property_data.get('state', 'N/A')} {property_data.get('zip_code', 'N/A')}"
    year_built = property_data.get("year_built", 0)
    property_age = datetime.now().year - year_built if year_built > 0 else "Unknown"
    severity_breakdown = summary.get("by_severity", {})
    critical = severity_breakdown.get("CRITICAL", 0)
    high = severity_breakdown.get("HIGH", 0)
    medium = severity_breakdown.get("MEDIUM", 0)
    low = severity_breakdown.get("LOW", 0)
    total_items = summary.get("total_items", len(findings))
    total_low = summary.get("total_low", 0)
    total_high = summary.get("total_high", 0)
    total_avg = summary.get("total_avg", 0)
    market_type = market_profile.get("market_type", "N/A")
    leverage = market_profile.get("leverage_score", "N/A")

    if critical > 0:
        urgency = "IMMEDIATE ACTION REQUIRED"
        urgency_detail = (
            f"{critical} critical safety/structural issues demand immediate attention before closing."
        )
    elif high > 2:
        urgency = "HIGH PRIORITY"
        urgency_detail = f"{high} high-priority items require negotiation before or at closing."
    else:
        urgency = "STANDARD PROCESS"
        urgency_detail = "Findings are consistent with typical inspection results for the property age."

    sorted_items = sorted(line_items, key=lambda x: _severity_sort_key(x.get("severity", "MEDIUM")))
    findings_text = ""
    for idx, item in enumerate(sorted_items, 1):
        sev = item.get("severity", "MEDIUM")
        findings_text += f"""
  [{idx}] [{sev}] {item.get("system", "N/A")} - {item.get("finding", "N/A")}
      Location:     {item.get("location", "N/A")}
      Cost Range:   ${item.get("total_low", 0):,.0f} - ${item.get("total_high", 0):,.0f}
      Avg Estimate: ${item.get("total_avg", 0):,.0f}
      DIY Option:   ${item.get("diy_low", 0):,.0f} - ${item.get("diy_high", 0):,.0f}
      Emergency:    ${item.get("emergency_low", 0):,.0f} - ${item.get("emergency_high", 0):,.0f}
      Material:     ${item.get("material_cost_low", 0):,.0f} - ${item.get("material_cost_high", 0):,.0f}
      Labor:        ${item.get("labor_cost_low", 0):,.0f} - ${item.get("labor_cost_high", 0):,.0f}
      Permit:       ${item.get("permit_cost", 0):,.0f}
"""

    rates = summary.get("rates_applied", {})
    rates_text = ""
    if rates:
        rates_text = f"""
  ZIP Code:       {summary.get("zip_code", "N/A")}
  City:           {rates.get("city", "N/A")}
  Cost Modifier:  {rates.get("cost_modifier", 1.0)}x
  Avg Labor Rate: ${rates.get("avg_labor_rate", 60)}/hr
  Material Mult:  {rates.get("avg_material_mult", 1.0)}x
  Permit Fee Est: ${rates.get("permit_fee_estimate", 275)}
"""

    insurance_text = ""
    ins_list = _safe_list(insurance_analysis)
    if ins_list:
        for ins in ins_list:
            insurance_text += f"""
  - {ins.get("type", ins.get("category", "N/A"))} [{ins.get("risk_level", ins.get("risk", "N/A"))}]
    {ins.get("description", ins.get("details", "N/A"))}
    Estimated Cost: {ins.get("estimated_cost", ins.get("additional_cost", ins.get("cost", "N/A")))}
"""
    else:
        insurance_text = "\n  No insurance risk data available.\n"

    env_text = ""
    env_list = _safe_list(environmental_data)
    if env_list:
        for env in env_list:
            env_text += f"""
  - {env.get("risk_type", env.get("type", "N/A"))} [{env.get("severity", env.get("risk_level", "N/A"))}]
    {env.get("description", env.get("details", "N/A"))}
    Zone: {env.get("zone", env.get("flood_zone", "N/A"))}
"""
    elif isinstance(environmental_data, dict):
        ed = environmental_data
        env_text = f"""
  Climate Zone:     {ed.get("climate_zone", "N/A")}
  Flood Zone:       {ed.get("flood_zone", "N/A")}
  Wildfire Risk:    {ed.get("wildfire_risk", "N/A")}
  Earthquake Risk:  {ed.get("earthquake_risk", "N/A")}
"""
    else:
        env_text = "\n  No environmental risk data available.\n"

    permit_text = ""
    permit_list = _safe_list(permit_data)
    if permit_list:
        for p in permit_list:
            status = p.get("status", "Unknown")
            permit_text += f"""
  - {p.get("permit_type", p.get("type", "N/A"))} [{status}]
    {p.get("description", p.get("details", "N/A"))}
    Permit #: {p.get("permit_number", p.get("number", "N/A"))}
"""
    elif isinstance(permit_data, dict):
        pd_dict = permit_data
        permit_text = f"""
  Total Permits:      {pd_dict.get("total_permits", "N/A")}
  Compliant:          {pd_dict.get("compliant", "N/A")}
  Non-Compliant:      {pd_dict.get("non_compliant", pd_dict.get("unpermitted_flags", "N/A"))}
  Pending:            {pd_dict.get("pending", "N/A")}
"""
    else:
        permit_text = "\n  No permit data available.\n"

    recall_text = ""
    recall_list = _safe_list(recall_data)
    if recall_list:
        for r in recall_list:
            recall_text += f"""
  - {r.get("product", r.get("item", "N/A"))} [{r.get("status", "Unknown")}]
    {r.get("description", r.get("recall_description", "N/A"))}
    Potential Savings: {r.get("potential_savings", r.get("estimated_savings", "N/A"))}
"""
    else:
        recall_text = "\n  No manufacturer recall matches found.\n"

    negotiation_text = ""
    neg_strategies = (
        _safe_dict(negotiation_strategies).get("strategies", [])
        if isinstance(negotiation_strategies, dict)
        else []
    )
    if neg_strategies:
        for s in neg_strategies:
            negotiation_text += f"""
  - [{s.get("severity", "N/A")}] {s.get("system", "N/A")}
    Strategy: {s.get("strategy", "N/A")}
    Action:   {s.get("action", "N/A")}
    Savings:  {s.get("estimated_savings", s.get("potential_savings", "N/A"))}
"""
    else:
        negotiation_text = "\n  No negotiation strategies available.\n"

    capex_text = ""
    capex = _safe_dict(capex_analysis)
    if capex:
        capex_summary = capex.get("summary", {})
        systems = capex.get("systems", capex.get("items", []))
        capex_text = f"""
  Weighted 24-Mo Risk:    ${capex_summary.get("weighted_24mo_risk", 0):,.0f}
  Total Replacement Est:  ${capex_summary.get("total_replacement", 0):,.0f}
"""
        if systems:
            capex_text += "  System Breakdown:\n"
            for sys in systems:
                capex_text += f"    - {sys.get('system', sys.get('name', 'N/A'))}: Prob {sys.get('failure_probability', sys.get('probability', 'N/A'))} | Replace ${sys.get('replacement_cost', sys.get('cost', 0)):,.0f}\n"

    dep_text = ""
    dep = _safe_dict(depreciation_data)
    if dep:
        systems_dep = dep.get("systems", dep.get("items", dep.get("depreciation_items", [])))
        if systems_dep:
            dep_text = "  Depreciation Timeline:\n"
            for d in systems_dep:
                dep_text += f"    - {d.get('system', d.get('name', 'N/A'))}: Age {d.get('age', 'N/A')}y / Life {d.get('useful_life', 'N/A')}y | Condition: {d.get('condition', d.get('condition_rating', 'N/A'))}\n"

    escrow_text = ""
    escrow = _safe_dict(escrow_data) if isinstance(escrow_data, dict) else {}
    escrow_list = _safe_list(escrow_data)
    if escrow:
        escrow_text = f"""
  Total Holdback:   ${escrow.get("total_holdback", 0):,.0f}
  Recommended:      {escrow.get("recommended", escrow.get("recommended_amount", "N/A"))}
"""
        conditions = escrow.get("conditions", [])
        if conditions:
            for c in conditions:
                escrow_text += f"    - {c.get('item', c.get('description', 'N/A'))}: ${c.get('amount', 0):,.0f} ({c.get('status', 'N/A')})\n"
    elif escrow_list:
        escrow_text = "  Escrow Holdback Items:\n"
        for e in escrow_list:
            escrow_text += f"    - {e.get('item', e.get('description', 'N/A'))}: ${e.get('amount', 0):,.0f} [{e.get('status', 'Pending')}]\n"
    else:
        escrow_text = "\n  No escrow holdback data available.\n"

    contractor_text = ""
    bids = _safe_dict(contractor_bids)
    bid_list = bids.get("bids", bids.get("contractors", [])) if bids else []
    if bid_list:
        contractor_text = "  Contractor Bids:\n"
        for b in bid_list:
            contractor_text += f"    - {b.get('contractor', b.get('name', 'N/A'))}: ${b.get('bid_amount', b.get('amount', 0)):,.0f} [{b.get('status', 'Pending')}]\n"

    investor_text = ""
    inv = _safe_dict(investor_analysis)
    if inv:
        investor_text = f"""
  After Repair Value (ARV):   ${inv.get("arv", inv.get("after_repair_value", 0)):,.0f}
  Max Allowable Offer (MAO):  ${inv.get("mao", inv.get("max_allowable_offer", 0)):,.0f}
  Cap Rate:                   {inv.get("cap_rate", inv.get("capitalization_rate", "N/A"))}%
  Deal Grade:                 {inv.get("deal_grade", inv.get("grade", "N/A"))}
"""

    recommendations = []
    if critical > 0:
        recommendations.append(
            f"  * PRIORITY 1: Address {critical} critical finding(s) immediately. These represent safety or structural hazards."
        )
    if high > 0:
        recommendations.append(
            f"  * PRIORITY 2: Negotiate ${summary.get('high_cost', total_avg * 0.5):,.0f} in credits or price reduction for {high} high-severity items."
        )
    if medium > 0:
        recommendations.append(
            f"  * PRIORITY 3: Request seller remediation or escrow holdback for {medium} medium-severity code/compliance items."
        )
    recommendations.append(
        f"  * Plan ${total_avg:,.0f} in expected repair costs within the first 12 months of ownership."
    )
    if isinstance(market_profile, dict) and market_profile.get("leverage_score", 50) > 60:
        recommendations.append(
            "  * Market conditions favor buyers - leverage inspection findings in negotiations."
        )
    recs_text = (
        "\n".join(recommendations) if recommendations else "  No specific recommendations at this time."
    )

    text = f"""
{"=" * 80}
PROPERTY REPAIR COST ESTIMATE REPORT
Comprehensive 21-Module Enterprise Analysis
{"=" * 80}

PROPERTY INFORMATION
{"-" * 40}
  Address:        {address}
  Year Built:     {year_built}
  Property Age:   {property_age} years
  Type:           {property_data.get("property_type", "N/A")}
  Sq Footage:     {property_data.get("square_footage", "N/A")}
  Beds / Baths:   {property_data.get("bedrooms", "N/A")} / {property_data.get("bathrooms", "N/A")}
  Roof:           {property_data.get("roof_type", "N/A")}
  HVAC:           {property_data.get("hvac_type", "N/A")}
  Plumbing:       {property_data.get("plumbing_type", "N/A")}
  Electrical:     {property_data.get("electrical_type", "N/A")}
  Foundation:     {property_data.get("foundation_type", "N/A")}

{"=" * 80}
EXECUTIVE SUMMARY
{"=" * 80}

  Urgency:        {urgency}
  Detail:         {urgency_detail}
  Total Findings: {total_items} ({critical} Critical, {high} High, {medium} Medium, {low} Low)
  Cost Range:     ${total_low:,.0f} - ${total_high:,.0f}
  Average Est:    ${total_avg:,.0f}
  Market Type:    {market_type}
  Buyer Leverage: {leverage}/100

{"=" * 80}
DETAILED FINDINGS (Sorted by Severity)
{"=" * 80}
{findings_text}
{"=" * 80}
COST BREAKDOWN
{"=" * 80}

  Total Low:      ${total_low:,.0f}
  Total High:     ${total_high:,.0f}
  Total Average:  ${total_avg:,.0f}
{rates_text}
{"=" * 80}
DEPRECIATION & CAPEX ANALYSIS
{"=" * 80}
{dep_text if dep_text else "  No depreciation data available."}
{capex_text if capex_text else "  No CapEx analysis available."}

{"=" * 80}
MARKET ANALYSIS & NEGOTIATION
{"=" * 80}

  Market Type:         {market_type}
  Buyer Leverage:      {leverage}/100
  Avg Days on Market:  {market_profile.get("avg_days_on_market", "N/A")}
  Months of Supply:    {market_profile.get("months_of_supply", "N/A")}
  Assessment:          {market_profile.get("leverage_description", "N/A")}
{negotiation_text}
{"=" * 80}
CONTRACTOR BIDS
{"=" * 80}
{contractor_text if contractor_text else "  No contractor bid data available."}

{"=" * 80}
INSURANCE RISK SUMMARY
{"=" * 80}
{insurance_text}
{"=" * 80}
ENVIRONMENTAL RISK
{"=" * 80}
{env_text}
{"=" * 80}
PERMITS & COMPLIANCE
{"=" * 80}
{permit_text}
{"=" * 80}
MANUFACTURER RECALLS
{"=" * 80}
{recall_text}
{"=" * 80}
ESCROW HOLDBACK ANALYSIS
{"=" * 80}
{escrow_text}
{"=" * 80}
INVESTOR ANALYSIS
{"=" * 80}
{investor_text if investor_text else "  No investor analysis data available."}

{"=" * 80}
RECOMMENDATIONS
{"=" * 80}
{recs_text}

{"=" * 80}
DISCLAIMER
{"=" * 80}
This report is generated by automated analysis tools and is intended for informational
purposes only. Cost estimates are based on regional averages and embedded cost databases.
Actual contractor bids may vary. Always obtain licensed contractor estimates before
making repair decisions. This report does not constitute engineering, legal, or
financial advice. Consult licensed professionals for all structural, electrical,
plumbing, and environmental assessments.

Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}
"""
    return text


# ---------------------------------------------------------------------------
# PDF-ready HTML report (all 21 modules)
# ---------------------------------------------------------------------------


def generate_pdf_report(
    property_data,
    findings,
    cost_matrix,
    market_profile,
    insurance_analysis=None,
    environmental_data=None,
    permit_data=None,
    recall_data=None,
    negotiation_strategies=None,
    capex_analysis=None,
    depreciation_data=None,
    escrow_data=None,
    contractor_bids=None,
    spatial_data=None,
    investor_analysis=None,
):
    summary = cost_matrix.get("summary", {})
    line_items = cost_matrix.get("line_items", [])
    address = f"{property_data.get('address', 'N/A')}, {property_data.get('city', 'N/A')}, {property_data.get('state', 'N/A')} {property_data.get('zip_code', 'N/A')}"
    year_built = property_data.get("year_built", 0)
    property_age = datetime.now().year - year_built if year_built > 0 else "Unknown"
    severity_breakdown = summary.get("by_severity", {})
    total_low = summary.get("total_low", 0)
    total_high = summary.get("total_high", 0)
    total_avg = summary.get("total_avg", 0)
    total_items = summary.get("total_items", 0)
    critical = severity_breakdown.get("CRITICAL", 0)
    high = severity_breakdown.get("HIGH", 0)
    medium = severity_breakdown.get("MEDIUM", 0)
    low = severity_breakdown.get("LOW", 0)
    market_type = market_profile.get("market_type", "N/A") if isinstance(market_profile, dict) else "N/A"
    leverage = market_profile.get("leverage_score", "N/A") if isinstance(market_profile, dict) else "N/A"
    avg_dom = market_profile.get("avg_days_on_market", "N/A") if isinstance(market_profile, dict) else "N/A"
    months_supply = (
        market_profile.get("months_of_supply", "N/A") if isinstance(market_profile, dict) else "N/A"
    )
    leverage_desc = (
        market_profile.get("leverage_description", "N/A") if isinstance(market_profile, dict) else "N/A"
    )

    if critical > 0:
        urgency_text = "IMMEDIATE ACTION REQUIRED"
        urgency_color = "#FF453A"
    elif high > 2:
        urgency_text = "HIGH PRIORITY"
        urgency_color = "#FF9F0A"
    else:
        urgency_text = "STANDARD PROCESS"
        urgency_color = "#30D158"

    capex = _safe_dict(capex_analysis)
    capex_summary = capex.get("summary", {})
    weighted_risk = capex_summary.get("weighted_24mo_risk", 0)

    dep = _safe_dict(depreciation_data)

    sorted_items = sorted(line_items, key=lambda x: _severity_sort_key(x.get("severity", "MEDIUM")))

    insurability_score = "N/A"
    ins_analysis = _safe_dict(insurance_analysis) if isinstance(insurance_analysis, dict) else {}
    if ins_analysis:
        insurability_score = ins_analysis.get("summary", {}).get(
            "insurability_score", ins_analysis.get("insurability_score", "N/A")
        )
    elif isinstance(insurance_analysis, list) and insurance_analysis:
        high_risk = sum(
            1
            for i in insurance_analysis
            if str(i.get("risk_level", i.get("risk", ""))).upper() in ("HIGH", "CRITICAL")
        )
        total_ins = len(insurance_analysis)
        insurability_score = (
            f"{max(0, round(100 - (high_risk / max(total_ins, 1) * 100)))}/100" if total_ins else "N/A"
        )

    severity_bar_html = ""
    max_count = max(critical, high, medium, low, 1)
    for sev_name, sev_count, sev_color in [
        ("CRITICAL", critical, "#FF453A"),
        ("HIGH", high, "#FF9F0A"),
        ("MEDIUM", medium, "#FFD60A"),
        ("LOW", low, "#30D158"),
    ]:
        pct = (sev_count / max_count * 100) if max_count > 0 else 0
        severity_bar_html += f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
          <span style="width:70px;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:rgba(245,245,247,0.55)">{sev_name}</span>
          <div style="flex:1;height:20px;background:rgba(255,255,255,0.05);border-radius:4px;overflow:hidden">
            <div style="width:{pct}%;height:100%;background:{sev_color};border-radius:4px;transition:width 0.3s"></div>
          </div>
          <span style="width:24px;text-align:right;font-size:13px;font-weight:600;color:{sev_color}">{sev_count}</span>
        </div>"""

    findings_rows = ""
    for item in sorted_items:
        sev = item.get("severity", "MEDIUM")
        sc = _severity_color(sev)
        findings_rows += f"""
        <tr>
          <td><span style="color:{sc};font-weight:600">{sev}</span></td>
          <td>{item.get("system", "N/A")}</td>
          <td>{item.get("finding", "N/A")}</td>
          <td>{item.get("location", "N/A")}</td>
          <td style="text-align:right">{format_currency(item.get("diy_low", 0))}</td>
          <td style="text-align:right">{format_currency(item.get("total_low", 0))}</td>
          <td style="text-align:right">{format_currency(item.get("total_high", 0))}</td>
          <td style="text-align:right;font-weight:600">{format_currency(item.get("total_avg", 0))}</td>
        </tr>"""

    dep_rows = ""
    systems_dep = dep.get("systems", dep.get("items", dep.get("depreciation_items", []))) if dep else []
    if systems_dep:
        for d in systems_dep:
            age = d.get("age", "N/A")
            life = d.get("useful_life", "N/A")
            cond = d.get("condition", d.get("condition_rating", "N/A"))
            cost = d.get("replacement_cost", d.get("cost", 0))
            prob = d.get("failure_probability", d.get("probability", "N/A"))
            dep_rows += f"""
        <tr>
          <td>{d.get("system", d.get("name", "N/A"))}</td>
          <td style="text-align:center">{age}</td>
          <td style="text-align:center">{life}</td>
          <td style="text-align:center">{cond}</td>
          <td style="text-align:center">{prob}</td>
          <td style="text-align:right">{format_currency(cost)}</td>
        </tr>"""

    capex_rows = ""
    capex_systems = capex.get("systems", capex.get("items", []))
    for cs in capex_systems:
        capex_rows += f"""
        <tr>
          <td>{cs.get("system", cs.get("name", "N/A"))}</td>
          <td style="text-align:center">{cs.get("failure_probability", cs.get("probability", "N/A"))}</td>
          <td style="text-align:right">{format_currency(cs.get("replacement_cost", cs.get("cost", 0)))}</td>
          <td>{cs.get("timeline", cs.get("expected_timeline", "N/A"))}</td>
          <td><span style="color:{_severity_color(cs.get("risk_level", cs.get("severity", "MEDIUM")))};font-weight:600">{cs.get("risk_level", cs.get("severity", "N/A"))}</span></td>
        </tr>"""

    neg_rows = ""
    neg_strategies = (
        _safe_dict(negotiation_strategies).get("strategies", [])
        if isinstance(negotiation_strategies, dict)
        else []
    )
    for s in neg_strategies:
        neg_rows += f"""
        <tr>
          <td>{s.get("system", "N/A")}</td>
          <td><span style="color:{_severity_color(s.get("severity", "MEDIUM"))};font-weight:600">{s.get("severity", "N/A")}</span></td>
          <td>{s.get("strategy", "N/A")}</td>
          <td style="font-size:12px">{s.get("action", "N/A")}</td>
          <td style="text-align:right">{s.get("estimated_savings", s.get("potential_savings", "N/A"))}</td>
        </tr>"""

    bid_rows = ""
    bids = _safe_dict(contractor_bids)
    bid_list = bids.get("bids", bids.get("contractors", [])) if bids else []
    for b in bid_list:
        rec = b.get("recommended", b.get("is_recommended", False))
        highlight = "rgba(48,209,88,0.08)" if rec else ""
        star = " &#9733;" if rec else ""
        bid_rows += f"""
        <tr style="background:{highlight}">
          <td>{b.get("contractor", b.get("name", "N/A"))}{star}</td>
          <td>{b.get("specialty", b.get("trade", "N/A"))}</td>
          <td style="text-align:right">{format_currency(b.get("bid_amount", b.get("amount", 0)))}</td>
          <td style="text-align:center">{b.get("timeline", b.get("estimated_timeline", "N/A"))}</td>
          <td style="text-align:center">{b.get("rating", "N/A")}</td>
          <td>{b.get("status", "Pending")}</td>
        </tr>"""

    ins_rows = ""
    ins_list = _safe_list(insurance_analysis) if isinstance(insurance_analysis, list) else []
    for ins in ins_list:
        risk_level = ins.get("risk_level", ins.get("risk", "Unknown"))
        rc = _severity_color(str(risk_level).upper())
        ins_rows += f"""
        <tr>
          <td>{ins.get("type", ins.get("category", "N/A"))}</td>
          <td><span style="color:{rc};font-weight:600">{risk_level}</span></td>
          <td>{ins.get("description", ins.get("details", "N/A"))}</td>
          <td style="text-align:right">{ins.get("estimated_cost", ins.get("additional_cost", ins.get("cost", "N/A")))}</td>
        </tr>"""

    env_items = _safe_list(environmental_data) if isinstance(environmental_data, list) else []
    env_dict = _safe_dict(environmental_data) if isinstance(environmental_data, dict) else {}
    env_rows = ""
    climate_zone = env_dict.get("climate_zone", "N/A")
    flood_zone = env_dict.get("flood_zone", "N/A")
    wildfire_risk = env_dict.get("wildfire_risk", "N/A")
    earthquake_risk = env_dict.get("earthquake_risk", "N/A")
    for e in env_items:
        env_rows += f"""
        <tr>
          <td>{e.get("risk_type", e.get("type", "N/A"))}</td>
          <td><span style="color:{_severity_color(e.get("severity", e.get("risk_level", "MEDIUM")))};font-weight:600">{e.get("severity", e.get("risk_level", "N/A"))}</span></td>
          <td>{e.get("description", e.get("details", "N/A"))}</td>
          <td>{e.get("zone", e.get("flood_zone", "N/A"))}</td>
        </tr>"""

    permit_items = _safe_list(permit_data) if isinstance(permit_data, list) else []
    permit_dict = _safe_dict(permit_data) if isinstance(permit_data, dict) else {}
    permit_rows = ""
    total_permits = permit_dict.get("total_permits", "N/A")
    compliant_permits = permit_dict.get("compliant", "N/A")
    unpermitted_flags = permit_dict.get("unpermitted_flags", permit_dict.get("non_compliant", 0))
    pending_permits = permit_dict.get("pending", "N/A")
    for p in permit_items:
        pstatus = p.get("status", "Unknown")
        psc = (
            "#30D158"
            if str(pstatus).upper() in ("APPROVED", "COMPLIANT", "CLOSED")
            else (
                "#FF453A"
                if str(pstatus).upper() in ("VIOLATION", "EXPIRED", "NON-COMPLIANT", "UNPERMITTED")
                else "#FFD60A"
            )
        )
        permit_rows += f"""
        <tr>
          <td>{p.get("permit_type", p.get("type", "N/A"))}</td>
          <td>{p.get("permit_number", p.get("number", "N/A"))}</td>
          <td><span style="color:{psc};font-weight:600">{pstatus}</span></td>
          <td>{p.get("description", p.get("details", "N/A"))}</td>
          <td>{p.get("date", p.get("issue_date", "N/A"))}</td>
        </tr>"""

    recall_items = _safe_list(recall_data)
    recall_rows = ""
    total_savings = 0
    for r in recall_items:
        sav = r.get("potential_savings", r.get("estimated_savings", 0))
        if isinstance(sav, int | float):
            total_savings += sav
        recall_rows += f"""
        <tr>
          <td>{r.get("product", r.get("item", "N/A"))}</td>
          <td>{r.get("manufacturer", "N/A")}</td>
          <td>{r.get("recall_date", r.get("date", "N/A"))}</td>
          <td><span style="color:{_severity_color(r.get("severity", "HIGH"))};font-weight:600">{r.get("status", "RECALL")}</span></td>
          <td style="font-size:12px">{r.get("description", r.get("recall_description", "N/A"))}</td>
          <td style="text-align:right">{format_currency(sav) if isinstance(sav, int | float) else sav}</td>
        </tr>"""

    escrow_items = _safe_list(escrow_data)
    escrow_dict = _safe_dict(escrow_data) if isinstance(escrow_data, dict) else {}
    escrow_rows = ""
    total_holdback = escrow_dict.get("total_holdback", 0)
    escrow_conditions = escrow_dict.get("conditions", [])
    for ec in escrow_conditions:
        escrow_rows += f"""
        <tr>
          <td>{ec.get("item", ec.get("description", "N/A"))}</td>
          <td style="text-align:right">{format_currency(ec.get("amount", 0))}</td>
          <td><span style="color:{_severity_color(ec.get("severity", "MEDIUM"))}">{ec.get("condition", ec.get("release_condition", "N/A"))}</span></td>
          <td>{ec.get("status", "Pending")}</td>
        </tr>"""
    for ei in escrow_items:
        escrow_rows += f"""
        <tr>
          <td>{ei.get("item", ei.get("description", "N/A"))}</td>
          <td style="text-align:right">{format_currency(ei.get("amount", 0))}</td>
          <td>{ei.get("condition", ei.get("release_condition", "N/A"))}</td>
          <td>{ei.get("status", "Pending")}</td>
        </tr>"""

    inv = _safe_dict(investor_analysis)
    inv_arv = inv.get("arv", inv.get("after_repair_value", 0))
    inv_mao = inv.get("mao", inv.get("max_allowable_offer", 0))
    inv_cap_rate = inv.get("cap_rate", inv.get("capitalization_rate", "N/A"))
    inv_grade = inv.get("deal_grade", inv.get("grade", "N/A"))
    inv_monthly_rent = inv.get("monthly_rent", inv.get("estimated_rent", 0))
    inv_cash_on_cash = inv.get("cash_on_cash_return", inv.get("cash_on_cash", "N/A"))

    inv_rows = ""
    inv_metrics = inv.get("metrics", inv.get("key_metrics", []))
    for m in inv_metrics:
        inv_rows += f"""
        <tr>
          <td>{m.get("metric", m.get("name", "N/A"))}</td>
          <td style="text-align:right">{m.get("value", "N/A")}</td>
        </tr>"""

    spatial = _safe_dict(spatial_data)
    spatial_insights = ""
    if spatial:
        dist_items = spatial.get("distances", spatial.get("nearby_places", []))
        if dist_items:
            spatial_insights = (
                "<table><thead><tr><th>Location</th><th>Distance</th><th>Impact</th></tr></thead><tbody>"
            )
            for di in dist_items:
                spatial_insights += f"<tr><td>{di.get('name', di.get('location', 'N/A'))}</td><td>{di.get('distance', 'N/A')}</td><td>{di.get('impact', di.get('price_impact', 'N/A'))}</td></tr>"
            spatial_insights += "</tbody></table>"
        else:
            spatial_insights = f"<div class='info-row'><span class='k'>Walk Score</span><span class='v'>{spatial.get('walk_score', 'N/A')}</span></div><div class='info-row'><span class='k'>Transit Score</span><span class='v'>{spatial.get('transit_score', 'N/A')}</span></div><div class='info-row'><span class='k'>Location Rating</span><span class='v'>{spatial.get('location_rating', 'N/A')}</span></div>"

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Property Repair Cost Estimate - {property_data.get("address", "N/A")}</title>
<style>
  @page {{
    size: A4;
    margin: 18mm 15mm 18mm 15mm;
  }}
  @media print {{
    body {{ background: #000 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .report {{ padding: 0 !important; max-width: 100% !important; }}
    details {{ open: true; }}
    details[open] > summary ~ * {{ display: block !important; }}
    .section {{ page-break-inside: avoid; }}
    .page-break {{ page-break-before: always; }}
    section[data-break="true"] {{ page-break-before: always; }}
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'SF Pro Display', 'Helvetica Neue', Helvetica, Arial, sans-serif;
    background: #000;
    color: #F5F5F7;
    line-height: 1.55;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  .report {{
    max-width: 960px;
    margin: 0 auto;
    padding: 40px 48px;
  }}

  /* Cover Page */
  .cover {{
    min-height: 90vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: flex-start;
    padding: 60px 0;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 48px;
  }}
  .cover .brand-line {{
    width: 56px; height: 4px; background: #0A84FF; border-radius: 2px; margin-bottom: 32px;
  }}
  .cover h1 {{
    font-size: 42px; font-weight: 700; letter-spacing: -1.2px; color: #F5F5F7;
    line-height: 1.15; margin-bottom: 16px;
  }}
  .cover .cover-subtitle {{
    font-size: 18px; color: rgba(245,245,247,0.55); font-weight: 400; margin-bottom: 40px;
  }}
  .cover .cover-address {{
    font-size: 15px; color: #0A84FF; font-weight: 500; margin-bottom: 8px;
  }}
  .cover .cover-date {{
    font-size: 13px; color: rgba(245,245,247,0.4);
  }}
  .cover .cover-badge {{
    display: inline-block; padding: 6px 14px; border-radius: 20px;
    background: rgba(10,132,255,0.15); color: #0A84FF;
    font-size: 12px; font-weight: 600; letter-spacing: 0.5px; margin-top: 24px;
  }}

  /* TOC */
  .toc {{
    background: #1C1C1E; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
    padding: 28px 32px; margin-bottom: 40px;
  }}
  .toc h2 {{
    font-size: 16px; font-weight: 600; color: #0A84FF; margin-bottom: 16px;
    letter-spacing: -0.2px;
  }}
  .toc-list {{
    list-style: none; columns: 2; column-gap: 32px;
  }}
  .toc-list li {{
    padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.04);
  }}
  .toc-list a {{
    color: rgba(245,245,247,0.7); text-decoration: none; font-size: 13px;
    transition: color 0.15s;
  }}
  .toc-list a:hover {{ color: #0A84FF; }}

  /* Sections */
  .section {{
    margin-bottom: 40px;
  }}
  .section-title {{
    font-size: 20px; font-weight: 700; color: #0A84FF; margin-bottom: 20px;
    letter-spacing: -0.3px; display: flex; align-items: center; gap: 10px;
  }}
  .section-title .section-num {{
    font-size: 12px; background: rgba(10,132,255,0.18); color: #0A84FF;
    padding: 3px 9px; border-radius: 6px; font-weight: 600;
  }}

  /* Details/Summary collapsible */
  details {{
    background: #1C1C1E; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
    margin-bottom: 16px; overflow: hidden;
  }}
  details[open] {{
    border-color: rgba(10,132,255,0.25);
  }}
  summary {{
    padding: 16px 20px; cursor: pointer; font-size: 14px; font-weight: 600;
    color: #F5F5F7; display: flex; align-items: center; gap: 10px;
    list-style: none; user-select: none;
    transition: background 0.15s;
  }}
  summary::-webkit-details-marker {{ display: none; }}
  summary::before {{
    content: '\\25B6'; font-size: 10px; color: #0A84FF; transition: transform 0.2s;
  }}
  details[open] > summary::before {{ transform: rotate(90deg); }}
  summary:hover {{ background: rgba(255,255,255,0.03); }}
  details > .detail-body {{ padding: 0 20px 20px 20px; }}

  /* Metric Grid */
  .metric-grid {{
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 24px;
  }}
  .metric-grid.grid-2 {{ grid-template-columns: repeat(2, 1fr); }}
  .metric-grid.grid-6 {{ grid-template-columns: repeat(6, 1fr); }}
  .metric-card {{
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px; padding: 18px 16px;
  }}
  .metric-card .label {{
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px;
    color: rgba(245,245,247,0.45); margin-bottom: 6px;
  }}
  .metric-card .value {{
    font-size: 22px; font-weight: 600; color: #F5F5F7;
  }}
  .metric-card .value.accent {{ color: #0A84FF; }}
  .metric-card .value.warn {{ color: #FF9F0A; }}
  .metric-card .value.danger {{ color: #FF453A; }}
  .metric-card .value.success {{ color: #30D158; }}
  .metric-card .value.gold {{ color: #FFD60A; }}

  .urgency-banner {{
    display: inline-block; padding: 8px 18px; border-radius: 6px;
    font-size: 13px; font-weight: 600; letter-spacing: 0.4px; margin-bottom: 20px;
  }}

  /* Tables */
  table {{
    width: 100%; border-collapse: collapse; font-size: 13px;
  }}
  thead th {{
    text-align: left; padding: 10px 12px; font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.6px;
    color: rgba(245,245,247,0.5); border-bottom: 1px solid rgba(255,255,255,0.1);
    font-weight: 500; position: sticky; top: 0; background: #1C1C1E;
  }}
  tbody td {{
    padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.05); color: #F5F5F7;
  }}
  tbody tr:hover {{ background: rgba(255,255,255,0.03); }}
  tbody tr:nth-child(even) {{ background: rgba(255,255,255,0.015); }}
  tbody tr:nth-child(even):hover {{ background: rgba(255,255,255,0.04); }}

  /* Info rows */
  .info-grid {{
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;
  }}
  .info-row {{
    display: flex; justify-content: space-between; padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 13px;
  }}
  .info-row .k {{ color: rgba(245,245,247,0.55); }}
  .info-row .v {{ font-weight: 500; color: #F5F5F7; }}

  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}

  /* Severity bar chart */
  .severity-bar-chart {{ max-width: 480px; }}

  /* Footer */
  .footer {{
    margin-top: 48px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.08);
    font-size: 11px; color: rgba(245,245,247,0.35); line-height: 1.65;
  }}
</style>
</head>
<body>
<div class="report">

  <!-- COVER -->
  <div class="cover">
    <div class="brand-line"></div>
    <h1>Property Repair<br>Cost Estimate</h1>
    <div class="cover-subtitle">Comprehensive 21-Module Inspection Analysis</div>
    <div class="cover-address">{address}</div>
    <div class="cover-date">{datetime.now().strftime("%B %d, %Y")}</div>
    <div class="cover-badge">ENTERPRISE REPORT v3.0</div>
  </div>

  <!-- TABLE OF CONTENTS -->
  <nav class="toc" id="toc">
    <h2>Table of Contents</h2>
    <ol class="toc-list">
      <li><a href="#dashboard">Executive Dashboard</a></li>
      <li><a href="#cost-analysis">Cost Analysis</a></li>
      <li><a href="#depreciation-capex">Depreciation &amp; CapEx</a></li>
      <li><a href="#market-negotiation">Market &amp; Negotiation</a></li>
      <li><a href="#contractor-bids">Contractor Bids</a></li>
      <li><a href="#insurance-risk">Insurance Risk</a></li>
      <li><a href="#environmental">Environmental Risk</a></li>
      <li><a href="#permits">Permits &amp; Records</a></li>
      <li><a href="#recalls">Manufacturer Recalls</a></li>
      <li><a href="#escrow">Escrow Holdback</a></li>
      <li><a href="#investor">Investor Analysis</a></li>
    </ol>
  </nav>

  <!-- 1. EXECUTIVE DASHBOARD -->
  <section id="dashboard" class="section" data-break="true">
    <div class="section-title"><span class="section-num">01</span> Executive Dashboard</div>
    <div class="urgency-banner" style="background:{urgency_color}22;color:{urgency_color}">{urgency_text}</div>
    <div class="metric-grid grid-6" style="margin-top:12px">
      <div class="metric-card">
        <div class="label">Total Findings</div>
        <div class="value">{total_items}</div>
      </div>
      <div class="metric-card">
        <div class="label">Total Cost</div>
        <div class="value accent">{format_currency(total_avg)}</div>
      </div>
      <div class="metric-card">
        <div class="label">Critical</div>
        <div class="value danger">{critical}</div>
      </div>
      <div class="metric-card">
        <div class="label">Market Type</div>
        <div class="value" style="font-size:15px">{market_type}</div>
      </div>
      <div class="metric-card">
        <div class="label">Buyer Leverage</div>
        <div class="value warn">{leverage}/100</div>
      </div>
      <div class="metric-card">
        <div class="label">Insurability</div>
        <div class="value success">{insurability_score}</div>
      </div>
    </div>
    <div style="margin-top:20px">
      <div class="section-title" style="font-size:14px;margin-bottom:12px">Findings by Severity</div>
      <div class="severity-bar-chart">
        {severity_bar_html}
      </div>
    </div>
    <div style="margin-top:24px">
      <div class="section-title" style="font-size:14px;margin-bottom:12px">Property Details</div>
      <div class="info-grid">
        <div>
          <div class="info-row"><span class="k">Year Built</span><span class="v">{year_built}</span></div>
          <div class="info-row"><span class="k">Property Age</span><span class="v">{property_age} years</span></div>
          <div class="info-row"><span class="k">Type</span><span class="v">{property_data.get("property_type", "N/A")}</span></div>
          <div class="info-row"><span class="k">Sq Footage</span><span class="v">{property_data.get("square_footage", "N/A")}</span></div>
        </div>
        <div>
          <div class="info-row"><span class="k">Bed / Bath</span><span class="v">{property_data.get("bedrooms", "N/A")} / {property_data.get("bathrooms", "N/A")}</span></div>
          <div class="info-row"><span class="k">Roof</span><span class="v">{property_data.get("roof_type", "N/A")}</span></div>
          <div class="info-row"><span class="k">HVAC</span><span class="v">{property_data.get("hvac_type", "N/A")}</span></div>
          <div class="info-row"><span class="k">Foundation</span><span class="v">{property_data.get("foundation_type", "N/A")}</span></div>
        </div>
      </div>
    </div>
  </section>

  <!-- 2. COST ANALYSIS -->
  <section id="cost-analysis" class="section" data-break="true">
    <div class="section-title"><span class="section-num">02</span> Cost Analysis</div>
    <details open>
      <summary>Severity Cost Breakdown</summary>
      <div class="detail-body">
        <div class="severity-bar-chart" style="max-width:100%">
          {severity_bar_html}
        </div>
      </div>
    </details>
    <details open>
      <summary>All Line Items ({total_items} findings)</summary>
      <div class="detail-body" style="overflow-x:auto">
        <table>
          <thead>
            <tr>
              <th>Severity</th><th>System</th><th>Description</th><th>Location</th>
              <th style="text-align:right">DIY Low</th>
              <th style="text-align:right">Low</th>
              <th style="text-align:right">High</th>
              <th style="text-align:right">Avg</th>
            </tr>
          </thead>
          <tbody>
            {findings_rows}
          </tbody>
        </table>
      </div>
    </details>
    <details>
      <summary>Cost Summary</summary>
      <div class="detail-body">
        <div class="info-grid">
          <div>
            <div class="info-row"><span class="k">Total Low</span><span class="v">{format_currency(total_low)}</span></div>
            <div class="info-row"><span class="k">Total High</span><span class="v">{format_currency(total_high)}</span></div>
            <div class="info-row"><span class="k">Total Average</span><span class="v" style="color:#0A84FF">{format_currency(total_avg)}</span></div>
          </div>
          <div>
            <div class="info-row"><span class="k">Material Range</span><span class="v">{format_currency(summary.get("material_cost_low", total_low * 0.4))} - {format_currency(summary.get("material_cost_high", total_high * 0.4))}</span></div>
            <div class="info-row"><span class="k">Labor Range</span><span class="v">{format_currency(summary.get("labor_cost_low", total_low * 0.45))} - {format_currency(summary.get("labor_cost_high", total_high * 0.45))}</span></div>
            <div class="info-row"><span class="k">Permits</span><span class="v">{format_currency(summary.get("permit_cost", total_avg * 0.05))}</span></div>
          </div>
        </div>
      </div>
    </details>
  </section>

  <!-- 3. DEPRECIATION & CAPEX -->
  <section id="depreciation-capex" class="section" data-break="true">
    <div class="section-title"><span class="section-num">03</span> Depreciation &amp; CapEx</div>
    {"<details open><summary>System Depreciation Timeline</summary><div class='detail-body' style='overflow-x:auto'><table><thead><tr><th>System</th><th style='text-align:center'>Age (yrs)</th><th style='text-align:center'>Useful Life</th><th style='text-align:center'>Condition</th><th style='text-align:center'>Failure Prob</th><th style='text-align:right'>Replace Cost</th></tr></thead><tbody>" + dep_rows + "</tbody></table></div></details>" if dep_rows else '<p style="color:rgba(245,245,247,0.45);font-size:13px;padding:12px 0">No depreciation data available.</p>'}
    {"<details open><summary>24-Month CapEx Risk Horizon</summary><div class='detail-body' style='overflow-x:auto'><table><thead><tr><th>System</th><th style='text-align:center'>Failure Prob</th><th style='text-align:right'>Replacement Cost</th><th>Timeline</th><th>Risk Level</th></tr></thead><tbody>" + capex_rows + "</tbody></table>" + f"<div style='margin-top:12px;font-size:13px;color:rgba(245,245,247,0.55)'>Weighted 24-Month Risk Exposure: <span style='color:#FF9F0A;font-weight:600'>{format_currency(weighted_risk)}</span></div>" + "</div></details>" if capex_rows else '<p style="color:rgba(245,245,247,0.45);font-size:13px;padding:12px 0">No CapEx analysis data available.</p>'}
  </section>

  <!-- 4. MARKET & NEGOTIATION -->
  <section id="market-negotiation" class="section" data-break="true">
    <div class="section-title"><span class="section-num">04</span> Market &amp; Negotiation</div>
    <details open>
      <summary>Market Conditions</summary>
      <div class="detail-body">
        <div class="metric-grid grid-2" style="margin-bottom:16px">
          <div class="metric-card"><div class="label">Market Type</div><div class="value" style="font-size:18px">{market_type}</div></div>
          <div class="metric-card"><div class="label">Buyer Leverage</div><div class="value warn">{leverage}/100</div></div>
        </div>
        <div class="info-grid">
          <div>
            <div class="info-row"><span class="k">Avg Days on Market</span><span class="v">{avg_dom}</span></div>
            <div class="info-row"><span class="k">Months of Supply</span><span class="v">{months_supply}</span></div>
          </div>
          <div>
            <div class="info-row"><span class="k">Assessment</span><span class="v" style="font-size:12px">{leverage_desc}</span></div>
          </div>
        </div>
      </div>
    </details>
    {"<details open><summary>Negotiation Strategies (" + str(len(neg_strategies)) + " items)</summary><div class='detail-body' style='overflow-x:auto'><table><thead><tr><th>System</th><th>Severity</th><th>Strategy</th><th>Action</th><th style='text-align:right'>Savings</th></tr></thead><tbody>" + neg_rows + "</tbody></table></div></details>" if neg_rows else '<p style="color:rgba(245,245,247,0.45);font-size:13px;padding:12px 0">No negotiation strategies available.</p>'}
  </section>

  <!-- 5. CONTRACTOR BIDS -->
  <section id="contractor-bids" class="section" data-break="true">
    <div class="section-title"><span class="section-num">05</span> Contractor Bids</div>
    {"<details open><summary>Bid Comparison (" + str(len(bid_list)) + " bids)</summary><div class='detail-body' style='overflow-x:auto'><table><thead><tr><th>Contractor</th><th>Specialty</th><th style='text-align:right'>Bid Amount</th><th style='text-align:center'>Timeline</th><th style='text-align:center'>Rating</th><th>Status</th></tr></thead><tbody>" + bid_rows + "</tbody></table></div></details>" if bid_rows else '<p style="color:rgba(245,245,247,0.45);font-size:13px;padding:12px 0">No contractor bids available.</p>'}
  </section>

  <!-- 6. INSURANCE RISK -->
  <section id="insurance-risk" class="section" data-break="true">
    <div class="section-title"><span class="section-num">06</span> Insurance Risk</div>
    <div class="metric-card" style="display:inline-block;margin-bottom:16px">
      <div class="label">Insurability Score</div>
      <div class="value success">{insurability_score}</div>
    </div>
    {"<details open><summary>Red Flags &amp; Risk Items (" + str(len(ins_list)) + " items)</summary><div class='detail-body' style='overflow-x:auto'><table><thead><tr><th>Type</th><th>Risk Level</th><th>Description</th><th style='text-align:right'>Est. Cost</th></tr></thead><tbody>" + ins_rows + "</tbody></table></div></details>" if ins_rows else '<p style="color:rgba(245,245,247,0.45);font-size:13px;padding:12px 0">No insurance risk data available.</p>'}
  </section>

  <!-- 7. ENVIRONMENTAL RISK -->
  <section id="environmental" class="section" data-break="true">
    <div class="section-title"><span class="section-num">07</span> Environmental Risk</div>
    <details open>
      <summary>Climate &amp; Zone Overview</summary>
      <div class="detail-body">
        <div class="info-grid">
          <div>
            <div class="info-row"><span class="k">Climate Zone</span><span class="v">{climate_zone}</span></div>
            <div class="info-row"><span class="k">Flood Zone</span><span class="v">{flood_zone}</span></div>
          </div>
          <div>
            <div class="info-row"><span class="k">Wildfire Risk</span><span class="v">{wildfire_risk}</span></div>
            <div class="info-row"><span class="k">Earthquake Risk</span><span class="v">{earthquake_risk}</span></div>
          </div>
        </div>
      </div>
    </details>
    {"<details open><summary>Environmental Risk Items (" + str(len(env_items)) + " items)</summary><div class='detail-body' style='overflow-x:auto'><table><thead><tr><th>Risk Type</th><th>Severity</th><th>Description</th><th>Zone</th></tr></thead><tbody>" + env_rows + "</tbody></table></div></details>" if env_rows else '<p style="color:rgba(245,245,247,0.45);font-size:13px;padding:12px 0">No environmental risk items found.</p>'}
  </section>

  <!-- 8. PERMITS & RECORDS -->
  <section id="permits" class="section" data-break="true">
    <div class="section-title"><span class="section-num">08</span> Permits &amp; Records</div>
    <div class="metric-grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:16px">
      <div class="metric-card"><div class="label">Total Permits</div><div class="value">{total_permits}</div></div>
      <div class="metric-card"><div class="label">Compliant</div><div class="value success">{compliant_permits}</div></div>
      <div class="metric-card"><div class="label">Unpermitted</div><div class="value danger">{unpermitted_flags}</div></div>
      <div class="metric-card"><div class="label">Pending</div><div class="value gold">{pending_permits}</div></div>
    </div>
    {"<details open><summary>Permit Details (" + str(len(permit_items)) + " records)</summary><div class='detail-body' style='overflow-x:auto'><table><thead><tr><th>Type</th><th>Permit #</th><th>Status</th><th>Description</th><th>Date</th></tr></thead><tbody>" + permit_rows + "</tbody></table></div></details>" if permit_rows else '<p style="color:rgba(245,245,247,0.45);font-size:13px;padding:12px 0">No permit records available.</p>'}
  </section>

  <!-- 9. MANUFACTURER RECALLS -->
  <section id="recalls" class="section" data-break="true">
    <div class="section-title"><span class="section-num">09</span> Manufacturer Recalls</div>
    <div class="metric-card" style="display:inline-block;margin-bottom:16px">
      <div class="label">Potential Savings from Recalls</div>
      <div class="value accent">{format_currency(total_savings)}</div>
    </div>
    {"<details open><summary>Recall Matches (" + str(len(recall_items)) + " items)</summary><div class='detail-body' style='overflow-x:auto'><table><thead><tr><th>Product</th><th>Manufacturer</th><th>Recall Date</th><th>Status</th><th>Description</th><th style='text-align:right'>Savings</th></tr></thead><tbody>" + recall_rows + "</tbody></table></div></details>" if recall_rows else '<p style="color:rgba(245,245,247,0.45);font-size:13px;padding:12px 0">No manufacturer recall matches found.</p>'}
  </section>

  <!-- 10. ESCROW HOLDBACK -->
  <section id="escrow" class="section" data-break="true">
    <div class="section-title"><span class="section-num">10</span> Escrow Holdback</div>
    <div class="metric-card" style="display:inline-block;margin-bottom:16px">
      <div class="label">Total Recommended Holdback</div>
      <div class="value accent">{format_currency(total_holdback)}</div>
    </div>
    {"<details open><summary>Holdback Items &amp; Release Conditions</summary><div class='detail-body' style='overflow-x:auto'><table><thead><tr><th>Item</th><th style='text-align:right'>Amount</th><th>Release Condition</th><th>Status</th></tr></thead><tbody>" + escrow_rows + "</tbody></table></div></details>" if escrow_rows else '<p style="color:rgba(245,245,247,0.45);font-size:13px;padding:12px 0">No escrow holdback data available.</p>'}
  </section>

  <!-- 11. INVESTOR ANALYSIS -->
  <section id="investor" class="section" data-break="true">
    <div class="section-title"><span class="section-num">11</span> Investor Analysis</div>
    {"<div class='metric-grid grid-2' style='margin-bottom:16px'><div class='metric-card'><div class='label'>After Repair Value (ARV)</div><div class='value accent'>" + format_currency(inv_arv) + "</div></div><div class='metric-card'><div class='label'>Max Allowable Offer (MAO)</div><div class='value success'>" + format_currency(inv_mao) + "</div></div></div><div class='metric-grid' style='grid-template-columns:repeat(4,1fr);margin-bottom:16px'><div class='metric-card'><div class='label'>Cap Rate</div><div class='value'>" + str(inv_cap_rate) + "%</div></div><div class='metric-card'><div class='label'>Deal Grade</div><div class='value gold'>" + str(inv_grade) + "</div></div><div class='metric-card'><div class='label'>Monthly Rent</div><div class='value'>" + format_currency(inv_monthly_rent) + "</div></div><div class='metric-card'><div class='label'>Cash-on-Cash</div><div class='value'>" + str(inv_cash_on_cash) + "%</div></div></div>" if inv else '<p style="color:rgba(245,245,247,0.45);font-size:13px;padding:12px 0">No investor analysis data available.</p>'}
    {"<details open><summary>Key Metrics</summary><div class='detail-body' style='overflow-x:auto'><table><thead><tr><th>Metric</th><th style='text-align:right'>Value</th></tr></thead><tbody>" + inv_rows + "</tbody></table></div></details>" if inv_rows else ""}
  </section>

  <!-- SPATIAL DATA (if available) -->
  {"<section id='spatial' class='section' data-break='true'><div class='section-title'><span class='section-num'>12</span> Location &amp; Spatial Analysis</div>" + spatial_insights + "</section>" if spatial else ""}

  <!-- FOOTER -->
  <div class="footer">
    <strong>Disclaimer:</strong> This report is generated by automated analysis tools and is intended for informational purposes only.
    Cost estimates are based on regional averages and embedded cost databases. Actual contractor bids may vary.
    Always obtain licensed contractor estimates before making repair decisions. This report does not constitute
    engineering, legal, or financial advice. Consult licensed professionals for all structural, electrical,
    plumbing, and environmental assessments.<br><br>
    <strong>Data Sources:</strong> Regional cost databases, CPSC recall database, FEMA flood maps, local permit records,
    real-time market data, and embedded cost estimation models.<br><br>
    Generated on {datetime.now().strftime("%B %d, %Y at %I:%M %p")} &middot; Enterprise Report v3.0
  </div>

</div>
</body>
</html>"""
    return report_html


# ---------------------------------------------------------------------------
# Comprehensive CSV export (all modules)
# ---------------------------------------------------------------------------


def generate_csv_export(
    findings,
    cost_matrix,
    market_profile=None,
    insurance_analysis=None,
    environmental_data=None,
    permit_data=None,
    recall_data=None,
    negotiation_strategies=None,
    capex_analysis=None,
    depreciation_data=None,
    escrow_data=None,
    contractor_bids=None,
    spatial_data=None,
    investor_analysis=None,
    property_data=None,
):
    line_items = cost_matrix.get("line_items", [])
    summary = cost_matrix.get("summary", {})
    output = io.StringIO()
    writer = csv.writer(output)

    # --- HEADER ---
    writer.writerow(["COMPREHENSIVE PROPERTY ANALYSIS EXPORT"])
    writer.writerow([f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
    writer.writerow([])

    # --- SECTION: FINDINGS ---
    writer.writerow(["=== FINDINGS ==="])
    writer.writerow(
        [
            "System",
            "Severity",
            "Description",
            "Location",
            "Confidence",
            "DIY Low",
            "DIY High",
            "Contractor Low",
            "Contractor High",
            "Emergency Low",
            "Emergency High",
            "Material Low",
            "Material High",
            "Labor Low",
            "Labor High",
            "Permit Cost",
            "Total Low",
            "Total High",
            "Total Avg",
        ]
    )
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    items_with_idx = []
    for idx, finding in enumerate(findings):
        matching_cost = None
        for item in line_items:
            if finding.get("description", "")[:50] in item.get("finding", "") or item.get(
                "system", ""
            ) == finding.get("system_category", ""):
                matching_cost = item
                break
        if not matching_cost and idx < len(line_items):
            matching_cost = line_items[idx]
        items_with_idx.append((finding, matching_cost))
    items_with_idx.sort(key=lambda pair: severity_order.get(pair[0].get("severity", "MEDIUM"), 5))
    for finding, cost in items_with_idx:
        c = cost or {}
        writer.writerow(
            [
                finding.get("system_category", "N/A"),
                finding.get("severity", "MEDIUM"),
                finding.get("description", "N/A"),
                finding.get("location", "N/A"),
                finding.get("confidence_score", ""),
                c.get("diy_low", ""),
                c.get("diy_high", ""),
                c.get("total_low", c.get("contractor_low", "")),
                c.get("total_high", c.get("contractor_high", "")),
                c.get("emergency_low", ""),
                c.get("emergency_high", ""),
                c.get("material_cost_low", ""),
                c.get("material_cost_high", ""),
                c.get("labor_cost_low", ""),
                c.get("labor_cost_high", ""),
                c.get("permit_cost", ""),
                c.get("total_low", ""),
                c.get("total_high", ""),
                c.get("total_avg", ""),
            ]
        )
    writer.writerow([])

    # --- SECTION: COST SUMMARY ---
    writer.writerow(["=== COST SUMMARY ==="])
    writer.writerow(["Total Items", summary.get("total_items", len(findings))])
    writer.writerow(["Total Low", summary.get("total_low", 0)])
    writer.writerow(["Total High", summary.get("total_high", 0)])
    writer.writerow(["Total Average", summary.get("total_avg", 0)])
    rates = summary.get("rates_applied", {})
    if rates:
        writer.writerow(["ZIP Code", summary.get("zip_code", "")])
        writer.writerow(["City", rates.get("city", "")])
        writer.writerow(["Cost Modifier", rates.get("cost_modifier", "")])
        writer.writerow(["Avg Labor Rate", rates.get("avg_labor_rate", "")])
        writer.writerow(["Material Mult", rates.get("avg_material_mult", "")])
        writer.writerow(["Permit Fee", rates.get("permit_fee_estimate", "")])
    writer.writerow([])

    # --- SECTION: MARKET CONTEXT ---
    mp = _safe_dict(market_profile)
    if mp:
        writer.writerow(["=== MARKET CONTEXT ==="])
        writer.writerow(["Market Type", mp.get("market_type", "N/A")])
        writer.writerow(["Buyer Leverage", mp.get("leverage_score", "N/A")])
        writer.writerow(["Avg Days on Market", mp.get("avg_days_on_market", "N/A")])
        writer.writerow(["Months of Supply", mp.get("months_of_supply", "N/A")])
        writer.writerow(["Assessment", mp.get("leverage_description", "N/A")])
        writer.writerow([])

    # --- SECTION: NEGOTIATION STRATEGIES ---
    neg_strategies = (
        _safe_dict(negotiation_strategies).get("strategies", [])
        if isinstance(negotiation_strategies, dict)
        else []
    )
    if neg_strategies:
        writer.writerow(["=== NEGOTIATION STRATEGIES ==="])
        writer.writerow(["System", "Severity", "Strategy", "Action", "Estimated Savings"])
        for s in neg_strategies:
            writer.writerow(
                [
                    s.get("system", "N/A"),
                    s.get("severity", "N/A"),
                    s.get("strategy", "N/A"),
                    s.get("action", "N/A"),
                    s.get("estimated_savings", s.get("potential_savings", "N/A")),
                ]
            )
        writer.writerow([])

    # --- SECTION: INSURANCE RISK ---
    ins_list = _safe_list(insurance_analysis)
    if ins_list:
        writer.writerow(["=== INSURANCE RISK ==="])
        writer.writerow(["Type", "Risk Level", "Description", "Estimated Cost"])
        for ins in ins_list:
            writer.writerow(
                [
                    ins.get("type", ins.get("category", "N/A")),
                    ins.get("risk_level", ins.get("risk", "N/A")),
                    ins.get("description", ins.get("details", "N/A")),
                    ins.get("estimated_cost", ins.get("additional_cost", ins.get("cost", "N/A"))),
                ]
            )
        writer.writerow([])

    # --- SECTION: ENVIRONMENTAL RISK ---
    env_list = _safe_list(environmental_data) if isinstance(environmental_data, list) else []
    env_dict = _safe_dict(environmental_data) if isinstance(environmental_data, dict) else {}
    if env_list or env_dict:
        writer.writerow(["=== ENVIRONMENTAL RISK ==="])
        if env_dict:
            writer.writerow(["Climate Zone", env_dict.get("climate_zone", "N/A")])
            writer.writerow(["Flood Zone", env_dict.get("flood_zone", "N/A")])
            writer.writerow(["Wildfire Risk", env_dict.get("wildfire_risk", "N/A")])
            writer.writerow(["Earthquake Risk", env_dict.get("earthquake_risk", "N/A")])
        if env_list:
            writer.writerow(["Risk Type", "Severity", "Description", "Zone"])
            for e in env_list:
                writer.writerow(
                    [
                        e.get("risk_type", e.get("type", "N/A")),
                        e.get("severity", e.get("risk_level", "N/A")),
                        e.get("description", e.get("details", "N/A")),
                        e.get("zone", e.get("flood_zone", "N/A")),
                    ]
                )
        writer.writerow([])

    # --- SECTION: PERMITS ---
    permit_list = _safe_list(permit_data) if isinstance(permit_data, list) else []
    permit_dict = _safe_dict(permit_data) if isinstance(permit_data, dict) else {}
    if permit_list or permit_dict:
        writer.writerow(["=== PERMITS & COMPLIANCE ==="])
        if permit_dict:
            writer.writerow(["Total Permits", permit_dict.get("total_permits", "N/A")])
            writer.writerow(["Compliant", permit_dict.get("compliant", "N/A")])
            writer.writerow(
                ["Unpermitted", permit_dict.get("unpermitted_flags", permit_dict.get("non_compliant", 0))]
            )
            writer.writerow(["Pending", permit_dict.get("pending", "N/A")])
        if permit_list:
            writer.writerow(["Permit Type", "Permit Number", "Status", "Description", "Date"])
            for p in permit_list:
                writer.writerow(
                    [
                        p.get("permit_type", p.get("type", "N/A")),
                        p.get("permit_number", p.get("number", "N/A")),
                        p.get("status", "Unknown"),
                        p.get("description", p.get("details", "N/A")),
                        p.get("date", p.get("issue_date", "N/A")),
                    ]
                )
        writer.writerow([])

    # --- SECTION: RECALLS ---
    recall_list = _safe_list(recall_data)
    if recall_list:
        writer.writerow(["=== MANUFACTURER RECALLS ==="])
        writer.writerow(
            ["Product", "Manufacturer", "Recall Date", "Status", "Description", "Potential Savings"]
        )
        for r in recall_list:
            writer.writerow(
                [
                    r.get("product", r.get("item", "N/A")),
                    r.get("manufacturer", "N/A"),
                    r.get("recall_date", r.get("date", "N/A")),
                    r.get("status", "RECALL"),
                    r.get("description", r.get("recall_description", "N/A")),
                    r.get("potential_savings", r.get("estimated_savings", "N/A")),
                ]
            )
        writer.writerow([])

    # --- SECTION: ESCROW ---
    escrow_dict = _safe_dict(escrow_data) if isinstance(escrow_data, dict) else {}
    escrow_list = _safe_list(escrow_data)
    if escrow_dict or escrow_list:
        writer.writerow(["=== ESCROW HOLDBACK ==="])
        if escrow_dict:
            writer.writerow(["Total Holdback", escrow_dict.get("total_holdback", 0)])
            writer.writerow(["Recommended", escrow_dict.get("recommended", "N/A")])
        conditions = escrow_dict.get("conditions", []) if escrow_dict else []
        all_escrow = conditions + escrow_list
        if all_escrow:
            writer.writerow(["Item", "Amount", "Release Condition", "Status"])
            for e in all_escrow:
                writer.writerow(
                    [
                        e.get("item", e.get("description", "N/A")),
                        e.get("amount", 0),
                        e.get("condition", e.get("release_condition", "N/A")),
                        e.get("status", "Pending"),
                    ]
                )
        writer.writerow([])

    # --- SECTION: CONTRACTOR BIDS ---
    bids = _safe_dict(contractor_bids)
    bid_list = bids.get("bids", bids.get("contractors", [])) if bids else []
    if bid_list:
        writer.writerow(["=== CONTRACTOR BIDS ==="])
        writer.writerow(
            ["Contractor", "Specialty", "Bid Amount", "Timeline", "Rating", "Recommended", "Status"]
        )
        for b in bid_list:
            writer.writerow(
                [
                    b.get("contractor", b.get("name", "N/A")),
                    b.get("specialty", b.get("trade", "N/A")),
                    b.get("bid_amount", b.get("amount", 0)),
                    b.get("timeline", b.get("estimated_timeline", "N/A")),
                    b.get("rating", "N/A"),
                    b.get("recommended", b.get("is_recommended", False)),
                    b.get("status", "Pending"),
                ]
            )
        writer.writerow([])

    # --- SECTION: CAPEX ---
    capex = _safe_dict(capex_analysis)
    if capex:
        capex_summary = capex.get("summary", {})
        writer.writerow(["=== CAPEX ANALYSIS ==="])
        writer.writerow(["Weighted 24-Mo Risk", capex_summary.get("weighted_24mo_risk", 0)])
        writer.writerow(["Total Replacement Est", capex_summary.get("total_replacement", 0)])
        capex_systems = capex.get("systems", capex.get("items", []))
        if capex_systems:
            writer.writerow(["System", "Failure Probability", "Replacement Cost", "Timeline", "Risk Level"])
            for cs in capex_systems:
                writer.writerow(
                    [
                        cs.get("system", cs.get("name", "N/A")),
                        cs.get("failure_probability", cs.get("probability", "N/A")),
                        cs.get("replacement_cost", cs.get("cost", 0)),
                        cs.get("timeline", cs.get("expected_timeline", "N/A")),
                        cs.get("risk_level", cs.get("severity", "N/A")),
                    ]
                )
        writer.writerow([])

    # --- SECTION: DEPRECIATION ---
    dep = _safe_dict(depreciation_data)
    systems_dep = dep.get("systems", dep.get("items", dep.get("depreciation_items", []))) if dep else []
    if systems_dep:
        writer.writerow(["=== DEPRECIATION ==="])
        writer.writerow(
            ["System", "Age", "Useful Life", "Condition", "Failure Probability", "Replacement Cost"]
        )
        for d in systems_dep:
            writer.writerow(
                [
                    d.get("system", d.get("name", "N/A")),
                    d.get("age", "N/A"),
                    d.get("useful_life", "N/A"),
                    d.get("condition", d.get("condition_rating", "N/A")),
                    d.get("failure_probability", d.get("probability", "N/A")),
                    d.get("replacement_cost", d.get("cost", 0)),
                ]
            )
        writer.writerow([])

    # --- SECTION: INVESTOR ---
    inv = _safe_dict(investor_analysis)
    if inv:
        writer.writerow(["=== INVESTOR ANALYSIS ==="])
        writer.writerow(["ARV", inv.get("arv", inv.get("after_repair_value", 0))])
        writer.writerow(["MAO", inv.get("mao", inv.get("max_allowable_offer", 0))])
        writer.writerow(["Cap Rate", inv.get("cap_rate", inv.get("capitalization_rate", "N/A"))])
        writer.writerow(["Deal Grade", inv.get("deal_grade", inv.get("grade", "N/A"))])
        writer.writerow(["Monthly Rent", inv.get("monthly_rent", inv.get("estimated_rent", 0))])
        writer.writerow(["Cash-on-Cash", inv.get("cash_on_cash_return", inv.get("cash_on_cash", "N/A"))])
        writer.writerow(["NOI", inv.get("noi", inv.get("net_operating_income", 0))])
        writer.writerow([])

    # --- SECTION: SPATIAL ---
    spatial = _safe_dict(spatial_data)
    if spatial:
        writer.writerow(["=== SPATIAL / LOCATION ANALYSIS ==="])
        writer.writerow(["Walk Score", spatial.get("walk_score", "N/A")])
        writer.writerow(["Transit Score", spatial.get("transit_score", "N/A")])
        writer.writerow(["Location Rating", spatial.get("location_rating", "N/A")])
        dist_items = spatial.get("distances", spatial.get("nearby_places", []))
        if dist_items:
            writer.writerow(["Nearby Location", "Distance", "Impact"])
            for di in dist_items:
                writer.writerow(
                    [
                        di.get("name", di.get("location", "N/A")),
                        di.get("distance", "N/A"),
                        di.get("impact", di.get("price_impact", "N/A")),
                    ]
                )
        writer.writerow([])

    return output.getvalue()


# ---------------------------------------------------------------------------
# Comprehensive text report (all 21 modules)
# ---------------------------------------------------------------------------


def generate_text_report(
    property_data,
    findings,
    cost_matrix,
    market_profile,
    insurance_analysis=None,
    environmental_data=None,
    permit_data=None,
    recall_data=None,
    negotiation_strategies=None,
    capex_analysis=None,
    depreciation_data=None,
    escrow_data=None,
    contractor_bids=None,
    spatial_data=None,
    investor_analysis=None,
):
    summary = cost_matrix.get("summary", {})
    line_items = cost_matrix.get("line_items", [])
    address = f"{property_data.get('address', 'N/A')}, {property_data.get('city', 'N/A')}, {property_data.get('state', 'N/A')} {property_data.get('zip_code', 'N/A')}"
    year_built = property_data.get("year_built", 0)
    property_age = datetime.now().year - year_built if year_built > 0 else "Unknown"
    severity_breakdown = summary.get("by_severity", {})
    critical = severity_breakdown.get("CRITICAL", 0)
    high = severity_breakdown.get("HIGH", 0)
    medium = severity_breakdown.get("MEDIUM", 0)
    low = severity_breakdown.get("LOW", 0)
    total_items = summary.get("total_items", len(findings))
    total_low = summary.get("total_low", 0)
    total_high = summary.get("total_high", 0)
    total_avg = summary.get("total_avg", 0)
    market_type = market_profile.get("market_type", "N/A") if isinstance(market_profile, dict) else "N/A"
    leverage = market_profile.get("leverage_score", "N/A") if isinstance(market_profile, dict) else "N/A"

    if critical > 0:
        urgency = "IMMEDIATE ACTION REQUIRED"
        urgency_detail = (
            f"{critical} critical safety/structural issues demand immediate attention before closing."
        )
    elif high > 2:
        urgency = "HIGH PRIORITY"
        urgency_detail = f"{high} high-priority items require negotiation before or at closing."
    else:
        urgency = "STANDARD PROCESS"
        urgency_detail = "Findings are consistent with typical inspection results for the property age."

    sorted_items = sorted(line_items, key=lambda x: _severity_sort_key(x.get("severity", "MEDIUM")))
    findings_text = ""
    for idx, item in enumerate(sorted_items, 1):
        sev = item.get("severity", "MEDIUM")
        findings_text += f"""
  [{idx}] [{sev}] {item.get("system", "N/A")} - {item.get("finding", "N/A")}
      Location:     {item.get("location", "N/A")}
      Cost Range:   ${item.get("total_low", 0):,.0f} - ${item.get("total_high", 0):,.0f}
      Avg Estimate: ${item.get("total_avg", 0):,.0f}
      DIY Option:   ${item.get("diy_low", 0):,.0f} - ${item.get("diy_high", 0):,.0f}
      Emergency:    ${item.get("emergency_low", 0):,.0f} - ${item.get("emergency_high", 0):,.0f}
      Material:     ${item.get("material_cost_low", 0):,.0f} - ${item.get("material_cost_high", 0):,.0f}
      Labor:        ${item.get("labor_cost_low", 0):,.0f} - ${item.get("labor_cost_high", 0):,.0f}
      Permit:       ${item.get("permit_cost", 0):,.0f}
"""

    rates = summary.get("rates_applied", {})
    rates_text = ""
    if rates:
        rates_text = f"""
  ZIP Code:       {summary.get("zip_code", "N/A")}
  City:           {rates.get("city", "N/A")}
  Cost Modifier:  {rates.get("cost_modifier", 1.0)}x
  Avg Labor Rate: ${rates.get("avg_labor_rate", 60)}/hr
  Material Mult:  {rates.get("avg_material_mult", 1.0)}x
  Permit Fee Est: ${rates.get("permit_fee_estimate", 275)}
"""

    ins_list = _safe_list(insurance_analysis)
    insurance_text = ""
    if ins_list:
        for ins in ins_list:
            insurance_text += f"""
  - {ins.get("type", ins.get("category", "N/A"))} [{ins.get("risk_level", ins.get("risk", "N/A"))}]
    {ins.get("description", ins.get("details", "N/A"))}
    Estimated Cost: {ins.get("estimated_cost", ins.get("additional_cost", ins.get("cost", "N/A")))}
"""
    else:
        insurance_text = "\n  No insurance risk data available.\n"

    env_list = _safe_list(environmental_data) if isinstance(environmental_data, list) else []
    env_dict = _safe_dict(environmental_data) if isinstance(environmental_data, dict) else {}
    env_text = ""
    if env_list:
        for e in env_list:
            env_text += f"""
  - {e.get("risk_type", e.get("type", "N/A"))} [{e.get("severity", e.get("risk_level", "N/A"))}]
    {e.get("description", e.get("details", "N/A"))}
    Zone: {e.get("zone", e.get("flood_zone", "N/A"))}
"""
    elif env_dict:
        env_text = f"""
  Climate Zone:     {env_dict.get("climate_zone", "N/A")}
  Flood Zone:       {env_dict.get("flood_zone", "N/A")}
  Wildfire Risk:    {env_dict.get("wildfire_risk", "N/A")}
  Earthquake Risk:  {env_dict.get("earthquake_risk", "N/A")}
"""
    else:
        env_text = "\n  No environmental risk data available.\n"

    permit_list = _safe_list(permit_data) if isinstance(permit_data, list) else []
    permit_dict = _safe_dict(permit_data) if isinstance(permit_data, dict) else {}
    permit_text = ""
    if permit_list:
        for p in permit_list:
            permit_text += f"""
  - {p.get("permit_type", p.get("type", "N/A"))} [{p.get("status", "Unknown")}]
    {p.get("description", p.get("details", "N/A"))}
    Permit #: {p.get("permit_number", p.get("number", "N/A"))}
"""
    elif permit_dict:
        permit_text = f"""
  Total Permits:      {permit_dict.get("total_permits", "N/A")}
  Compliant:          {permit_dict.get("compliant", "N/A")}
  Non-Compliant:      {permit_dict.get("unpermitted_flags", permit_dict.get("non_compliant", "N/A"))}
  Pending:            {permit_dict.get("pending", "N/A")}
"""
    else:
        permit_text = "\n  No permit data available.\n"

    recall_list = _safe_list(recall_data)
    recall_text = ""
    if recall_list:
        for r in recall_list:
            recall_text += f"""
  - {r.get("product", r.get("item", "N/A"))} [{r.get("status", "Unknown")}]
    {r.get("description", r.get("recall_description", "N/A"))}
    Potential Savings: {r.get("potential_savings", r.get("estimated_savings", "N/A"))}
"""
    else:
        recall_text = "\n  No manufacturer recall matches found.\n"

    neg_strategies = (
        _safe_dict(negotiation_strategies).get("strategies", [])
        if isinstance(negotiation_strategies, dict)
        else []
    )
    negotiation_text = ""
    if neg_strategies:
        for s in neg_strategies:
            negotiation_text += f"""
  - [{s.get("severity", "N/A")}] {s.get("system", "N/A")}
    Strategy: {s.get("strategy", "N/A")}
    Action:   {s.get("action", "N/A")}
    Savings:  {s.get("estimated_savings", s.get("potential_savings", "N/A"))}
"""
    else:
        negotiation_text = "\n  No negotiation strategies available.\n"

    capex = _safe_dict(capex_analysis)
    capex_text = ""
    if capex:
        capex_summary = capex.get("summary", {})
        capex_systems = capex.get("systems", capex.get("items", []))
        capex_text = f"""
  Weighted 24-Mo Risk:    ${capex_summary.get("weighted_24mo_risk", 0):,.0f}
  Total Replacement Est:  ${capex_summary.get("total_replacement", 0):,.0f}
"""
        if capex_systems:
            capex_text += "  System Breakdown:\n"
            for cs in capex_systems:
                capex_text += f"    - {cs.get('system', cs.get('name', 'N/A'))}: Prob {cs.get('failure_probability', cs.get('probability', 'N/A'))} | Replace ${cs.get('replacement_cost', cs.get('cost', 0)):,.0f}\n"

    dep = _safe_dict(depreciation_data)
    dep_text = ""
    if dep:
        systems_dep = dep.get("systems", dep.get("items", dep.get("depreciation_items", [])))
        if systems_dep:
            dep_text = "  Depreciation Timeline:\n"
            for d in systems_dep:
                dep_text += f"    - {d.get('system', d.get('name', 'N/A'))}: Age {d.get('age', 'N/A')}y / Life {d.get('useful_life', 'N/A')}y | Condition: {d.get('condition', d.get('condition_rating', 'N/A'))}\n"

    escrow_dict = _safe_dict(escrow_data) if isinstance(escrow_data, dict) else {}
    escrow_list = _safe_list(escrow_data)
    escrow_text = ""
    if escrow_dict:
        escrow_text = f"""
  Total Holdback:   ${escrow_dict.get("total_holdback", 0):,.0f}
  Recommended:      {escrow_dict.get("recommended", "N/A")}
"""
        conditions = escrow_dict.get("conditions", [])
        if conditions:
            for c in conditions:
                escrow_text += f"    - {c.get('item', c.get('description', 'N/A'))}: ${c.get('amount', 0):,.0f} ({c.get('status', 'N/A')})\n"
    elif escrow_list:
        escrow_text = "  Escrow Holdback Items:\n"
        for e in escrow_list:
            escrow_text += f"    - {e.get('item', e.get('description', 'N/A'))}: ${e.get('amount', 0):,.0f} [{e.get('status', 'Pending')}]\n"
    else:
        escrow_text = "\n  No escrow holdback data available.\n"

    bids = _safe_dict(contractor_bids)
    bid_list = bids.get("bids", bids.get("contractors", [])) if bids else []
    contractor_text = ""
    if bid_list:
        contractor_text = "  Contractor Bids:\n"
        for b in bid_list:
            star = " *" if b.get("recommended", b.get("is_recommended", False)) else ""
            contractor_text += f"    - {b.get('contractor', b.get('name', 'N/A'))}{star}: ${b.get('bid_amount', b.get('amount', 0)):,.0f} [{b.get('status', 'Pending')}]\n"

    inv = _safe_dict(investor_analysis)
    investor_text = ""
    if inv:
        investor_text = f"""
  After Repair Value (ARV):   ${inv.get("arv", inv.get("after_repair_value", 0)):,.0f}
  Max Allowable Offer (MAO):  ${inv.get("mao", inv.get("max_allowable_offer", 0)):,.0f}
  Cap Rate:                   {inv.get("cap_rate", inv.get("capitalization_rate", "N/A"))}%
  Deal Grade:                 {inv.get("deal_grade", inv.get("grade", "N/A"))}
  Monthly Rent:               ${inv.get("monthly_rent", inv.get("estimated_rent", 0)):,.0f}
  Cash-on-Cash Return:        {inv.get("cash_on_cash_return", inv.get("cash_on_cash", "N/A"))}%
  NOI:                        ${inv.get("noi", inv.get("net_operating_income", 0)):,.0f}
"""

    spatial = _safe_dict(spatial_data)
    spatial_text = ""
    if spatial:
        spatial_text = f"""
  Walk Score:      {spatial.get("walk_score", "N/A")}
  Transit Score:   {spatial.get("transit_score", "N/A")}
  Location Rating: {spatial.get("location_rating", "N/A")}
"""
        dist_items = spatial.get("distances", spatial.get("nearby_places", []))
        if dist_items:
            spatial_text += "  Nearby Locations:\n"
            for di in dist_items:
                spatial_text += f"    - {di.get('name', di.get('location', 'N/A'))}: {di.get('distance', 'N/A')} ({di.get('impact', di.get('price_impact', 'N/A'))})\n"

    recommendations = []
    if critical > 0:
        recommendations.append(
            f"  * PRIORITY 1: Address {critical} critical finding(s) immediately. These represent safety or structural hazards."
        )
    if high > 0:
        recommendations.append(
            f"  * PRIORITY 2: Negotiate ${summary.get('high_cost', total_avg * 0.5):,.0f} in credits or price reduction for {high} high-severity items."
        )
    if medium > 0:
        recommendations.append(
            f"  * PRIORITY 3: Request seller remediation or escrow holdback for {medium} medium-severity code/compliance items."
        )
    recommendations.append(
        f"  * Plan ${total_avg:,.0f} in expected repair costs within the first 12 months of ownership."
    )
    if isinstance(market_profile, dict) and market_profile.get("leverage_score", 50) > 60:
        recommendations.append(
            "  * Market conditions favor buyers - leverage inspection findings in negotiations."
        )
    recs_text = (
        "\n".join(recommendations) if recommendations else "  No specific recommendations at this time."
    )

    text = f"""
{"=" * 80}
PROPERTY REPAIR COST ESTIMATE REPORT
Comprehensive 21-Module Enterprise Analysis
{"=" * 80}

PROPERTY INFORMATION
{"-" * 40}
  Address:        {address}
  Year Built:     {year_built}
  Property Age:   {property_age} years
  Type:           {property_data.get("property_type", "N/A")}
  Sq Footage:     {property_data.get("square_footage", "N/A")}
  Beds / Baths:   {property_data.get("bedrooms", "N/A")} / {property_data.get("bathrooms", "N/A")}
  Roof:           {property_data.get("roof_type", "N/A")}
  HVAC:           {property_data.get("hvac_type", "N/A")}
  Plumbing:       {property_data.get("plumbing_type", "N/A")}
  Electrical:     {property_data.get("electrical_type", "N/A")}
  Foundation:     {property_data.get("foundation_type", "N/A")}

{"=" * 80}
EXECUTIVE SUMMARY
{"=" * 80}

  Urgency:        {urgency}
  Detail:         {urgency_detail}
  Total Findings: {total_items} ({critical} Critical, {high} High, {medium} Medium, {low} Low)
  Cost Range:     ${total_low:,.0f} - ${total_high:,.0f}
  Average Est:    ${total_avg:,.0f}
  Market Type:    {market_type}
  Buyer Leverage: {leverage}/100

{"=" * 80}
DETAILED FINDINGS (Sorted by Severity)
{"=" * 80}
{findings_text}
{"=" * 80}
COST BREAKDOWN
{"=" * 80}

  Total Low:      ${total_low:,.0f}
  Total High:     ${total_high:,.0f}
  Total Average:  ${total_avg:,.0f}
{rates_text}
{"=" * 80}
DEPRECIATION & CAPEX ANALYSIS
{"=" * 80}
{dep_text if dep_text else "  No depreciation data available."}
{capex_text if capex_text else "  No CapEx analysis available."}

{"=" * 80}
MARKET ANALYSIS & NEGOTIATION
{"=" * 80}

  Market Type:         {market_type}
  Buyer Leverage:      {leverage}/100
  Avg Days on Market:  {market_profile.get("avg_days_on_market", "N/A") if isinstance(market_profile, dict) else "N/A"}
  Months of Supply:    {market_profile.get("months_of_supply", "N/A") if isinstance(market_profile, dict) else "N/A"}
  Assessment:          {market_profile.get("leverage_description", "N/A") if isinstance(market_profile, dict) else "N/A"}
{negotiation_text}
{"=" * 80}
CONTRACTOR BIDS
{"=" * 80}
{contractor_text if contractor_text else "  No contractor bid data available."}

{"=" * 80}
INSURANCE RISK SUMMARY
{"=" * 80}
{insurance_text}
{"=" * 80}
ENVIRONMENTAL RISK
{"=" * 80}
{env_text}
{"=" * 80}
PERMITS & COMPLIANCE
{"=" * 80}
{permit_text}
{"=" * 80}
MANUFACTURER RECALLS
{"=" * 80}
{recall_text}
{"=" * 80}
ESCROW HOLDBACK ANALYSIS
{"=" * 80}
{escrow_text}
{"=" * 80}
INVESTOR ANALYSIS
{"=" * 80}
{investor_text if investor_text else "  No investor analysis data available."}

{"=" * 80}
LOCATION & SPATIAL ANALYSIS
{"=" * 80}
{spatial_text if spatial_text else "  No spatial data available."}

{"=" * 80}
RECOMMENDATIONS
{"=" * 80}
{recs_text}

{"=" * 80}
DISCLAIMER
{"=" * 80}
This report is generated by automated analysis tools and is intended for informational
purposes only. Cost estimates are based on regional averages and embedded cost databases.
Actual contractor bids may vary. Always obtain licensed contractor estimates before
making repair decisions. This report does not constitute engineering, legal, or
financial advice. Consult licensed professionals for all structural, electrical,
plumbing, and environmental assessments.

Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}
"""
    return text
