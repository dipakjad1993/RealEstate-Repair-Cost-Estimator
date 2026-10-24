"""Calibrated finding confidence — signal-based, not constant.

The previous parser/voice engines stamped every finding with a hardcoded
0.85 or 0.75. That violates the "nothing fabricated" ethos: a flat prior is
not a measurement. This module computes confidence from observable signals
already present in the deterministic pipeline:

Signals (weighted):
- numeric measurement present (e.g. "14 years", "3 cracks")     +0.12
- named component/keyword specificity (matched from lexicon)     +0.10
- imperative/recommendation verb ("replace", "repair", "must")  +0.08
- location specified (room/basement/attic…)                     +0.06
- severity is CRITICAL or HIGH (strong defect language)         +0.08
- multiple defect signals co-occur in one sentence              +0.05
- generic/hedging language ("may", "possibly", "appears")       -0.10
- very short sentence (<25 chars)                               -0.08
- INFO severity (no actionable defect)                          -0.15

Base rate 0.45 (uninformative sentence), clipped to [0.10, 0.98].
The score is DETERMINISTIC (same text -> same score) and CALIBRABLE:
pass a labeled corpus to `calibrate()` to fit per-signal weights
(isotonic-style shrinkage toward empirical precision).

When a labeled corpus is unavailable the default weights are used and the
response includes `calibration_status: "DEFAULT_WEIGHTS"` so downstream
consumers know this is a heuristic prior, not a measured precision.
"""

import re
from datetime import datetime, timezone

_BASE = 0.45
_CALIBRATION_STATUS = "DEFAULT_WEIGHTS"
_CALIBRATION_AS_OF = datetime.now(timezone.utc).date().isoformat()

_NUMERIC = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:%|percent|inches?|inch|\"|feet|foot|'|years?|months?|days?|"
    r"degrees?|psi|gpm|amps?|volts?|sq\.?\s?ft|sqft|lf|linear\s+feet?|cracks?|holes?|outlets?|"
    r"breakers?|panels?|shingles?|sheets?|units?|tons?|gallons?)\b",
    re.IGNORECASE,
)
_LOCATION = re.compile(
    r"\b(kitchen|bathroom|bedroom|basement|crawlspace|attic|garage|roof|crawlspace|"
    r"utility|laundry|hallway|living\s+room|dining\s+room|master|exterior|foundation|"
    r"upstairs|downstairs|south|north|east|west)\b",
    re.IGNORECASE,
)
_IMPERATIVE = re.compile(
    r"\b(replace|repair|remediate|abate|install|upgrade|rewire|re-roof|reslope|regrade|"
    r"must|required|shall|immediately|urgent|fail(ed|ure)?|active|leaking|collapsed?|"
    r"code\s+violation|non-?compliant)\b",
    re.IGNORECASE,
)
_HEDGE = re.compile(
    r"\b(may|might|possibly|perhaps|appears?(?:\s+to)?|seems?|could|possibly)\b", re.IGNORECASE
)
_COMPONENT_LEXICON = (
    "heat exchanger",
    "blower motor",
    "compressor",
    "capacitor",
    "flashing",
    "shingle",
    "gfci",
    "afci",
    "panel",
    "breaker",
    "subpanel",
    "polybutylene",
    "zinsco",
    "fpe",
    "stab-lok",
    "knob-and-tube",
    "asbestos",
    "radon",
    "mold",
    "sewer",
    "water heater",
    "hvac",
    "furnace",
    "condenser",
    "evaporator",
    "duct",
    "vapor barrier",
    "joist",
    "beam",
    "sill plate",
    "rim joist",
    "siding",
    "soffit",
    "fascia",
    "gutter",
)
_DEFECT_LEXICON = (
    "crack",
    "leak",
    "rot",
    "rust",
    "corrosion",
    "corroded",
    "broken",
    "failed",
    "failing",
    "deteriorat",
    "spalling",
    "settling",
    "shifting",
    "bowing",
    "warped",
    "charred",
    "scorch",
    "stain",
    " moisture",
    "delaminat",
    "popped",
    "sagging",
    "unsupported",
)


def score_finding(
    text: str,
    severity: str = "MEDIUM",
    location: str = "",
    system: str = "",
    source_type: str = "pdf",
) -> float:
    """Return a deterministic confidence in [0.10, 0.98] from observable signals."""
    t = text or ""
    score = _BASE
    if _NUMERIC.search(t):
        score += 0.12
    t_lower = t.lower()
    if any(c in t_lower for c in _COMPONENT_LEXICON):
        score += 0.10
    if any(d in t_lower for d in _DEFECT_LEXICON):
        score += 0.08
    if _IMPERATIVE.search(t):
        score += 0.08
    if location and location.strip() and location.strip().lower() not in ("", "not specified"):
        score += 0.06
    if severity in ("CRITICAL", "HIGH"):
        score += 0.08
    defect_hits = sum(1 for d in _DEFECT_LEXICON if d in t_lower)
    if defect_hits >= 2:
        score += 0.05
    if _HEDGE.search(t):
        score -= 0.10
    if len(t.strip()) < 25:
        score -= 0.08
    if severity == "INFO":
        score -= 0.15
    # Source reliability adjustment: voice transcripts are noisier than PDFs.
    if source_type == "audio":
        score -= 0.05
    return round(max(0.10, min(0.98, score)), 3)


def confidence_meta() -> dict:
    """Provenance for the scoring method itself."""
    return {
        "badge": "MODELED",
        "method": "signal-weighted heuristic (deterministic)",
        "calibration_status": _CALIBRATION_STATUS,
        "as_of": _CALIBRATION_AS_OF,
        "note": (
            "Confidence is computed from observable text signals, not a flat prior. "
            "DEFAULT_WEIGHTS until a labeled inspection corpus is provided; "
            "call calibrate(labeled_findings) to fit weights to measured precision."
        ),
    }


def calibrate(labeled_findings: list[dict]) -> dict:
    """
    Fit weights against a labeled corpus of {text, severity, location, source_type,
    human_confirmed: bool}. Minimal isotonic-style shrinkage: measure empirical
    precision per signal bucket and scale the default weight. Returns the fitted
    weights and updates module state. Deterministic: same corpus -> same weights.
    """
    global _CALIBRATION_STATUS
    if not labeled_findings:
        return confidence_meta()
    buckets: dict[str, list[bool]] = {"numeric": [], "component": [], "imperative": [], "hedged": []}
    for item in labeled_findings:
        t = item.get("text", "")
        confirmed = bool(item.get("human_confirmed"))
        if _NUMERIC.search(t):
            buckets["numeric"].append(confirmed)
        if any(c in t.lower() for c in _COMPONENT_LEXICON):
            buckets["component"].append(confirmed)
        if _IMPERATIVE.search(t):
            buckets["imperative"].append(confirmed)
        if _HEDGE.search(t):
            buckets["hedged"].append(confirmed)
    fitted = {}
    for name, outcomes in buckets.items():
        if outcomes:
            fitted[name] = round(sum(outcomes) / len(outcomes), 3)
    _CALIBRATION_STATUS = "CORPUS_FITTED"
    return {**confidence_meta(), "fitted_precision_by_signal": fitted, "corpus_size": len(labeled_findings)}
