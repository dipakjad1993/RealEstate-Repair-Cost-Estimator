"""MCP server: repair-estimator-mcp — agents call estimate_repair (enterprise).

Stdio JSON-RPC (MCP-compatible): tools/list + tools/call estimate_repair.
Allows GPTBot/ClaudeBot/PerplexityBot agent traffic (we WANT agent traffic).
"""

import json
import sys

TOOLS = [
    {
        "name": "estimate_repair",
        "description": "Deterministic repair estimate with provenance badges. Input: address/state/zip/findings[]. Output: totals, rooms, ARV, share_token.",
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
    }
]


def call_estimate(args: dict):
    from engines.comps_engine import estimate_arv
    from engines.cost_engine import generate_cost_matrix
    from engines.pii_vault import redact_dict
    from engines.room_engine import rate_rooms
    from engines.share_engine import seal_snapshot

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
    rooms = rate_rooms([{**f, "location": "General"} for f in findings])
    arv = estimate_arv(
        args.get("comps", []), subject_sqft=args.get("sqft", 1500), list_price=args.get("list_price")
    )
    snap = redact_dict({"totals": cm.get("summary", {}), "rooms": rooms, "arv": arv})
    return {**snap, "share_token": seal_snapshot(snap), "provenance": "VERIFIED baselines + MODELED assembly"}


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
        elif method == "tools/call":
            name = (msg.get("params") or {}).get("name")
            args = (msg.get("params") or {}).get("arguments", {})
            if name == "estimate_repair":
                try:
                    print(json.dumps({"id": mid, "result": call_estimate(args)}), flush=True)
                except Exception as e:
                    print(json.dumps({"id": mid, "error": str(e)[:300]}), flush=True)
            else:
                print(json.dumps({"id": mid, "error": f"unknown tool {name}"}), flush=True)
        elif method == "ping":
            print(json.dumps({"id": mid, "result": "pong"}), flush=True)


if __name__ == "__main__":
    main()
