"""
Environmental Risk Engine (VERIFIED REBUILD)
============================================
Real risk data from:
- US Census Geocoder (address -> lat/lon), only resolves real addresses
- USGS Earthquake catalog + faultlinemap.com seismic data
- FEMA National Flood Hazard Layer (multi-host retry; honest UNAVAILABLE on failure)
- Open-Meteo real climate

No fabricated flood zones or seismic values.
"""

import logging
from datetime import datetime

from engines.real_data_fetcher import (
    geocode_address,
    geocode_zip,
    get_flood_zone_by_coords,
    get_recent_earthquakes,
    get_seismic_hazard_by_coords,
    get_weather,
)

logger = logging.getLogger(__name__)


def assess_environmental_risks(property_data, findings):
    street = property_data.get("address", "")
    city = property_data.get("city", "")
    zip_code = property_data.get("zip_code", "")
    state = property_data.get("state", "")
    address = ", ".join([p for p in [street, city, state, zip_code] if p])

    geo = None
    if address:
        geo = geocode_address(address)
    elif zip_code:
        geo = geocode_zip(zip_code)

    location = geo

    coords = None
    if location:
        coords = (location.get("lat"), location.get("lon"))

    flood = get_flood_zone_by_coords(*coords) if coords else None
    seismic = get_seismic_hazard_by_coords(*coords) if coords else None
    quakes = get_recent_earthquakes(*coords, radius_km=75) if coords else None
    weather = get_weather(*coords) if coords else None

    flood_val = (flood.value or {}) if flood else {}
    seismic_val = (seismic.value or {}) if seismic else {}
    quake_val = (quakes.value or {}) if quakes else {}
    weather_val = (weather.value or {}) if weather else {}

    findings_risk = _categorize_finding_risks(findings)

    geo_src = (
        "US Census Geocoder (matched address)"
        if geo and geo.get("matched_address")
        else "No geocoding source configured"
    )
    return {
        "address_resolved": location is not None,
        "geocoding": {
            "status": "VERIFIED" if geo else "UNAVAILABLE",
            "source": geo_src,
            "coords": coords,
            "matched_address": location.get("matched_address", "") if geo else "",
            "county": location.get("county", "") if geo else "",
        },
        "flood": {
            "status": flood.provenance.status if flood else "UNAVAILABLE",
            "source": flood.provenance.source if flood else "",
            "zone": flood_val.get("zone"),
            "risk_level": _flood_level(flood_val.get("zone")),
            "fema_url": flood_val.get("url") if flood_val.get("zone") else "",
        },
        "seismic": {
            "status": seismic.provenance.status if seismic else "UNAVAILABLE",
            "source": seismic.provenance.source if seismic else "",
            "sds": seismic_val.get("sds"),
            "sd1": seismic_val.get("sd1"),
            "pga": seismic_val.get("pga"),
            "hazard_level": seismic_val.get("hazard_level"),
            "risk_level": _seismic_level(seismic_val),
        },
        "earthquakes": {
            "status": quakes.provenance.status if quakes else "UNAVAILABLE",
            "count_75km_1yr": quake_val.get("total_count") if quake_val else 0,
            "largest_magnitude": quake_val.get("max_magnitude") if quake_val else None,
            "nearest_fault": seismic_val.get("nearest_fault"),
        },
        "weather": {
            "status": weather.provenance.status if weather else "UNAVAILABLE",
            "temperature_f": weather_val.get("temperature_f"),
            "precipitation_inches": weather_val.get("precipitation_inches"),
            "wind_mph": weather_val.get("wind_mph"),
            "conditions": weather_val.get("conditions"),
        },
        "finding_derived_risks": findings_risk,
        "summary_level": _overall_risk(flood_val, seismic_val, findings_risk),
        "generated_at": datetime.now().isoformat(),
    }


def _categorize_finding_risks(findings):
    risks = {"mold_moisture": 0, "foundation": 0, "fire": 0, "electrical": 0, "other": 0}
    for f in findings:
        sys = (f.get("system_category") or "").upper()
        desc = (f.get("description") or "").lower()
        if "mold" in desc or sys in ("MOISTURE",):
            risks["mold_moisture"] += 1
        elif sys in ("STRUCTURAL",):
            risks["foundation"] += 1
        elif sys in ("FIRE_SAFETY", "HVAC") and "gas" in desc:
            risks["fire"] += 1
        elif sys in ("ELECTRICAL",):
            risks["electrical"] += 1
    return risks


def _flood_level(zone):
    if not zone:
        return "UNKNOWN"
    if zone in ("A", "AE", "A1-A30", "AH", "AO", "AR", "V", "VE", "V1-V30"):
        return "HIGH (FEMA SFHA)"
    if zone in ("B", "C", "X", "X500"):
        return "LOW/MODERATE"
    return f"UNCLASSIFIED ({zone})"


def _seismic_level(s):
    if not s:
        return "UNKNOWN"
    sds = s.get("sds") or 0
    if sds >= 0.5:
        return "HIGH"
    if sds >= 0.25:
        return "MODERATE"
    return "LOW"


def _overall_risk(flood_val, seismic_val, finding_risks):
    score = 0
    if flood_val.get("zone") in ("A", "AE", "V", "VE"):
        score += 3
    sds = (seismic_val or {}).get("Sds") or 0
    if sds >= 0.5:
        score += 2
    if finding_risks["foundation"]:
        score += 1
    if finding_risks["mold_moisture"]:
        score += 1
    if score >= 4:
        return "HIGH"
    if score >= 2:
        return "MODERATE"
    return "LOW"


def generate_climate_risk_profile(property_data):
    zip_code = property_data.get("zip_code", "")
    address = property_data.get("address", "")
    city = property_data.get("city", "")
    state = property_data.get("state", "")
    full = ", ".join([p for p in [address, city, state, zip_code] if p])
    geo = geocode_address(full) if full else geocode_zip(zip_code)
    loc = geo
    weather = get_weather(loc["lat"], loc["lon"]) if loc else None
    w = weather.value if weather else {}
    return {
        "zip_code": zip_code,
        "status": weather.provenance.status if weather else "UNAVAILABLE",
        "source": weather.provenance.source if weather else "",
        "current": {
            "temperature_f": w.get("temperature_f"),
            "wind_mph": w.get("wind_mph"),
            "precipitation_inches": w.get("precipitation_inches"),
            "conditions": w.get("conditions"),
        },
        "notes": ["Real-time conditions from Open-Meteo."],
    }
