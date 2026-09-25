"""Canonical config — thin versioned loader (enterprise).

Cost/config tables live versioned in data/*.json (see data/config_version.json).
This module re-exports the same names the engines import, loaded from JSON
so tables can be refreshed (RSMeans/BLS OEWS/FRED PPI) without code edits.

Full legacy monolith preserved at config.legacy.py for audit diff.
"""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ENGINES_DIR = BASE_DIR / "engines"
UTILS_DIR = BASE_DIR / "utils"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# DB: Postgres/Supabase when configured, sqlite fallback otherwise.
# DB_PATH retained for back-compat (local cache / tests).
DB_PATH = DATA_DIR / "repair_estimator.db"
DATABASE_URL = os.environ.get("DATABASE_URL", os.environ.get("SUPABASE_DB_URL", ""))
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

CONFIG_VERSION_FILE = DATA_DIR / "config_version.json"


def _load(name):
    f = DATA_DIR / f"{name}.json"
    try:
        payload = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload
    except Exception:
        return None


def config_version() -> str:
    try:
        return json.loads(CONFIG_VERSION_FILE.read_text(encoding="utf-8")).get("version", "unknown")
    except Exception:
        return "unknown"


# Versioned datasets (authoritative). Fall back to minimal safe defaults
# so the app boots even if a JSON file is missing.
REGIONS = _load("regions") or {
    "northeast": ["CT", "ME", "MA", "NH", "NJ", "NY", "PA", "RI", "VT"],
    "southeast": ["AL", "AR", "DE", "FL", "GA", "KY", "LA", "MD", "MS", "NC", "SC", "TN", "VA", "WV"],
    "midwest": ["IL", "IN", "IA", "KS", "MI", "MN", "MO", "NE", "ND", "OH", "SD", "WI"],
    "southwest": ["AZ", "NM", "OK", "TX"],
    "west": ["AK", "CA", "CO", "HI", "ID", "MT", "NV", "OR", "UT", "WA", "WY"],
}
STATE_TAX_MULTIPLIERS = _load("state_tax_multipliers") or {"CA": 1.38, "TX": 0.92, "FL": 0.95, "NY": 1.33}
SeverityLevels = _load("severity_levels") or {
    "CRITICAL": {
        "color": "#DC2626",
        "label": "Critical - Safety/Structural",
        "priority": 1,
        "icon": "🔴",
        "bg": "rgba(220,38,38,0.12)",
    },
    "HIGH": {
        "color": "#EA580C",
        "label": "High - Active Damage",
        "priority": 2,
        "icon": "🟠",
        "bg": "rgba(234,88,12,0.12)",
    },
    "MEDIUM": {
        "color": "#CA8A04",
        "label": "Medium - Code/Compliance",
        "priority": 3,
        "icon": "🟡",
        "bg": "rgba(202,138,4,0.12)",
    },
    "LOW": {
        "color": "#16A34A",
        "label": "Low - Maintenance/Cosmetic",
        "priority": 4,
        "icon": "🟢",
        "bg": "rgba(22,163,74,0.12)",
    },
    "INFO": {
        "color": "#2563EB",
        "label": "Informational",
        "priority": 5,
        "icon": "🔵",
        "bg": "rgba(37,99,235,0.12)",
    },
}
SEVERITY_EMOJI = {
    "CRITICAL": "🔴",
    "HIGH": "🟠",
    "MEDIUM": "🟡",
    "LOW": "🟢",
    "INFO": "🔵",
}
DEPRECIATION_TABLES = _load("depreciation_tables") or {}
CLIMATE_ZONES = _load("climate_zones") or {}
INSURANCE_RED_FLAGS = _load("insurance_red_flags") or []
ZIP_COST_MODIFIERS = _load("zip_cost_modifiers") or {}
INSPECTION_SYSTEM_PATTERNS = _load("inspection_system_patterns") or {}
MATERIAL_COSTS_2026 = _load("material_costs_2026") or {}
MUNICIPAL_PERMIT_TYPES = _load("municipal_permit_types") or []

HELP_CONTENT = {}
LEGAL_DISCLAIMER = """
**IMPORTANT DISCLAIMER:** Automated cost estimates for informational purposes only.
Not engineering, legal, financial, or insurance advice. Obtain licensed contractor
estimates and review legal documents with a licensed attorney before deciding.
"""
MARKET_DATA_NOTE = """
**Market Data Note:** Market conditions are modeled from verified anchors (user MLS,
Census ACS) unless live comp enrichment is configured. Verify with your own CMA.
"""

# Official source registry (authoritative endpoints; proxies labeled fallback).
OFFICIAL_SOURCES = {
    "census_geocoder": "https://geocoding.geo.census.gov/geocoder",
    "census_acs": "https://api.census.gov/data",
    "usgs_earthquake": "https://earthquake.usgs.gov/fdsnws/event/1/query",
    "usgs_design_maps": "https://earthquake.usgs.gov/ws/designmaps/asce7-22.json",
    "fema_nfhl_arcgis": "https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer",
    "fema_nfhl_wms": "https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer/WMSServer",
    "bls_oes": "https://www.bls.gov/oes/",
    "bls_api": "https://api.bls.gov/publicAPI/v2/timeseries/data/",
    "cpsc": "https://www.saferproducts.gov/RestWebServices/Recall",
    "open_meteo": "https://api.open-meteo.com/v1/forecast",
}
FALLBACK_SOURCES = {
    # Labeled proxies — never presented as authoritative.
    "flood_proxy": "https://floodzonemap.org/api/lookup",
    "seismic_proxy": "https://faultlinemap.com/api",
    "nominatim_zip": "https://nominatim.openstreetmap.org/search",
}
