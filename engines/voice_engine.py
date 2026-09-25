import re
from datetime import datetime

from config import SeverityLevels


def process_audio_transcript(transcript_text, property_id=None):
    findings = extract_findings_from_text(transcript_text)
    return {
        "transcript": transcript_text,
        "findings_extracted": findings,
        "total_findings": len(findings),
        "severity_breakdown": {
            "CRITICAL": len([f for f in findings if f["severity"] == "CRITICAL"]),
            "HIGH": len([f for f in findings if f["severity"] == "HIGH"]),
            "MEDIUM": len([f for f in findings if f["severity"] == "MEDIUM"]),
            "LOW": len([f for f in findings if f["severity"] == "LOW"]),
        },
        "processed_at": datetime.now().isoformat(),
    }


def extract_findings_from_text(text):
    findings = []
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    for sentence in sentences:
        severity = _classify_severity(sentence)
        system = _classify_system(sentence)
        location = _extract_location(sentence)
        if severity in ["CRITICAL", "HIGH", "MEDIUM"] or len(sentence) > 40:
            findings.append(
                {
                    "description": sentence.strip(),
                    "severity": severity,
                    "severity_score": SeverityLevels.get(severity, {}).get("priority", 5),
                    "system_category": system,
                    "location": location,
                    "subsystem": _extract_subcomponent(sentence),
                    "component": system,
                    "source_section": "Audio Transcript",
                    "confidence_score": 0.75,
                    "source_type": "audio",
                }
            )
    return findings


def _classify_severity(text):
    text_lower = text.lower()
    critical_kw = [
        "dangerous",
        "immediate",
        "safety",
        "fire",
        "gas leak",
        "active leak",
        "collapse",
        "hazard",
        "emergency",
        "broken",
        "failing",
    ]
    high_kw = [
        "damaged",
        "rust",
        "corroded",
        "leaking",
        "crack",
        "rot",
        "water damage",
        "code violation",
        "not working",
        "malfunction",
    ]
    medium_kw = [
        "worn",
        "aging",
        "maintenance",
        "recommend",
        "should be",
        "minor",
        "slight",
        "noisy",
        "staining",
    ]
    if any(kw in text_lower for kw in critical_kw):
        return "CRITICAL"
    elif any(kw in text_lower for kw in high_kw):
        return "HIGH"
    elif any(kw in text_lower for kw in medium_kw):
        return "MEDIUM"
    elif len(text_lower) > 30:
        return "LOW"
    return "INFO"


def _classify_system(text):
    text_lower = text.lower()
    system_keywords = {
        "HVAC": [
            "hvac",
            "heating",
            "cooling",
            "air conditioner",
            "furnace",
            "duct",
            "thermostat",
            "heat pump",
        ],
        "ROOF": ["roof", "shingle", "flashing", "gutter", "attic", "soffit", "chimney"],
        "ELECTRICAL": ["electrical", "wiring", "panel", "circuit", "breaker", "gfci", "outlet", "switch"],
        "PLUMBING": ["plumbing", "pipe", "drain", "faucet", "toilet", "sink", "water heater", "sewer"],
        "STRUCTURAL": ["foundation", "crack", "settling", "beam", "structural", "joist"],
        "EXTERIOR": ["siding", "paint", "deck", "railing", "driveway", "grading", "windows", "doors"],
        "INSULATION": ["insulation", "vapor barrier", "attic insulation"],
        "APPLIANCES": ["stove", "oven", "refrigerator", "dishwasher", "washer", "dryer"],
        "FIRE_SAFETY": ["smoke detector", "carbon monoxide", "fireplace", "chimney"],
        "MOISTURE": ["mold", "moisture", "damp", "water stain", "condensation"],
    }
    best_system = "OTHER"
    best_score = 0
    for system, keywords in system_keywords.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > best_score:
            best_score = score
            best_system = system
    return best_system


def _extract_location(text):
    text_lower = text.lower()
    location_patterns = [
        "kitchen",
        "bathroom",
        "bedroom",
        "living room",
        "garage",
        "basement",
        "attic",
        "hallway",
        "dining room",
        "utility",
        "laundry",
        "master bedroom",
    ]
    for loc in location_patterns:
        if loc in text_lower:
            return loc.title()
    return "Not specified"


def _extract_subcomponent(text):
    text_lower = text.lower()
    subcomponents = {
        "heat exchanger": "heat exchanger",
        "blower motor": "blower motor",
        "compressor": "compressor",
        "capacitor": "capacitor",
        "flashing": "flashing",
        "shingle": "shingles",
        "gfci": "GFCI outlet",
        "panel": "electrical panel",
        "pipe": "pipe",
        "drain": "drain",
        "faucet": "faucet",
        "foundation": "foundation",
        "crack": "crack",
        "siding": "siding",
        "paint": "paint",
        "deck": "deck",
        "window": "window",
        "door": "door",
        "insulation": "insulation",
        "mold": "mold",
        "moisture": "moisture",
    }
    for keyword, component in subcomponents.items():
        if keyword in text_lower:
            return component
    return ""


def format_transcript_findings(findings):
    lines = []
    for f in findings:
        severity_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(
            f["severity"], "⚪"
        )
        lines.append(f"{severity_emoji} [{f['severity']}] {f['system_category']}: {f['description'][:120]}")
    return "\n".join(lines)
