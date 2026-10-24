"""MCP server: repair-estimator-mcp — agents call estimate_repair (enterprise v3.4).

Stdio JSON-RPC (MCP-compatible): tools/list + tools/call + resources/list +
resources/read. Agents cite RESOURCES (repair://cost-tables/{zip},
repair://provenance/{estimate_id}); tools are for actions. This follows the
2026 MCP guidance: expose data as resources so citations survive.

Also fixes the rate_rooms(...) call that previously omitted cost_by_finding
(unlike api_server), which produced zero-cost room rows over MCP.
"""

import json
import sys

TOOLS = [
    {
        "name": "estimate_repair",
        "description": "Deterministic repair estimate with provenance badges. Input: address/state/zip/findings[]. Output: totals, line_items (each badged + as_of + source_url), rooms, ARV, share_token.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "address": {"type": "string"},
                "state": {"type": "string"},
                "zip_code": {"type": "string"},
                "sqft": {"type": "number"},
                "findings": {"type": "array", "items": {"type": "object"}},
                "comps": {"type": "array", "items": {"type": "object"}},
                "list_price": {"type": "number"},
            },
        },
    },
    {
        "name": "get_provenance_legend",
        "description": "Return the 5-badge provenance legend and the deterministic-pipeline contract.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

RESOURCES = [
    {
        "uri": "repair://provenance/legend",
        "name": "Provenance badge legend",
        "description": "The 5-badge contract: VERIFIED / USER_PROVIDED / MODELED / REQUIRES_KEY / UNAVAILABLE.",
        "mimeType": "application/json",
    },
    {
        "uri": "repair://cost-tables/{zip}",
        "name": "ZIP cost modifier table",
        "description": "Versioned ZIP-level cost modifier for a ZIP code (MODELED, as_of-stamped).",
        "mimeType": "application/json",
    },
]

PROVENANCE_LEGEND = {
    "VERIFIED": "Live government data (Census/BLS/FEMA/USGS/CPSC/FRED) or evidence-backed user MLS",
    "USER_PROVIDED": "User quotes/MLS/uploads — authoritative, always wins",
    "MODELED": "Deterministic estimate from verified baselines — NOT a quote",
    "REQUIRES_KEY": "Live enrichment available once an API key is configured",
    "UNAVAILABLE": "Source unreachable — reported honestly, never guessed",
    "determinism": "Same inputs → same outputs. No randomness. Estimates, never simulations.",
}


def call_estimate(args: dict):
    from engines.comps_engine import estimate_arv
    from engines.cost_engine import generate_cost_matrix
    from engines.pii_vault import redact_dict
    from engines.room_engine import rate_rooms

    findings = [
        {
            "description": f.get("description", ""),
            "severity": f.get("severity", "MEDIUM"),
            "system_category": f.get("system", "OTHER"),
            "key": f.get("description", ""),
        }
        for f in args.get("findings", [])
    ]
    cm = generate_cost_matrix(findings, args.get("state", ""), args.get("zip_code", ""), [], None)
    cost_by = {
        it.get("finding_key", it.get("finding", "")): {
            "low": it.get("total_low", 0),
            "mid": it.get("total_avg", 0),
            "high": it.get("total_high", 0),
        }
        for it in cm.get("line_items", [])
    }
    rooms = rate_rooms(
        [{**f, "location": f.get("location", "General")} for f in findings],
        cost_by,
    )
    arv = estimate_arv(
        args.get("comps", []), subject_sqft=args.get("sqft", 1500), list_price=args.get("list_price")
    )
    badge_counts: dict[str, int] = {}
    for it in cm.get("line_items", []):
        b = it.get("badge", "MODELED")
        badge_counts[b] = badge_counts.get(b, 0) + 1
    snap = redact_dict({"totals": cm.get("summary", {}), "rooms": rooms, "arv": arv})
    try:
        from engines.share_engine import seal_snapshot

        token = seal_snapshot(snap)
    except Exception:
        token = None
    return {
        **snap,
        "line_items": cm.get("line_items", []),
        "badge_counts": badge_counts,
        "share_token": token,
        "provenance": "VERIFIED baselines + MODELED assembly",
    }


def read_resource(uri: str):
    if uri == "repair://provenance/legend":
        return PROVENANCE_LEGEND
    if uri.startswith("repair://cost-tables/"):
        zip_code = uri.split("/")[-1]
        from config import ZIP_COST_MODIFIERS

        row = ZIP_COST_MODIFIERS.get(zip_code)
        if not row:
            return {"zip_code": zip_code, "badge": "UNAVAILABLE", "note": "No modifier for this ZIP."}
        return {"zip_code": zip_code, "badge": "MODELED", "modifier": row.get("modifier", 1.0), **row}
    return None


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        mid = msg.get("id")
        method = msg.get("method", "")
        if method == "tools/list":
            print(json.dumps({"id": mid, "result": {"tools": TOOLS}}), flush=True)
        elif method == "resources/list":
            print(json.dumps({"id": mid, "result": {"resources": RESOURCES}}), flush=True)
        elif method == "resources/read":
            uri = (msg.get("params") or {}).get("uri", "")
            body = read_resource(uri)
            if body is None:
                print(json.dumps({"id": mid, "error": f"unknown resource {uri}"}), flush=True)
            else:
                print(
                    json.dumps(
                        {
                            "id": mid,
                            "result": {
                                "contents": [
                                    {"uri": uri, "mimeType": "application/json", "text": json.dumps(body)}
                                ]
                            },
                        }
                    ),
                    flush=True,
                )
        elif method == "tools/call":
            name = (msg.get("params") or {}).get("name")
            args = (msg.get("params") or {}).get("arguments", {})
            if name == "estimate_repair":
                try:
                    print(json.dumps({"id": mid, "result": call_estimate(args)}), flush=True)
                except Exception as e:
                    print(json.dumps({"id": mid, "error": str(e)[:300]}), flush=True)
            elif name == "get_provenance_legend":
                print(json.dumps({"id": mid, "result": PROVENANCE_LEGEND}), flush=True)
            else:
                print(json.dumps({"id": mid, "error": f"unknown tool {name}"}), flush=True)
        elif method == "ping":
            print(json.dumps({"id": mid, "result": "pong"}), flush=True)


if __name__ == "__main__":
    main()
