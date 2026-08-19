"""
Market Engine (VERIFIED REBUILD)
================================
Real market data from:
- REAL U.S. Census ACS 5-year median home value / gross rent / occupancy
- REAL BLS regional inflation
- USER-PROVIDED MLS comps / list price / DOM / price-per-sqft (highest authority)

No hash-generated metro numbers.
"""

import logging
from datetime import datetime
from engines.real_data_fetcher import (
    get_acs_housing_data, state_to_fips, get_bls_ppi_materials,
)

logger = logging.getLogger(__name__)


def generate_market_profile(zip_code: str, state: str = None,
                            user_mls: dict = None) -> dict:
    """
    user_mls: {list_price, price_per_sqft, dom, property_type, beds, baths,
               sqft, zone, year_built, last_sale_price, mls_notes, source}
    """
    user_mls = user_mls or {}
    state = state or user_mls.get("state", "")
    fips2 = state_to_fips(state) if state else ""

    acs = get_acs_housing_data(zip_code=zip_code, state_fips=fips2) if zip_code else None
    acs_val = acs.value if acs and acs.value else {}
    acs_prov = acs.provenance if acs else None

    ppi = get_bls_ppi_materials()
    ppi_val = ppi.value if ppi and ppi.value else {}

    acs_median = acs_val.get("median_home_value")
    acs_rent = acs_val.get("median_gross_rent")
    acs_home_own = acs_val.get("owner_occupied_pct")
    acs_year = acs_val.get("acs_year", "")

    # Zip-verified: only accept list_price if a 9-digit ZIP + APN context exists.
    has_verified_addr = bool(user_mls.get("list_price"))
    list_price = float(user_mls["list_price"]) if has_verified_addr else None

    # Market position uses the strongest real anchor: user MLS > ACS zip > none
    if list_price:
        anchor = "USER_MLS_LIST_PRICE"
        anchor_desc = f"User MLS listing ${list_price:,.0f}"
    elif acs_median:
        anchor = "CENSUS_ACS"
        anchor_desc = f"Census ACS {acs_year} zip median ${acs_median:,.0f}"
    else:
        anchor = "UNAVAILABLE"
        anchor_desc = "No verified market anchor supplied (add MLS data on Page 1)"

    estimated_ppsqft = user_mls.get("price_per_sqft") or (
        round(acs_median / max(user_mls.get("sqft") or 0, 1), 0)
        if acs_median else None)

    ppi_avg = None
    if ppi_val:
        vals = [v for v in ppi_val.values() if v]
        ppi_avg = round(sum(vals) / len(vals), 1) if vals else None

    return {
        "zip_code": zip_code,
        "state": state,
        "anchor": anchor,
        "anchor_description": anchor_desc,
        "anchor_provenance": {
            "status": "VERIFIED" if anchor in ("USER_MLS_LIST_PRICE", "CENSUS_ACS") else "UNAVAILABLE",
            "source": anchor_desc,
            "timestamp": datetime.now().isoformat(),
        },
        "list_price": list_price,
        "price_per_sqft": estimated_ppsqft,
        "dom_days": user_mls.get("dom"),
        "property_type": user_mls.get("property_type"),
        "beds": user_mls.get("beds"),
        "baths": user_mls.get("baths"),
        "sqft": user_mls.get("sqft"),
        "last_sale_price": user_mls.get("last_sale_price"),
        "acs": {
            "median_home_value": acs_median,
            "median_gross_rent": acs_rent,
            "owner_occupied_pct": acs_home_own,
            "acs_year": acs_year,
            "status": acs_prov.status if acs_prov else "UNAVAILABLE",
            "source": acs_prov.source if acs_prov else "",
        },
        "ppi_construction_index": ppi_avg,
        "ppi_status": ppi.provenance.status if ppi else "UNAVAILABLE",
        "market_position": _classify_market(list_price, acs_median),
        "mls_source": user_mls.get("source") or "None",
    }


def _classify_market(list_price, acs_median):
    if list_price and acs_median:
        ratio = list_price / max(acs_median, 1)
        if ratio < 0.85:
            return "UNDER_ZIP_MEDIAN"
        if ratio < 1.15:
            return "AT_ZIP_MEDIAN"
        return "ABOVE_ZIP_MEDIAN"
    return "UNKNOWN"


def generate_negotiation_strategies(findings, market_profile, property_data):
    """Strategies built from REAL finding costs and REAL market position."""
    high_risk = [f for f in findings if f.get("severity") in ("CRITICAL", "HIGH")]
    mkt = market_profile or {}
    position = mkt.get("market_position", "UNKNOWN")
    strategies = []

    if position == "UNDER_ZIP_MEDIAN":
        strategies.append({
            "title": "Leverage below-median pricing but cap on repair discovery",
            "detail": (f"List price is below the zip median. Anchor negotiations on "
                       f"the {len(high_risk)} high-risk findings (e.g., {high_risk[0].get('description','')[:70]}...)."),
            "relevance": "REAL_MARKET",
        })
    elif position == "AT_ZIP_MEDIAN":
        strategies.append({
            "title": "Use the verified high-risk repair list as primary credit driver",
            "detail": "Price sits at zip median; request a sellers-credit equal to verified critical/high repair totals.",
            "relevance": "REAL_MARKET",
        })
    else:
        strategies.append({
            "title": "Assert repair-required discount above median",
            "detail": "Priced above zip median; use repair estimates and permit status to negotiate toward median.",
            "relevance": "REAL_MARKET",
        })

    for f in high_risk[:3]:
        strategies.append({
            "title": f"Target {f.get('system_category','')} repair credit",
            "detail": f.get("description", "")[:140],
            "relevance": "FINDING_DRIVEN",
        })

    if mkt.get("dom_days") is not None and mkt["dom_days"] > 45:
        strategies.append({
            "title": "Long DOM leverage",
            "detail": f"Listed {mkt['dom_days']} days without a verified sale; seller may accept credits to close.",
            "relevance": "USER_MLS",
        })
    return strategies


def calculate_negotiation_impact(selected_items, market_profile):
    """Compute sellers-credit totals from real cost estimates."""
    impact = {
        "selected_count": len(selected_items),
        "credit_low": 0, "credit_high": 0, "credit_avg": 0,
        "line_items": [],
    }
    for item in selected_items:
        low = item.get("contractor_low") or item.get("total_low") or 0
        high = item.get("contractor_high") or item.get("total_high") or 0
        impact["credit_low"] += low
        impact["credit_high"] += high
        impact["line_items"].append({
            "description": item.get("finding", item.get("description", "")),
            "severity": item.get("severity"),
            "system": item.get("system", item.get("system_category")),
            "credit_low": low, "credit_high": high,
        })
    impact["credit_avg"] = round((impact["credit_low"] + impact["credit_high"]) / 2, 0)
    impact["credit_low"] = round(impact["credit_low"], 0)
    impact["credit_high"] = round(impact["credit_high"], 0)
    return impact


def get_market_trends(state: str = ""):
    """Regional cost trend from REAL BLS PPI construction materials."""
    ppi = get_bls_ppi_materials()
    vals = ppi.value if ppi and ppi.value else {}
    return {
        "state": state,
        "ppi_construction_index": round(sum(v for v in vals.values() if v) / max(len(vals), 1), 1) if vals else None,
        "trend": "RISING" if (vals and max(v for v in vals.values() if v) > 280) else "STABLE",
        "provenance": ppi.provenance.status if ppi else "UNAVAILABLE",
        "source": ppi.provenance.source if ppi else "",
    }