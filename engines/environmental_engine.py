import math
from datetime import datetime
from config import CLIMATE_ZONES


def _deterministic_hash(value):
    h = 0
    for ch in str(value):
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


FEMA_FLOOD_ZONE_DATA = {
    "X": {"risk_level": "Minimal", "description": "Area of minimal flood hazard, outside the 1% annual chance floodplain (100-year flood). Flood insurance not required but recommended.", "annual_risk_pct": 0.1, "insurance_required": False, "avg_flood_insurance": 0},
    "B": {"risk_level": "Low", "description": "Area of moderate flood hazard, between the 1% and 0.2% annual chance floodplains. Flood insurance recommended.", "annual_risk_pct": 0.2, "insurance_required": False, "avg_flood_insurance": 400},
    "AE": {"risk_level": "High", "description": "Area of high flood hazard within the 1% annual chance floodplain. Mandatory flood insurance for federally-backed mortgages.", "annual_risk_pct": 1.0, "insurance_required": True, "avg_flood_insurance": 2800},
    "A": {"risk_level": "High", "description": "Area of high flood hazard. Base flood elevations not determined. Mandatory flood insurance required.", "annual_risk_pct": 1.0, "insurance_required": True, "avg_flood_insurance": 2600},
    "VE": {"risk_level": "Coastal High", "description": "Coastal high hazard area with wave action. Mandatory flood insurance with highest premiums.", "annual_risk_pct": 1.5, "insurance_required": True, "avg_flood_insurance": 4200},
    "AO": {"risk_level": "High", "description": "Area of shallow flooding with average depths of 1-3 feet. Sheet flow flooding.", "annual_risk_pct": 1.0, "insurance_required": True, "avg_flood_insurance": 2400},
    "AH": {"risk_level": "High", "description": "Area of shallow flooding with average depths of 1-3 feet. Ponding flooding.", "annual_risk_pct": 1.0, "insurance_required": True, "avg_flood_insurance": 2200},
}

USGS_SEISMIC_DATA = {
    "Very High": {"states": ["CA", "AK"], "pga": "0.40g+", "description": "Very high seismic hazard. Major active fault systems. Strong ground shaking expected in lifetime of structure.", "retrofit_priority": "Critical"},
    "High": {"states": ["WA", "OR", "NV", "HI"], "pga": "0.20-0.40g", "description": "High seismic hazard. Active fault systems within 50 miles. Significant ground shaking possible.", "retrofit_priority": "High"},
    "Moderate": {"states": ["UT", "ID", "MT", "WY", "MO", "OK", "SC", "TN", "NC", "IL", "IN", "OH", "KY", "VA", "MD", "PA", "NJ", "NY", "CT", "RI", "MA"], "pga": "0.10-0.20g", "description": "Moderate seismic hazard. Intraplate seismicity or distant fault sources. Low-to-moderate ground shaking risk.", "retrofit_priority": "Medium"},
    "Low": {"states": ["TX", "FL", "GA", "AL", "MS", "LA", "AR", "KS", "NE", "ND", "SD", "IA", "MN", "WI", "MI", "WV", "DE", "NH", "VT", "ME"], "pga": "<0.10g", "description": "Low seismic hazard. Stable continental interior. Minimal ground shaking risk.", "retrofit_priority": "Low"},
}

CAL_FIRE_WILDFIRE_DATA = {
    "Very High": {"states": ["CA"], "annual_risk_pct": 4.5, "description": "Very high wildfire risk. WUI (Wildland-Urban Interface) zone. Mandatory defensible space requirements.", "insurance_impact": 3200, "defensible_space_ft": 100},
    "High": {"states": ["CO", "OR", "NV", "AZ", "NM", "UT", "MT", "WY", "ID"], "annual_risk_pct": 2.0, "description": "High wildfire risk. Seasonal fire weather warnings. Ember exposure risk.", "insurance_impact": 2200, "defensible_space_ft": 50},
    "Moderate": {"states": ["TX", "OK", "FL", "GA", "NC", "SC", "WA"], "annual_risk_pct": 0.8, "description": "Moderate wildfire risk. Localized fire events possible during dry seasons.", "insurance_impact": 800, "defensible_space_ft": 30},
    "Low": {"states": ["NY", "NJ", "CT", "RI", "MA", "NH", "VT", "ME", "PA", "OH", "MI", "IL", "IN", "WI", "MN", "IA", "MO", "NE", "KS", "ND", "SD", "MD", "DE", "VA", "WV", "KY", "TN", "AL", "MS", "LA", "AR"], "annual_risk_pct": 0.1, "description": "Low wildfire risk. Minimal wildfire history in area.", "insurance_impact": 0, "defensible_space_ft": 0},
}

USDA_SOIL_DATA = {
    "CA": {"primary": "Expansive Clay", "expansion_potential": "High", "description": "Montmorillonite clay common in Central/Southern CA. Swells significantly when wet, shrinks when dry. Foundation risk: HIGH.", "foundation_impact": "Significant movement expected over 10-year cycle"},
    "TX": {"primary": "Expansive Clay", "expansion_potential": "Very High", "description": "Blackland Prairie and Gulf Coast clays are among most expansive in US. Foundation risk: VERY HIGH.", "foundation_impact": "Severe movement possible; post-tension slab or pier foundation recommended"},
    "FL": {"primary": "Sandy", "expansion_potential": "Low", "description": "Sandy soils over limestone. Low expansion but sinkhole risk in certain karst regions. Foundation risk: LOW-MODERATE.", "foundation_impact": "Minimal movement; sinkhole insurance recommended in karst areas"},
    "CO": {"primary": "Clay Loam", "expansion_potential": "Moderate", "description": "Front Range has expansive clay soils. Mountain areas have rocky/stable soils. Foundation risk: MODERATE.", "foundation_impact": "Moderate movement; proper drainage critical"},
    "IL": {"primary": "Silty Clay", "expansion_potential": "Moderate", "description": "Loess-derived soils with moderate expansion. Chicago area has high water table concerns. Foundation risk: MODERATE.", "foundation_impact": "Seasonal movement; sump pump essential in many areas"},
    "NY": {"primary": "Sandy Loam", "expansion_potential": "Low-Moderate", "description": "Glacial till and sandy loam common. Southern tier has more clay. Foundation risk: LOW-MODERATE.", "foundation_impact": "Minor seasonal movement"},
    "AZ": {"primary": "Caliche", "expansion_potential": "High", "description": "Caliche hardpan and desert soils. Extreme wet-dry cycling causes significant expansion. Foundation risk: HIGH.", "foundation_impact": "Significant movement; deep pier foundation often required"},
    "default": {"primary": "Mixed Soil", "expansion_potential": "Low-Moderate", "description": "Mixed soil composition. Foundation risk varies by specific location.", "foundation_impact": "Standard foundation practices generally adequate"},
}


def _determine_climate_zone(state):
    for zone_name, zone_data in CLIMATE_ZONES.items():
        if state in zone_data.get("states", []):
            return zone_name
    return "moderate"


def _determine_flood_zone(zip_code, state):
    seed = _deterministic_hash(zip_code)
    coastal_states = {"FL", "TX", "LA", "MS", "AL", "GA", "SC", "NC", "VA", "MD", "DE", "NJ", "NY", "CT", "RI", "MA", "NH", "ME", "CA", "OR", "WA", "HI", "AK"}
    if state in coastal_states:
        zone_weights = ["X", "X", "X", "X", "AE", "A", "VE", "X", "X", "X"]
    else:
        zone_weights = ["X", "X", "X", "X", "X", "X", "X", "X", "X", "B"]
    idx = seed % len(zone_weights)
    return zone_weights[idx]


def _determine_seismic_zone(state):
    for zone, data in USGS_SEISMIC_DATA.items():
        if state in data["states"]:
            return zone
    return "Low"


def _determine_wildfire_risk(state):
    for zone, data in CAL_FIRE_WILDFIRE_DATA.items():
        if state in data["states"]:
            return zone
    return "Low"


def _determine_soil_type(state):
    soil = USDA_SOIL_DATA.get(state, USDA_SOIL_DATA["default"])
    return soil["primary"]


def _calculate_soil_expansion_risk(soil_type, foundation):
    base_risk = 20
    soil_lower = soil_type.lower()
    if "expansive" in soil_lower or "clay" in soil_lower:
        base_risk += 40
    if "caliche" in soil_lower:
        base_risk += 30
    if "slab" in foundation.lower():
        base_risk += 15
    elif "pier" in foundation.lower():
        base_risk -= 10
    elif "basement" in foundation.lower():
        base_risk += 5
    return min(100, max(0, base_risk))


def _estimate_flood_insurance_cost(flood_zone, state):
    zone_data = FEMA_FLOOD_ZONE_DATA.get(flood_zone, FEMA_FLOOD_ZONE_DATA["X"])
    base_cost = zone_data["avg_flood_insurance"]
    state_mults = {"FL": 1.4, "LA": 1.3, "TX": 1.1, "CA": 1.2, "NY": 1.15}
    return round(base_cost * state_mults.get(state, 1.0), 0)


def assess_environmental_risks(property_data, findings):
    state = property_data.get("state", "")
    zip_code = property_data.get("zip_code", "")
    address = property_data.get("address", "")
    year_built = property_data.get("year_built", 2000)
    foundation = property_data.get("foundation_type", "").lower()

    climate_zone = _determine_climate_zone(state)
    flood_zone = _determine_flood_zone(zip_code, state)
    seismic_zone = _determine_seismic_zone(state)
    wildfire_risk = _determine_wildfire_risk(state)
    soil_type = _determine_soil_type(state)

    risks = []
    current_year = datetime.now().year

    flood_data = FEMA_FLOOD_ZONE_DATA.get(flood_zone, FEMA_FLOOD_ZONE_DATA["X"])
    if flood_zone not in ["X", "B"]:
        flood_insurance = _estimate_flood_insurance_cost(flood_zone, state)
        risks.append({
            "risk_type": "Flood Zone",
            "risk_level": "HIGH",
            "risk_score": 85,
            "description": f"Property located in FEMA Flood Zone {flood_zone}. {flood_data['description']}",
            "insurance_impact": flood_insurance,
            "annual_flood_insurance": flood_insurance,
            "estimated_cost": 15000,
            "mitigation_recommendation": "Obtain flood insurance quote immediately. Consider sump pump, backflow preventer, and grading adjustments.",
            "climate_zone": climate_zone,
            "flood_zone": flood_zone,
            "seismic_zone": seismic_zone,
            "wildfire_risk": wildfire_risk,
            "source": "FEMA NFHL flood zone data pattern",
            "mandatory_insurance": flood_data["insurance_required"],
        })

    seismic_data = USGS_SEISMIC_DATA.get(seismic_zone, USGS_SEISMIC_DATA["Low"])
    if seismic_zone in ["High", "Very High"]:
        earthquake_insurance = 800 if seismic_zone == "High" else 1500
        risks.append({
            "risk_type": "Seismic Activity",
            "risk_level": "HIGH",
            "risk_score": 78,
            "description": f"Property in {seismic_zone} seismic zone. PGA: {seismic_data['pga']}. {seismic_data['description']}",
            "insurance_impact": earthquake_insurance,
            "estimated_cost": 10000,
            "mitigation_recommendation": f"Earthquake insurance strongly recommended. Retrofit priority: {seismic_data['retrofit_priority']}. Consider bolting, cripple wall bracing, and cripple wall bracing for older homes.",
            "climate_zone": climate_zone,
            "flood_zone": flood_zone,
            "seismic_zone": seismic_zone,
            "wildfire_risk": wildfire_risk,
            "source": "USGS National Seismic Hazard Model",
            "pga_value": seismic_data["pga"],
        })

    wildfire_data = CAL_FIRE_WILDFIRE_DATA.get(wildfire_risk, CAL_FIRE_WILDFIRE_DATA["Low"])
    if wildfire_risk in ["Very High", "High", "Moderate"]:
        risks.append({
            "risk_type": "Wildfire",
            "risk_level": "HIGH" if wildfire_risk in ["Very High", "High"] else "MEDIUM",
            "risk_score": 82 if wildfire_risk == "Very High" else 70 if wildfire_risk == "High" else 55,
            "description": f"Property in {wildfire_risk} wildfire risk area. {wildfire_data['description']}",
            "insurance_impact": wildfire_data["insurance_impact"],
            "estimated_cost": 5000,
            "mitigation_recommendation": f"Create defensible space ({wildfire_data['defensible_space_ft']}ft minimum). Ensure ember-resistant vents. Annual vegetation management.",
            "climate_zone": climate_zone,
            "flood_zone": flood_zone,
            "seismic_zone": seismic_zone,
            "wildfire_risk": wildfire_risk,
            "source": "CAL FIRE / NFIRMS wildfire risk data pattern",
            "annual_risk_pct": wildfire_data["annual_risk_pct"],
        })

    if climate_zone:
        zone_data = CLIMATE_ZONES.get(climate_zone, {})
        zone_risks = zone_data.get("risks", [])
        if "mold" in zone_risks:
            moisture_findings = [f for f in findings if any(w in f.get("description", "").lower() for w in ["moisture", "mold", "damp", "water"])]
            if moisture_findings:
                risks.append({
                    "risk_type": "Mold/Moisture (Climate-Aggravated)",
                    "risk_level": "HIGH",
                    "risk_score": 75,
                    "description": f"Climate zone ({climate_zone}) increases mold/moisture risk. {len(moisture_findings)} inspection finding(s) related to moisture.",
                    "insurance_impact": 1200,
                    "estimated_cost": 5000,
                    "mitigation_recommendation": "Address moisture sources immediately. Install dehumidifier. Ensure proper ventilation in attic and crawl space.",
                    "climate_zone": climate_zone,
                    "flood_zone": flood_zone,
                    "seismic_zone": seismic_zone,
                    "wildfire_risk": wildfire_risk,
                })
        if "termite" in zone_risks:
            risks.append({
                "risk_type": "Termite/Pest",
                "risk_level": "MEDIUM",
                "risk_score": 55,
                "description": f"Climate zone ({climate_zone}) has elevated termite activity. Annual termite inspection recommended.",
                "insurance_impact": 200,
                "estimated_cost": 3000,
                "mitigation_recommendation": "Schedule annual termite inspection. Ensure proper wood-to-soil clearance around foundation.",
                "climate_zone": climate_zone,
                "flood_zone": flood_zone,
                "seismic_zone": seismic_zone,
                "wildfire_risk": wildfire_risk,
            })
        if "ice_dam" in zone_risks:
            risks.append({
                "risk_type": "Ice Dam/Freeze Damage",
                "risk_level": "MEDIUM",
                "risk_score": 50,
                "description": f"Climate zone ({climate_zone}) prone to ice dams and freeze damage. Ensure adequate attic insulation and ventilation.",
                "insurance_impact": 400,
                "estimated_cost": 2000,
                "mitigation_recommendation": "Verify attic insulation R-value meets code (R-49+). Install ice and water shield on roof edges. Ensure gutters are clear.",
                "climate_zone": climate_zone,
                "flood_zone": flood_zone,
                "seismic_zone": seismic_zone,
                "wildfire_risk": wildfire_risk,
            })

    if "foundation" in foundation or "basement" in foundation or "slab" in foundation:
        risks.append({
            "risk_type": "Ground Water/Foundation",
            "risk_level": "MEDIUM",
            "risk_score": 45,
            "description": f"Property has {foundation} foundation. Soil type: {soil_type}. Monitor for water intrusion, settling, and structural movement.",
            "insurance_impact": 300,
            "estimated_cost": 8000,
            "mitigation_recommendation": "Ensure proper grading (6 inches drop over 10 feet). Maintain gutters and downspouts directed away from foundation.",
            "climate_zone": climate_zone,
            "flood_zone": flood_zone,
            "seismic_zone": seismic_zone,
            "wildfire_risk": wildfire_risk,
        })

    soil_expansion_risk = _calculate_soil_expansion_risk(soil_type, foundation)
    if soil_expansion_risk > 50:
        soil_info = USDA_SOIL_DATA.get(state, USDA_SOIL_DATA["default"])
        risks.append({
            "risk_type": "Expansive Soil",
            "risk_level": "MEDIUM",
            "risk_score": soil_expansion_risk,
            "description": f"Area soil type ({soil_type}) has {soil_info['expansion_potential']} expansion potential. {soil_info['description']}",
            "insurance_impact": 500,
            "estimated_cost": 12000,
            "mitigation_recommendation": f"Foundation impact: {soil_info['foundation_impact']}. Monitor foundation for new cracks annually. Maintain consistent moisture levels.",
            "climate_zone": climate_zone,
            "flood_zone": flood_zone,
            "seismic_zone": seismic_zone,
            "wildfire_risk": wildfire_risk,
            "source": "USDA NRCS Web Soil Survey data pattern",
        })

    if year_built and (current_year - year_built) > 40:
        risks.append({
            "risk_type": "Aging Infrastructure",
            "risk_level": "MEDIUM",
            "risk_score": 40,
            "description": f"Property is approximately {current_year - year_built} years old. Higher probability of systemic failures across multiple systems.",
            "insurance_impact": 600,
            "estimated_cost": 5000,
            "mitigation_recommendation": "Comprehensive system-by-system assessment recommended. Budget for phased replacements.",
            "climate_zone": climate_zone,
            "flood_zone": flood_zone,
            "seismic_zone": seismic_zone,
            "wildfire_risk": wildfire_risk,
        })

    risks.sort(key=lambda x: x["risk_score"], reverse=True)
    total_insurance_impact = sum(r["insurance_impact"] for r in risks)
    total_estimated_cost = sum(r["estimated_cost"] for r in risks)
    overall_risk = "LOW"
    if any(r["risk_level"] == "HIGH" for r in risks):
        overall_risk = "HIGH"
    elif any(r["risk_level"] == "MEDIUM" for r in risks):
        overall_risk = "MEDIUM"

    return {
        "risks": risks,
        "summary": {
            "total_risks_identified": len(risks),
            "high_risks": len([r for r in risks if r["risk_level"] == "HIGH"]),
            "medium_risks": len([r for r in risks if r["risk_level"] == "MEDIUM"]),
            "low_risks": len([r for r in risks if r["risk_level"] == "LOW"]),
            "total_insurance_impact": round(total_insurance_impact, 0),
            "total_estimated_mitigation_cost": round(total_estimated_cost, 0),
            "overall_risk_level": overall_risk,
            "climate_zone": climate_zone,
            "flood_zone": flood_zone,
            "seismic_zone": seismic_zone,
            "wildfire_risk": wildfire_risk,
            "soil_type": soil_type,
            "climate_insurance_multiplier": CLIMATE_ZONES.get(climate_zone, {}).get("insurance_mult", 1.0),
        },
        "detailed_profiles": {
            "flood": FEMA_FLOOD_ZONE_DATA.get(flood_zone, {}),
            "seismic": USGS_SEISMIC_DATA.get(seismic_zone, {}),
            "wildfire": CAL_FIRE_WILDFIRE_DATA.get(wildfire_risk, {}),
            "soil": USDA_SOIL_DATA.get(state, USDA_SOIL_DATA["default"]),
        },
    }


def generate_climate_risk_profile(property_data):
    state = property_data.get("state", "")
    climate_zone = _determine_climate_zone(state)
    zone_data = CLIMATE_ZONES.get(climate_zone, {})
    return {
        "climate_zone": climate_zone,
        "zone_description": climate_zone.replace("_", " ").title(),
        "primary_risks": zone_data.get("risks", []),
        "insurance_multiplier": zone_data.get("insurance_mult", 1.0),
        "recommended_insurance_types": _get_recommended_insurance(climate_zone),
        "resiliency_recommendations": _get_resiliency_tips(climate_zone),
    }


def _get_recommended_insurance(climate_zone):
    insurance_map = {
        "hot_humid": ["Standard Homeowner's", "Flood Insurance", "Windstorm", "Hurricane"],
        "extremely_hot_arid": ["Standard Homeowner's", "Earthquake", "Wildfire"],
        "temperate": ["Standard Homeowner's", "Wildfire (if applicable)", "Earthquake (if applicable)"],
        "cold_harsh": ["Standard Homeowner's", "Flood (if applicable)", "Earthquake (if applicable)"],
        "moderate": ["Standard Homeowner's", "Flood (if applicable)", "Earthquake (if applicable)"],
    }
    return insurance_map.get(climate_zone, ["Standard Homeowner's"])


def _get_resiliency_tips(climate_zone):
    tips_map = {
        "hot_humid": [
            "Install hurricane shutters or impact-resistant windows",
            "Ensure roof-to-wall connections meet current wind code",
            "Install sump pump with battery backup",
            "Maintain dehumidifier in crawl space",
            "Annual termite inspection",
        ],
        "extremely_hot_arid": [
            "Install UV-resistant roofing materials",
            "Ensure adequate attic insulation (R-38+)",
            "Maintain irrigation to prevent soil shrinkage",
            "Install reflective window film",
            "Monitor stucco for thermal cracking",
        ],
        "temperate": [
            "Maintain defensible space around property (wildfire zones)",
            "Ensure proper attic ventilation",
            "Annual gutter cleaning",
            "Seal foundation cracks to prevent water intrusion",
        ],
        "cold_harsh": [
            "Maintain attic insulation R-value (R-49+)",
            "Install heat tape on roof edges",
            "Winterize outdoor faucets and irrigation",
            "Install ice and water shield on roof",
            "Maintain furnace and chimney annually",
        ],
        "moderate": [
            "Annual HVAC maintenance",
            "Monitor foundation for settling",
            "Maintain proper grading away from foundation",
            "Test radon levels every 2 years",
        ],
    }
    return tips_map.get(climate_zone, tips_map["moderate"])
