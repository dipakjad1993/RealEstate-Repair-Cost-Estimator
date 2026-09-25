"""FastAPI backend: agent-ready estimate API + share portal + OpenAPI (enterprise).

Run: uvicorn api_server:app --port 8000
Docs: /docs  OpenAPI: /api/openapi.json  Share: /s/{token}
"""

import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from engines.pii_vault import redact_dict
from engines.rate_limit import GLOBAL_LIMITER
from engines.share_engine import open_snapshot, seal_snapshot

API_KEY = os.environ.get("API_KEY", "")

app = FastAPI(
    title="Repair Estimator API",
    version="3.1.0",
    description="Provenance-tracked repair estimates. Every figure carries VERIFIED/USER_PROVIDED/MODELED/REQUIRES_KEY/UNAVAILABLE.",
)


class EstimateRequest(BaseModel):
    address: str = ""
    city: str = ""
    state: str = Field(default="", max_length=2)
    zip_code: str = ""
    sqft: float = 1500
    year_built: int = 1995
    findings: list[dict[str, Any]] = []
    list_price: float | None = None
    comps: list[dict[str, Any]] = []


def _auth(authorization: str = ""):
    if API_KEY and authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="invalid API key")


@app.get("/api/openapi.json")
def openapi_json():
    return JSONResponse(app.openapi())


@app.get("/llms.txt")
def llms_txt():
    return HTMLResponse(
        "# Repair Estimator\n"
        "> Provenance-tracked repair estimates from verified gov data.\n\n"
        "## API\n- POST /api/estimate_repair {address, state, zip_code, findings[]}\n"
        "- GET /s/{token} lender share portal\n- GET /api/health\n\n"
        "## Provenance badges\nVERIFIED USER_PROVIDED MODELED REQUIRES_KEY UNAVAILABLE\n"
        "## Rules\n- MODELED figures are deterministic estimates, not quotes.\n"
        "- USER_QUOTE rows are authoritative.\n",
        media_type="text/plain",
    )


@app.get("/api/health")
def health():
    try:
        from engines.gov_sources_v2 import detailed_health

        return detailed_health()
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


@app.post("/api/estimate_repair")
def estimate_repair(req: EstimateRequest, authorization: str = Header(default="")):
    _auth(authorization)
    if not GLOBAL_LIMITER.allow(authorization or "anon"):
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    from engines.comps_engine import estimate_arv
    from engines.cost_engine import generate_cost_matrix
    from engines.room_engine import rate_rooms

    cm = generate_cost_matrix(
        [
            {
                "description": f.get("description", ""),
                "severity": f.get("severity", "MEDIUM"),
                "system_category": f.get("system", "OTHER"),
                "key": f.get("description", ""),
            }
            for f in req.findings
        ],
        req.state,
        req.zip_code,
        [],
        None,
    )
    cost_by = {
        it.get("finding_key", it.get("finding", "")): {
            "low": it.get("total_low", 0),
            "mid": it.get("total_avg", 0),
            "high": it.get("total_high", 0),
        }
        for it in cm.get("line_items", [])
    }
    rooms = rate_rooms(
        [
            {
                "description": f.get("description", ""),
                "severity": f.get("severity", "MEDIUM"),
                "system_category": f.get("system", "OTHER"),
                "location": f.get("room", "General"),
                "key": f.get("description", ""),
            }
            for f in req.findings
        ],
        cost_by,
    )
    arv = estimate_arv(req.comps, subject_sqft=req.sqft, list_price=req.list_price)
    snapshot = {
        "totals": cm.get("summary", {}),
        "rooms": rooms,
        "arv": arv,
        "provenance": "pipeline: VERIFIED baselines + MODELED assembly",
    }
    token = seal_snapshot(
        redact_dict(
            {
                "zip": req.zip_code,
                "state": req.state,
                "totals": cm.get("summary", {}),
                "rooms": rooms,
                "arv": arv,
            }
        )
    )
    return {
        "totals": cm.get("summary", {}),
        "rooms": rooms,
        "arv": arv,
        "share_token": token,
        "provenance": snapshot["provenance"],
    }


@app.get("/s/{token}", response_class=HTMLResponse)
def share_portal(token: str):
    snap = open_snapshot(token)
    if not snap:
        raise HTTPException(status_code=404, detail="share link invalid or expired")
    totals = snap.get("totals") or {}
    rows = "".join(
        f"<tr><td>{r.get('room')}</td><td>{r.get('condition')}</td><td>{r.get('priority')}</td>"
        f"<td>${r.get('low', 0):,.0f}–${r.get('high', 0):,.0f}</td></tr>"
        for r in snap.get("rooms", [])
    )
    return (
        f"<html><head><title>Lender package</title></head><body style='font-family:Inter,Arial'>"
        f"<h1>Repair estimate — lender package</h1>"
        f"<p>Total avg ${totals.get('total_avg', 0):,.0f} · Range ${totals.get('total_low', 0):,.0f}–${totals.get('total_high', 0):,.0f}</p>"
        f"<table border=1 cellpadding=6><tr><th>Room</th><th>Condition</th><th>Priority</th><th>Range</th></tr>{rows}</table>"
        f"<p>Provenance: VERIFIED baselines + MODELED assembly. Not a quote.</p></body></html>"
    )
