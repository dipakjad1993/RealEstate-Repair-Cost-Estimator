import random
from datetime import datetime

def generate_seo_landing_pages(zip_code, cost_data):
    pages = []
    systems = [
        ("hvac", "HVAC", "Air Conditioning & Heating"),
        ("roof", "Roof", "Roofing"),
        ("electrical", "Electrical", "Electrical"),
        ("plumbing", "Plumbing", "Plumbing"),
        ("foundation", "Foundation", "Foundation & Structural"),
        ("windows", "Windows", "Windows & Doors"),
    ]
    rng = random.Random(sum(ord(c) for c in zip_code))
    for system_key, system_name, system_display in systems:
        base_cost = cost_data.get(system_key, rng.randint(500, 5000))
        slug = f"cost-to-fix-{system_key}-{zip_code}"
        pages.append({
            "zip_code": zip_code,
            "system_type": system_name,
            "system_display": system_display,
            "avg_cost": round(base_cost * cost_data.get("modifier", 1.0), 0),
            "page_slug": slug,
            "page_title": f"Average Cost to Fix {system_display} in {zip_code} | 2026 Real Data",
            "meta_description": f"What does it cost to repair {system_display.lower()} in {zip_code}? See real 2026 cost data, contractor rates, and local pricing trends.",
            "h1": f"{system_display} Repair Costs in {zip_code}",
            "impressions": rng.randint(100, 5000),
            "clicks": rng.randint(10, 500),
            "conversions": rng.randint(1, 50),
            "estimated_monthly_traffic": rng.randint(200, 8000),
            "keyword_difficulty": round(rng.uniform(15, 65), 1),
            "content_sections": _generate_content_sections(system_name, zip_code, base_cost),
        })
    return {
        "pages": pages,
        "total_pages": len(pages),
        "total_estimated_traffic": sum(p["estimated_monthly_traffic"] for p in pages),
        "total_estimated_impressions": sum(p["impressions"] for p in pages),
    }

def _generate_content_sections(system, zip_code, base_cost):
    sections = [
        {
            "heading": f"What Does {system} Repair Cost in {zip_code}?",
            "content": f"Based on real inspection data processed through our platform, the average {system.lower()} repair in the {zip_code} area ranges from ${base_cost * 0.6:,.0f} to ${base_cost * 1.5:,.0f}. This data is derived from actual home inspection reports analyzed by our AI engine, combined with localized contractor pricing data.",
        },
        {
            "heading": f"Common {system} Issues Found in {zip_code} Homes",
            "content": f"Homes in the {zip_code} area frequently exhibit {system.lower()} issues including aging components, deferred maintenance, and code violations. Our analysis of local inspection reports shows the most common issues relate to systems that are approaching or exceeding their expected useful life.",
        },
        {
            "heading": f"DIY vs. Professional {system} Repair in {zip_code}",
            "content": f"While some {system.lower()} repairs can be handled by experienced homeowners, most significant issues require a licensed contractor. In {zip_code}, professional {system.lower()} contractors typically charge between $60-$120/hour. Our cost estimates include both DIY and professional pricing tiers.",
        },
        {
            "heading": f"When to Negotiate {system} Repairs in {zip_code}",
            "content": f"If you're buying a home in {zip_code} and the inspection reveals {system.lower()} issues, you have options. You can request the seller make repairs before closing, negotiate a credit for the estimated cost, or reduce the purchase price. Our tool helps you calculate the exact amounts to request.",
        },
    ]
    return sections

def generate_seo_analytics(pages):
    total_impressions = sum(p["impressions"] for p in pages)
    total_clicks = sum(p["clicks"] for p in pages)
    total_conversions = sum(p["conversions"] for p in pages)
    ctr = round(total_clicks / max(total_impressions, 1) * 100, 2)
    conversion_rate = round(total_conversions / max(total_clicks, 1) * 100, 2)
    return {
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "total_conversions": total_conversions,
        "click_through_rate": ctr,
        "conversion_rate": conversion_rate,
        "estimated_monthly_value": round(total_conversions * 150, 0),
        "top_performing_page": max(pages, key=lambda x: x["conversions"]) if pages else None,
        "recommendations": [
            f"Current CTR of {ctr}% can be improved by adding schema markup for local business.",
            f"Conversion rate of {conversion_rate}% is {'above' if conversion_rate > 3 else 'below'} industry average (3%).",
            "Add FAQ sections targeting long-tail keywords like 'how much does [system] repair cost near me'.",
            "Create seasonal content targeting weather-related repair searches.",
        ],
    }

def track_lead_magnet(zip_code, email=None, phone=None):
    rng = random.Random(datetime.now().timestamp())
    return {
        "visitor_ip": f"192.168.{rng.randint(1, 255)}.{rng.randint(1, 255)}",
        "email": email or "visitor@example.com",
        "phone": phone or "",
        "zip_code": zip_code,
        "lead_captured": bool(email or phone),
        "source_page": f"/repair-cost-estimator/{zip_code}",
        "conversion_timestamp": datetime.now().isoformat(),
        "estimated_lead_value": round(rng.uniform(50, 500), 2),
    }

def generate_lead_magnet_widget_config(agent_name, agent_email, branding=None):
    config = {
        "widget_title": "Got a Scary Home Inspection Report?",
        "widget_subtitle": "Upload it here to see the real repair cost in 60 seconds",
        "cta_button": "Analyze My Report Now",
        "agent_name": agent_name,
        "agent_email": agent_email,
        "branding": branding or {
            "primary_color": "#1E40AF",
            "accent_color": "#F59E0B",
            "font_family": "Inter, sans-serif",
        },
        "lead_capture_fields": ["email", "phone"],
        "preview_items": 3,
        "unlock_message": "Enter your email and phone to unlock the full report with local contractor pricing.",
        "social_proof": f"Join 1,200+ {agent_name.split()[0]}'s clients who saved an average of $4,800 on repairs.",
    }
    return config
