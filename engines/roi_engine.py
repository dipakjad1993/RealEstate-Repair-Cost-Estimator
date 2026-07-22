import math
from datetime import datetime


def _deterministic_hash(value):
    h = 0
    for ch in str(value):
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


def generate_brokerage_roi_data(broker_id="BROKER-001", num_agents=12, num_transactions=45):
    seed = _deterministic_hash(broker_id + str(datetime.now().month))
    agent_names = [
        "Sarah Chen", "Marcus Williams", "Jennifer Rodriguez", "David Park",
        "Amanda Foster", "Michael Torres", "Rachel Kim", "James Mitchell",
        "Lisa Nakamura", "Robert Chang", "Michelle Brown", "Kevin Johnson",
    ]
    transactions = []
    total_credits = 0
    total_repairs = 0
    total_items = 0
    total_granted = 0
    agents = []

    for i in range(min(num_agents, len(agent_names))):
        agent_name = agent_names[i]
        agent_seed = _deterministic_hash(agent_name + broker_id)
        agent_transactions = 2 + (agent_seed % 5)
        agent_credits = 0
        agent_items = 0
        agent_granted = 0
        for j in range(agent_transactions):
            txn_seed = _deterministic_hash(agent_name + str(j) + broker_id)
            finding_count = 3 + (txn_seed % 10)
            credits_negotiated = 800 + (txn_seed % 14200)
            repairs_requested = credits_negotiated * (1.1 + (txn_seed % 50) / 100)
            items_req = finding_count
            items_grt = max(1, items_req - (txn_seed % 5))
            transaction = {
                "agent": agent_name,
                "zip_code": str(10001 + (txn_seed % 89998)),
                "credits_negotiated": round(credits_negotiated, 0),
                "repairs_requested": round(repairs_requested, 0),
                "items_requested": items_req,
                "items_granted": items_grt,
                "success_rate": round(items_grt / max(items_req, 1) * 100, 1),
                "date": f"2026-{((txn_seed % 6) + 1):02d}-{((txn_seed % 28) + 1):02d}",
            }
            transactions.append(transaction)
            agent_credits += credits_negotiated
            agent_items += items_req
            agent_granted += items_grt
        agents.append({
            "name": agent_name,
            "total_transactions": agent_transactions,
            "total_credits_negotiated": round(agent_credits, 0),
            "avg_credit_per_deal": round(agent_credits / max(agent_transactions, 1), 0),
            "items_requested": agent_items,
            "items_granted": agent_granted,
            "success_rate": round(agent_granted / max(agent_items, 1) * 100, 1),
            "estimated_revenue_impact": round(agent_credits * 0.03, 0),
        })
        total_credits += agent_credits
        total_items += agent_items
        total_granted += agent_granted
    agents.sort(key=lambda x: x["total_credits_negotiated"], reverse=True)

    top_inspectors = [
        {"name": "ABC Home Inspections", "avg_findings": 8.5, "avg_severity_score": 2.8, "reports_processed": 8 + (seed % 13)},
        {"name": "Precision Inspection Services", "avg_findings": 7.2, "avg_severity_score": 3.1, "reports_processed": 5 + (seed % 11)},
        {"name": "Golden State Inspectors", "avg_findings": 9.1, "avg_severity_score": 2.5, "reports_processed": 4 + (seed % 9)},
        {"name": "ProInspect LLC", "avg_findings": 6.8, "avg_severity_score": 3.3, "reports_processed": 3 + (seed % 8)},
    ]

    zip_averages = {}
    for t in transactions:
        z = t["zip_code"][:3] + "xx"
        if z not in zip_averages:
            zip_averages[z] = {"total_credits": 0, "count": 0}
        zip_averages[z]["total_credits"] += t["credits_negotiated"]
        zip_averages[z]["count"] += 1
    for z in zip_averages:
        zip_averages[z]["avg_credit"] = round(zip_averages[z]["total_credits"] / max(zip_averages[z]["count"], 1), 0)

    return {
        "broker_id": broker_id,
        "report_period": f"Q1-Q2 {datetime.now().year}",
        "summary": {
            "total_agents": len(agents),
            "total_transactions": len(transactions),
            "total_credits_negotiated": round(total_credits, 0),
            "total_repairs_requested": round(sum(t["repairs_requested"] for t in transactions), 0),
            "overall_success_rate": round(total_granted / max(total_items, 1) * 100, 1),
            "avg_credits_per_transaction": round(total_credits / max(len(transactions), 1), 0),
            "estimated_team_revenue_impact": round(total_credits * 0.03, 0),
        },
        "agent_performance": agents,
        "transactions": transactions,
        "top_inspector_companies": top_inspectors,
        "zip_code_averages": zip_averages,
        "insights": _generate_insights(agents, transactions, zip_averages),
    }


def _generate_insights(agents, transactions, zip_averages):
    insights = []
    if agents:
        top = agents[0]
        insights.append(f"Top Performer: {top['name']} negotiated ${top['total_credits_negotiated']:,.0f} across {top['total_transactions']} deals with {top['success_rate']:.0f}% item acceptance rate.")
    if len(agents) > 1:
        bottom = agents[-1]
        insights.append(f"Coaching Opportunity: {bottom['name']} averages ${bottom['avg_credit_per_deal']:,.0f}/deal. Consider training on escalation strategies and documentation practices.")
    if transactions:
        avg_success = sum(t["success_rate"] for t in transactions) / len(transactions)
        insights.append(f"Team-wide item acceptance rate: {avg_success:.0f}%. Industry benchmark is 65-75%.")
    high_performing_zips = sorted(zip_averages.items(), key=lambda x: x[1]["avg_credit"], reverse=True)[:3]
    if high_performing_zips:
        top_zips = ", ".join([f"{z[0]}xx (${z[1]['avg_credit']:,.0f})" for z in high_performing_zips])
        insights.append(f"Highest average credits by zip prefix: {top_zips}. Consider focusing outreach in these high-value markets.")
    return insights
