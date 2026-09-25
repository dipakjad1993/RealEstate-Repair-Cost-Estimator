"""Lazy Excel export (split from export_engine bloat). openpyxl."""

import io


def build_excel_workbook(line_items: list, rooms: list = None, comps: dict = None) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Line items"
    ws.append(["System", "Severity", "Finding", "Low", "High", "Provenance"])
    for it in line_items or []:
        ws.append(
            [
                it.get("system"),
                it.get("severity"),
                str(it.get("finding", ""))[:200],
                it.get("contractor_low", it.get("total_low")),
                it.get("contractor_high", it.get("total_high")),
                it.get("provenance"),
            ]
        )
    if rooms:
        w2 = wb.create_sheet("Rooms")
        w2.append(["Room", "Condition", "Priority", "Low", "Mid", "High", "Top issue"])
        for r in rooms:
            w2.append(
                [
                    r.get("room"),
                    r.get("condition"),
                    r.get("priority"),
                    r.get("low"),
                    r.get("mid"),
                    r.get("high"),
                    r.get("top_issue"),
                ]
            )
    if comps and comps.get("comps_weighted"):
        w3 = wb.create_sheet("Comps")
        w3.append(["Price", "Sqft", "$/sqft", "Dist mi", "Recency d", "Weight"])
        for c in comps["comps_weighted"]:
            w3.append(
                [
                    c.get("price"),
                    c.get("sqft"),
                    c.get("ppsf"),
                    c.get("distance_mi"),
                    c.get("recency_days"),
                    c.get("weight_norm"),
                ]
            )
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
