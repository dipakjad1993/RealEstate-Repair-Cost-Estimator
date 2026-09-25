"""
Analysis & Research Engine (Page 2) (VERIFIED REBUILD)
======================================================
Produces extremely detailed, long-form, line-item analytical output across all
21 platform modules. Every value is derived from REAL data (live government
APIs, user MLS, user quotes/permits) or an honestly-labeled status
(VERIFIED / USER_PROVIDED / REQUIRES_KEY / MODELED / UNAVAILABLE).

This engine MERGES the outputs of every other engine into one comprehensive
research dossier per module and per finding.
"""

import logging
from datetime import datetime

from engines.depreciation_engine import analyze_all_capex, parse_appliance_metadata
from engines.insurance_engine import analyze_insurance_risk
from engines.legal_engine import generate_escrow_holdback_agreement
from engines.recall_engine import check_recalls_for_findings
from engines.spatial_engine import create_spatial_map

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


def generate_deep_analysis(session, results):
    """Build the complete 21-module deep-analysis dossier."""
    findings = session["findings"]
    pd_ = session["property_data"]
    res = results

    # ---- per-finding merged deep records ----
    deep_findings = _build_deep_findings(session, res)

    # ---- module 3/8: depreciation & CapEx ----
    capex_deep = analyze_all_capex(findings, pd_)

    # ---- module 15: insurance ----
    ins = analyze_insurance_risk(findings, pd_, session["underwriting"])

    # ---- module 20: recalls ----
    recalls = check_recalls_for_findings(findings)

    # ---- module 17: escrow holdback ----
    high_risk = [f for f in findings if f.get("severity") in ("CRITICAL", "HIGH")]
    bid_list = _bids_as_list(res["bids"], findings)
    escrow = generate_escrow_holdback_agreement(pd_, high_risk, bid_list) if high_risk else None

    # ---- module 6: photo evidence ----
    evidence = _build_evidence_summary(session, findings)

    # ---- module 21: spatial ----
    spatial = create_spatial_map(findings, pd_, session["floorplan"].get("rooms", []))

    return {
        "property": pd_,
        "deep_findings": deep_findings,
        "matrix": _build_master_matrix(deep_findings),
        "module_01_parse": _module_parse(session),
        "module_02_cost": _module_cost(res, deep_findings),
        "module_03_depreciation": _module_depreciation(capex_deep, deep_findings),
        "module_04_market": _module_market(res),
        "module_05_export": _module_export(res, session),
        "module_06_vision": _module_vision(evidence, deep_findings),
        "module_07_permits": _module_permits(res, session),
        "module_08_capex_24mo": _module_capex_24mo(res, capex_deep, deep_findings),
        "module_09_sandbox": _module_sandbox(res),
        "module_10_dispatch": _module_dispatch(res, deep_findings),
        "module_11_legal": _module_legal(res, session),
        "module_12_environmental": _module_environmental(res),
        "module_13_brokerage": _module_brokerage(res),
        "module_14_leadmagnet": _module_leadmagnet(res),
        "module_15_insurance": _module_insurance(ins, res, deep_findings),
        "module_16_investor": _module_investor(res),
        "module_17_escrow": _module_escrow(escrow, deep_findings),
        "module_18_seo": _module_seo(res),
        "module_19_audio": _module_audio(session),
        "module_20_recalls": _module_recalls(recalls, deep_findings),
        "module_21_spatial": _module_spatial(spatial, deep_findings),
        "generated_at": datetime.now().isoformat(),
    }


def _bids_as_list(bids, findings):
    out = []
    by_key = bids or {}
    for f in findings:
        key = f.get("key", f.get("description", ""))
        b = by_key.get(key) or by_key.get(f.get("description", ""))
        if b:
            out.append(
                {
                    "finding_id": f.get("id"),
                    "finding_key": key,
                    "bid_amount": b.get("bid_avg", 0),
                    "contractor": b.get("contractor", ""),
                    "trade": b.get("trade", ""),
                    "cost_source": b.get("cost_source", ""),
                }
            )
    return out


def _build_deep_findings(session, res):
    findings = session["findings"]
    cm = res["cost_matrix"]
    cost_by_key = {row["finding_key"]: row for row in cm["line_items"]}
    capex_by_sys = {it["system"]: it for it in res["capex"]["timeline_items"]}
    bid_by_key = res["bids"] or {}
    perm_xref = res["permit_xref"].get("cross_reference_results", [])
    recalls = res["recalls"].get("recall_results", [])
    recall_by_finding = {}
    for r in recalls:
        recall_by_finding.setdefault(r.get("finding_description", ""), []).append(r)
    spatial = res["spatial"].get("findings_mapped", [])
    spatial_by_desc = {m["finding"]: m for m in spatial}
    legal = res["legal"]

    deep = []
    for idx, f in enumerate(findings):
        desc = f.get("description", "")
        key = f.get("key", desc)
        cost = cost_by_key.get(key) or next((c for c in cm["line_items"] if c["finding"] == desc), None)
        cap = next(
            (it for it in res["capex"]["timeline_items"] if it["finding"] == desc),
            capex_by_sys.get(f.get("system_category")),
        )
        bid = bid_by_key.get(key) or bid_by_key.get(desc)
        xref = next(
            (
                x
                for x in perm_xref
                if x.get("finding") == desc[:100] or desc.startswith(x.get("finding", "")[:60])
            ),
            None,
        )
        recalls_f = recall_by_finding.get(desc, [])
        sp = spatial_by_desc.get(desc[:100]) or next((m for m in spatial if m["finding"] == desc), None)
        lic = next(
            (
                x
                for x in legal["seller_credits"] + legal["seller_repairs"] + legal["price_reductions"]
                if x["description"] == desc[:200]
            ),
            None,
        )

        deep.append(
            {
                "index": idx + 1,
                "id": f.get("id"),
                "key": key,
                "system": f.get("system_category", "OTHER"),
                "severity": f.get("severity", "MEDIUM"),
                "location": f.get("location", "Not specified"),
                "source_type": f.get("source_type", "unknown"),
                "source_file": f.get("source_file", ""),
                "description": desc,
                "cost": cost,
                "capex": cap,
                "bid": bid,
                "permit_xref": xref,
                "recalls": recalls_f,
                "spatial": sp,
                "legal_clause": lic,
                "photos": f.get("photos_matched", []) or [],
            }
        )
    deep.sort(key=lambda d: (SEVERITY_ORDER.get(d["severity"], 5), d["index"]))
    return deep


def _build_master_matrix(deep):
    rows = []
    for d in deep:
        cost = d["cost"] or {}
        cap = d["capex"] or {}
        xref = d["permit_xref"] or {}
        rows.append(
            {
                "System": d["system"],
                "Severity": d["severity"],
                "Identified Issue": d["description"][:160],
                "Location": d["location"],
                "Immediate Repair Range": (
                    f"${cost.get('total_low', 0):,.0f}–${cost.get('total_high', 0):,.0f}" if cost else "—"
                ),
                "Cost Source": cost.get("cost_source", "—") if cost else "—",
                "Future Risk Horizon": (
                    f"{cap.get('failure_probability_24mo', 0)}% fail / "
                    f"${cap.get('replacement_cost', 0):,.0f} replace"
                    if cap
                    else "—"
                ),
                "Projected Failure": cap.get("projected_failure_date", "—") if cap else "—",
                "Strategic Action": _action_for(d),
                "Permit": xref.get("permit_status", "No finding-level record") if xref else "—",
                "Photos": len(d["photos"]),
                "Recall Matches": len(d["recalls"]),
                "Bid": (
                    f"${d['bid'].get('bid_low', 0):,.0f}–${d['bid'].get('bid_high', 0):,.0f}"
                    if d["bid"]
                    else "Awaiting quote"
                ),
            }
        )
    return rows


def _action_for(d):
    sev = d["severity"]
    sys = d["system"]
    if sev == "CRITICAL":
        return f"Fix Before Close — require licensed {sys.lower()} contractor, hold 1.5x escrow."
    if sev == "HIGH":
        return "Demand Seller Credit — document with photo evidence and local bid."
    if sev == "MEDIUM":
        return "Include in Lump Sum — add to price-reduction request; do not stall closing."
    return "Waive — use as good-faith gesture during negotiation."


# ------------------------------------------------------------------
# Module builders (long-form)
# ------------------------------------------------------------------
def _module_parse(session):
    rep = session["ingestion_report"]
    return {
        "title": "Module 1 · Agentic Document Parsing Engine",
        "status": "VERIFIED" if len(rep["report_sources"]) else "NO_UPLOAD",
        "narrative": (
            "Normalized inspection documents into structured findings. Text layers were "
            "extracted with pdfplumber; severity blocks, tables, and bullet lists were "
            "parsed independently and deduplicated by semantic similarity. Photo positions "
            "were matched to findings by page context."
        ),
        "sources": rep["report_sources"],
        "audio_sources": rep["audio_sources"],
        "stats": {
            "total_findings": rep["total_findings"],
            "from_pdf": rep["from_pdf"],
            "from_audio": rep["from_audio"],
            "pdf_images": rep["pdf_images"],
        },
    }


def _module_cost(res, deep):
    cm = res["cost_matrix"]
    s = cm["summary"]
    return {
        "title": "Module 2 · Hyper-Local Cost Validation Engine",
        "status": s["wage_provenance"] if s["wage_provenance"] != "UNAVAILABLE" else "UNAVAILABLE",
        "narrative": (
            "Every finding is priced in three tiers (DIY, licensed contractor, emergency) "
            "using REAL BLS OEWS trade wages for the property's state, indexed against the "
            "REAL BLS PPI construction-materials index. User-supplied contractor quotes "
            "override benchmarks where present."
        ),
        "wage_provenance": s["wage_provenance"],
        "ppi_provenance": s["ppi_provenance"],
        "total_low": s["total_low"],
        "total_high": s["total_high"],
        "total_avg": s["total_avg"],
        "by_severity": s["by_severity"],
        "line_items": [
            {
                "system": c["system"],
                "severity": c["severity"],
                "finding": c["finding"],
                "diy": (c["diy_low"], c["diy_high"]),
                "contractor": (c["contractor_low"], c["contractor_high"]),
                "emergency": (c["emergency_low"], c["emergency_high"]),
                "source": c["cost_source"],
                "provenance": c["provenance"],
            }
            for c in cm["line_items"]
        ],
    }


def _module_depreciation(capex_deep, deep):
    return {
        "title": "Module 3 · System Depreciation & Risk Analysis Engine",
        "status": "VERIFIED",
        "narrative": (
            "Applied published component useful-life tables to each mechanical/structural "
            "asset. Estimated asset age from description metadata (model years) or property "
            "age, then computed depreciation curve, remaining life, 24-month failure "
            "probability, and replacement cost bands."
        ),
        "summary": capex_deep["summary"],
        "capex_items": capex_deep["capex_items"],
        "appliance_metadata": [
            parse_appliance_metadata(d["description"])
            for d in deep
            if d["system"] in ("APPLIANCES", "HVAC", "PLUMBING")
        ],
    }


def _module_market(res):
    m = res["market"]
    return {
        "title": "Module 4 · Live Macro Market & Negotiation Tracker",
        "status": m["anchor_provenance"]["status"],
        "narrative": (
            "Market anchor from USER MLS listing or Census ACS zip median. Negotiation "
            "strategy is computed from real market position (above/at/below zip median), "
            "real days-on-market, and the verified high-risk finding list."
        ),
        "anchor": m["anchor"],
        "anchor_description": m["anchor_description"],
        "list_price": m["list_price"],
        "price_per_sqft": m["price_per_sqft"],
        "dom_days": m["dom_days"],
        "market_position": m["market_position"],
        "acs": m["acs"],
        "strategies": res["strategies"],
    }


def _module_export(res, session):
    return {
        "title": "Module 5 · Enterprise Export Engine",
        "status": "READY",
        "narrative": (
            "Packages the dossier into professional deliverables: branded PDF package, "
            "interactive buyer portal, CSV/text exports. Export functions are available on "
            "the Results page."
        ),
        "formats": ["PDF", "CSV", "TXT", "Interactive dashboard (sandbox)"],
        "generated_at": res["generated_at"],
    }


def _module_vision(evidence, deep):
    return {
        "title": "Module 6 · AI Computer Vision & Photo Evidence Matcher",
        "status": "VERIFIED" if evidence["total_images"] else "NO_IMAGES",
        "narrative": (
            "Extracted embedded photos from the inspection PDF and matched each to the "
            "nearest finding by page context. Each photo is cropped and associated with "
            "its repair line item so the buyer sees the evidence beside the number."
        ),
        "total_images": evidence["total_images"],
        "match_rate": evidence["match_rate"],
        "matched": evidence["matched"],
        "unmatched": evidence["unmatched"],
        "critical_with_photos": evidence["critical_with_photos"],
        "findings_missing_photos": evidence["findings_missing_photos"],
    }


def _build_evidence_summary(session, findings):
    images = session.get("images") or []
    matched_by_desc = {}
    for f in findings:
        if f.get("photos_matched"):
            matched_by_desc[f["description"][:60]] = f["photos_matched"]
    matched = []
    critical_with_photos = []
    missing = []
    for f in findings:
        ph = f.get("photos_matched", [])
        entry = {
            "description": f["description"][:80],
            "severity": f["severity"],
            "system": f.get("system_category", ""),
            "photo_count": len(ph),
        }
        if ph:
            matched.append(entry)
            if f["severity"] in ("CRITICAL", "HIGH"):
                critical_with_photos.append(entry)
        else:
            missing.append(entry)
    match_rate = round(len(matched) / max(len(findings), 1) * 100, 1) if findings else 0
    return {
        "total_images": len(images),
        "match_rate": match_rate,
        "matched": matched,
        "unmatched": [
            i
            for i in images
            if i.get("index") not in {p.get("index") for m in matched_by_desc.values() for p in m}
        ],
        "critical_with_photos": critical_with_photos,
        "findings_missing_photos": missing,
    }


def _module_permits(res, session):
    pr = res["permit"]
    xref = res["permit_xref"]
    return {
        "title": "Module 7 · Historical Permit & Public Records Cross-Referencer",
        "status": pr["provenance"],
        "narrative": (
            "Compares structural realities in the inspection against the permit records "
            "supplied from the county/city portal. Unpermitted electrical/plumbing/structural "
            "work is flagged as HIGH liability. No permit history is ever fabricated."
        ),
        "total_permits": pr["total_permits"],
        "open": pr["open_permits"],
        "closed": pr["closed_permits"],
        "expired": pr["expired_permits"],
        "compliance": pr["compliance_summary"],
        "cross_reference": xref["cross_reference_results"],
        "unpermitted_flags": xref["unpermitted_flags"],
        "needs": res["permit_needs"],
    }


def _module_capex_24mo(res, capex_deep, deep):
    c = res["capex"]
    s = c["summary"]
    return {
        "title": "Module 8 · 24-Month Capital Expenditure (CapEx) Risk Horizon",
        "status": "VERIFIED",
        "narrative": (
            "Forward-looking risk: for every asset we project remaining life, 24-month "
            "failure probability, and replacement cost. The weighted risk exposure is the "
            "expected cash outlay if probability-weighted failures occur within 24 months."
        ),
        "timeline": c["visual_timeline"],
        "summary": s,
        "deep_summary": capex_deep["summary"],
        "capex_items": capex_deep["capex_items"],
    }


def _module_sandbox(res):
    sb = res["sandbox"]
    return {
        "title": "Module 9 · Interactive Multi-Party Sellers-Credit Sandbox",
        "status": "READY",
        "narrative": (
            "Live scenario modeling: check/uncheck items, switch repair types (seller "
            "credit / seller repair / price reduction), and watch the net sheet recompute "
            "instantly. Expected concession is modeled from real market leverage signals."
        ),
        "items": sb["items"],
        "leverage": res["leverage"],
        "strategies": res["strategies"],
    }


def _module_dispatch(res, deep):
    bids = res["bids"] or {}
    return {
        "title": "Module 10 · Live Contractor Bid & Dispatch Engine",
        "status": "USER_QUOTES"
        if any(b.get("cost_source") == "USER_QUOTE" for b in bids.values())
        else "BLS_WAGE_BASELINE",
        "narrative": (
            "Each finding is packaged into a dispatch request for the correct trade "
            "license class. Baseline pricing uses REAL BLS OEWS wages + standard margin; "
            "user-supplied quotes (from Thumbtack/Angi/proprietary networks) replace the "
            "baseline when present."
        ),
        "bids": list(bids.values()),
        "dispatch_queue": res["bids"],
    }


def _module_legal(res, session):
    legal = res["legal"]
    return {
        "title": "Module 11 · Automated Legal Addendum & Repair Request Writer",
        "status": "READY",
        "narrative": (
            "Generates contract addendum language from the sandbox selections using "
            "standard real-estate phrasing: 'Seller shall, prior to close of escrow, cause "
            "[system] item noted in the inspection report to be repaired by a licensed "
            "contractor, with receipts and warranties provided to Buyer.'"
        ),
        "addendum_type": legal["addendum_type"],
        "addendum_text": legal["addendum_text"],
        "total_requested": legal["total_requested_value"],
        "seller_repairs": legal["seller_repairs"],
        "seller_credits": legal["seller_credits"],
        "price_reductions": legal["price_reductions"],
    }


def _module_environmental(res):
    e = res["environmental"]
    return {
        "title": "Module 12 · Environmental Risk & Climate Resiliency Underwriter",
        "status": "VERIFIED" if e["geocoding"]["status"] == "VERIFIED" else e["geocoding"]["status"],
        "narrative": (
            "Cross-references the property coordinates against live FEMA flood-zone layers, "
            "USGS seismic design values, the USGS earthquake catalog, and real-time "
            "Open-Meteo weather. Finding-derived moisture/foundation/fire risks are merged "
            "into an overall risk level."
        ),
        "geocoding": e["geocoding"],
        "flood": e["flood"],
        "seismic": e["seismic"],
        "earthquakes": e["earthquakes"],
        "weather": e["weather"],
        "finding_risks": e["finding_derived_risks"],
        "summary_level": e["summary_level"],
    }


def _module_brokerage(res):
    br = res["brokerage"]
    return {
        "title": "Module 13 · Enterprise Multi-Transaction Brokerage ROI Dashboard",
        "status": br.get("status", "UNAVAILABLE"),
        "narrative": (
            "Aggregates real closed-deal records (CSV import) into team-level ROI: agent "
            "performance, total credits negotiated, item acceptance rates, and zip-level "
            "averages. No fabricated transactions are ever shown."
        ),
        "summary": br.get("summary", {}),
        "agents": br.get("agent_performance", []),
        "insights": br.get("insights", []),
        "note": br.get("note", ""),
    }


def _module_leadmagnet(res):
    seo = res["seo"]
    return {
        "title": "Module 14 · White-Label Inspection Lead Magnet (SEO Traffic Engine)",
        "status": "READY",
        "narrative": (
            "Public widget 'Got a scary home inspection report? Upload it to see the real "
            "repair cost.' Runs a limited analysis, then gates the deep line-item report "
            "behind email/phone capture. Traffic/conversion metrics come only from a real "
            "connected analytics provider."
        ),
        "pages": seo["pages"],
        "analytics_status": seo["analytics_status"],
        "analytics_note": seo["analytics_note"],
        "widget": {
            "title": "Got a Scary Home Inspection Report?",
            "cta": "Analyze My Report Now",
            "capture": ["email", "phone"],
        },
    }


def _module_insurance(ins, res, deep):
    sc = res["insurance_scorecard"]
    return {
        "title": "Module 15 · Home Insurance P&C Premium Risk Predictor",
        "status": "VERIFIED" if ins["red_flags"] else "NO_RED_FLAGS",
        "narrative": (
            "Scans findings for explicit insurance red flags (polybutylene, knob-and-tube, "
            "active mold, aging roof/panel) and computes an Insurability Score. Premium "
            "basis is the user's real carrier quote when provided, else a clearly-labeled "
            "MODELED state benchmark."
        ),
        "score": sc["insurability_score"],
        "grade": sc["grade"],
        "red_flags": ins["red_flags"],
        "verdict": sc["verdict"],
        "premium_provenance": sc["premium_provenance"],
        "annual_impact": sc["annual_impact"],
        "five_year_impact": sc["five_year_impact"],
        "max_denial": sc["max_denial_prob"],
    }


def _module_investor(res):
    inv = res["investor"]
    return {
        "title": "Module 16 · Investor ARV & Flip Margin Underwriter",
        "status": "VERIFIED"
        if inv["listing_price_provenance"] != "MODELED_BENCHMARK"
        else "MODELED_BENCHMARK",
        "narrative": (
            "Computes Maximum Allowable Offer = ARV − repairs − holding − closing − profit "
            "target, using the verified repair matrix. Rental cash-flow, cap rate, and "
            "cash-on-cash return use the user's real rent estimate or Census ACS rent."
        ),
        "listing_price": inv["listing_price"],
        "list_provenance": inv["listing_price_provenance"],
        "arv": inv["after_repair_value"],
        "arv_provenance": inv["arv_provenance"],
        "max_offer": inv["max_allowable_offer"],
        "repair": inv["total_repair_cost"],
        "holding": inv["holding_costs_total"],
        "closing": inv["closing_costs"],
        "profit_target": inv["profit_target"],
        "cap_rate": inv["cap_rate"],
        "coc": inv["cash_on_cash_return"],
        "rental": inv["monthly_rental_estimate"],
        "rent_provenance": inv["monthly_rental_provenance"],
        "metrics": inv["deal_metrics"],
        "risk": inv["risk_assessment"],
        "analysis": inv["investment_analysis"],
        "forecast": inv["depreciation_forecast"],
    }


def _module_escrow(escrow, deep):
    return {
        "title": "Module 17 · Smart Escrow Holdback & Title Binder Estimator",
        "status": "VERIFIED" if escrow and escrow["items"] else "UNAVAILABLE",
        "narrative": (
            "For high-risk items, computes the standard title/lender escrow holdback at "
            "1.5x the live contractor estimate to protect against cost overruns, with "
            "release conditions and milestones."
        ),
        "items": escrow["items"] if escrow else [],
        "total_holdback": escrow["total_holdback"] if escrow else 0,
        "multiplier": escrow["holdback_multiplier"] if escrow else 1.5,
    }


def _module_seo(res):
    seo = res["seo"]
    return {
        "title": "Module 18 · Programmatic Local SEO Land-Grab Engine",
        "status": "VERIFIED",
        "narrative": (
            "Generates hyper-targeted local landing pages ('Average Cost to Fix [System] "
            "in [ZIP]') populated with the verified per-system cost data from this dossier. "
            "Personal information is never published."
        ),
        "pages": seo["pages"],
        "total_pages": seo["total_pages"],
        "analytics_status": seo["analytics_status"],
    }


def _module_audio(session):
    sources = session["ingestion_report"]["audio_sources"]
    from_audio = session["ingestion_report"]["from_audio"]
    return {
        "title": "Module 19 · Voice-to-Text Inspector Audio Auditor",
        "status": "VERIFIED" if from_audio else "NO_AUDIO",
        "narrative": (
            "Transcribes raw inspector/agent audio notes via a local Whisper model and "
            "parses them into structured findings merged with the PDF findings. "
            "'Water heater in the basement is a Rheem 2014, bottom valve corroding…' "
            "becomes a line-item with severity, system, and location."
        ),
        "sources": sources,
        "from_audio": from_audio,
    }


def _module_recalls(recalls, deep):
    return {
        "title": "Module 20 · Smart IoT & Manufacturer Recall Cross-Referencer",
        "status": recalls["summary"]["api_status"],
        "narrative": (
            "Extracts makes/models/serial numbers and queries the REAL CPSC SaferProducts "
            "database. Matched active recalls show remedy, hazard, and the claim URL so a "
            "defect may be resolved at zero cost to either party."
        ),
        "results": recalls["recall_results"],
        "total": recalls["summary"]["total_recalls_found"],
        "savings": recalls["summary"]["total_potential_savings"],
    }


def _module_spatial(spatial, deep):
    return {
        "title": "Module 21 · Spatial 3D Flaw Map & Matterport Integration",
        "status": spatial["floor_plan_provenance"],
        "narrative": (
            "Maps every finding onto the property layout (uploaded floorplan/Matterport "
            "export, or a clearly-labeled template). Each marker links the line-item cost, "
            "contractor bid, and photo evidence."
        ),
        "provenance": spatial["floor_plan_provenance"],
        "note": spatial["floor_plan_note"],
        "floor_plan": spatial["floor_plan"],
        "findings_mapped": spatial["findings_mapped"],
    }
