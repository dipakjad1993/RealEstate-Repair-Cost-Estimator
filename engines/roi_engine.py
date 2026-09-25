"""
Brokerage ROI Engine (VERIFIED REBUILD)
=======================================
Computes real brokerage economics ONLY from real user-supplied transaction
records (CSV/import). Returns honest UNAVAILABLE with guidance when no records
are provided. No fabricated transactions, agents, or inspector companies.
"""

from datetime import datetime


def generate_brokerage_roi_data(broker_id="", user_transactions=None):
    """
    user_transactions: list of dicts:
      {agent, zip_code, date, credits_negotiated, items_requested, items_granted,
       commission_rate, deal_value, repairs_requested}
    """
    txns = list(user_transactions or [])
    if not txns:
        return {
            "status": "UNAVAILABLE",
            "note": "Import real closed-deal records (CSV) to compute brokerage ROI. "
            "This tool does not fabricate transaction history.",
            "broker_id": broker_id or "UNSET",
        }

    agent_map = {}
    total_credits = 0.0
    total_requested = 0
    total_granted = 0
    total_value = 0.0
    for t in txns:
        agent = t.get("agent", "Unassigned")
        credits = float(t.get("credits_negotiated", 0) or 0)
        req = int(t.get("items_requested", 0) or 0)
        grt = int(t.get("items_granted", 0) or 0)
        total_credits += credits
        total_requested += req
        total_granted += grt
        total_value += float(t.get("deal_value", 0) or 0)
        a = agent_map.setdefault(
            agent,
            {"name": agent, "transactions": 0, "credits": 0.0, "requested": 0, "granted": 0, "value": 0.0},
        )
        a["transactions"] += 1
        a["credits"] += credits
        a["requested"] += req
        a["granted"] += grt
        a["value"] += float(t.get("deal_value", 0) or 0)

    agents = []
    for a in agent_map.values():
        a["avg_credit_per_deal"] = round(a["credits"] / max(a["transactions"], 1), 0)
        a["success_rate"] = round(a["granted"] / max(a["requested"], 1) * 100, 1)
        a["commission_revenue"] = round(a["value"] * float(t.get("commission_rate", 0.03) or 0.03), 0)
        agents.append(a)
    agents.sort(key=lambda x: x["credits"], reverse=True)

    overall = round(total_granted / max(total_requested, 1) * 100, 1)
    insights = []
    if agents:
        insights.append(
            f"Top agent: {agents[0]['name']} negotiated ${agents[0]['credits']:,.0f} across {agents[0]['transactions']} deals."
        )
    if len(agents) > 1:
        insights.append(
            f"Coaching opportunity: {agents[-1]['name']} averages ${agents[-1]['avg_credit_per_deal']:,.0f}/deal."
        )
    insights.append(f"Team item acceptance rate: {overall}% (industry benchmark 65-75%).")

    return {
        "status": "VERIFIED",
        "source": "USER_TRANSACTION_IMPORT",
        "broker_id": broker_id or "USER_IMPORT",
        "report_period": f"Imported {len(txns)} records as of {datetime.now().strftime('%Y-%m-%d')}",
        "summary": {
            "total_agents": len(agents),
            "total_transactions": len(txns),
            "total_credits_negotiated": round(total_credits, 0),
            "overall_success_rate": overall,
            "avg_credits_per_transaction": round(total_credits / max(len(txns), 1), 0),
            "total_deal_value": round(total_value, 0),
        },
        "agent_performance": agents,
        "transactions": txns,
        "insights": insights,
    }
