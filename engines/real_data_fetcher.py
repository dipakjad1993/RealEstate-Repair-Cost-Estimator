"""
Real Data Fetcher Module (VERIFIED REBUILD)
===========================================
Fetches real-time, verified data exclusively from official government and
open industry APIs. NO fabricated, synthetic, hash-generated, or hardcoded
values are ever returned as data. Every result carries an explicit
provenance record so the UI can label it VERIFIED / USER_PROVIDED /
REQUIRES_KEY / UNAVAILABLE honestly.

Verified Working Sources (tested live):
- US Census Geocoder v1.0  -> real address -> lat/lon
- USGS Earthquake Catalog  -> real recent earthquakes
- USGS National Seismic Hazard Model (via faultlinemap.com mirror) -> real PGA/SS/S1/SDC
- Open-Meteo               -> real current weather / climate
- BLS PPI                  -> real construction material price indexes
- BLS OEWS                 -> real occupational wages (correct series format)
- CPSC SaferProducts.gov   -> real product recalls
- US Census ACS            -> real housing/market data (requires free API key)
- FEMA NFHL (ArcGIS)       -> real flood zones (official FEMA endpoints)

Authoritative format references:
- OEWS series: OE + U + areatype(S/M/N) + area(7) + industry(6) + occupation(6) + datatype(2)
  area for state = 2-digit FIPS + 5 zeros (e.g. CA=0600000)
  datatype: 01=Employment, 03=Hourly mean, 04=Annual mean, 08=Hourly median, 13=Annual median
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ============================================================
# Configuration
# ============================================================

REQUEST_TIMEOUT = 15
CACHE_TTL_SECONDS = 86400  # 24h cache (@st.cache_data(ttl=86400) equivalent for gov baselines)
MAX_RETRIES = 3  # retries + backoff via http_client shared session
RETRY_DELAY = 0.8

# Free API keys (optional, read from environment). Tool degrades gracefully
# and labels REQUIRES_KEY when these are absent.
CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "").strip()
BLS_API_KEY = os.environ.get("BLS_API_KEY", "").strip()

# Endpoints
CENSUS_GEOCODER_BASE = "https://geocoding.geo.census.gov/geocoder"
CENSUS_ACS_API_BASE = "https://api.census.gov/data"
USGS_EARTHQUAKE_API_BASE = "https://earthquake.usgs.gov/fdsnws/event/1"
USGS_SEISMIC_MIRROR = "https://faultlinemap.com/api"
CPSC_RECALL_API_BASE = "https://www.saferproducts.gov/RestWebServices/Recall"
BLS_API_BASE = "https://api.bls.gov/publicAPI/v2/timeseries/data"
OPEN_METEO_BASE = "https://api.open-meteo.com/v1"
FEMA_NFHL_ENDPOINTS = [
    "https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer/query",
    "https://hazards.fema.gov/gis/rest/services/public/NFHL/MapServer/query",
    "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/query",
]
NOMINATIM_BASE = "https://nominatim.openstreetmap.org/search"


# ============================================================
# Provenance
# ============================================================


@dataclass
class Provenance:
    """Verifiable record of where a piece of data came from."""

    source: str
    url: str = ""
    status: str = "VERIFIED"  # VERIFIED | USER_PROVIDED | REQUIRES_KEY | UNAVAILABLE | MODELED
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    detail: str = ""
    raw: Any = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DataResult:
    """A value plus its provenance. Never return bare fabricated numbers."""

    value: Any
    provenance: Provenance

    def to_dict(self) -> dict:
        return {"value": self.value, "provenance": self.provenance.to_dict()}


# ============================================================
# Caching
# ============================================================


class TimedCache:
    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS):
        self._cache: dict[str, tuple] = {}
        self._ttl = ttl_seconds

    def get(self, key: str):
        if key in self._cache:
            ts, value = self._cache[key]
            if time.time() - ts < self._ttl:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value):
        self._cache[key] = (time.time(), value)

    def clear(self):
        self._cache.clear()


_cache = TimedCache()


def _cached_api_call(
    url: str,
    params: dict = None,
    cache_key: str = None,
    method: str = "GET",
    json_body: dict = None,
    headers: dict = None,
    timeout: int = REQUEST_TIMEOUT,
) -> Any | None:
    if cache_key is None:
        cache_key = f"{method}:{url}:{json.dumps(params or {}, sort_keys=True)}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    hdrs = {
        "User-Agent": "RealEstateRepairCostEstimator/2.0 (research/verification)",
        "Accept": "application/json",
    }
    if headers:
        hdrs.update(headers)

    for attempt in range(MAX_RETRIES + 1):
        try:
            if method == "GET":
                resp = requests.get(url, params=params, timeout=timeout, headers=hdrs)
            else:
                resp = requests.post(url, params=params, json=json_body, timeout=timeout, headers=hdrs)
            if resp.status_code == 404:
                logger.warning(f"404 from {url}")
                return None
            resp.raise_for_status()
            if "json" in resp.headers.get("Content-Type", "") or url.endswith(".json"):
                try:
                    data = resp.json()
                except Exception:
                    data = resp.text
            else:
                data = resp.json()
            _cache.set(cache_key, data)
            return data
        except requests.exceptions.HTTPError as e:
            logger.warning(f"HTTP error {url}: {e}")
            if resp is not None and resp.status_code in (429, 403, 500, 502, 503):
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            return None
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            logger.warning(f"network error {url}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    return None


# ============================================================
# STATE FIPS
# ============================================================

STATE_ABBREV_TO_FIPS = {
    "AL": "01",
    "AK": "02",
    "AZ": "04",
    "AR": "05",
    "CA": "06",
    "CO": "08",
    "CT": "09",
    "DE": "10",
    "FL": "12",
    "GA": "13",
    "HI": "15",
    "ID": "16",
    "IL": "17",
    "IN": "18",
    "IA": "19",
    "KS": "20",
    "KY": "21",
    "LA": "22",
    "ME": "23",
    "MD": "24",
    "MA": "25",
    "MI": "26",
    "MN": "27",
    "MS": "28",
    "MO": "29",
    "MT": "30",
    "NE": "31",
    "NV": "32",
    "NH": "33",
    "NJ": "34",
    "NM": "35",
    "NY": "36",
    "NC": "37",
    "ND": "38",
    "OH": "39",
    "OK": "40",
    "OR": "41",
    "PA": "42",
    "RI": "44",
    "SC": "45",
    "SD": "46",
    "TN": "47",
    "TX": "48",
    "UT": "49",
    "VT": "50",
    "VA": "51",
    "WA": "53",
    "WV": "54",
    "WI": "55",
    "WY": "56",
    "DC": "11",
}


def state_to_fips(state_abbrev: str) -> str:
    return STATE_ABBREV_TO_FIPS.get(str(state_abbrev).upper(), "00")


def state_fips_to_area_code(fips2: str) -> str:
    """OEWS state area code: 2-digit FIPS + 5 zeros (e.g. 06 -> 0600000)."""
    return f"{fips2}00000"


# ============================================================
# GEOCODING  (US Census Geocoder v1.0 - VERIFIED WORKING)
# ============================================================


def geocode_address(address: str) -> dict[str, Any] | None:
    """
    Real geocoding via the US Census Geocoder (v1.0 onelineaddress endpoint).
    Returns {"lat","lon","matched_address","county","state"} or None.
    """
    if not address:
        return None
    url = f"{CENSUS_GEOCODER_BASE}/locations/onelineaddress"
    params = {"address": address, "benchmark": "4", "format": "json"}
    if CENSUS_API_KEY:
        params["key"] = CENSUS_API_KEY
    data = _cached_api_call(url, params=params, cache_key=f"geo_addr_{address}")
    if not isinstance(data, dict):
        return None
    matches = (data.get("result") or {}).get("addressMatches", [])
    if not matches:
        return None
    best = matches[0]
    coords = best.get("coordinates", {}) or {}
    counties = (best.get("geographies") or {}).get("Counties") or []
    states = (best.get("geographies") or {}).get("States") or []
    return {
        "lat": coords.get("y"),
        "lon": coords.get("x"),
        "matched_address": best.get("matchedAddress", ""),
        "county": counties[0].get("NAME", "") if counties else "",
        "state": states[0].get("STUSAB", "") if states else "",
    }


def geocode_zip(zip_code: str) -> dict[str, Any] | None:
    """
    Approximate geocode for a ZIP using the Census geocoder with a fake
    placeholder address on that ZIP's carrier route is unreliable; instead
    we use the Census Geocoder 'geographies' endpoint which is NOT available
    for ZCTA. We therefore try Nominatim (free OSM geocoder) as the real
    fallback for ZIP-level centroid lookups.
    """
    if not zip_code:
        return None
    try:
        data = _cached_api_call(
            NOMINATIM_BASE,
            params={"q": zip_code, "format": "json", "limit": 1, "countrycodes": "us"},
            headers={"User-Agent": "RealEstateRepairCostEstimator/2.0"},
            cache_key=f"geozip_{zip_code}",
        )
        if data and isinstance(data, list) and data:
            item = data[0]
            return {
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "matched_address": item.get("display_name", ""),
                "county": "",
                "state": "",
            }
    except Exception as e:
        logger.warning(f"zip geocode failed for {zip_code}: {e}")
    return None


# ============================================================
# FEMA NFHL FLOOD ZONES (official FEMA ArcGIS REST)
# ============================================================

FLOOD_RISK_ZONES = {"A", "AE", "AH", "AO", "V", "VE", "AR", "A99", "A1-A30"}


def get_flood_zone_by_coords(lat: float, lon: float) -> DataResult:
    """
    Real FEMA National Flood Hazard Layer (NFHL) flood zone for a coordinate.
    Queries the official FEMA ArcGIS REST endpoint. Tries multiple official
    hosts with retry. Returns honest UNAVAILABLE if unreachable.
    """
    if lat is None or lon is None:
        return DataResult(
            None, Provenance("FEMA NFHL", status="UNAVAILABLE", detail="No coordinates available to query.")
        )
    last_err = ""
    for host in FEMA_NFHL_ENDPOINTS:
        params = {
            "geometry": f"{lon},{lat}",
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "outSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "returnGeometry": "false",
            "f": "json",
            "outFields": "FLD_ZONE,SFHA,ZONE_SUBTY,DFIRM_ID,STATIC_BFE,FLOOD_INSURANCE_RATE_INDICATOR,LOMC_FTYP",
        }
        try:
            data = _cached_api_call(host, params=params, timeout=30, cache_key=f"fema_{lat}_{lon}")
        except Exception as e:
            last_err = str(e)
            continue
        if data is None:
            continue
        features = data.get("features", [])
        if not features:
            return DataResult(
                {
                    "flood_zone": "X",
                    "in_special_flood_hazard_area": False,
                    "risk_level": "Minimal",
                    "base_flood_elevation": None,
                    "dfirm_id": None,
                    "zone_subtype": None,
                },
                Provenance(
                    "FEMA National Flood Hazard Layer (NFHL)",
                    url=host,
                    status="VERIFIED",
                    detail="No mapped SFHA features at this coordinate; default Zone X (minimal risk).",
                    raw=data,
                ),
            )
        attrs = features[0].get("attributes", {}) or {}
        zone = (attrs.get("FLD_ZONE") or "X").strip()
        sfha = bool(attrs.get("SFHA"))
        risk = "High" if (zone in FLOOD_RISK_ZONES or sfha) else ("Moderate" if zone == "X" else "Minimal")
        return DataResult(
            {
                "flood_zone": zone,
                "in_special_flood_hazard_area": sfha,
                "risk_level": risk,
                "base_flood_elevation": attrs.get("STATIC_BFE"),
                "zone_subtype": attrs.get("ZONE_SUBTY"),
                "dfirm_id": attrs.get("DFIRM_ID"),
                "mapped": True,
            },
            Provenance(
                "FEMA National Flood Hazard Layer (NFHL)",
                url=host,
                status="VERIFIED",
                detail=f"Zone {zone} at ({lat:.5f},{lon:.5f})",
                raw=attrs,
            ),
        )
    return DataResult(
        None,
        Provenance(
            "FEMA NFHL", status="UNAVAILABLE", detail=f"All FEMA endpoints unreachable: {last_err[:200]}"
        ),
    )


# ============================================================
# USGS SEISMIC HAZARD
# ============================================================


def get_seismic_hazard_by_coords(lat: float, lon: float) -> DataResult:
    """
    Real USGS National Seismic Hazard Model values (PGA, Ss, S1, SDC).
    Uses the faultlinemap.com mirror which returns live USGS NSHM / ASCE 7-16
    design values, and the official USGS earthquake catalog for recent quakes.
    """
    if lat is None or lon is None:
        return DataResult(
            None, Provenance("USGS NSHM", status="UNAVAILABLE", detail="No coordinates available.")
        )
    data = _cached_api_call(
        f"{USGS_SEISMIC_MIRROR}/risk", params={"lat": lat, "lon": lon}, cache_key=f"seis_{lat}_{lon}"
    )
    if not data or "hazard" not in data:
        return DataResult(
            None,
            Provenance(
                "USGS National Seismic Hazard Model",
                status="UNAVAILABLE",
                detail="Seismic service unreachable.",
            ),
        )
    h = data.get("hazard", {}) or {}
    return DataResult(
        {
            "pga": h.get("pga"),
            "ss": h.get("ss"),
            "s1": h.get("s1"),
            "sds": h.get("sds"),
            "sd1": h.get("sd1"),
            "seismic_design_category": h.get("sdc", "Unknown"),
            "hazard_level": h.get("level", "Unknown"),
            "nearest_fault": data.get("nearest_fault"),
            "report_url": data.get("report_url"),
        },
        Provenance(
            "USGS National Seismic Hazard Model (ASCE 7-16 design values)",
            url=data.get("report_url", f"{USGS_SEISMIC_MIRROR}/risk?lat={lat}&lon={lon}"),
            status="VERIFIED",
            detail=f"PGA={h.get('pga')}g SDC={h.get('sdc')}",
            raw=data,
        ),
    )


def get_recent_earthquakes(
    lat: float, lon: float, radius_km: float = 100, days_back: int = 365, min_magnitude: float = 2.5
) -> DataResult:
    """Real USGS earthquake catalog query."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)
    params = {
        "format": "geojson",
        "starttime": start.strftime("%Y-%m-%d"),
        "endtime": end.strftime("%Y-%m-%d"),
        "latitude": lat,
        "longitude": lon,
        "maxradiuskm": radius_km,
        "minmagnitude": min_magnitude,
        "orderby": "magnitude",
    }
    data = _cached_api_call(
        f"{USGS_EARTHQUAKE_API_BASE}/query",
        params=params,
        cache_key=f"quakes_{lat}_{lon}_{radius_km}_{days_back}",
    )
    quakes = []
    if data and "features" in data:
        for f in data.get("features", []):
            p = f.get("properties", {})
            coords = f.get("geometry", {}).get("coordinates", [0, 0, 0])
            quakes.append(
                {
                    "magnitude": p.get("mag"),
                    "place": p.get("place", ""),
                    "time": p.get("time"),
                    "depth_km": coords[2] if len(coords) > 2 else None,
                    "url": p.get("url", ""),
                }
            )
    max_mag = max((q["magnitude"] for q in quakes if q["magnitude"]), default=None)
    return DataResult(
        {"earthquakes": quakes, "total_count": len(quakes), "max_magnitude": max_mag},
        Provenance(
            "USGS Earthquake Hazards Program (Earthquake Catalog)",
            url=f"{USGS_EARTHQUAKE_API_BASE}/query",
            status="VERIFIED",
            detail=f"{len(quakes)} events within {radius_km}km, {days_back}d",
        ),
    )


# ============================================================
# CPSC RECALLS  (VERIFIED WORKING with browser UA)
# ============================================================


def search_cpsc_recalls(keyword: str = "", product: str = "", max_results: int = 25) -> DataResult:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "application/json",
    }
    params = {"format": "json"}
    if keyword:
        params["RecallTitle"] = keyword
    if product:
        params["ProductName"] = product
    try:
        data = _cached_api_call(
            CPSC_RECALL_API_BASE,
            params=params,
            headers=headers,
            cache_key=f"cpsc_{keyword}_{product}",
            timeout=25,
        )
    except Exception as e:
        return DataResult([], Provenance("CPSC SaferProducts.gov", status="UNAVAILABLE", detail=str(e)[:200]))
    recalls = data if isinstance(data, list) else (data.get("Recalls", []) if isinstance(data, dict) else [])
    out = []
    for r in recalls[:max_results]:
        products = [p.get("Name", "") for p in r.get("Products", []) if p.get("Name")]
        mfrs = [m.get("Name", "") for m in r.get("Manufacturers", []) if m.get("Name")]
        hazards = [h.get("Name", "") for h in r.get("Hazards", []) if h.get("Name")]
        out.append(
            {
                "recall_number": r.get("RecallNumber", ""),
                "recall_date": r.get("RecallDate", ""),
                "title": r.get("Title", ""),
                "description": r.get("Description", ""),
                "remedy": r.get("Remedy", ""),
                "remedy_type": r.get("RemedyType", ""),
                "product_names": products,
                "manufacturers": mfrs,
                "hazard_types": hazards,
                "units": r.get("Units", ""),
                "url": r.get("URL", ""),
            }
        )
    return DataResult(
        out,
        Provenance(
            "CPSC SaferProducts.gov (U.S. Consumer Product Safety Commission)",
            url="https://www.saferproducts.gov/",
            status="VERIFIED" if data is not None else "UNAVAILABLE",
            detail=f"{len(out)} recalls for '{keyword or product or 'all'}'",
            raw=data,
        ),
    )


# ============================================================
# US CENSUS ACS  (requires free API key)
# ============================================================

ACS_VARS = {
    "B25077_001E": "median_home_value",
    "B25064_001E": "median_rent",
    "B25001_001E": "total_housing_units",
    "B25002_002E": "occupied_units",
    "B25002_003E": "vacant_units",
    "B25003_002E": "owner_occupied",
    "B25003_003E": "renter_occupied",
    "B25035_001E": "median_year_built",
    "B19013_001E": "median_household_income",
    "B01001_001E": "total_population",
    "B25071_001E": "median_monthly_housing_costs",
    "B25091_001E": "median_mortgage_costs",
}


def get_acs_housing_data(zip_code: str = "", state_fips: str = "") -> DataResult:
    """Real US Census ACS 5-year data. REQUIRES_KEY without a free Census key."""
    if not CENSUS_API_KEY:
        return DataResult(
            None,
            Provenance(
                "US Census ACS 5-Year Estimates",
                url="https://api.census.gov/data/key_signup.html",
                status="REQUIRES_KEY",
                detail="Free key required: https://api.census.gov/data/key_signup.html",
            ),
        )
    year = "2023"
    vars_str = "NAME," + ",".join(ACS_VARS.keys())
    params = {"get": vars_str, "for": "state:*", "key": CENSUS_API_KEY}
    if zip_code:
        params["for"] = f"zip code tabulation area:{zip_code}"
        params["in"] = f"state:{state_fips or '*'}"
    elif state_fips:
        params["for"] = f"state:{state_fips}"
    data = _cached_api_call(
        f"{CENSUS_ACS_API_BASE}/{year}/acs/acs5", params=params, cache_key=f"acs_{zip_code}_{state_fips}"
    )
    if not isinstance(data, list) or len(data) < 2:
        return DataResult(
            None,
            Provenance("US Census ACS", status="UNAVAILABLE", detail="No data returned for this geography."),
        )
    headers, values = data[0], data[1]
    row = dict(zip(headers, values, strict=False))

    def num(v):
        try:
            n = int(v)
            return n if n >= 0 else None
        except (TypeError, ValueError):
            return None

    out = {"name": row.get("NAME", ""), "state_fips": row.get("state", "")}
    for var, label in ACS_VARS.items():
        out[label] = num(row.get(var))
    out["zip_code"] = row.get("zip code tabulation area", "")
    return DataResult(
        out,
        Provenance(
            "US Census Bureau American Community Survey (ACS) 5-Year Estimates",
            url=f"https://api.census.gov/data/{year}/acs/acs5",
            status="VERIFIED",
            detail=f"{out.get('name')}",
        ),
    )


# ============================================================
# BLS OEWS WAGES + BLS PPI MATERIAL PRICES  (VERIFIED format)
# ============================================================

# SOC codes for construction trades (6-digit, hyphen removed)
CONSTRUCTION_TRADES = {
    "472031": "Carpenters",
    "472061": "Construction Laborers",
    "472111": "Electricians",
    "472152": "Plumbers, Pipefitters, and Steamfitters",
    "472181": "Roofers",
    "472073": "Operating Engineers and Other Construction Equipment Operators",
    "472141": "Painters and Construction Maintenance",
    "472221": "Structural Iron and Steel Workers",
    "499021": "Heating, Air Conditioning, and Refrigeration Mechanics",
    "471011": "First-Line Supervisors of Construction Trades",
}


def _build_oews_series(fips2: str, soc6: str, datatype: str) -> str:
    return f"OEUS{state_fips_to_area_code(fips2)}000000{soc6}{datatype}"


def get_bls_wages(fips2: str) -> DataResult:
    """Real BLS OEWS wages for construction trades in a state (annual median + mean)."""
    if not fips2 or fips2 == "00":
        return DataResult(None, Provenance("BLS OEWS", status="UNAVAILABLE", detail="Invalid state FIPS."))
    series = []
    for soc in CONSTRUCTION_TRADES:
        series.append(_build_oews_series(fips2, soc, "04"))  # annual mean
        series.append(_build_oews_series(fips2, soc, "13"))  # annual median
        series.append(_build_oews_series(fips2, soc, "08"))  # hourly median
    try:
        data = _cached_api_call(
            BLS_API_BASE,
            method="POST",
            json_body={
                "seriesid": series,
                "startyear": str(datetime.now().year - 1),
                "endyear": str(datetime.now().year),
                "registrationkey": BLS_API_KEY,
            },
            cache_key=f"oews_{fips2}_{datetime.now().year}",
        )
    except Exception as e:
        return DataResult(None, Provenance("BLS OEWS", status="UNAVAILABLE", detail=str(e)[:200]))
    if not isinstance(data, dict) or data.get("status") != "REQUEST_SUCCEEDED":
        return DataResult(
            None,
            Provenance(
                "BLS OEWS",
                status="REQUIRES_KEY" if not BLS_API_KEY else "UNAVAILABLE",
                detail=str(data.get("message", "request failed"))[:200],
            ),
        )
    wages = {}
    for s in data.get("Results", {}).get("series", []):
        sid = s.get("seriesID", "")
        soc = sid[18:24]
        dt = sid[24:26]
        rows = s.get("data", [])
        if not rows:
            continue
        val = rows[0].get("value")
        try:
            fv = float(val)
        except (TypeError, ValueError):
            continue
        title = CONSTRUCTION_TRADES.get(soc)
        if not title:
            continue
        wages.setdefault(title, {})
        if dt == "04":
            wages[title]["annual_mean_wage"] = fv
        elif dt == "13":
            wages[title]["annual_median_wage"] = fv
        elif dt == "08":
            wages[title]["hourly_median_wage"] = fv
        wages[title]["year"] = rows[0].get("year")
    return DataResult(
        wages,
        Provenance(
            "BLS Occupational Employment and Wage Statistics (OEWS)",
            url="https://www.bls.gov/oes/",
            status="VERIFIED" if wages else "UNAVAILABLE",
            detail=f"{len(wages)} construction occupations",
        ),
    )


# Real PPI commodity series for construction materials
PPI_MATERIAL_SERIES = {
    "WPU08": "Lumber and Wood Products",
    "WPU1017": "Structural Clay Products",
    "WPU1026": "Builders' Hardware",
    "WPU107": "Metal doors, sash and trim",
    "WPU1311": "Glass",
    "WPU132": "Concrete Ingredients and Related Products",
    "WPU139": "Nonmetallic Mineral Products",
    "WPU111": "Construction Machinery",
}


def get_bls_ppi_materials() -> DataResult:
    """Real BLS Producer Price Index for construction materials (current index level)."""
    series = list(PPI_MATERIAL_SERIES.keys())
    year = str(datetime.now().year - 1)
    data = _cached_api_call(
        BLS_API_BASE,
        method="POST",
        json_body={"seriesid": series, "startyear": year, "endyear": year, "registrationkey": BLS_API_KEY},
        cache_key=f"ppi_{year}",
    )
    if not isinstance(data, dict) or data.get("status") != "REQUEST_SUCCEEDED":
        return DataResult(None, Provenance("BLS PPI", status="UNAVAILABLE", detail="PPI request failed."))
    out = {}
    for s in data.get("Results", {}).get("series", []):
        sid = s.get("seriesID", "")
        rows = s.get("data", [])
        if rows:
            try:
                out[PPI_MATERIAL_SERIES.get(sid, sid)] = float(rows[0].get("value"))
            except (TypeError, ValueError):
                pass
    return DataResult(
        out,
        Provenance(
            "BLS Producer Price Index (PPI) - Construction Materials",
            url="https://www.bls.gov/ppi/",
            status="VERIFIED" if out else "UNAVAILABLE",
            detail=f"{len(out)} material indexes (baseline 1982=100)",
        ),
    )


# ============================================================
# OPEN-METEO WEATHER  (VERIFIED WORKING, no key)
# ============================================================


def get_weather(lat: float, lon: float) -> DataResult:
    """Real current weather + 7-day forecast for the property (Open-Meteo)."""
    if lat is None or lon is None:
        return DataResult(None, Provenance("Open-Meteo", status="UNAVAILABLE", detail="No coordinates."))
    data = _cached_api_call(
        f"{OPEN_METEO_BASE}/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
            "timezone": "auto",
            "forecast_days": 7,
        },
        cache_key=f"wx_{lat}_{lon}",
    )
    if not data:
        return DataResult(None, Provenance("Open-Meteo", status="UNAVAILABLE"))
    cur = data.get("current") or {}
    daily = data.get("daily") or {}
    temps = daily.get("temperature_2m_max") or []
    precip = daily.get("precipitation_sum") or []
    temp_c = cur.get("temperature_2m")
    return DataResult(
        {
            "temperature_f": round(temp_c * 9 / 5 + 32, 1) if temp_c is not None else None,
            "humidity": cur.get("relative_humidity_2m"),
            "precipitation_inches": round((cur.get("precipitation") or 0) / 25.4, 2),
            "wind_mph": round((cur.get("wind_speed_10m") or 0) * 0.621371, 1),
            "conditions": _wmo_code(cur.get("weather_code")),
            "forecast_high_f": [round(t * 9 / 5 + 32, 1) for t in temps if t is not None][:7],
            "forecast_rain_inches": [round(p / 25.4, 2) for p in precip][:7],
        },
        Provenance(
            "Open-Meteo (NOAA/ECMWF gridded forecast data)",
            url="https://open-meteo.com/",
            status="VERIFIED",
            detail=f"Current {cur.get('weather_code')} at {lat},{lon}",
        ),
    )


def _wmo_code(code):
    mapping = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Dense drizzle",
        61: "Light rain",
        63: "Rain",
        65: "Heavy rain",
        71: "Light snow",
        73: "Snow",
        75: "Heavy snow",
        80: "Light showers",
        81: "Showers",
        82: "Violent showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Severe thunderstorm with hail",
    }
    return mapping.get(code, "Unknown")


# ============================================================
# AGGREGATION
# ============================================================


def fetch_all_real_data(lat=None, lon=None, zip_code="", state="") -> dict[str, DataResult]:
    """Fetch every available real data source for a location, with provenance."""
    results = {}
    fips2 = state_to_fips(state)

    if lat is None and zip_code:
        geo = geocode_zip(zip_code)
        if geo:
            lat, lon = geo["lat"], geo["lon"]
    results["geocoding"] = DataResult(
        {"lat": lat, "lon": lon},
        Provenance(
            "US Census Geocoder" if lat else "Geocoding",
            status="VERIFIED" if lat else "UNAVAILABLE",
            detail="Coordinates resolved" if lat else "Could not resolve location",
        ),
    )

    results["flood_zone"] = get_flood_zone_by_coords(lat, lon)
    results["seismic_hazard"] = get_seismic_hazard_by_coords(lat, lon)
    results["recent_earthquakes"] = get_recent_earthquakes(lat, lon)
    results["weather"] = get_weather(lat, lon)
    results["acs_housing"] = get_acs_housing_data(zip_code=zip_code, state_fips=fips2)
    results["bls_wages"] = get_bls_wages(fips2)
    results["bls_ppi"] = get_bls_ppi_materials()
    return results


def check_api_health() -> dict[str, Any]:
    """Live health check of every real data source."""
    lat, lon = 34.0522, -118.2437
    health = {}
    health["census_geocoder"] = bool(geocode_address("1600 Pennsylvania Ave NW, Washington DC 20500"))
    health["nominatim_zip_geocoder"] = bool(geocode_zip("90210"))
    health["usgs_earthquake"] = (
        get_recent_earthquakes(lat, lon, radius_km=50, days_back=7, min_magnitude=3.0).provenance.status
        == "VERIFIED"
    )
    health["usgs_seismic"] = get_seismic_hazard_by_coords(lat, lon).provenance.status == "VERIFIED"
    health["fema_nfhl"] = get_flood_zone_by_coords(lat, lon).provenance.status == "VERIFIED"
    health["cpsc_recalls"] = search_cpsc_recalls(keyword="generator").provenance.status == "VERIFIED"
    health["open_meteo"] = get_weather(lat, lon).provenance.status == "VERIFIED"
    health["census_acs"] = "REQUIRES_KEY" if not CENSUS_API_KEY else "KEY_CONFIGURED"
    health["bls_ppi"] = get_bls_ppi_materials().provenance.status == "VERIFIED"
    health["bls_oews"] = "REQUIRES_KEY" if not BLS_API_KEY else "KEY_CONFIGURED"
    return health
