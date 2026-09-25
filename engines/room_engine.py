"""Room-by-room conditioner: Good/Fair/Poor/Gut + Low/Mid/High + priority (enterprise).

Deterministic: severity weights per room -> condition; cost rows mapped by
location substring; priority from worst severity in room.
"""

SEV_W = {"CRITICAL": 10, "HIGH": 5, "MEDIUM": 2, "LOW": 0.5, "INFO": 0.1}


def rate_rooms(findings, cost_by_finding=None):
    cost_by_finding = cost_by_finding or {}
    rooms = {}
    for f in findings or []:
        room = (f.get("location") or "General").strip().title() or "General"
        rooms.setdefault(room, []).append(f)
    out = []
    for room, items in sorted(rooms.items()):
        score = sum(SEV_W.get(str(i.get("severity", "LOW")).upper(), 0.5) for i in items)
        worst = min(
            items,
            key=lambda i: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}.get(
                str(i.get("severity", "LOW")).upper(), 5
            ),
        )
        w = str(worst.get("severity", "LOW")).upper()
        if score >= 10 or w == "CRITICAL":
            cond, priority = "Gut" if score >= 20 else "Poor", "Immediate (<30d)"
        elif score >= 5 or w == "HIGH":
            cond, priority = "Poor", "Immediate (<30d)"
        elif score >= 2:
            cond, priority = "Fair", "6-mo"
        elif score >= 0.5:
            cond, priority = "Fair", "12-mo"
        else:
            cond, priority = "Good", "Deferred"
        low = mid = high = 0
        for i in items:
            c = cost_by_finding.get(i.get("key", i.get("description", ""))) or {}
            low += c.get("low", 0) or 0
            mid += c.get("mid", c.get("avg", 0)) or 0
            high += c.get("high", 0) or 0
        out.append(
            {
                "room": room,
                "condition": cond,
                "priority": priority,
                "items": len(items),
                "worst_severity": w,
                "low": round(low),
                "mid": round(mid),
                "high": round(high),
                "top_issue": worst.get("description", "")[:120],
            }
        )
    # Rooms with no findings are Good/Deferred only if explicitly surveyed — not assumed.
    return out
