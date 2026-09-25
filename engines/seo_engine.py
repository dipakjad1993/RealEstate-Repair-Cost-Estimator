"""
SEO Landing Page Engine (VERIFIED REBUILD)
==========================================
Programmatically generated local landing pages from REAL data:
- Real ZIP code
- Real repair costs from the verified cost matrix
- Honest analytics (UNAVAILABLE until a real analytics source is connected)

No random impressions/clicks/traffic or fabricated lead values.
"""

from datetime import datetime


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
        pages.append(
            {
                "zip_code": zip_code,
                "system_type": system_name,
                "system_display": system_display,
                "avg_cost": avg_cost,
                "cost_provenance": "VERIFIED" if avg_cost else "UNAVAILABLE",
                "page_slug": slug,
                "nextjs_route": f"/{slug}",
                "page_title": f"Average Cost to Fix {system_display} in {zip_code} (2026) — Provenance-tracked",
                "meta_description": f"What does {system_display.lower()} repair cost in {zip_code} in 2026? Verified baseline from inspection findings + BLS wages/PPI. Low/Mid/High with provenance.",
                "h1": f"{system_display} Repair Costs in {zip_code} (2026) — Low / Mid / High",
                "answer_capsule_50w": (
                    f"{system_display} repair in {zip_code} averages ${avg_cost:,.0f} in 2026 "
                    f"(verified cost matrix, BLS wages + PPI). Low for minor scope, high for "
                    f"emergency/replacement. On-site quotes win; this is a baseline, not a bid."
                    if avg_cost
                    else f"No verified {system_display.lower()} cost data for {zip_code} yet — upload an inspection report."
                ),
                "content_sections": _generate_content_sections(system_name, zip_code, avg_cost),
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
        "conversion_timestamp": datetime.now().isoformat(),
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
            "primary_color": "#1E40AF",
            "accent_color": "#F59E0B",
            "font_family": "Inter, sans-serif",
        },
        "lead_capture_fields": ["email", "phone"],
        "preview_items": 3,
        "unlock_message": "Enter your email and phone to unlock the full report with verified local repair estimates.",
    }
    return config
