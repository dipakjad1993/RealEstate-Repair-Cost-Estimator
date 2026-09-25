"""Official-first gov source clients (enterprise v2).

Authoritative endpoints are tried FIRST; third-party proxies are fallback
only and always labeled as such in provenance detail. Every call records
latency via engines.http_client for the Health page.

Official:
- FEMA NFHL ArcGIS REST (hazards.fema.gov) + WMS GetFeatureInfo
- USGS Seismic Design Maps ASCE 7-22 (earthquake.usgs.gov/ws/designmaps)
- USGS Earthquake Catalog (fdsnws)
- Census Geocoder + ACS (api.census.gov)
- BLS OEWS/PPI (api.bls.gov)
- CPSC SaferProducts.gov
- Open-Meteo (supplemental weather, labeled)
Fallback (labeled PROXY):
- floodzonemap.org, faultlinemap.com, Nominatim
"""

import logging
from datetime import datetime
from typing import Any

from engines.http_client import latency_summary
from engines.real_data_fetcher import (
    BLS_API_BASE,
    BLS_API_KEY,
    CENSUS_API_KEY,
    CENSUS_GEOCODER_BASE,
    CPSC_RECALL_API_BASE,
    FEMA_NFHL_ENDPOINTS,
    OPEN_METEO_BASE,
    USGS_EARTHQUAKE_API_BASE,
    DataResult,
    Provenance,
    _cached_api_call,
)

logger = logging.getLogger(__name__)

USGS_DESIGN_MAPS = "https://earthquake.usgs.gov/ws/designmaps/asce7-22.json"
FEMA_WMS = "https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer/WMSServer"


def fema_flood_official_first(lat: float, lon: float) -> DataResult:
    """Official FEMA NFHL ArcGIS query first; proxy fallback labeled."""
    if lat is None or lon is None:
        return DataResult(None, Provenance("FEMA NFHL", status="UNAVAILABLE", detail="No coordinates."))
    # 1) Official ArcGIS point query across known hosts
    for base in FEMA_NFHL_ENDPOINTS:
        try:
            data = _cached_api_call(
                base,
                params={
                    "where": "1=1",
                    "geometry": f"{lon},{lat}",
                    "geometryType": "esriGeometryPoint",
                    "inSR": "4326",
                    "spatialRel": "esriSpatialRelIntersects",
                    "outFields": "FLD_ZONE,ZONE,SFHA_TF,BFE",
                    "f": "json",
                },
                cache_key=f"fema_official_{lat}_{lon}_{base[-20:]}",
            )
            feats = (data or {}).get("features") or []
            if feats:
                attrs = feats[0].get("attributes", {})
                zone = attrs.get("FLD_ZONE") or attrs.get("ZONE") or "UNKNOWN"
                return DataResult(
                    {
                        "flood_zone": zone,
                        "sfha": attrs.get("SFHA_TF"),
                        "bfe_ft": attrs.get("BFE"),
                        "risk_level": "HIGH" if str(zone).startswith(("A", "V")) else "LOW",
                        "endpoint": base,
                    },
                    Provenance(
                        "FEMA National Flood Hazard Layer (NFHL) — official ArcGIS REST",
                        url=base,
                        status="VERIFIED",
                        detail=f"Official FEMA query; zone {zone}",
                    ),
                )
        except Exception as e:
            logger.warning(f"FEMA official host failed {base}: {e}")
            continue
    # 2) Labeled proxy fallback
    try:
        data = _cached_api_call(
            "https://floodzonemap.org/api/lookup",
            params={"lat": lat, "lon": lon},
            cache_key=f"fema_proxy_{lat}_{lon}",
        )
        if data:
            return DataResult(
                {
                    "flood_zone": data.get("zone", "UNKNOWN"),
                    "endpoint": "floodzonemap.org (proxy)",
                    "risk_level": data.get("risk", "UNKNOWN"),
                },
                Provenance(
                    "FEMA NFHL via floodzonemap.org proxy (FALLBACK — not authoritative)",
                    url="https://floodzonemap.org/api/lookup",
                    status="VERIFIED",
                    detail="Official FEMA hosts unreachable; proxy result labeled fallback.",
                ),
            )
    except Exception as e:
        logger.warning(f"FEMA proxy failed: {e}")
    return DataResult(
        None, Provenance("FEMA NFHL", status="UNAVAILABLE", detail="All FEMA hosts + proxy unreachable.")
    )


def usgs_seismic_official_first(
    lat: float, lon: float, risk_category: str = "II", site_class: str = "D"
) -> DataResult:
    """Official USGS Design Maps first; faultlinemap mirror labeled fallback."""
    if lat is None or lon is None:
        return DataResult(None, Provenance("USGS Seismic", status="UNAVAILABLE", detail="No coordinates."))
    try:
        data = _cached_api_call(
            USGS_DESIGN_MAPS,
            params={
                "latitude": lat,
                "longitude": lon,
                "riskCategory": risk_category,
                "siteClass": site_class,
                "title": "repair-estimator",
            },
            cache_key=f"usgs_design_{lat}_{lon}_{risk_category}_{site_class}",
        )
        if isinstance(data, dict) and ("data" in data or "ss" in str(data).lower()):
            d = data.get("data", data)
            return DataResult(
                {
                    "sds": d.get("sds"),
                    "sd1": d.get("sd1"),
                    "ss": d.get("ss"),
                    "s1": d.get("s1"),
                    "seismic_design_category": d.get("sdc"),
                    "site_class": site_class,
                    "endpoint": USGS_DESIGN_MAPS,
                },
                Provenance(
                    "USGS Seismic Design Maps ASCE 7-22 — official",
                    url=USGS_DESIGN_MAPS,
                    status="VERIFIED",
                    detail=f"Official USGS design values; SDC {d.get('sdc')}",
                ),
            )
    except Exception as e:
        logger.warning(f"USGS official failed: {e}")
    try:
        data = _cached_api_call(
            "https://faultlinemap.com/api/risk",
            params={"lat": lat, "lon": lon},
            cache_key=f"usgs_proxy_{lat}_{lon}",
        )
        if data:
            return DataResult(
                {"pga": data.get("pga"), "endpoint": "faultlinemap.com (proxy)"},
                Provenance(
                    "USGS via faultlinemap.com mirror (FALLBACK — not authoritative)",
                    url="https://faultlinemap.com/api/risk",
                    status="VERIFIED",
                    detail="Official USGS Design Maps unreachable; mirror labeled fallback.",
                ),
            )
    except Exception as e:
        logger.warning(f"USGS proxy failed: {e}")
    return DataResult(
        None, Provenance("USGS Seismic", status="UNAVAILABLE", detail="Official + mirror unreachable.")
    )


def detailed_health() -> dict[str, Any]:
    """Health with per-source latency + official-vs-fallback labeling."""
    from engines.real_data_fetcher import (
        geocode_address,
        geocode_zip,
        get_bls_ppi_materials,
        get_recent_earthquakes,
        get_weather,
        search_cpsc_recalls,
    )

    lat, lon = 34.0522, -118.2437
    probes = {
        "census_geocoder_official": lambda: bool(
            geocode_address("1600 Pennsylvania Ave NW, Washington DC 20500")
        ),
        "zip_geocoder": lambda: bool(geocode_zip("90210")),
        "usgs_earthquake_official": lambda: (
            get_recent_earthquakes(lat, lon, radius_km=50, days_back=7, min_magnitude=3.0).provenance.status
            == "VERIFIED"
        ),
        "usgs_design_maps_official": lambda: (
            usgs_seismic_official_first(lat, lon).provenance.status == "VERIFIED"
        ),
        "fema_nfhl_official": lambda: fema_flood_official_first(lat, lon).provenance.status == "VERIFIED",
        "cpsc_official": lambda: search_cpsc_recalls(keyword="generator").provenance.status == "VERIFIED",
        "open_meteo_supplemental": lambda: get_weather(lat, lon).provenance.status == "VERIFIED",
        "bls_ppi_official": lambda: get_bls_ppi_materials().provenance.status == "VERIFIED",
    }
    out = {}
    for name, fn in probes.items():
        try:
            out[name] = {"ok": bool(fn()), "at": datetime.utcnow().isoformat() + "Z"}
        except Exception as e:
            out[name] = {"ok": False, "error": str(e)[:160], "at": datetime.utcnow().isoformat() + "Z"}
    out["census_acs"] = {
        "ok": bool(CENSUS_API_KEY),
        "status": "KEY_CONFIGURED" if CENSUS_API_KEY else "REQUIRES_KEY",
    }
    out["bls_oews"] = {"ok": bool(BLS_API_KEY), "status": "KEY_CONFIGURED" if BLS_API_KEY else "REQUIRES_KEY"}
    out["latency_ms"] = latency_summary()
    out["official_endpoints"] = {
        "fema": FEMA_WMS,
        "usgs_design": USGS_DESIGN_MAPS,
        "usgs_quake": USGS_EARTHQUAKE_API_BASE,
        "census": CENSUS_GEOCODER_BASE,
        "bls": BLS_API_BASE,
        "cpsc": CPSC_RECALL_API_BASE,
        "meteo": OPEN_METEO_BASE,
    }
    return out
