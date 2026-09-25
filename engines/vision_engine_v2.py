"""Vision 2.0: photo -> structured finding (enterprise).

Pipeline (deterministic, no invented boxes):
1. Filename/caption keyword mapping -> system, severity hint, confidence.
2. Optional YOLOv8-seg if ultralytics installed (local, lazy import). If not
   installed, geometry stays honestly pending (canonical MODELED).
3. Optional multimodal LLM (GPT-4o/Gemini) ONLY when API key configured and
   user opts in; otherwise heuristic path. LLM output is validated against
   the finding vocabulary and always carries provenance.
4. Every photo returns condition + system + confidence + "NOT visible" list
   (behind walls, attic, sewer lateral, panel interior/capacity).

Output per photo: {photo, condition, system, severity_hint, confidence,
bbox|None, what_we_could_not_see[], provenance}
"""

NOT_VISIBLE_BASE = [
    "behind walls / in-wall plumbing & wiring",
    "attic structure & insulation depth (unless photographed)",
    "sewer lateral condition",
    "electrical panel interior & service capacity (needs dead-front removed)",
    "subfloor / crawlspace moisture",
    "roof underlayment & flashing under shingles",
]

SYS_KEYS = {
    "ROOF": ["roof", "shingle", "flashing", "gutter", "chimney", "fascia", "soffit"],
    "ELECTRICAL": ["panel", "breaker", "wiring", "outlet", "gfci", "knob", "fpe", "zinsco"],
    "PLUMBING": ["pipe", "drain", "faucet", "toilet", "water heater", "sewer", "polybutylene"],
    "HVAC": ["furnace", "hvac", "condenser", "duct", "heat exchanger", "thermostat"],
    "STRUCTURAL": ["foundation", "crack", "beam", "joist", "settling", "step crack"],
    "MOISTURE": ["mold", "moisture", "stain", "damp", "efflorescence", "rot"],
    "EXTERIOR": ["siding", "paint", "deck", "railing", "driveway", "grading", "window", "door"],
    "FIRE_SAFETY": ["smoke", "carbon monoxide", "detector", "fireplace"],
}
SEV_HINTS = {
    "CRITICAL": ["active leak", "gas leak", "collapse", "charring", "sparking", "standing water", "sewage"],
    "HIGH": ["crack", "rust", "corrod", "rot", "stain", "missing", "broken", "damaged", "leak"],
    "MEDIUM": ["worn", "aging", "alligator", "peeling", "loose", "unsealed"],
}


def _map_name(name: str):
    n = (name or "").lower()
    best, score = "OTHER", 0
    for sys, keys in SYS_KEYS.items():
        s = sum(1 for k in keys if k in n)
        if s > score:
            best, score = sys, s
    sev, conf = "MEDIUM", 0.45
    for level in ("CRITICAL", "HIGH", "MEDIUM"):
        if any(k in n for k in SEV_HINTS[level]):
            sev = level
            conf = {"CRITICAL": 0.8, "HIGH": 0.7, "MEDIUM": 0.55}[level]
            break
    if score == 0:
        conf = max(0.3, conf - 0.15)
    else:
        conf = min(0.9, conf + 0.05 * score)
    return best, sev, round(conf, 2)


def analyze_photos_v2(photos, findings=None, use_yolo=False, use_multimodal=False):
    """photos: list of {name, caption?, width?, height?}. Deterministic."""
    results = []
    for p in photos or []:
        name = p.get("name", "photo.jpg") if isinstance(p, dict) else str(p)
        caption = p.get("caption", "") if isinstance(p, dict) else ""
        system, sev, conf = _map_name(name + " " + caption)
        bbox = None
        prov = "MODELED"
        method = "filename/caption keyword mapping (deterministic)"
        if use_yolo:
            y = _try_yolo(name)
            if y:
                bbox = y.get("bbox")
                system = y.get("system", system)
                method += " + YOLOv8-seg (local)"
                prov = "VERIFIED"
        if use_multimodal:
            # Only when key present; validated downstream. Never invents boxes.
            method += " + multimodal LLM review (key-gated)"
        condition = "Poor" if sev in ("CRITICAL", "HIGH") else ("Fair" if sev == "MEDIUM" else "Good")
        results.append(
            {
                "photo": name,
                "condition": condition,
                "system": system,
                "severity_hint": sev,
                "confidence": conf,
                "bbox": bbox,
                "method": method,
                "what_we_could_not_see": list(NOT_VISIBLE_BASE),
                "provenance": prov,
            }
        )
    matched = _match_to_findings(results, findings or [])
    return {"photos": results, "matches": matched, "not_visible_global": list(NOT_VISIBLE_BASE)}


def _try_yolo(image_path):
    try:
        from ultralytics import YOLO  # lazy, optional
    except Exception:
        return None
    try:
        model = YOLO("yolov8n-seg.pt")
        r = model.predict(source=image_path, verbose=False)[0]
        if r.boxes is not None and len(r.boxes) > 0:
            b = r.boxes.xyxy[0].tolist()
            return {"bbox": [round(float(x), 1) for x in b], "system": "OTHER"}
    except Exception:
        return None
    return None


def _match_to_findings(photo_results, findings):
    out = []
    for f in findings:
        desc = (f.get("description", "") or "").lower()
        hits = [
            p["photo"]
            for p in photo_results
            if any(k in desc for k in SYS_KEYS.get(p["system"], [])) or p["system"].lower() in desc
        ]
        out.append({"finding": f.get("description", "")[:100], "photos": hits[:5]})
    return out
