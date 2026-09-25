from datetime import datetime

from config import DEPRECIATION_TABLES, ZIP_COST_MODIFIERS


def analyze_investor_deal(
    property_data, findings, cost_matrix, capex_analysis, market_profile=None, user_inputs=None
):
    """
    Real deal math. Prefers verified anchors:
    - list_price/ARV/rent from user MLS (market_profile) or explicit user_inputs
    - repair costs from the verified cost matrix
    - 24-month CapEx risk from the capex engine
    Falls back to clearly-labeled MODELED benchmarks only where no real anchor exists.
    """
    user_inputs = user_inputs or {}
    current_year = datetime.now().year
    year_built = property_data.get("year_built", current_year - 20)
    prop_age = current_year - year_built if year_built else 20
    sqft = property_data.get("square_footage", 1800)
    zip_code = property_data.get("zip_code", "")
    state = property_data.get("state", "")
    bedrooms = property_data.get("bedrooms", 3)
    bathrooms = property_data.get("bathrooms", 2)

    mkt = market_profile or {}
    total_repair = cost_matrix.get("summary", {}).get("total_avg", 0)
    total_repair_low = cost_matrix.get("summary", {}).get("total_low", 0)
    total_repair_high = cost_matrix.get("summary", {}).get("total_high", 0)
    capex_weighted = capex_analysis.get("summary", {}).get("weighted_risk_exposure", 0)

    listing_price, list_provenance = _listing_price(
        mkt, user_inputs, zip_code, sqft, property_data, bedrooms, bathrooms
    )
    arv, arv_provenance = _arv(
        mkt, user_inputs, listing_price, total_repair, state, zip_code, sqft, property_data
    )
    holding_costs_monthly = _estimate_holding_costs(listing_price, state)
    closing_costs_buyer = listing_price * 0.03
    closing_costs_seller = listing_price * 0.01
    holding_period_months = int(user_inputs.get("holding_months", 6))
    total_holding = holding_costs_monthly * holding_period_months
    profit_target = listing_price * 0.12
    max_offer = (
        arv - total_repair - total_holding - closing_costs_buyer - closing_costs_seller - profit_target
    )

    monthly_rental, rent_provenance = _rental(mkt, user_inputs, zip_code, sqft, bedrooms, bathrooms)
    annual_rental = monthly_rental * 12
    annual_noi = annual_rental * 0.75
    cap_rate = (annual_noi / arv * 100) if arv > 0 else 0
    cash_invested = max_offer + total_repair + closing_costs_buyer
    monthly_mortgage = max_offer * (float(user_inputs.get("interest_rate", 0.07)) / 12)
    cash_on_cash = ((annual_noi - (monthly_mortgage * 12)) / cash_invested * 100) if cash_invested > 0 else 0
    capex_reserve_5yr = capex_weighted * 2.5

    depreciation_forecast = _build_5yr_capex_forecast(findings, property_data)

    return {
        "listing_price": round(listing_price, 0),
        "listing_price_provenance": list_provenance,
        "after_repair_value": round(arv, 0),
        "arv_provenance": arv_provenance,
        "monthly_rental_provenance": rent_provenance,
        "max_allowable_offer": round(max_offer, 0),
        "total_repair_cost": round(total_repair, 0),
        "total_repair_range": {"low": round(total_repair_low, 0), "high": round(total_repair_high, 0)},
        "holding_costs_total": round(total_holding, 0),
        "holding_costs_monthly": round(holding_costs_monthly, 0),
        "closing_costs": round(closing_costs_buyer, 0),
        "profit_target": round(profit_target, 0),
        "cap_rate": round(cap_rate, 2),
        "cash_on_cash_return": round(cash_on_cash, 2),
        "monthly_rental_estimate": round(monthly_rental, 0),
        "annual_rental_income": round(annual_rental, 0),
        "annual_noi": round(annual_noi, 0),
        "capex_reserve_5yr": round(capex_reserve_5yr, 0),
        "depreciation_forecast": depreciation_forecast,
        "deal_metrics": {
            "repair_to_arv_ratio": round(total_repair / max(arv, 1) * 100, 1),
            "offer_to_arv_ratio": round(max_offer / max(arv, 1) * 100, 1),
            "gross_rent_multiplier": round(arv / max(annual_rental, 1), 2),
            "cash_required": round(cash_invested, 0),
            "net_monthly_cashflow": round((annual_noi - (max_offer * 0.07)) / 12, 0),
        },
        "risk_assessment": {
            "repair_risk": "HIGH"
            if total_repair > arv * 0.25
            else "MEDIUM"
            if total_repair > arv * 0.15
            else "LOW",
            "hold_risk": "HIGH"
            if holding_period_months > 9
            else "MEDIUM"
            if holding_period_months > 6
            else "LOW",
            "capex_risk": "HIGH" if capex_weighted > 10000 else "MEDIUM" if capex_weighted > 5000 else "LOW",
            "overall_deal_quality": _assess_deal_quality(
                max_offer, arv, total_repair, cap_rate, cash_on_cash
            ),
        },
        "investment_analysis": _generate_investment_analysis(
            listing_price,
            arv,
            max_offer,
            total_repair,
            monthly_rental,
            cap_rate,
            cash_on_cash,
            prop_age,
            sqft,
        ),
    }


def _listing_price(mkt, user_inputs, zip_code, sqft, property_data, bedrooms, bathrooms):
    if user_inputs.get("list_price"):
        return float(user_inputs["list_price"]), "USER_PROVIDED"
    if mkt.get("list_price"):
        return float(mkt["list_price"]), "USER_MLS_VERIFIED"
    # MODELED fallback: published state-level $/sqft benchmarks
    return _modeled_listing(zip_code, sqft, property_data, bedrooms, bathrooms), "MODELED_BENCHMARK"


def _modeled_listing(zip_code, sqft, property_data, bedrooms=3, bathrooms=2):
    state = property_data.get("state", "")
    year_built = property_data.get("year_built", 2000)
    age = datetime.now().year - year_built if year_built else 20
    state_ppsf = {
        "CA": 520,
        "NY": 480,
        "MA": 420,
        "WA": 400,
        "CO": 370,
        "OR": 350,
        "TX": 180,
        "FL": 220,
        "GA": 200,
        "NC": 195,
        "TN": 190,
        "AZ": 210,
        "IL": 200,
        "PA": 195,
        "OH": 160,
        "MI": 170,
        "default": 200,
    }
    base_ppsf = state_ppsf.get(state, state_ppsf["default"])
    modifier = (ZIP_COST_MODIFIERS.get(zip_code) or {}).get("modifier", 1.0)
    adjusted_ppsf = base_ppsf * modifier
    if age < 5:
        adjusted_ppsf *= 1.12
    elif age < 10:
        adjusted_ppsf *= 1.05
    elif age > 30:
        adjusted_ppsf *= 0.88
    elif age > 20:
        adjusted_ppsf *= 0.94
    bedroom_premium = 1.0 + (bedrooms - 3) * 0.03
    bathroom_premium = 1.0 + (bathrooms - 2) * 0.02
    return sqft * adjusted_ppsf * bedroom_premium * bathroom_premium


def _arv(mkt, user_inputs, listing_price, repair_cost, state, zip_code, sqft, property_data):
    if user_inputs.get("arv"):
        return float(user_inputs["arv"]), "USER_PROVIDED"
    if mkt.get("price_per_sqft") and mkt.get("sqft"):
        return mkt["price_per_sqft"] * mkt["sqft"], "USER_MLS_VERIFIED"
    roi_mults = {"CA": 0.75, "NY": 0.70, "TX": 0.85, "FL": 0.80, "default": 0.72}
    rehab_premium = repair_cost * roi_mults.get(state, roi_mults["default"])
    return listing_price + rehab_premium, "MODELED_BENCHMARK"


def _estimate_holding_costs(price, state=""):
    monthly_tax = price * 0.012 / 12
    monthly_insurance = price * 0.005 / 12
    monthly_interest = price * 0.07 / 12
    state_utility_mults = {"CA": 1.3, "TX": 1.2, "FL": 1.15, "NY": 1.25, "default": 1.0}
    util_mult = state_utility_mults.get(state, state_utility_mults["default"])
    monthly_maintenance = 250 * util_mult
    monthly_utilities = 350 * util_mult
    return round(
        monthly_tax + monthly_insurance + monthly_interest + monthly_maintenance + monthly_utilities, 0
    )


def _rental(mkt, user_inputs, zip_code, sqft, bedrooms=3, bathrooms=2):
    if user_inputs.get("monthly_rent"):
        return float(user_inputs["monthly_rent"]), "USER_PROVIDED"
    acs = mkt.get("acs") or {}
    if acs.get("median_gross_rent"):
        return float(acs["median_gross_rent"]), f"CENSUS_ACS_{acs.get('acs_year', '')}"
    state = mkt.get("state", "")
    state_rent_ppsf = {
        "CA": 2.50,
        "NY": 2.80,
        "MA": 2.30,
        "WA": 2.10,
        "CO": 2.00,
        "TX": 1.20,
        "FL": 1.50,
        "GA": 1.30,
        "NC": 1.25,
        "TN": 1.20,
        "AZ": 1.35,
        "IL": 1.60,
        "PA": 1.50,
        "OH": 1.10,
        "MI": 1.15,
        "default": 1.30,
    }
    base_ppsf = state_rent_ppsf.get(state, state_rent_ppsf["default"])
    base_rent = sqft * base_ppsf
    bedroom_adj = 1.0 + (bedrooms - 3) * 0.05
    bath_adj = 1.0 + (bathrooms - 2) * 0.03
    return base_rent * bedroom_adj * bath_adj, "MODELED_BENCHMARK"


def _assess_deal_quality(max_offer, arv, repair, cap_rate, coc):
    if cap_rate > 8 and coc > 15:
        return {
            "grade": "A",
            "verdict": "Excellent deal. Strong cash flow potential with high cap rate and cash-on-cash return.",
        }
    elif cap_rate > 6 and coc > 10:
        return {
            "grade": "B",
            "verdict": "Good deal. Solid investment with reasonable returns. Consider negotiating on price.",
        }
    elif cap_rate > 4 and coc > 5:
        return {
            "grade": "C",
            "verdict": "Marginal deal. Returns are acceptable but not compelling. Negotiate aggressively on purchase price.",
        }
    else:
        return {
            "grade": "D",
            "verdict": "Weak deal. Repair costs may erode profit margin. Consider passing or significantly reducing offer.",
        }


def _generate_investment_analysis(
    listing_price, arv, max_offer, total_repair, monthly_rental, cap_rate, coc, prop_age, sqft
):
    analysis = []
    repair_to_arv = total_repair / max(arv, 1) * 100
    if repair_to_arv > 25:
        analysis.append(
            f"REPAIR WARNING: Repair costs ({repair_to_arv:.1f}% of ARV) exceed 25% threshold. This significantly increases flip risk."
        )
    elif repair_to_arv > 15:
        analysis.append(
            f"Repair costs ({repair_to_arv:.1f}% of ARV) are within flip range but above ideal 15% target."
        )
    else:
        analysis.append(
            f"Repair costs ({repair_to_arv:.1f}% of ARV) are within ideal range for a flip project."
        )
    if cap_rate > 8:
        analysis.append(
            f"Cap rate ({cap_rate:.1f}%) exceeds 8% target - strong rental investment indicators."
        )
    elif cap_rate > 6:
        analysis.append(f"Cap rate ({cap_rate:.1f}%) is acceptable for rental investment in most markets.")
    else:
        analysis.append(
            f"Cap rate ({cap_rate:.1f}%) is below 6% - rental returns may not justify investment risk."
        )
    if prop_age > 30:
        analysis.append(
            f"Property age ({prop_age} years) increases CapEx risk. Budget for accelerated system replacements."
        )
    if sqft < 1200:
        analysis.append(
            "Smaller property may limit rental income potential. Consider target demographic (singles, couples vs families)."
        )
    elif sqft > 3000:
        analysis.append(
            "Larger property may attract higher-quality tenants but also higher maintenance costs."
        )
    return analysis


def _build_5yr_capex_forecast(findings, property_data):
    current_year = datetime.now().year
    year_built = property_data.get("year_built", current_year - 20)
    prop_age = current_year - year_built if year_built else 20
    forecast = []
    for year_offset in range(1, 6):
        year = current_year + year_offset
        year_costs = []
        for finding in findings:
            system = finding.get("system_category", "OTHER")
            asset_type = {
                "HVAC": "hvac",
                "ROOF": "roof_asphalt",
                "PLUMBING": "water_heater",
                "ELECTRICAL": "electrical_panel",
                "STRUCTURAL": "foundation",
            }.get(system)
            if asset_type:
                age_at_year = prop_age + year_offset
                dep = calculate_depreciation_curve(asset_type, age_at_year, finding.get("description", ""))
                if dep["failure_probability_24mo"] > 20:
                    year_costs.append(
                        {
                            "system": system,
                            "risk_prob": dep["failure_probability_24mo"],
                            "replacement_cost": dep["replacement_cost_avg"],
                            "expected_cost": dep["replacement_cost_avg"]
                            * dep["failure_probability_24mo"]
                            / 100,
                        }
                    )
        total_expected = sum(c["expected_cost"] for c in year_costs)
        forecast.append(
            {
                "year": year,
                "total_expected_cost": round(total_expected, 0),
                "items_at_risk": len(year_costs),
                "details": year_costs,
            }
        )
    return forecast


def calculate_depreciation_curve(asset_type, age_years, current_condition=None):
    table = DEPRECIATION_TABLES.get(asset_type)
    if not table:
        for key in DEPRECIATION_TABLES:
            if key in asset_type.lower():
                table = DEPRECIATION_TABLES[key]
                break
    if not table:
        table = {
            "useful_life": 20,
            "salvage_pct": 0.10,
            "replacement_avg": 3000,
            "replacement_range": (1500, 6000),
        }
    useful_life = table["useful_life"]
    salvage_pct = table["salvage_pct"]
    replacement_avg = table["replacement_avg"]
    replacement_low, replacement_high = table["replacement_range"]
    annual_dep = max(0, (1 - salvage_pct)) / useful_life
    depreciation_pct = min(1.0, age_years * annual_dep)
    remaining_value_pct = max(0, 1.0 - depreciation_pct)
    remaining_life = max(0, useful_life - age_years)
    if age_years > useful_life:
        failure_prob = min(0.98, 0.70 + (age_years - useful_life) * 0.05)
    elif age_years > useful_life * 0.8:
        failure_prob = 0.15 + (age_years / useful_life - 0.8) * 2.5
    else:
        failure_prob = max(0.02, (age_years / useful_life) ** 3 * 0.15)
    condition_mults = {
        "excellent": 0.7,
        "good": 0.85,
        "fair": 1.0,
        "poor": 1.25,
        "terrible": 1.5,
        "rust": 1.3,
        "leaking": 1.4,
        "broken": 1.5,
        "noisy": 1.1,
        "corroded": 1.35,
        "damaged": 1.3,
    }
    cond_mult = 1.0
    if current_condition:
        cond_lower = current_condition.lower()
        for condition, mult in condition_mults.items():
            if condition in cond_lower:
                cond_mult = mult
                break
    adjusted_failure_prob = min(0.99, failure_prob * cond_mult)
    if adjusted_failure_prob > 0.75:
        urgency = "IMMEDIATE REPLACEMENT - High failure risk"
    elif adjusted_failure_prob > 0.50:
        urgency = "PLAN REPLACEMENT - Likely within 12 months"
    elif adjusted_failure_prob > 0.25:
        urgency = "MONITOR CLOSELY - Replacement within 24 months probable"
    elif remaining_life <= 3:
        urgency = "BUDGET FOR REPLACEMENT - Approaching end of useful life"
    elif remaining_life <= 5:
        urgency = "BEGIN PLANNING - Approaching end of useful life"
    else:
        urgency = "ADEQUATE REMAINING LIFE"
    failure_horizon_months = int(remaining_life * 12 * (1 - adjusted_failure_prob))
    depreciation_value = replacement_avg * depreciation_pct
    return {
        "asset_type": asset_type,
        "age_years": age_years,
        "useful_life": useful_life,
        "remaining_life": round(remaining_life, 1),
        "depreciation_pct": round(depreciation_pct * 100, 1),
        "remaining_value_pct": round(remaining_value_pct * 100, 1),
        "annual_depreciation_rate": round(annual_dep * 100, 2),
        "replacement_cost_avg": replacement_avg,
        "replacement_cost_low": replacement_low,
        "replacement_cost_high": replacement_high,
        "current_depreciated_value": round(replacement_avg * remaining_value_pct, 0),
        "depreciation_loss": round(depreciation_value, 0),
        "failure_probability_24mo": round(adjusted_failure_prob * 100, 1),
        "failure_horizon_months": max(0, failure_horizon_months),
        "replacement_urgency": urgency,
        "salvage_value": round(replacement_avg * salvage_pct, 0),
        "depreciation_curve": _generate_depreciation_timeline(useful_life, salvage_pct),
    }


def _generate_depreciation_timeline(useful_life, salvage_pct):
    timeline = []
    annual_dep = (1 - salvage_pct) / useful_life
    for year in range(0, useful_life + 10):
        dep = min(1.0, year * annual_dep)
        remaining = max(0, 1.0 - dep)
        if year <= useful_life:
            prob = min(0.95, (year / useful_life) ** 3 * 0.15)
        else:
            prob = min(0.98, 0.70 + (year - useful_life) * 0.06)
        timeline.append(
            {
                "year": year,
                "depreciation_pct": round(dep * 100, 1),
                "remaining_value_pct": round(remaining * 100, 1),
                "failure_probability": round(prob * 100, 1),
            }
        )
    return timeline
