import math
from datetime import datetime
from config import STATE_TAX_MULTIPLIERS


_METRO_MARKET_DATA = {
    "nyc": {
        "prefixes": list(range(100, 150)),
        "label": "New York City Metro",
        "median_low": 780000, "median_high": 1200000,
        "ppsqft_low": 480, "ppsqft_high": 820,
        "dom_low": 22, "dom_high": 38,
        "listings_low": 600, "listings_high": 2200,
        "pending_ratio": 0.42,
        "yoy_low": 1.5, "yoy_high": 5.2,
        "months_supply_low": 2.2, "months_supply_high": 3.8,
    },
    "la": {
        "prefixes": list(range(900, 905)) + list(range(906, 913)) + list(range(914, 919)),
        "label": "Los Angeles Metro",
        "median_low": 850000, "median_high": 1500000,
        "ppsqft_low": 520, "ppsqft_high": 900,
        "dom_low": 20, "dom_high": 35,
        "listings_low": 500, "listings_high": 1800,
        "pending_ratio": 0.40,
        "yoy_low": -0.5, "yoy_high": 3.8,
        "months_supply_low": 2.0, "months_supply_high": 3.5,
    },
    "sf": {
        "prefixes": list(range(941, 945)) + [946, 947, 948, 949, 950, 951],
        "label": "San Francisco Bay Area",
        "median_low": 1100000, "median_high": 2000000,
        "ppsqft_low": 700, "ppsqft_high": 1200,
        "dom_low": 18, "dom_high": 32,
        "listings_low": 300, "listings_high": 1200,
        "pending_ratio": 0.44,
        "yoy_low": -1.2, "yoy_high": 4.5,
        "months_supply_low": 1.8, "months_supply_high": 3.2,
    },
    "chicago": {
        "prefixes": list(range(606, 611)) + [600, 601, 602, 603, 604, 605],
        "label": "Chicago Metro",
        "median_low": 320000, "median_high": 650000,
        "ppsqft_low": 180, "ppsqft_high": 380,
        "dom_low": 25, "dom_high": 48,
        "listings_low": 400, "listings_high": 1600,
        "pending_ratio": 0.38,
        "yoy_low": 2.0, "yoy_high": 6.5,
        "months_supply_low": 2.8, "months_supply_high": 4.8,
    },
    "houston": {
        "prefixes": list(range(770, 778)),
        "label": "Houston Metro",
        "median_low": 280000, "median_high": 520000,
        "ppsqft_low": 140, "ppsqft_high": 280,
        "dom_low": 28, "dom_high": 52,
        "listings_low": 500, "listings_high": 2000,
        "pending_ratio": 0.35,
        "yoy_low": 1.5, "yoy_high": 5.0,
        "months_supply_low": 3.0, "months_supply_high": 5.2,
    },
    "phoenix": {
        "prefixes": list(range(850, 857)) + list(range(857, 861)),
        "label": "Phoenix Metro",
        "median_low": 420000, "median_high": 680000,
        "ppsqft_low": 210, "ppsqft_high": 380,
        "dom_low": 22, "dom_high": 42,
        "listings_low": 350, "listings_high": 1500,
        "pending_ratio": 0.37,
        "yoy_low": 0.5, "yoy_high": 6.0,
        "months_supply_low": 2.5, "months_supply_high": 4.5,
    },
    "dallas": {
        "prefixes": list(range(752, 761)),
        "label": "Dallas-Fort Worth Metro",
        "median_low": 350000, "median_high": 620000,
        "ppsqft_low": 175, "ppsqft_high": 340,
        "dom_low": 24, "dom_high": 44,
        "listings_low": 500, "listings_high": 2000,
        "pending_ratio": 0.36,
        "yoy_low": 1.8, "yoy_high": 5.5,
        "months_supply_low": 2.8, "months_supply_high": 4.6,
    },
    "miami": {
        "prefixes": list(range(331, 333)) + [330, 331, 332],
        "label": "Miami-Dade Metro",
        "median_low": 480000, "median_high": 950000,
        "ppsqft_low": 300, "ppsqft_high": 620,
        "dom_low": 30, "dom_high": 55,
        "listings_low": 400, "listings_high": 1800,
        "pending_ratio": 0.33,
        "yoy_low": -3.0, "yoy_high": 2.5,
        "months_supply_low": 3.5, "months_supply_high": 6.5,
    },
    "seattle": {
        "prefixes": list(range(981, 983)) + list(range(983, 988)),
        "label": "Seattle Metro",
        "median_low": 750000, "median_high": 1300000,
        "ppsqft_low": 450, "ppsqft_high": 780,
        "dom_low": 16, "dom_high": 30,
        "listings_low": 300, "listings_high": 1100,
        "pending_ratio": 0.43,
        "yoy_low": 1.0, "yoy_high": 5.8,
        "months_supply_low": 1.8, "months_supply_high": 3.0,
    },
    "denver": {
        "prefixes": list(range(802, 806)),
        "label": "Denver Metro",
        "median_low": 520000, "median_high": 820000,
        "ppsqft_low": 280, "ppsqft_high": 480,
        "dom_low": 20, "dom_high": 38,
        "listings_low": 350, "listings_high": 1300,
        "pending_ratio": 0.40,
        "yoy_low": 0.8, "yoy_high": 4.5,
        "months_supply_low": 2.2, "months_supply_high": 4.0,
    },
    "boston": {
        "prefixes": [21, 22, 24],
        "label": "Boston Metro",
        "median_low": 650000, "median_high": 1100000,
        "ppsqft_low": 400, "ppsqft_high": 720,
        "dom_low": 18, "dom_high": 35,
        "listings_low": 300, "listings_high": 1200,
        "pending_ratio": 0.41,
        "yoy_low": 1.2, "yoy_high": 4.8,
        "months_supply_low": 2.0, "months_supply_high": 3.6,
    },
    "atlanta": {
        "prefixes": list(range(303, 310)),
        "label": "Atlanta Metro",
        "median_low": 350000, "median_high": 600000,
        "ppsqft_low": 170, "ppsqft_high": 320,
        "dom_low": 25, "dom_high": 45,
        "listings_low": 450, "listings_high": 1800,
        "pending_ratio": 0.36,
        "yoy_low": 2.5, "yoy_high": 6.0,
        "months_supply_low": 2.8, "months_supply_high": 4.8,
    },
    "sandiego": {
        "prefixes": list(range(921, 922)),
        "label": "San Diego Metro",
        "median_low": 720000, "median_high": 1200000,
        "ppsqft_low": 440, "ppsqft_high": 740,
        "dom_low": 18, "dom_high": 32,
        "listings_low": 250, "listings_high": 1000,
        "pending_ratio": 0.42,
        "yoy_low": -0.2, "yoy_high": 4.0,
        "months_supply_low": 2.0, "months_supply_high": 3.4,
    },
    "portland": {
        "prefixes": list(range(972, 973)),
        "label": "Portland Metro",
        "median_low": 480000, "median_high": 750000,
        "ppsqft_low": 270, "ppsqft_high": 440,
        "dom_low": 28, "dom_high": 48,
        "listings_low": 300, "listings_high": 1200,
        "pending_ratio": 0.36,
        "yoy_low": -0.5, "yoy_high": 3.0,
        "months_supply_low": 2.8, "months_supply_high": 4.8,
    },
    "nashville": {
        "prefixes": list(range(372, 373)),
        "label": "Nashville Metro",
        "median_low": 420000, "median_high": 680000,
        "ppsqft_low": 220, "ppsqft_high": 380,
        "dom_low": 22, "dom_high": 40,
        "listings_low": 350, "listings_high": 1400,
        "pending_ratio": 0.38,
        "yoy_low": 2.0, "yoy_high": 5.5,
        "months_supply_low": 2.5, "months_supply_high": 4.2,
    },
    "charlotte": {
        "prefixes": list(range(282, 283)),
        "label": "Charlotte Metro",
        "median_low": 340000, "median_high": 550000,
        "ppsqft_low": 165, "ppsqft_high": 300,
        "dom_low": 24, "dom_high": 42,
        "listings_low": 400, "listings_high": 1600,
        "pending_ratio": 0.37,
        "yoy_low": 2.8, "yoy_high": 6.2,
        "months_supply_low": 2.6, "months_supply_high": 4.4,
    },
    "austin": {
        "prefixes": list(range(733, 734)) + list(range(786, 788)),
        "label": "Austin Metro",
        "median_low": 450000, "median_high": 750000,
        "ppsqft_low": 240, "ppsqft_high": 420,
        "dom_low": 28, "dom_high": 50,
        "listings_low": 400, "listings_high": 1600,
        "pending_ratio": 0.35,
        "yoy_low": -1.0, "yoy_high": 4.0,
        "months_supply_low": 3.0, "months_supply_high": 5.0,
    },
    "lasvegas": {
        "prefixes": list(range(891, 892)),
        "label": "Las Vegas Metro",
        "median_low": 380000, "median_high": 600000,
        "ppsqft_low": 200, "ppsqft_high": 340,
        "dom_low": 25, "dom_high": 45,
        "listings_low": 400, "listings_high": 1500,
        "pending_ratio": 0.36,
        "yoy_low": 0.5, "yoy_high": 5.0,
        "months_supply_low": 2.8, "months_supply_high": 4.8,
    },
    "raleigh": {
        "prefixes": list(range(276, 277)),
        "label": "Raleigh-Durham Metro",
        "median_low": 380000, "median_high": 580000,
        "ppsqft_low": 190, "ppsqft_high": 330,
        "dom_low": 20, "dom_high": 38,
        "listings_low": 300, "listings_high": 1200,
        "pending_ratio": 0.39,
        "yoy_low": 3.0, "yoy_high": 6.8,
        "months_supply_low": 2.4, "months_supply_high": 4.0,
    },
    "cosprings": {
        "prefixes": list(range(809, 810)),
        "label": "Colorado Springs Metro",
        "median_low": 420000, "median_high": 620000,
        "ppsqft_low": 220, "ppsqft_high": 360,
        "dom_low": 22, "dom_high": 40,
        "listings_low": 250, "listings_high": 1000,
        "pending_ratio": 0.38,
        "yoy_low": 1.0, "yoy_high": 5.0,
        "months_supply_low": 2.5, "months_supply_high": 4.2,
    },
}


def _get_state_from_zip(zip_code):
    try:
        prefix = int(zip_code[:3])
    except (ValueError, IndexError):
        return None
    ranges = [
        (50, 63, "MA"), (64, 69, "RI"), (70, 89, "ME"), (100, 149, "NY"),
        (150, 196, "PA"), (197, 220, "DE"), (221, 247, "MD"), (248, 268, "WV"),
        (270, 289, "NC"), (290, 299, "SC"), (300, 319, "GA"), (320, 339, "FL"),
        (350, 369, "AL"), (370, 385, "TN"), (386, 397, "MS"), (400, 427, "KY"),
        (430, 458, "OH"), (460, 479, "IN"), (480, 499, "MI"), (500, 528, "IA"),
        (530, 549, "WI"), (550, 567, "MN"), (570, 577, "SD"), (580, 588, "ND"),
        (590, 599, "MT"), (600, 629, "IL"), (630, 658, "MO"), (660, 679, "KS"),
        (680, 693, "NE"), (700, 714, "LA"), (716, 729, "AR"), (730, 749, "OK"),
        (750, 799, "TX"), (800, 816, "CO"), (820, 831, "WY"), (832, 838, "ID"),
        (840, 847, "UT"), (850, 865, "AZ"), (870, 884, "NM"), (889, 898, "NV"),
        (900, 966, "CA"), (967, 968, "HI"), (970, 979, "OR"), (980, 994, "WA"),
        (995, 999, "AK"),
    ]
    for start, end, st in ranges:
        if start <= prefix <= end:
            return st
    return None


def _deterministic_hash(value):
    h = 0
    for ch in str(value):
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


def _deterministic_float(zip_code, salt, low, high):
    h = _deterministic_hash(str(zip_code) + salt)
    return low + (h % 10000) / 10000.0 * (high - low)


def _deterministic_int(zip_code, salt, low, high):
    h = _deterministic_hash(str(zip_code) + salt)
    return low + h % (high - low + 1)


def _detect_metro(zip_code):
    try:
        prefix = int(zip_code[:3])
    except (ValueError, IndexError):
        return None
    for metro_key, metro in _METRO_MARKET_DATA.items():
        if prefix in metro["prefixes"]:
            return metro_key, metro
    return None


def _classify_market_type(months_supply):
    if months_supply < 2.0:
        return ("Strong Seller's Market", 20,
                "Extreme inventory shortage. Multiple offers are the norm. Sellers dictate terms. "
                "Buyers must submit strong, clean offers with minimal contingencies. "
                "Repair requests beyond critical safety items will likely be rejected.")
    elif months_supply < 3.0:
        return ("Seller's Market", 35,
                "Low inventory favors sellers. Homes sell quickly with limited price negotiation. "
                "Buyers should focus repair requests on critical safety and structural items only. "
                "Including cosmetic or minor items risks losing the property to competing offers.")
    elif months_supply < 4.5:
        return ("Balanced Market", 52,
                "Supply and demand are roughly in equilibrium. Both parties have reasonable leverage. "
                "Buyers can negotiate for documented repair items with supporting contractor estimates. "
                "Sellers are willing to address legitimate concerns to keep deals on track.")
    elif months_supply < 6.0:
        return ("Buyer's Market", 68,
                "Excess inventory gives buyers meaningful negotiating power. Sellers are more flexible "
                "on price and repairs. Buyers can request comprehensive repair credits including "
                "moderate and low-severity items. Longer time on market increases seller motivation.")
    else:
        return ("Strong Buyer's Market", 85,
                "Significant oversupply creates strong buyer leverage. Sellers face extended marketing "
                "periods and potential price reductions. Buyers can demand full repair credits, "
                "price reductions, or seller-funded home warranties across all severity levels.")


def _get_market_type_tier(leverage_score):
    if leverage_score < 30:
        return "strong_seller"
    elif leverage_score < 45:
        return "seller"
    elif leverage_score < 60:
        return "balanced"
    elif leverage_score < 75:
        return "buyer"
    else:
        return "strong_buyer"


def generate_market_profile(zip_code, state=None):
    if not state:
        state = _get_state_from_zip(zip_code)

    metro_result = _detect_metro(zip_code)
    now = datetime.now()
    month = now.month
    year_digit = now.year % 10

    if metro_result:
        _metro_key, metro = metro_result
        median_price = _deterministic_int(zip_code, "median", metro["median_low"], metro["median_high"])
        price_per_sqft = _deterministic_int(zip_code, "ppsqft", metro["ppsqft_low"], metro["ppsqft_high"])
        avg_dom = _deterministic_int(zip_code, "dom", metro["dom_low"], metro["dom_high"])
        inventory_depth = _deterministic_int(zip_code, "inventory", metro["listings_low"], metro["listings_high"])
        active_listings = _deterministic_int(zip_code, "active", int(inventory_depth * 0.35), int(inventory_depth * 0.75))
        pending_ratio = metro["pending_ratio"]
        pending_sales = _deterministic_int(zip_code, "pending", int(active_listings * 0.2), int(active_listings * 0.6))
        yoy_change = round(_deterministic_float(zip_code, "yoy", metro["yoy_low"], metro["yoy_high"]), 1)
        months_supply = round(_deterministic_float(zip_code, "mos", metro["months_supply_low"], metro["months_supply_high"]), 1)
        metro_label = metro["label"]
    else:
        median_price = _deterministic_int(zip_code, "median", 300000, 500000)
        typical_sqft = 2000
        price_per_sqft = round(median_price / typical_sqft)
        avg_dom = _deterministic_int(zip_code, "dom", 30, 55)
        inventory_depth = _deterministic_int(zip_code, "inventory", 200, 900)
        active_listings = _deterministic_int(zip_code, "active", int(inventory_depth * 0.35), int(inventory_depth * 0.75))
        pending_sales = _deterministic_int(zip_code, "pending", int(active_listings * 0.2), int(active_listings * 0.55))
        yoy_change = round(_deterministic_float(zip_code, "yoy", -1.0, 5.0), 1)
        months_supply = round(inventory_depth / max(pending_sales, 1), 1)
        metro_label = "Local Market"

    if months_supply < 1.0:
        months_supply = 1.0

    market_type, base_leverage, leverage_desc = _classify_market_type(months_supply)

    seasonal_modifier = 0
    if month in (5, 6, 7):
        seasonal_modifier = -3
    elif month in (11, 12, 1):
        seasonal_modifier = 5
    elif month in (2, 3, 4):
        seasonal_modifier = -1
    elif month in (8, 9, 10):
        seasonal_modifier = 2

    dom_penalty = 0
    if avg_dom > 45:
        dom_penalty = 8
    elif avg_dom > 35:
        dom_penalty = 4
    elif avg_dom > 25:
        dom_penalty = 0
    elif avg_dom > 18:
        dom_penalty = -4
    else:
        dom_penalty = -7

    trend_bonus = 0
    if yoy_change < -2:
        trend_bonus = 12
    elif yoy_change < 0:
        trend_bonus = 6
    elif yoy_change < 2:
        trend_bonus = 0
    elif yoy_change < 4:
        trend_bonus = -3
    else:
        trend_bonus = -6

    leverage_score = max(10, min(95, base_leverage + seasonal_modifier + dom_penalty + trend_bonus))

    absorption_rate = round(pending_sales / max(active_listings, 1) * 100, 1)
    typical_sqft = 2000
    if not metro_result:
        price_per_sqft = round(median_price / typical_sqft)

    now_ts = datetime.now()
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    quarter = f"Q{(now_ts.month - 1) // 3 + 1}"
    data_timestamp = f"{month_names[now_ts.month - 1]} {now_ts.year} {quarter} Estimate"

    return {
        "zip_code": zip_code,
        "state": state,
        "avg_days_on_market": avg_dom,
        "active_listings": active_listings,
        "pending_sales": pending_sales,
        "inventory_depth": inventory_depth,
        "median_sale_price": median_price,
        "price_per_sqft": price_per_sqft,
        "yoy_price_change_pct": yoy_change,
        "months_of_supply": months_supply,
        "market_type": market_type,
        "leverage_score": leverage_score,
        "leverage_description": leverage_desc,
        "absorption_rate": absorption_rate,
        "data_timestamp": data_timestamp,
        "data_source": f"deterministic_model_v3_{metro_label}",
    }


def generate_negotiation_strategies(findings, market_profile, property_data):
    leverage = market_profile.get("leverage_score", 50)
    market_type = market_profile.get("market_type", "Balanced Market")
    months_supply = market_profile.get("months_of_supply", 3.5)
    avg_dom = market_profile.get("avg_days_on_market", 30)
    median_price = market_profile.get("median_sale_price", 400000)
    yoy_change = market_profile.get("yoy_price_change_pct", 0.0)
    market_tier = _get_market_type_tier(leverage)

    severity_sort = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4, "INFO": 5}
    sorted_findings = sorted(findings, key=lambda x: severity_sort.get(x.get("severity", "LOW"), 5))

    strategies = []
    total_estimated_cost = 0.0

    for idx, finding in enumerate(sorted_findings):
        severity = finding.get("severity", "MEDIUM")
        system = finding.get("system_category", "OTHER")
        desc = finding.get("description", "")[:120]
        est_cost = finding.get("estimated_cost_avg", 0)
        total_estimated_cost += est_cost

        if severity == "CRITICAL":
            strat, action, rationale, potential_savings = _critical_strategy(
                market_tier, leverage, system, est_cost, months_supply, avg_dom, median_price
            )
            priority_rank = max(1, 10 - idx)
        elif severity == "HIGH":
            strat, action, rationale, potential_savings = _high_strategy(
                market_tier, leverage, system, est_cost, months_supply, avg_dom, median_price
            )
            priority_rank = max(2, 9 - idx)
        elif severity == "MEDIUM":
            strat, action, rationale, potential_savings = _medium_strategy(
                market_tier, leverage, system, est_cost, months_supply, avg_dom
            )
            priority_rank = max(3, 8 - idx)
        elif severity == "LOW":
            strat, action, rationale, potential_savings = _low_strategy(
                market_tier, leverage, system, est_cost
            )
            priority_rank = max(4, 7 - idx)
        else:
            strat, action, rationale, potential_savings = _info_strategy(
                market_tier, system
            )
            priority_rank = max(5, 6 - idx)

        market_context = (
            f"{market_type} with {months_supply} months of supply. "
            f"Homes averaging {avg_dom} days on market. "
            f"YoY price movement: {yoy_change:+.1f}%. "
            f"Buyer leverage score: {leverage}/100."
        )

        strategies.append({
            "finding_id": finding.get("id"),
            "severity": severity,
            "system": system,
            "description": desc,
            "strategy": strat,
            "action": action,
            "rationale": rationale,
            "priority_rank": priority_rank,
            "market_context": market_context,
            "leverage_score": leverage,
            "potential_savings": potential_savings,
        })

    critical_count = sum(1 for s in strategies if s["severity"] == "CRITICAL")
    high_count = sum(1 for s in strategies if s["severity"] == "HIGH")
    medium_count = sum(1 for s in strategies if s["severity"] == "MEDIUM")
    low_count = sum(1 for s in strategies if s["severity"] == "LOW")
    actionable_count = len([s for s in strategies if s["strategy"] not in ("INFORMATIONAL NOTE",)])

    if market_tier == "strong_seller":
        executive_summary = (
            f"AGGRESSIVE SELLER'S MARKET STRATEGY — {market_type}: "
            f"With {months_supply} months of inventory and homes selling in {avg_dom} days, "
            f"the seller holds dominant negotiating position. You have {critical_count} critical "
            f"and {high_count} high-priority findings totaling an estimated ${total_estimated_cost:,.0f} "
            f"in repair costs. RECOMMENDATION: Request repair before closing or equivalent credit "
            f"for CRITICAL items ONLY. Do not include HIGH or MEDIUM items in formal requests — "
            f"this risks the seller pivoting to a backup offer. Present contractor bids to "
            f"substantiate requests. Target 30-45% of total estimated repair costs as a realistic "
            f"concession expectation. Consider offering to waive inspection contingency on non-critical "
            f"items as a strategic concession to strengthen your position on critical items."
        )
    elif market_tier == "seller":
        executive_summary = (
            f"SELLER-FAVORED MARKET STRATEGY — {market_type}: "
            f"With {months_supply} months of inventory and {avg_dom} DOM, the seller has the upper hand "
            f"but is not in complete control. You have {critical_count} critical and {high_count} high-priority "
            f"findings. RECOMMENDATION: Focus formal repair requests on critical safety items and the top "
            f"2-3 highest-cost high-severity items. Present 2-3 contractor bids for each requested item "
            f"to demonstrate legitimacy. Target 45-60% of total estimated repair costs. Bundle medium "
            f"items informally but do not make them deal-breakers. Expected concession range: "
            f"${total_estimated_cost * 0.45:,.0f} - ${total_estimated_cost * 0.60:,.0f}."
        )
    elif market_tier == "balanced":
        executive_summary = (
            f"BALANCED MARKET STRATEGY — {market_type}: "
            f"With {months_supply} months of inventory and {avg_dom} DOM, both parties have reasonable "
            f"leverage. You have {critical_count} critical, {high_count} high, and {medium_count} medium "
            f"findings. RECOMMENDATION: Present a comprehensive but realistic repair request package. "
            f"Lead with critical items, include high-severity items with contractor documentation, "
            f"and bundle medium items as a secondary package. Request seller credit rather than "
            f"specific repairs for flexibility. Target 55-70% of total estimated repair costs. "
            f"Expected concession range: ${total_estimated_cost * 0.55:,.0f} - "
            f"${total_estimated_cost * 0.70:,.0f}. Consider a home warranty ask as a goodwill add-on."
        )
    elif market_tier == "buyer":
        executive_summary = (
            f"BUYER-FAVORED MARKET STRATEGY — {market_type}: "
            f"With {months_supply} months of inventory and {avg_dom} DOM, you hold meaningful negotiating "
            f"power. Sellers are motivated and face carrying costs with extended market time. "
            f"You have {critical_count} critical, {high_count} high, and {medium_count} medium findings. "
            f"RECOMMENDATION: Request comprehensive itemized credits for all critical, high, and "
            f"medium-severity items. Include supporting documentation and contractor estimates. "
            f"Target 65-80% of total estimated repair costs. You can also request a home warranty, "
            f"closing cost contribution, or rate buydown as additional concessions. "
            f"Expected concession range: ${total_estimated_cost * 0.65:,.0f} - "
            f"${total_estimated_cost * 0.80:,.0f}."
        )
    else:
        executive_summary = (
            f"AGGRESSIVE BUYER'S MARKET STRATEGY — {market_type}: "
            f"With {months_supply} months of inventory and {avg_dom} DOM, you hold maximum negotiating "
            f"power. The seller is facing significant carrying costs and market pressure. "
            f"You have {critical_count} critical, {high_count} high, {medium_count} medium, and "
            f"{low_count} low-severity findings. RECOMMENDATION: Request full itemized credits for "
            f"ALL findings including low-severity items. Present the total as a comprehensive "
            f"reduction request. Target 75-95% of total estimated repair costs plus additional "
            f"concessions such as home warranty, closing costs, and furnishings. "
            f"Expected concession range: ${total_estimated_cost * 0.75:,.0f} - "
            f"${total_estimated_cost * 0.95:,.0f}. You are in the strongest possible position."
        )

    return {
        "strategies": strategies,
        "executive_summary": executive_summary,
        "market_context": market_profile,
        "total_items": len(strategies),
        "recommended_items_to_request": actionable_count,
    }


def _critical_strategy(market_tier, leverage, system, est_cost, months_supply, avg_dom, median_price):
    seller_risk_pct = (est_cost / median_price * 100) if median_price > 0 else 0
    contingency_buffer = est_cost * 0.15

    if market_tier in ("strong_seller", "seller"):
        strat = "REPAIR BEFORE CLOSING OR EQUIVALENT CREDIT"
        action = (
            f"Step 1: Obtain a detailed inspection report from a licensed {system.lower()} specialist "
            f"documenting the critical defect with photos, measurements, and code references.\n"
            f"Step 2: Obtain 2-3 written contractor estimates for the full repair, ensuring each "
            f"includes scope of work, timeline, materials, labor, and warranty terms.\n"
            f"Step 3: Present findings to seller's agent via formal repair addendum. State clearly "
            f"that this is a safety-critical item that must be resolved before closing.\n"
            f"Step 4: Set a 5-business-day deadline for seller response. If no response, escalate "
            f"to buyer's agent to contact seller's agent directly.\n"
            f"Step 5: If seller refuses repair, demand equivalent seller credit at closing "
            f"(${est_cost + contingency_buffer:,.0f} including 15% contingency buffer). "
            f"This is non-negotiable as it affects occupant safety."
        )
        rationale = (
            f"Critical safety defects in {system.lower()} systems create legal liability for the seller "
            f"if known and undisclosed. Even in a seller's market, sellers risk deal collapse and potential "
            f"lawsuits by refusing to address genuine safety hazards. The cost of this repair "
            f"(${est_cost:,.0f}) represents only {seller_risk_pct:.2f}% of the property value, making it "
            f"a trivial concession for the seller relative to the risk of losing the deal. "
            f"With homes selling in {avg_dom} days, the seller can likely find a replacement buyer, "
            f"but the disclosed defect will follow them to the next transaction as well."
        )
        potential_savings = est_cost + contingency_buffer
    elif market_tier == "balanced":
        strat = "REQUEST REPAIR OR CREDIT WITH DOCUMENTATION"
        action = (
            f"Step 1: Commission a specialized {system.lower()} inspection to fully document the defect "
            f"including severity assessment and code compliance status.\n"
            f"Step 2: Obtain 2-3 licensed contractor bids with detailed scope of work.\n"
            f"Step 3: Submit formal repair request via inspection response addendum, requesting "
            f"seller to complete repair before closing OR provide credit of ${est_cost + contingency_buffer:,.0f}.\n"
            f"Step 4: Include all supporting documentation (inspection report, contractor bids, "
            f"code references) with the request.\n"
            f"Step 5: Set 7-business-day response deadline. Offer to accept escrow holdback "
            f"if repair cannot be completed before closing."
        )
        rationale = (
            f"In a balanced market, sellers recognize that critical safety issues must be addressed. "
            f"The {system.lower()} defect at ${est_cost:,.0f} is a legitimate, documented concern "
            f"that any reasonable seller will want to resolve. With balanced inventory levels, "
            f"both parties have incentive to close the deal. Offering the escrow holdback option "
            f"gives the seller flexibility while ensuring you are protected."
        )
        potential_savings = est_cost + contingency_buffer
    else:
        strat = "DEMAND FULL CREDIT OR PRICE REDUCTION"
        action = (
            f"Step 1: Obtain comprehensive {system.lower()} inspection with photos, measurements, "
            f"and detailed defect documentation.\n"
            f"Step 2: Obtain 3 written contractor bids. Select the median bid as the baseline "
            f"request amount and include all three as supporting evidence.\n"
            f"Step 3: Submit formal demand for seller credit of ${est_cost * 1.15:,.0f} "
            f"(repair cost + 15% contingency) OR equivalent price reduction.\n"
            f"Step 4: Explicitly state that the critical safety defect is a material defect "
            f"that must be disclosed to future buyers if not resolved.\n"
            f"Step 5: Set 3-business-day deadline. Indicate willingness to proceed with closing "
            f"if credit is applied. If refused, consider requesting escrow holdback of "
            f"${est_cost * 1.5:,.0f} (1.5x estimate) with milestone-based release."
        )
        rationale = (
            f"In a buyer's market with {months_supply} months of inventory and {avg_dom} DOM, "
            f"the seller faces significant pressure to close. This critical {system.lower()} defect "
            f"(${est_cost:,.0f}) is a material disclosure issue — if not resolved, the seller must "
            f"disclose it to all future buyers, reducing their negotiating position further. "
            f"Sellers in this market are highly motivated to avoid re-listing. Full credit is "
            f"the expected standard for critical items in buyer-favorable conditions."
        )
        potential_savings = est_cost * 1.15

    return strat, action, rationale, round(potential_savings, 0)


def _high_strategy(market_tier, leverage, system, est_cost, months_supply, avg_dom, median_price):
    contingency_buffer = est_cost * 0.12

    if market_tier in ("strong_seller", "seller"):
        strat = "TARGETED ASK — TOP 2-3 ITEMS ONLY"
        action = (
            f"Step 1: Prioritize this finding against all other high-severity items. "
            f"If this is in the top 2-3 by cost, proceed; otherwise, defer.\n"
            f"Step 2: Obtain 2 contractor estimates to establish documented repair cost "
            f"of ${est_cost:,.0f}.\n"
            f"Step 3: Include this item in a focused repair request alongside only the "
            f"highest-cost critical/high findings. Do not exceed 3 total items.\n"
            f"Step 4: Request seller credit of ${est_cost + contingency_buffer:,.0f} "
            f"rather than specific repair to maintain deal momentum.\n"
            f"Step 5: Frame the request as a reasonable accommodation that protects both "
            f"parties. Set 5-business-day response deadline."
        )
        rationale = (
            f"In a seller's market, requesting too many items risks losing the property. "
            f"This {system.lower()} issue at ${est_cost:,.0f} should only be included if it "
            f"is among your top 2-3 highest-cost findings. The seller's alternative is a "
            f"backup offer that may not include this request, so they have incentive to "
            f"make reasonable concessions on significant items. Target 40-55% of total "
            f"estimated high-severity costs."
        )
        potential_savings = (est_cost + contingency_buffer) * 0.48
    elif market_tier == "balanced":
        strat = "BUNDLED NEGOTIATION WITH DOCUMENTATION"
        action = (
            f"Step 1: Obtain 2-3 written contractor estimates for the {system.lower()} repair.\n"
            f"Step 2: Bundle this item with other high-severity findings into a single "
            f"comprehensive repair request addendum.\n"
            f"Step 3: Present total package request as a unified concession, not individual items. "
            f"Group by system category for clarity.\n"
            f"Step 4: Request seller credit of ${est_cost + contingency_buffer:,.0f} for this item "
            f"within the overall package. Offer escrow holdback as alternative.\n"
            f"Step 5: Set 7-business-day deadline. Be prepared to negotiate down 15-25% "
            f"from initial ask as a realistic compromise."
        )
        rationale = (
            f"Balanced market conditions support reasonable repair requests for documented issues. "
            f"Bundling this {system.lower()} finding (${est_cost:,.0f}) with other items creates "
            f"a stronger negotiating position than individual requests. Sellers in balanced markets "
            f"expect some negotiation and have typically budgeted 3-5% of sale price for buyer "
            f"concessions. This item represents a legitimate, documented concern."
        )
        potential_savings = (est_cost + contingency_buffer) * 0.60
    else:
        strat = "COMPREHENSIVE CREDIT DEMAND"
        action = (
            f"Step 1: Obtain 3 licensed contractor bids with detailed scope of work and timelines.\n"
            f"Step 2: Include this item in a comprehensive repair credit request covering all "
            f"high and critical severity findings.\n"
            f"Step 3: Request seller credit of ${est_cost * 1.12:,.0f} (cost + 12% contingency) "
            f"for this specific item within the total package.\n"
            f"Step 4: Present the full package as a single price reduction or credit request "
            f"at closing. Include photos and inspection documentation.\n"
            f"Step 5: Set 5-business-day deadline. Indicate that all items are non-negotiable "
            f"in the current market but offer to accept escrow holdback if timing is an issue."
        )
        rationale = (
            f"In a buyer's market ({months_supply} months supply, {avg_dom} DOM), the seller is "
            f"highly motivated to close. This {system.lower()} repair at ${est_cost:,.0f} is a "
            f"documented, legitimate expense that the seller should absorb. With strong buyer "
            f"leverage, full credit for high-severity items is the market standard. Sellers "
            f"who refuse risk losing the deal and facing an even weaker negotiating position "
            f"with the next buyer."
        )
        potential_savings = est_cost * 1.12

    return strat, action, rationale, round(potential_savings, 0)


def _medium_strategy(market_tier, leverage, system, est_cost, months_supply, avg_dom):
    if market_tier in ("buyer", "strong_buyer"):
        strat = "BUNDLE IN COMPREHENSIVE CREDIT REQUEST"
        action = (
            f"Step 1: Document the {system.lower()} issue with photos and inspector notes.\n"
            f"Step 2: Obtain 1-2 contractor estimates to establish a cost baseline "
            f"of ${est_cost:,.0f}.\n"
            f"Step 3: Include this item as a line item in the comprehensive repair credit "
            f"request alongside critical and high-severity items.\n"
            f"Step 4: Do not make this a standalone demand. Present it as part of the "
            f"total package at ${est_cost:,.0f}.\n"
            f"Step 5: If seller pushes back on medium items, offer to waive this in exchange "
            f"for full credit on critical and high items."
        )
        rationale = (
            f"Buyer-favorable conditions allow inclusion of medium-severity items in comprehensive "
            f"requests. While the {system.lower()} issue (${est_cost:,.0f}) alone may not justify "
            f"a standalone demand, it adds weight to the total package. Sellers in this market "
            f"are accustomed to concession requests across all severity levels. Use this item "
            f"as a negotiation chip — concede it if needed to preserve credits on higher-priority items."
        )
        potential_savings = est_cost * 0.65
    elif market_tier == "balanced":
        strat = "SECONDARY BUNDLE — NEGOTIATION CHIP"
        action = (
            f"Step 1: Note the {system.lower()} issue in the inspection response with photos.\n"
            f"Step 2: Include in the overall repair request as a secondary item bundled with "
            f"high-severity findings.\n"
            f"Step 3: Request credit of ${est_cost:,.0f} but be prepared to waive this item "
            f"if seller resists.\n"
            f"Step 4: Use as a concession item — 'We will waive the {system.lower()} repair "
            f"request if you agree to full credit on the critical items.'\n"
            f"Step 5: If seller agrees to all items, accept the credit. If not, prioritize "
            f"critical/high items and formally waive medium items."
        )
        rationale = (
            f"In balanced markets, medium-severity items serve as strategic negotiation chips. "
            f"The ${est_cost:,.0f} {system.lower()} repair is legitimate but not critical enough "
            f"to risk deal collapse. Including it in the package increases total ask volume, "
            f"giving you room to make concessions that feel significant to the seller while "
            f"preserving your core requests. This is standard practice in balanced negotiations."
        )
        potential_savings = est_cost * 0.45
    else:
        strat = "LEVERAGE POINT — DO NOT FORMALIZE"
        action = (
            f"Step 1: Document the {system.lower()} issue in your personal inspection notes "
            f"for future reference.\n"
            f"Step 2: Do NOT include in formal repair request addendum.\n"
            f"Step 3: Mention verbally to your agent as background context for overall "
            f"negotiation positioning.\n"
            f"Step 4: If seller is responsive on critical items, consider bringing this up "
            f"as a goodwill request after primary negotiations conclude.\n"
            f"Step 5: Accept as-is in the standard transaction unless seller is exceptionally "
            f"cooperative."
        )
        rationale = (
            f"In a seller's market, including medium-severity items in formal requests risks "
            f"alienating the seller and potentially losing the deal. The ${est_cost:,.0f} "
            f"{system.lower()} repair is not significant enough to justify the negotiating risk. "
            f"Preserve seller goodwill for critical items. This issue can be addressed post-closing "
            f"as a planned maintenance item. Current market conditions do not support formal "
            f"requests for non-critical items."
        )
        potential_savings = 0

    return strat, action, rationale, round(potential_savings, 0)


def _low_strategy(market_tier, leverage, system, est_cost):
    if market_tier in ("buyer", "strong_buyer"):
        strat = "INCLUDE FOR WEIGHT — LOW PRIORITY"
        action = (
            f"Step 1: Note the {system.lower()} maintenance item in the inspection response.\n"
            f"Step 2: Include as a line item in the comprehensive concession request at ${est_cost:,.0f}.\n"
            f"Step 3: Do not spend negotiating capital on this item individually.\n"
            f"Step 4: Accept whatever the seller offers on this item — full, partial, or waived.\n"
            f"Step 5: If seller concedes on all items, great. If not, this is the first item to waive."
        )
        rationale = (
            f"In a buyer's market, even low-severity items can be included to increase total "
            f"concession volume. The ${est_cost:,.0f} {system.lower()} maintenance item adds "
            f"negligible negotiating risk but contributes to the overall package. Sellers "
            f"expect comprehensive requests in buyer-favorable conditions."
        )
        potential_savings = est_cost * 0.35
    elif market_tier == "balanced":
        strat = "OPTIONAL GOODWILL BUNDLE"
        action = (
            f"Step 1: Mention the {system.lower()} item informally to your agent.\n"
            f"Step 2: Include only if the total package is already well-received by seller.\n"
            f"Step 3: Frame as 'routine maintenance items we noticed' rather than demands.\n"
            f"Step 4: Be prepared to immediately waive this if seller shows any resistance.\n"
            f"Step 5: Accept as-is if it helps close the deal on more important items."
        )
        rationale = (
            f"Low-severity items in balanced markets are optional additions that should not "
            f"interfere with primary negotiations. The ${est_cost:,.0f} {system.lower()} "
            f"item is best used as a minor concession point or goodwill gesture."
        )
        potential_savings = est_cost * 0.25
    else:
        strat = "WAIVE FOR GOODWILL"
        action = (
            f"Step 1: Acknowledge the {system.lower()} maintenance item in your records.\n"
            f"Step 2: Do NOT include in any formal repair request or addendum.\n"
            f"Step 3: Inform your agent you are voluntarily waiving this item as a "
            f"goodwill gesture to the seller.\n"
            f"Step 4: Use this waiver as a talking point: 'We noted several maintenance "
            f"items but chose to focus only on safety-critical repairs.'\n"
            f"Step 5: Address post-closing as part of your planned maintenance schedule."
        )
        rationale = (
            f"In a seller's market, waiving low-severity items builds goodwill and demonstrates "
            f"reasonable buyer behavior. The ${est_cost:,.0f} {system.lower()} maintenance item "
            f"is not worth risking the deal. The goodwill generated can help on critical negotiations. "
            f"This is standard practice for experienced buyers in competitive markets."
        )
        potential_savings = 0

    return strat, action, rationale, round(potential_savings, 0)


def _info_strategy(market_tier, system):
    strat = "INFORMATIONAL NOTE"
    action = (
        f"Step 1: Review the informational note about the {system.lower()} system for your records.\n"
        f"Step 2: No formal action required — this is not a defect or repair item.\n"
        f"Step 3: Consider the information when planning post-closing maintenance.\n"
        f"Step 4: Discuss with your agent if you have questions about the system's condition.\n"
        f"Step 5: No negotiation request warranted."
    )
    rationale = (
        f"Informational findings do not represent defects or repair needs. They provide context "
        f"about the {system.lower()} system's condition for your awareness. No negotiation "
        f"action is appropriate."
    )
    return strat, action, rationale, 0


def calculate_negotiation_impact(selected_items, market_profile):
    leverage = market_profile.get("leverage_score", 50)
    market_type = market_profile.get("market_type", "Balanced Market")
    months_supply = market_profile.get("months_of_supply", 3.5)
    avg_dom = market_profile.get("avg_days_on_market", 30)
    median_price = market_profile.get("median_sale_price", 400000)
    market_tier = _get_market_type_tier(leverage)

    total_requested = sum(item.get("estimated_cost_avg", 0) for item in selected_items)

    base_concession_rates = {
        "strong_seller": (0.30, 0.45),
        "seller": (0.45, 0.60),
        "balanced": (0.55, 0.70),
        "buyer": (0.65, 0.80),
        "strong_buyer": (0.75, 0.95),
    }
    rate_low, rate_high = base_concession_rates[market_tier]

    dom_adjustment = 0.0
    if avg_dom > 50:
        dom_adjustment = 0.08
    elif avg_dom > 40:
        dom_adjustment = 0.04
    elif avg_dom > 30:
        dom_adjustment = 0.0
    elif avg_dom > 20:
        dom_adjustment = -0.04
    else:
        dom_adjustment = -0.07

    supply_adjustment = 0.0
    if months_supply > 6.0:
        supply_adjustment = 0.06
    elif months_supply > 4.5:
        supply_adjustment = 0.03
    elif months_supply > 3.0:
        supply_adjustment = 0.0
    elif months_supply > 2.0:
        supply_adjustment = -0.04
    else:
        supply_adjustment = -0.08

    deal_size_factor = 0.0
    deal_size_ratio = total_requested / median_price if median_price > 0 else 0
    if deal_size_ratio > 0.10:
        deal_size_factor = 0.05
    elif deal_size_ratio > 0.05:
        deal_size_factor = 0.02
    elif deal_size_ratio < 0.01:
        deal_size_factor = -0.03

    critical_count = sum(1 for item in selected_items if item.get("severity") == "CRITICAL")
    high_count = sum(1 for item in selected_items if item.get("severity") == "HIGH")
    severity_weight = 0.0
    if critical_count > 0:
        severity_weight += 0.03 * critical_count
    if high_count > 0:
        severity_weight += 0.01 * high_count

    expected_concession_rate = max(0.15, min(0.95,
        (rate_low + rate_high) / 2 + dom_adjustment + supply_adjustment + deal_size_factor + severity_weight
    ))

    expected_concession_amount = total_requested * expected_concession_rate

    contingency_reserve = total_requested * 0.10
    net_expected_benefit = expected_concession_amount - contingency_reserve

    if market_tier in ("strong_seller", "seller"):
        strategy_adjustment = "Conservative — Focus on critical safety items only. Maximize documentation strength."
        acceptance_probability = "55-70%"
        negotiation_timeline = "3-5 business days"
    elif market_tier == "balanced":
        strategy_adjustment = "Moderate — Package all documented items. Be prepared to negotiate 15-25%."
        acceptance_probability = "70-85%"
        negotiation_timeline = "5-7 business days"
    else:
        strategy_adjustment = "Aggressive — Request comprehensive credits. Hold firm on most items."
        acceptance_probability = "80-95%"
        negotiation_timeline = "3-7 business days"

    return {
        "total_requested": round(total_requested, 0),
        "expected_concession_rate": round(expected_concession_rate * 100, 1),
        "expected_concession_amount": round(expected_concession_amount, 0),
        "market_leverage": leverage,
        "strategy_adjustment": strategy_adjustment,
        "contingency_reserve": round(contingency_reserve, 0),
        "net_expected_benefit": round(net_expected_benefit, 0),
        "acceptance_probability": acceptance_probability,
        "negotiation_timeline": negotiation_timeline,
        "deal_size_ratio_pct": round(deal_size_ratio * 100, 2),
        "dom_adjustment_pct": round(dom_adjustment * 100, 1),
        "supply_adjustment_pct": round(supply_adjustment * 100, 1),
    }


_STATE_MARKET_PROFILES = {
    "CA": {
        "trend_direction": "Stable",
        "price_trend_pct": 0.5,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "High buyer pressure — rates near 6.2% keep monthly payments elevated",
        "seasonal_factor": "Peak season premium (summer) / Mild winter discount",
        "notes": "California markets remain bifurcated. Coastal metros (SF, LA, San Diego) show flat "
                 "to slight declines due to affordability constraints. Inland markets (Sacramento, "
                 "Riverside) continue moderate growth. Supply constrained by Prop 13 lock-in effect. "
                 "New construction minimal in coastal areas due to land costs.",
    },
    "TX": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.2,
        "inventory_trend": "Increasing",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure — Texas markets absorbing new supply",
        "seasonal_factor": "Strong spring/summer activity",
        "notes": "Texas continues strong growth driven by corporate relocations and population influx. "
                 "New construction is robust, keeping inventory from becoming critically low. DFW and "
                 "Austin showing strongest appreciation. Houston steady. San Antonio more affordable "
                 "entry point attracting first-time buyers.",
    },
    "FL": {
        "trend_direction": "Declining",
        "price_trend_pct": -1.5,
        "inventory_trend": "Increasing",
        "dom_trend": "Lengthening",
        "rate_impact": "High buyer pressure — insurance costs compounding affordability",
        "seasonal_factor": "Snowbird premium (Jan-Apr) / Hurricane season discount (Aug-Oct)",
        "notes": "Florida markets softening due to skyrocketing insurance costs (avg $4,200/yr statewide), "
                 "rising HOA fees post-Surfside legislation, and increased inventory from investor exits. "
                 "Miami and Tampa seeing largest corrections. Southwest FL particularly impacted by "
                 "insurance availability. New construction competing directly with existing inventory.",
    },
    "NY": {
        "trend_direction": "Rising",
        "price_trend_pct": 2.8,
        "inventory_trend": "Decreasing",
        "dom_trend": "Shortening",
        "rate_impact": "Moderate buyer pressure — NYC co-op/condo market absorbing rate increases",
        "seasonal_factor": "Spring market peak (Mar-Jun) / Holiday slowdown",
        "notes": "New York metro continues steady appreciation. Manhattan luxury segment strong with "
                 "international buyer return. Brooklyn and Queens seeing gentrification-driven growth. "
                 "Upstate NY more affordable with remote work sustaining demand. Inventory remains "
                 "constrained in NYC proper, supporting prices despite elevated rates.",
    },
    "IL": {
        "trend_direction": "Rising",
        "price_trend_pct": 4.5,
        "inventory_trend": "Decreasing",
        "dom_trend": "Shortening",
        "rate_impact": "Moderate buyer pressure — Chicago affordability attracting remote workers",
        "seasonal_factor": "Strong spring market / Slow winter",
        "notes": "Chicago metro showing solid appreciation driven by relative affordability compared to "
                 "coastal markets. Suburban areas seeing strongest growth. Inventory tight in popular "
                 "neighborhoods. Property taxes remain high but price-to-income ratios favorable.",
    },
    "OH": {
        "trend_direction": "Rising",
        "price_trend_pct": 5.2,
        "inventory_trend": "Decreasing",
        "dom_trend": "Shortening",
        "rate_impact": "Low buyer pressure — affordability is a major draw",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Ohio markets among the strongest in the Midwest. Columbus driven by tech sector growth. "
                 "Cleveland and Cincinnati benefiting from affordability migration. Extremely low inventory "
                 "in desirable suburbs. New construction cannot keep pace with demand.",
    },
    "MI": {
        "trend_direction": "Rising",
        "price_trend_pct": 4.8,
        "inventory_trend": "Decreasing",
        "dom_trend": "Shortening",
        "rate_impact": "Low buyer pressure — strong value proposition",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Michigan housing market strengthening. Grand Rapids and Ann Arbor leading appreciation. "
                 "Detroit metro continuing slow but steady recovery. Auto industry EV investments "
                 "driving employment and housing demand in southeastern Michigan.",
    },
    "MN": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.8,
        "inventory_trend": "Decreasing",
        "dom_trend": "Shortening",
        "rate_impact": "Moderate buyer pressure",
        "seasonal_factor": "Compressed spring/summer season",
        "notes": "Twin Cities market tight with low inventory. Strong job market anchored by healthcare, "
                 "retail, and tech sectors. Harsh winters compress selling season, creating urgency "
                 "during spring/summer months. Suburban growth continues.",
    },
    "CO": {
        "trend_direction": "Rising",
        "price_trend_pct": 2.8,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure — mountain town premium",
        "seasonal_factor": "Year-round demand in Front Range",
        "notes": "Colorado market stabilizing after rapid post-pandemic growth. Denver metro inventory "
                 "normalizing. Mountain communities remain premium-priced. Colorado Springs strong "
                 "with military and defense sector employment. New construction active along Front Range.",
    },
    "WA": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.5,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure — tech sector recovery",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Seattle metro recovering with tech sector stabilization. Amazon, Microsoft, and "
                 "other tech employers continue driving demand. Eastern WA more affordable with "
                 "growing remote worker migration. Inventory stabilizing but still below historical norms.",
    },
    "OR": {
        "trend_direction": "Stable",
        "price_trend_pct": 1.0,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Portland market flat with moderate inventory. Slight softening from 2024-2025 peaks. "
                 "Affordability improving relative to Seattle. Tech sector layoffs impacted Portland "
                 "less than Seattle. New construction helping stabilize prices.",
    },
    "GA": {
        "trend_direction": "Rising",
        "price_trend_pct": 4.0,
        "inventory_trend": "Stable",
        "dom_trend": "Shortening",
        "rate_impact": "Low buyer pressure — strong affordability",
        "seasonal_factor": "Year-round activity",
        "notes": "Atlanta metro continues strong growth. Film industry, tech, and corporate headquarters "
                 "driving employment. Suburban areas (Alpharetta, Marietta, Johns Creek) seeing "
                 "strongest appreciation. Affordable compared to coastal markets, attracting migration.",
    },
    "NC": {
        "trend_direction": "Rising",
        "price_trend_pct": 4.5,
        "inventory_trend": "Stable",
        "dom_trend": "Shortening",
        "rate_impact": "Low buyer pressure — strong job market",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Raleigh-Durham and Charlotte among fastest-growing metros nationally. Research Triangle "
                 "attracting biotech and tech employers. Banking sector in Charlotte stable. "
                 "Population growth outpacing new construction. Inventory tight.",
    },
    "TN": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.8,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Low buyer pressure — no state income tax advantage",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Nashville remains one of the hottest markets in the Southeast. Entertainment, healthcare, "
                 "and tech sectors driving growth. No state income tax attracting relocators. "
                 "Memphis more affordable with slower growth. Knoxville seeing spillover demand.",
    },
    "AZ": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.0,
        "inventory_trend": "Increasing",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure",
        "seasonal_factor": "Winter snowbird demand / Summer slowdown",
        "notes": "Phoenix market recovering after 2022-2023 correction. New construction helping "
                 "meet demand. Semiconductor manufacturing (TSMC) driving employment in Phoenix metro. "
                 "Tucson more affordable with steady growth. Extreme heat concerns moderating some demand.",
    },
    "NV": {
        "trend_direction": "Rising",
        "price_trend_pct": 2.5,
        "inventory_trend": "Increasing",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure",
        "seasonal_factor": "Year-round activity",
        "notes": "Las Vegas market stabilizing. Raiders, A's relocation, and Formula 1 driving "
                 "entertainment sector employment. California migration continues but at slower pace. "
                 "New construction active in Henderson and North Las Vegas. Water concerns "
                 "long-term but not impacting 2026 values.",
    },
    "UT": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.5,
        "inventory_trend": "Stable",
        "dom_trend": "Shortening",
        "rate_impact": "Moderate buyer pressure — strong job market",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Salt Lake City metro among strongest in Mountain West. Tech sector (Silicon Slopes) "
                 "driving employment. Population growth among highest nationally. New construction "
                 "active but not keeping pace with demand.",
    },
    "MA": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.0,
        "inventory_trend": "Decreasing",
        "dom_trend": "Shortening",
        "rate_impact": "High buyer pressure — limited supply in desirable areas",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Boston metro constrained by geography and zoning. Biotech and education sectors "
                 "strong. Cambridge and Somerville extremely tight inventory. Suburban markets "
                 "benefiting from school quality demand. New construction minimal in core areas.",
    },
    "PA": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.2,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Philadelphia metro showing solid appreciation. Life sciences sector growing. "
                 "Pittsburgh diversified economy stable. Suburban PA markets benefiting from "
                 "NYC/DC remote worker migration. Amtrak service improvements increasing connectivity.",
    },
    "NJ": {
        "trend_direction": "Rising",
        "price_trend_pct": 2.5,
        "inventory_trend": "Decreasing",
        "dom_trend": "Shortening",
        "rate_impact": "High buyer pressure — proximity to NYC premium",
        "seasonal_factor": "Spring/summer peak",
        "notes": "New Jersey market strong due to NYC proximity and remote work. Property taxes remain "
                 "highest nationally but price-to-income favorable vs Manhattan. Shore communities "
                 "seeing premium pricing. New construction focused on luxury segment.",
    },
    "MD": {
        "trend_direction": "Rising",
        "price_trend_pct": 2.8,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure — federal employment stability",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Maryland market stable with federal government employment providing floor. Baltimore "
                 "more affordable with缓慢 revitalization. DC suburbs (Montgomery County, Prince George's) "
                 "strong. Annapolis and Eastern Shore benefiting from lifestyle migration.",
    },
    "VA": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.0,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure — tech and defense sectors",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Virginia market strong. Northern Virginia (NoVA) driven by data centers, Amazon HQ2, "
                 "and defense contractors. Richmond more affordable with growing tech scene. "
                 "Hampton Roads stable with military presence.",
    },
    "SC": {
        "trend_direction": "Rising",
        "price_trend_pct": 4.2,
        "inventory_trend": "Stable",
        "dom_trend": "Shortening",
        "rate_impact": "Low buyer pressure — affordability migration",
        "seasonal_factor": "Year-round activity",
        "notes": "South Carolina experiencing strong growth. Charleston, Greenville, and Columbia all "
                 "seeing appreciation. Manufacturing (BMW, Volvo) driving employment. Retirement "
                 "migration continues. New construction active.",
    },
    "IN": {
        "trend_direction": "Rising",
        "price_trend_pct": 4.8,
        "inventory_trend": "Decreasing",
        "dom_trend": "Shortening",
        "rate_impact": "Low buyer pressure — strong affordability",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Indiana among strongest Midwest markets. Indianapolis driven by logistics, healthcare, "
                 "and manufacturing. Extreme affordability attracting remote workers. Low inventory "
                 "in desirable suburbs. New construction moderate.",
    },
    "WI": {
        "trend_direction": "Rising",
        "price_trend_pct": 4.0,
        "inventory_trend": "Decreasing",
        "dom_trend": "Shortening",
        "rate_impact": "Low buyer pressure",
        "seasonal_factor": "Compressed spring/summer season",
        "notes": "Wisconsin market tight. Milwaukee and Madison leading growth. Fox Valley benefiting "
                 "from manufacturing. University towns (Madison, Eau Claire) stable. Low inventory "
                 "driving quick sales in desirable areas.",
    },
    "MO": {
        "trend_direction": "Rising",
        "price_trend_pct": 4.2,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Low buyer pressure — strong affordability",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Kansas City and St. Louis showing solid growth. Kansas City benefiting from tech "
                 "and healthcare employment. St. Louis slower but stable. Both markets extremely "
                 "affordable compared to national averages.",
    },
    "KS": {
        "trend_direction": "Rising",
        "price_trend_pct": 4.0,
        "inventory_trend": "Decreasing",
        "dom_trend": "Shortening",
        "rate_impact": "Low buyer pressure",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Kansas market steady with Kansas City metro leading growth. Wichita stable with "
                 "aviation manufacturing. Affordable housing attracting relocators from coasts.",
    },
    "IA": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.5,
        "inventory_trend": "Decreasing",
        "dom_trend": "Shortening",
        "rate_impact": "Low buyer pressure",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Iowa market tight with low inventory. Des Moines metro leading with insurance and "
                 "financial services employment. Affordable housing attracting young buyers.",
    },
    "NE": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.8,
        "inventory_trend": "Decreasing",
        "dom_trend": "Shortening",
        "rate_impact": "Low buyer pressure",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Omaha and Lincoln showing strong growth. Insurance, finance, and agriculture "
                 "sectors stable. Low inventory in metro areas. Affordable compared to national average.",
    },
    "MD": {
        "trend_direction": "Rising",
        "price_trend_pct": 2.8,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Maryland market stable. DC suburbs strong. Baltimore more affordable with缓慢 revitalization.",
    },
    "AL": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.5,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Low buyer pressure — strong affordability",
        "seasonal_factor": "Year-round activity",
        "notes": "Alabama market growing. Huntsville driven by defense and aerospace. Birmingham stable. "
                 "Mobile and Gulf Coast seeing retirement migration. Extremely affordable.",
    },
    "LA": {
        "trend_direction": "Stable",
        "price_trend_pct": 1.5,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure",
        "seasonal_factor": "Year-round activity",
        "notes": "Louisiana market flat. New Orleans recovering from insurance crisis. Baton Rouge "
                 "stable with state government employment. Shreveport more affordable. Flood insurance "
                 "costs impacting affordability.",
    },
    "AR": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.8,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Low buyer pressure",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Arkansas market growing slowly. Northwest Arkansas (Bentonville/Walmart) strong. "
                 "Little Rock stable. Extremely affordable housing market.",
    },
    "OK": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.0,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Low buyer pressure",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Oklahoma City and Tulsa showing moderate growth. Energy sector recovery supporting "
                 "economy. Affordable housing attracting relocators.",
    },
    "KY": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.5,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Low buyer pressure",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Louisville and Lexington showing solid growth. Healthcare and logistics driving "
                 "employment. Affordable compared to Midwest peers.",
    },
    "MS": {
        "trend_direction": "Stable",
        "price_trend_pct": 2.0,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Low buyer pressure",
        "seasonal_factor": "Year-round activity",
        "notes": "Mississippi market slow but stable. Jackson area more affordable. Gulf Coast "
                 "seeing tourism-driven growth. Extremely affordable housing.",
    },
    "NM": {
        "trend_direction": "Rising",
        "price_trend_pct": 2.5,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure",
        "seasonal_factor": "Spring/summer peak",
        "notes": "New Mexico market moderate. Albuquerque and Santa Fe stable. Los Alamos and "
                 "national lab employment providing stability. Moderate affordability.",
    },
    "ID": {
        "trend_direction": "Rising",
        "price_trend_pct": 4.0,
        "inventory_trend": "Stable",
        "dom_trend": "Shortening",
        "rate_impact": "Moderate buyer pressure — California migration",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Idaho among fastest-growing states. Boise driven by California remote worker "
                 "migration. Inventory tight. New construction active but not keeping pace.",
    },
    "MT": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.0,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure — lifestyle migration",
        "seasonal_factor": "Year-round demand",
        "notes": "Montana market strong. Bozeman and Missoula seeing luxury segment growth. "
                 "Remote worker migration from West Coast. Limited inventory constraining supply.",
    },
    "WY": {
        "trend_direction": "Stable",
        "price_trend_pct": 2.0,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Low buyer pressure",
        "seasonal_factor": "Year-round activity",
        "notes": "Wyoming market stable. Jackson Hole premium pricing. Cheyenne more affordable "
                 "with Colorado commuter demand. Energy sector supporting economy.",
    },
    "NH": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.5,
        "inventory_trend": "Decreasing",
        "dom_trend": "Shortening",
        "rate_impact": "Moderate buyer pressure — no income tax advantage",
        "seasonal_factor": "Spring/summer peak",
        "notes": "New Hampshire benefiting from Massachusetts tax migration. Southern NH strong "
                 "with Boston commuter demand. North Country more affordable. Low inventory.",
    },
    "VT": {
        "trend_direction": "Rising",
        "price_trend_pct": 2.5,
        "inventory_trend": "Decreasing",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure",
        "seasonal_factor": "Winter ski premium / Summer tourism",
        "notes": "Vermont market tight with extremely limited inventory. Burlington strongest market. "
                 "Ski communities premium-priced. Remote worker migration sustained.",
    },
    "ME": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.0,
        "inventory_trend": "Decreasing",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure",
        "seasonal_factor": "Summer coastal premium",
        "notes": "Maine market tight. Portland and southern Maine strongest. Remote worker migration "
                 "from Boston. Vacation communities premium-priced. Limited year-round inventory.",
    },
    "RI": {
        "trend_direction": "Rising",
        "price_trend_pct": 2.8,
        "inventory_trend": "Decreasing",
        "dom_trend": "Shortening",
        "rate_impact": "Moderate buyer pressure",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Rhode Island small but tight market. Providence benefiting from Boston spillover. "
                 "Newport premium for coastal. Low inventory driving appreciation.",
    },
    "CT": {
        "trend_direction": "Rising",
        "price_trend_pct": 2.5,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure — NYC commuter demand",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Connecticut stable with NYC commuter demand. Fairfield County premium. Hartford "
                 "more affordable. Insurance and finance sectors supporting employment.",
    },
    "DE": {
        "trend_direction": "Rising",
        "price_trend_pct": 2.8,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Low buyer pressure — no sales tax advantage",
        "seasonal_factor": "Spring/summer peak",
        "notes": "Delaware small market with moderate growth. Wilmington benefiting from Philly "
                 "spillover. Beach communities seasonal. No sales tax attracting retail.",
    },
    "WV": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.0,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Low buyer pressure",
        "seasonal_factor": "Spring/summer peak",
        "notes": "West Virginia market slow but improving. Eastern panhandle benefiting from DC "
                 "commuter migration. Charleston and Huntington stable. Extremely affordable.",
    },
    "ND": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.5,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Low buyer pressure",
        "seasonal_factor": "Spring/summer peak",
        "notes": "North Dakota stable with energy sector support. Fargo growing with tech and "
                 "healthcare. Bismarck stable. Extreme cold limits winter activity.",
    },
    "SD": {
        "trend_direction": "Rising",
        "price_trend_pct": 3.2,
        "inventory_trend": "Decreasing",
        "dom_trend": "Shortening",
        "rate_impact": "Low buyer pressure",
        "seasonal_factor": "Spring/summer peak",
        "notes": "South Dakota stable. Sioux Falls growing with finance and healthcare. "
                 "No income tax attracting businesses. Low inventory in metro areas.",
    },
    "AK": {
        "trend_direction": "Stable",
        "price_trend_pct": 1.0,
        "inventory_trend": "Stable",
        "dom_trend": "Stable",
        "rate_impact": "Moderate buyer pressure — unique market dynamics",
        "seasonal_factor": "Summer construction season",
        "notes": "Alaska market unique. Anchorage stable with oil sector. Fairbanks smaller market. "
                 "Remote communities have limited market data. Construction season compressed.",
    },
    "HI": {
        "trend_direction": "Declining",
        "price_trend_pct": -1.0,
        "inventory_trend": "Stable",
        "dom_trend": "Lengthening",
        "rate_impact": "High buyer pressure — affordability crisis",
        "seasonal_factor": "Year-round demand",
        "notes": "Hawaii market softening due to extreme affordability constraints. Local residents "
                 "priced out. Tourism-dependent economy. Limited land for new construction. "
                 "Military presence providing some demand floor.",
    },
}


def get_market_trends(state):
    if not state:
        return {
            "state": state,
            "trend_direction": "Insufficient Data",
            "price_trend_pct": 0.0,
            "inventory_trend": "Unknown",
            "dom_trend": "Unknown",
            "rate_impact": "Unable to assess without state data",
            "seasonal_factor": "Unknown",
            "notes": "State code required for market trend analysis.",
        }

    state_upper = state.upper()
    profile = _STATE_MARKET_PROFILES.get(state_upper)

    if not profile:
        now = datetime.now()
        month = now.month
        base_trend = _deterministic_float(state_upper, "trend", 1.5, 4.5)
        seasonal_desc = _get_seasonal_description(month)

        return {
            "state": state_upper,
            "trend_direction": "Rising" if base_trend > 1.0 else "Stable",
            "price_trend_pct": round(base_trend, 1),
            "inventory_trend": "Stable",
            "dom_trend": "Stable",
            "rate_impact": "Moderate buyer pressure — 5.8-6.2% 30yr fixed mortgage rate environment",
            "seasonal_factor": seasonal_desc,
            "notes": (
                f"Market data for {state_upper} modeled from regional patterns. "
                f"2026 national context: 30-year fixed mortgage rates averaging 5.8-6.2%. "
                f"New construction inventory improving after 2024-2025 supply chain recovery. "
                f"Consumer confidence stabilizing. Labor market remains tight with 4.0-4.3% unemployment."
            ),
        }

    return {
        "state": state_upper,
        "trend_direction": profile["trend_direction"],
        "price_trend_pct": profile["price_trend_pct"],
        "inventory_trend": profile["inventory_trend"],
        "dom_trend": profile["dom_trend"],
        "rate_impact": profile["rate_impact"],
        "seasonal_factor": profile["seasonal_factor"],
        "notes": profile["notes"],
    }


def _get_seasonal_description(month):
    if month in (6, 7, 8):
        return "Peak summer season — highest activity, competitive pricing, 3-5% seasonal premium on listings"
    elif month in (3, 4, 5):
        return "Spring market — increasing inventory, strong buyer activity, optimal listing timing"
    elif month in (9, 10):
        return "Fall market — moderating activity, motivated sellers, potential for better negotiation"
    elif month in (11, 12, 1):
        return "Winter/off-season — lowest inventory, motivated sellers, 2-4% seasonal discount, best negotiating leverage"
    elif month == 2:
        return "Late winter — early spring prep, motivated sellers, pre-season positioning"
    else:
        return "Normal seasonal conditions"
