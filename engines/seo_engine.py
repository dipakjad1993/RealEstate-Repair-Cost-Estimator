"""
SEO / GEO Engine (v3.4 — 2026 answer-surface strategy)
=======================================================
The 2026 reality this module is built against:
- Citations ≠ mentions (Semrush 2026 AI Visibility Index).
- llms.txt is a courtesy file, not a lever (97% of valid llms.txt got ZERO
  requests — AnswerMetrix 2026). Kept for crawler politeness, not strategy.
- Structured data alone does NOT drive AI citations (Ahrefs 1,885-page
  study). Schema = classic SEO foundation. Document-level Q&A structure +
  answer-shaped pages DO correlate with citations.
- Freshness + per-figure as_of matter more in AI answers than classic SERPs.
- Each engine (ChatGPT / Gemini / Perplexity / AI Mode) is its own channel
  — AIO vs AI Mode share only 13.7% of citations (Ahrefs).
- Same prompt 3x same day = 9.2% URL overlap (SE Ranking) — you need
  longitudinal prompt-portfolio tracking, not a one-shot check.

This engine therefore provides:
1. generate_seo_landing_pages  — programmatic Q&A answer hubs per ZIP/trade
2. Prompt portfolio registry   — 200 ICP prompts, per-engine tracking schema
3. track_ai_visibility         — mention + citation + sentiment per engine,
   with the St. Gallen rolling-window protocol (7+ runs/day, 2–4wk windows)
4. generate_seo_analytics      — honest UNAVAILABLE until real data connected

No fabricated impressions/clicks/traffic. Ever.
"""

from datetime import datetime, timezone


def generate_seo_landing_pages(zip_code, cost_data):
    systems = [
        ("hvac", "HVAC", "Air Conditioning & Heating"),
        ("roof", "Roof", "Roofing"),
        ("electrical", "Electrical", "Electrical"),
        ("plumbing", "Plumbing", "Plumbing"),
        ("foundation", "Foundation", "Foundation & Structural"),
        ("windows", "Windows", "Windows & Doors"),
    ]
    pages = []
    cost_data = cost_data or {}
    line_items = cost_data.get("line_items", [])
    by_system = {}
    for row in line_items:
        sys = (row.get("system") or "").lower()
        by_system.setdefault(sys, []).append(row)

    for system_key, system_name, system_display in systems:
        rows = by_system.get(system_key, []) or by_system.get(
            {"foundation": "structural"}.get(system_key), []
        )
        if rows:
            lows = [r["total_low"] for r in rows if r.get("total_low")]
            highs = [r["total_high"] for r in rows if r.get("total_high")]
            avg_cost = (
                round(sum((lo + hi) / 2 for lo, hi in zip(lows, highs, strict=False)) / max(len(lows), 1), 0)
                if lows
                else None
            )
        else:
            avg_cost = None
        # Real Next.js route pattern: /repair-cost/{state}/{system}-cost-2026/
        # In-app preview only — deploy docs/repair-cost/** MDX for indexable GEO pages.
        slug = f"repair-cost/{zip_code}/{system_key}-cost-2026"
        as_of = datetime.now(timezone.utc).date().isoformat()
        pages.append(
            {
                "zip_code": zip_code,
                "system_type": system_name,
                "system_display": system_display,
                "avg_cost": avg_cost,
                "cost_provenance": "VERIFIED" if avg_cost else "UNAVAILABLE",
                "as_of": as_of,
                "page_slug": slug,
                "nextjs_route": f"/{slug}",
                "markdown_twin_route": f"/{slug}.md",
                "page_title": f"Average Cost to Fix {system_display} in {zip_code} ({datetime.now().year}) — Provenance-tracked",
                "meta_description": f"What does {system_display.lower()} repair cost in {zip_code} in {datetime.now().year}? Verified baseline from inspection findings + BLS wages/PPI. Low/Mid/High with per-figure badges and as_of timestamps.",
                "h1": f"{system_display} Repair Costs in {zip_code} ({datetime.now().year}) — Low / Mid / High",
                "answer_capsule_50w": (
                    f"{system_display} repair in {zip_code} averages ${avg_cost:,.0f} in {datetime.now().year} "
                    f"(verified cost matrix, BLS wages + PPI). Low for minor scope, high for "
                    f"emergency/replacement. On-site quotes win; this is a baseline, not a bid."
                    if avg_cost
                    else f"No verified {system_display.lower()} cost data for {zip_code} yet — upload an inspection report."
                ),
                "content_sections": _generate_content_sections(system_name, zip_code, avg_cost),
                "qa_block": _generate_qa_block(system_display, zip_code, avg_cost),
                "analytics": {
                    "status": "UNAVAILABLE",
                    "note": "Connect GA4 or your analytics provider to this page's slug to collect real traffic metrics.",
                },
            }
        )
    return {
        "pages": pages,
        "total_pages": len(pages),
        "analytics_status": "UNAVAILABLE",
        "analytics_note": "No fabricated traffic data. Connect a real analytics provider.",
        "geo_strategy_note": (
            "These pages are answer-shaped (Q&A + number table + per-row as_of + source). "
            "Deploy as crawlable HTML with markdown twins. llms.txt is a courtesy file only — "
            "do not count on it as a GEO lever (AnswerMetrix 2026)."
        ),
    }


def _generate_content_sections(system, zip_code, avg_cost):
    cost_line = (
        f"Verified estimates for this zip range around ${avg_cost:,.0f} (from real inspection "
        f"findings indexed to BLS OEWS wages and BLS PPI materials)."
        if avg_cost
        else "No verified cost data yet for this zip in this system — upload an inspection report to build it."
    )
    return [
        {"heading": f"What Does {system} Repair Cost in {zip_code}?", "content": cost_line},
        {
            "heading": f"Common {system} Issues Found in {zip_code} Homes",
            "content": f"Findings are parsed from actual uploaded home inspection reports. System-level "
            f"averages update automatically as verified reports are processed for {zip_code}.",
        },
        {
            "heading": f"DIY vs. Professional {system} Repair in {zip_code}",
            "content": "Labor estimates use real BLS OEWS state median wages for the trade; material "
            "estimates are indexed to real BLS PPI construction indexes. DIY estimates reflect "
            "materials-only cost.",
        },
        {
            "heading": f"When to Negotiate {system} Repairs in {zip_code}",
            "content": "Request a sellers-credit equal to verified contractor estimates (not just the "
            "cheapest quote). The negotiation sandbox on the results page computes exact credit ranges.",
        },
    ]


def _generate_qa_block(system, zip_code, avg_cost):
    """Answer-shaped Q&A — the format AI engines actually cite (AnswerMetrix: informational + comparative = ~59% of citations)."""
    year = datetime.now().year
    cost_sentence = (
        f"Repair for {system.lower()} in {zip_code} averages ${avg_cost:,.0f} (range depends on scope), "
        f"based on BLS OEWS wages and BLS PPI materials indexed to {year}."
        if avg_cost
        else f"No verified {system.lower()} cost data for {zip_code} yet."
    )
    return [
        {"q": f"How much does {system} repair cost in {zip_code} in {year}?", "a": cost_sentence},
        {
            "q": f"Is {system} repair expensive in {zip_code}?",
            "a": "It depends on scope. A MODELED baseline is available per finding; "
            "contractor quotes always win over modeled figures.",
        },
        {
            "q": f"Should I get multiple quotes for {system} repair in {zip_code}?",
            "a": "Yes. This tool provides a provenance-tracked baseline, not a bid. "
            "Compare against 2–3 licensed local contractor quotes.",
        },
    ]


# ------------------------------------------------------------------
# Prompt portfolio + AI visibility tracking (St. Gallen protocol)
# ------------------------------------------------------------------
ICP_PROMPT_SEEDS = [
    "how much does it cost to replace polybutylene piping in {city} {year}",
    "is a Zinsco panel a dealbreaker in {state}",
    "average cost to rewire a 1960s house in {city}",
    "Federal Pacific panel insurance denial probability",
    "cost to replace knob and tube wiring {city}",
    "how much does a new roof cost in {zip}",
    "foundation crack repair cost {city}",
    "asbestos siding removal cost {state}",
    "lead paint abatement cost per room",
    "mold remediation cost {city}",
    "cost to replace aluminum wiring in {state}",
    "septic replacement cost {county}",
    "how much does HVAC replacement cost in {zip}",
    "radon mitigation system cost {state}",
    "termite damage repair cost {city}",
    "water intrusion repair cost {zip}",
    "cost of sewer line replacement {city}",
    "electrical panel upgrade cost {state}",
    "is knob and tube wiring a dealbreaker",
    "how to estimate repair costs from inspection report",
    "repair estimate vs contractor quote difference",
    "seller credit vs repair request which is better",
    "what is a good repair to ARV ratio",
    "how to calculate max allowable offer with repairs",
    "insurance red flags that cause homeowner denial",
    "roof age insurance non-renewal {state}",
    "FPE Stab-Lok panel replacement cost",
    "cost to abate asbestos insulation {city}",
    "polybutylene pipe insurance coverage {state}",
    "how much does it cost to upgrade electrical to 200 amp {zip}",
]


def build_prompt_portfolio(cities: list[str] | None = None, states: list[str] | None = None) -> dict:
    """Build the 200-prompt tracking portfolio from ICP seeds × geos."""
    cities = cities or ["Phoenix", "Austin", "Tampa", "Denver", "Charlotte", "Atlanta"]
    states = states or ["AZ", "TX", "FL", "CO", "NC", "GA"]
    year = datetime.now().year
    prompts = []
    for seed in ICP_PROMPT_SEEDS:
        for city in cities[:4]:
            for state in states[:2]:
                prompts.append(
                    {
                        "prompt_id": f"p{len(prompts) + 1:03d}",
                        "prompt": seed.format(city=city, state=state, zip="85001", county="local", year=year),
                        "geo": {"city": city, "state": state},
                        "icp_category": _classify_prompt(seed),
                        "runs_per_day": 7,
                        "window_days": 28,
                    }
                )
                if len(prompts) >= 200:
                    break
            if len(prompts) >= 200:
                break
        if len(prompts) >= 200:
            break
    return {
        "portfolio": prompts,
        "total_prompts": len(prompts),
        "protocol": (
            "St. Gallen AI-visibility protocol: 7+ runs/day/prompt, 2–4 week rolling "
            "windows, report as rate ± range. Same prompt 3x same day = ~9.2% URL "
            "overlap (SE Ranking) — single snapshots are noise."
        ),
        "engines": ["chatgpt", "gemini", "perplexity", "ai_mode"],
        "metrics_per_run": ["mentioned", "cited", "sentiment", "cited_url_rank"],
    }


def _classify_prompt(seed: str) -> str:
    s = seed.lower()
    if any(w in s for w in ("insurance", "denial", "non-renewal")):
        return "insurance_risk"
    if any(w in s for w in ("offer", "arv", "credit", "seller", "repair to")):
        return "investor_deal"
    if any(w in s for w in ("cost", "how much")):
        return "cost_query"
    return "general"


def track_ai_visibility(
    prompt_id: str,
    engine: str,
    runs: list[dict],
) -> dict:
    """
    Aggregate one prompt+engine's runs into a mention/citation rate ± range.

    runs: [{"mentioned": bool, "cited": bool, "sentiment": -1|0|1, "cited_url_rank": int|None}]
    Returns rates as a rolling aggregate. Never fabricates — requires real run data.
    """
    if not runs:
        return {"status": "UNAVAILABLE", "note": "No run data supplied. Connect a scraper/API."}
    n = len(runs)
    mentioned = sum(1 for r in runs if r.get("mentioned"))
    cited = sum(1 for r in runs if r.get("cited"))
    sentiments = [r.get("sentiment", 0) for r in runs]
    url_overlap = _pairwise_url_overlap(runs)
    return {
        "prompt_id": prompt_id,
        "engine": engine,
        "runs": n,
        "mention_rate": round(mentioned / n * 100, 2),
        "citation_rate": round(cited / n * 100, 2),
        "sentiment_mean": round(sum(sentiments) / n, 3),
        "url_overlap_pct": url_overlap,
        "status": "VERIFIED",
        "source": "USER_PROVIDED_VISIBILITY_RUNS",
        "badge": "USER_PROVIDED",
        "note": (
            "Citation rate (model linked your URL) is distinct from mention rate "
            "(model named your brand). Fewer than half of top-100 mentioned brands "
            "appear in top-100 citation lists (Semrush 2026). Track both."
        ),
    }


def _pairwise_url_overlap(runs: list[dict]) -> float | None:
    """Mean pairwise Jaccard overlap of cited_urls across runs — the AI volatility metric."""
    sets = [frozenset(r.get("cited_urls") or []) for r in runs if r.get("cited_urls")]
    if len(sets) < 2:
        return None
    overlaps = []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            union = sets[i] | sets[j]
            if union:
                overlaps.append(len(sets[i] & sets[j]) / len(union) * 100)
    return round(sum(overlaps) / len(overlaps), 2) if overlaps else None


def generate_seo_analytics(pages, user_analytics=None):
    """
    user_analytics: real per-slug {slug: {impressions, clicks, conversions}} from
    an analytics provider. Returns UNAVAILABLE when none supplied.
    """
    if not user_analytics:
        return {
            "status": "UNAVAILABLE",
            "note": "No analytics source connected. Import per-slug metrics (impressions/clicks/conversions) to enable this view.",
        }
    total_imp = sum(a.get("impressions", 0) for a in user_analytics.values())
    total_clk = sum(a.get("clicks", 0) for a in user_analytics.values())
    total_conv = sum(a.get("conversions", 0) for a in user_analytics.values())
    ctr = round(total_clk / max(total_imp, 1) * 100, 2)
    cr = round(total_conv / max(total_clk, 1) * 100, 2)
    return {
        "status": "VERIFIED",
        "source": "USER_ANALYTICS",
        "total_impressions": total_imp,
        "total_clicks": total_clk,
        "total_conversions": total_conv,
        "click_through_rate": ctr,
        "conversion_rate": cr,
        "recommendations": [
            f"Current CTR of {ctr}% — add schema markup for local business.",
            f"Conversion rate of {cr}% vs 3% industry average.",
            "Add FAQ sections targeting long-tail 'cost to fix [system] near me' queries.",
        ],
    }


def track_lead_magnet(zip_code, email=None, phone=None):
    """Honest lead record — no fabricated IP or lead value."""
    return {
        "email": email or "",
        "phone": phone or "",
        "zip_code": zip_code,
        "lead_captured": bool(email or phone),
        "conversion_timestamp": datetime.now(timezone.utc).isoformat(),
        "source_page": f"/repair-cost-estimator/{zip_code}",
        "note": "Lead value is determined by the agent's closed-deal economics, not fabricated here.",
    }


def generate_lead_magnet_widget_config(agent_name, agent_email, branding=None):
    config = {
        "widget_title": "Got a Scary Home Inspection Report?",
        "widget_subtitle": "Upload it here to see the verified repair cost in 60 seconds",
        "cta_button": "Analyze My Report Now",
        "agent_name": agent_name,
        "agent_email": agent_email,
        "branding": branding
        or {
            "primary_color": "#0071E3",
            "accent_color": "#7C3AED",
            "font_family": "'Google Sans Flex', 'Google Sans', 'Inter', sans-serif",
        },
        "lead_capture_fields": ["email", "phone"],
        "preview_items": 3,
        "unlock_message": "Enter your email and phone to unlock the full report with verified local repair estimates.",
    }
    return config
