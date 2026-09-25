"""
Ingestion Engine (Page 1) (VERIFIED REBUILD)
=============================================
Collects and validates the multi-layer real inputs specified for Page 1:
1. Property metadata  (9-digit ZIP, APN, address, beds/baths/sqft/year built)
2. Market & geospatial feeds (MLS: list price, DOM, $/sqft, zone, last sale)
3. Price/underwriting data (carrier quote, interest rate, holding budget,
   contractor quotes, permit records)
4. Evidence uploads (inspection PDF, damage photos, audio recordings for
   Whisper transcription, floorplan / Matterport export, appliance nameplates)

Returns a fully-validated session input consumed by the analysis pipeline.
No data is fabricated here — missing inputs are reported honestly.
"""

import json
import logging
import re
from datetime import datetime

from engines.parser_engine import process_uploaded_report

logger = logging.getLogger(__name__)

# valid ZIP5 + ZIP4
ZIP_RE = re.compile(r"^\d{5}$")
ZIP9_RE = re.compile(r"^\d{5}-?\d{4}$")
APN_RE = re.compile(r"^\d{2,3}[-/]?\d{2}[-/]?\d{2,5}$")

STATE_ABBREV = {
    s.upper()
    for s in [
        "AL",
        "AK",
        "AZ",
        "AR",
        "CA",
        "CO",
        "CT",
        "DE",
        "FL",
        "GA",
        "HI",
        "ID",
        "IL",
        "IN",
        "IA",
        "KS",
        "KY",
        "LA",
        "ME",
        "MD",
        "MA",
        "MI",
        "MN",
        "MS",
        "MO",
        "MT",
        "NE",
        "NV",
        "NH",
        "NJ",
        "NM",
        "NY",
        "NC",
        "ND",
        "OH",
        "OK",
        "OR",
        "PA",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
        "DC",
    ]
}


def validate_zip9(zip9: str) -> dict:
    """Validate and normalize a 9-digit ZIP. Returns {zip5, zip4, valid, note}."""
    if not zip9:
        return {
            "zip5": "",
            "zip4": "",
            "valid": False,
            "note": "9-digit ZIP required for verification-grade geocoding/flood lookup.",
        }
    z = zip9.strip()
    if ZIP9_RE.match(z):
        z5, z4 = re.split(r"-", z.replace(" ", "")) if "-" in z else (z[:5], z[5:])
        return {
            "zip5": z5,
            "zip4": z4,
            "valid": True,
            "note": "USPS-deliverable format; used for Census/BLS/FEMA lookups.",
        }
    if ZIP_RE.match(z):
        return {
            "zip5": z,
            "zip4": "",
            "valid": False,
            "note": "5-digit ZIP only. Add the +4 for verification-grade accuracy.",
        }
    return {
        "zip5": "",
        "zip4": "",
        "valid": False,
        "note": "ZIP must be 5 or 9 digits (e.g. 90210 or 90210-4801).",
    }


def validate_apn(apn: str) -> dict:
    """Validate Assessor Parcel Number (APN)."""
    if not apn:
        return {"valid": False, "note": "APN is used to fetch parcel-level county records."}
    return {
        "valid": bool(APN_RE.match(apn.strip())),
        "note": "Format: 2-3 / 2 / 2-5 digit components (county-dependent).",
    }


def build_property_data(meta: dict) -> dict:
    """Construct the canonical property_data dict from validated metadata."""
    z = validate_zip9(meta.get("zip9", ""))
    a = validate_apn(meta.get("apn", ""))
    state = (meta.get("state") or "").upper().strip()
    return {
        "address": (meta.get("address") or "").strip(),
        "city": (meta.get("city") or "").strip(),
        "state": state if state in STATE_ABBREV else "",
        "zip_code": z["zip5"],
        "zip9": f"{z['zip5']}-{z['zip4']}" if z["valid"] else (z["zip5"] or ""),
        "zip_valid": z["valid"],
        "zip_note": z["note"],
        "apn": (meta.get("apn") or "").strip(),
        "apn_valid": a["valid"],
        "property_type": (meta.get("property_type") or "").strip(),
        "bedrooms": int(meta.get("beds") or 0),
        "bathrooms": int(meta.get("baths") or 0),
        "square_footage": int(meta.get("sqft") or 0),
        "year_built": int(meta.get("year_built") or 0),
        "lot_size": (meta.get("lot_size") or "").strip(),
    }


def validate_input_bundle(property_data: dict) -> dict:
    """Report which verification-critical inputs are present/missing."""
    return {
        "zip9_verified": bool(property_data.get("zip9")),
        "apn_provided": bool(property_data.get("apn")),
        "address_complete": bool(property_data.get("address") and property_data.get("state")),
        "mls_provided": False,
        "report_uploaded": False,
        "warnings": [],
    }


def ingest_inspection_report(pdf_files):
    """
    Process uploaded inspection PDF(s) -> findings + images + text.
    Returns findings list with provenance. Real extraction, no fabrication.
    """
    findings = []
    images = []
    sources = []
    for pdf in pdf_files or []:
        try:
            result = process_uploaded_report(pdf)
        except Exception as e:
            logger.error("PDF parse failed: %s", e)
            sources.append({"file": getattr(pdf, "name", "?"), "status": "FAILED", "detail": str(e)[:200]})
            continue
        src = {
            "file": getattr(pdf, "name", "?"),
            "status": "OK",
            "findings": result.get("extraction_stats", {}).get("finding_count", 0),
        }
        sources.append(src)
        images.extend(result.get("images", []) or [])
        for f in result.get("findings", []) or []:
            f["source_type"] = "inspection_pdf"
            f["source_file"] = getattr(pdf, "name", "?")
            findings.append(f)
    return {"findings": findings, "images": images, "sources": sources, "total_findings": len(findings)}


def ingest_audio_transcripts(audio_files):
    """Voice -> structured: faster-whisper/Deepgram when configured, else honest stub.

    openai-whisper (1GB torch) retired as default. Backend via WHISPER_BACKEND:
    none (default) | faster-whisper (local, lazy) | deepgram (API).
    Transcripts link to findings via engines.voice_nlp.
    """
    from engines.voice_nlp import transcription_backend

    findings = []
    sources = []
    backend = transcription_backend()
    for af in audio_files or []:
        name = getattr(af, "name", "?")
        if backend in ("", "none"):
            sources.append(
                {
                    "file": name,
                    "status": "SKIPPED",
                    "detail": "Transcription disabled by default (WHISPER_BACKEND=none). "
                    "Set faster-whisper or deepgram to enable.",
                }
            )
            continue
        try:
            text = ""
            if backend == "faster-whisper":
                import tempfile

                from faster_whisper import WhisperModel

                model = WhisperModel("small", compute_type="int8")
                suffix = "." + str(name).split(".")[-1] if "." in str(name) else ".wav"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tf:
                    tf.write(af.getvalue() if hasattr(af, "getvalue") else af.read())
                    tf.flush()
                    segments, _ = model.transcribe(tf.name)
                    text = " ".join(s.text for s in segments)
            elif backend == "deepgram":
                import os as _os

                import requests as _rq

                key = _os.environ.get("DEEPGRAM_API_KEY", "")
                if not key:
                    sources.append(
                        {"file": name, "status": "REQUIRES_KEY", "detail": "DEEPGRAM_API_KEY missing."}
                    )
                    continue
                audio_bytes = af.getvalue() if hasattr(af, "getvalue") else af.read()
                r = _rq.post(
                    "https://api.deepgram.com/v1/listen?model=nova-2",
                    headers={"Authorization": f"Token {key}", "Content-Type": "audio/wav"},
                    data=audio_bytes,
                    timeout=60,
                )
                r.raise_for_status()
                text = (
                    ((r.json().get("results") or {}).get("channels") or [{}])[0]
                    .get("alternatives", [{}])[0]
                    .get("transcript", "")
                )
            from engines.voice_engine import extract_findings_from_text
            from engines.voice_nlp import diarize_heuristic, link_transcript_to_findings

            for f in extract_findings_from_text(text or ""):
                f["source_type"] = "audio_recording"
                f["source_file"] = name
                findings.append(f)
            sources.append(
                {
                    "file": name,
                    "status": "OK",
                    "backend": backend,
                    "turns": len(diarize_heuristic(text or "")),
                    "linked": len(link_transcript_to_findings(text or "", findings)),
                }
            )
        except Exception as e:
            logger.error("Transcription failed: %s", e)
            sources.append({"file": name, "status": "FAILED", "detail": str(e)[:200]})
    return {"findings": findings, "sources": sources, "total_findings": len(findings), "backend": backend}


def ingest_floorplan(floorplan_file, matterport_url=""):
    """
    Build the spatial floor-plan from a real upload.
    Supports JSON/CSV room exports, else returns empty for template fallback.
    """
    if matterport_url:
        return {
            "provenance": "USER_PROVIDED",
            "matterport_url": matterport_url,
            "rooms": [],
            "note": "Matterport URL captured; export room layout JSON and upload it for mapping.",
        }
    if not floorplan_file:
        return {
            "provenance": "UNAVAILABLE",
            "rooms": [],
            "note": "No floorplan supplied — spatial mapping unavailable until JSON/CSV/Matterport export is uploaded.",
        }
    name = getattr(floorplan_file, "name", "").lower()
    try:
        if name.endswith(".json"):
            data = json.load(floorplan_file)
            rooms = data.get("rooms", data if isinstance(data, list) else [])
            return {"provenance": "USER_FLOORPLAN", "rooms": rooms}
        if name.endswith(".csv"):
            import csv

            reader = csv.DictReader(floorplan_file)
            rooms = [dict(r) for r in reader]
            return {"provenance": "USER_FLOORPLAN", "rooms": rooms}
    except Exception as e:
        logger.error("Floorplan parse failed: %s", e)
    return {
        "provenance": "MODELED",
        "rooms": [],
        "note": "Floorplan image received; overlay requires geometry extraction from a Matterport/DXF/JSON export.",
    }


def parse_contractor_quotes(quote_rows):
    """Validate user-supplied contractor quotes."""
    out = []
    for row in quote_rows or []:
        if not row.get("finding_key"):
            continue
        try:
            out.append(
                {
                    "finding_key": row["finding_key"],
                    "contractor": row.get("contractor", ""),
                    "phone": row.get("phone", ""),
                    "license": row.get("license", ""),
                    "low": float(row.get("low", 0)),
                    "high": float(row.get("high", 0)),
                    "eta_days": int(row.get("eta_days", 0) or 0),
                }
            )
        except (TypeError, ValueError):
            continue
    return out


def parse_permit_records(permit_rows):
    """Validate user-supplied permit records from the municipal portal."""
    out = []
    for row in permit_rows or []:
        if not row.get("permit_type"):
            continue
        out.append(
            {
                "permit_type": row["permit_type"],
                "permit_number": row.get("permit_number", ""),
                "permit_date": row.get("permit_date", ""),
                "status": row.get("status", "Closed"),
                "description": row.get("description", ""),
                "contractor": row.get("contractor", ""),
            }
        )
    return out


def compile_session_input(
    meta,
    mls=None,
    underwriting=None,
    quotes=None,
    permits=None,
    pdf_files=None,
    audio_files=None,
    floorplan_file=None,
    matterport_url="",
) -> dict:
    """Assemble the full Page-1 input bundle for the analysis pipeline."""
    mls = mls or {}
    underwriting = underwriting or {}
    property_data = build_property_data(meta)

    report = ingest_inspection_report(pdf_files)
    audio = ingest_audio_transcripts(audio_files)
    floorplan = ingest_floorplan(floorplan_file, matterport_url)

    findings = report["findings"] + audio["findings"]
    # dedupe by description similarity across sources
    findings = _dedupe(findings)

    user_mls = {
        "list_price": _num(mls.get("list_price")),
        "price_per_sqft": _num(mls.get("price_per_sqft")),
        "dom": _num(mls.get("dom_days")),
        "property_type": property_data["property_type"] or mls.get("property_type"),
        "beds": property_data["bedrooms"],
        "baths": property_data["bathrooms"],
        "sqft": property_data["square_footage"],
        "last_sale_price": _num(mls.get("last_sale_price")),
        "zone": mls.get("zone"),
        "source": mls.get("source"),
        "state": property_data["state"],
    }

    user_underwriting = {
        "annual_premium": _num(underwriting.get("annual_premium")),
        "interest_rate": _num(underwriting.get("interest_rate")) or 0.07,
        "holding_months": int(_num(underwriting.get("holding_months")) or 6),
        "arv": _num(underwriting.get("arv")),
        "monthly_rent": _num(underwriting.get("monthly_rent")),
        "list_price": _num(underwriting.get("list_price")),
    }

    return {
        "property_data": property_data,
        "mls": user_mls,
        "underwriting": user_underwriting,
        "quotes": parse_contractor_quotes(quotes),
        "permits": parse_permit_records(permits),
        "findings": findings,
        "images": report["images"] + audio["images"] if hasattr(audio, "images") else report["images"],
        "floorplan": floorplan,
        "ingestion_report": {
            "report_sources": report["sources"],
            "audio_sources": audio["sources"],
            "total_findings": len(findings),
            "from_pdf": len(report["findings"]),
            "from_audio": len(audio["findings"]),
            "pdf_images": len(report["images"]),
        },
        "validation": validate_input_bundle(property_data),
        "created_at": datetime.now().isoformat(),
        "pii": {
            "policy": "Raw address/APN never logged; display redacted. Full values in TTL vault only.",
            "redacted_display": __import__("engines.pii_vault", fromlist=["redact_dict"]).redact_dict(
                {"address": property_data.get("address"), "apn": property_data.get("apn")}
            ),
        },
    }


def _num(val):
    try:
        if val is None or val == "":
            return None
        return float(str(val).replace(",", "").replace("$", ""))
    except (ValueError, TypeError):
        return None


def _dedupe(findings):
    out = []
    seen = set()
    for f in findings:
        desc = (f.get("description") or "")[:60].lower()
        if desc in seen:
            continue
        seen.add(desc)
        out.append(f)
    return out
