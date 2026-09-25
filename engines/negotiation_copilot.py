"""Agentic negotiation copilot (LangGraph-style, deterministic, cited).

Drafts offer credit language from sandbox totals + leverage + DOM, with
citations to finding indices. No LLM required; LLM polish is optional and
key-gated. Output is a letter + clause table agents can paste into addenda.
"""


def draft_offer_credit(line_items, leverage=50, dom=0, buyer_name="Buyer", address="Subject Property"):
    items = list(line_items or [])
    total = sum(float(i.get("bid_high", i.get("estimated_high", i.get("high", 0))) or 0) for i in items)
    # Expected concession scales with leverage + DOM (transparent).
    dom_uplift = 0.15 if (dom or 0) > 60 else (0.08 if (dom or 0) > 30 else 0.0)
    rate = min(0.95, 0.35 + (float(leverage or 50) / 100) * 0.5 + dom_uplift)
    expected = round(total * rate)
    clauses = []
    for n, i in enumerate(items[:12], 1):
        clauses.append(
            {
                "n": n,
                "system": i.get("system", ""),
                "severity": i.get("severity", ""),
                "finding": str(i.get("finding", i.get("description", "")))[:110],
                "ask": float(i.get("bid_high", i.get("estimated_high", i.get("high", 0))) or 0),
                "citation": f"[Finding #{n} · {i.get('severity', '')} {i.get('system', '')}]",
            }
        )
    letter = (
        f"Re: Repair credit request — {address}\n\n"
        f"Dear Seller, on behalf of {buyer_name}, we request a seller credit of "
        f"${total:,.0f} (expected concession ~${expected:,.0f} at leverage {leverage}/100, {dom} DOM), "
        f"based on the cited inspection findings below. Each line references the inspection "
        f"finding index for auditability.\n\n"
        + "\n".join(f"{c['n']}. {c['citation']} {c['finding']} — ask ${c['ask']:,.0f}." for c in clauses)
        + "\n\nIn lieu of repairs, credit at closing. High-risk items may alternatively be "
        "held in escrow at 1.5x per the holdback schedule."
    )
    return {
        "letter": letter,
        "clauses": clauses,
        "total_ask": round(total),
        "expected_concession": expected,
        "leverage": leverage,
        "dom": dom,
        "citations": [c["citation"] for c in clauses],
    }
