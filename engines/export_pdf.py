"""Lazy PDF export (split from export_engine bloat). fpdf2, no heavy deps."""

from datetime import datetime


def build_pdf_package(summary: dict, line_items: list, title="Repair Estimate — Lender Package") -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title[:90])
    pdf.ln(12)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        0,
        6,
        f"Generated {datetime.utcnow().isoformat()}Z. Provenance: VERIFIED gov baselines + USER_PROVIDED quotes where shown. MODELED figures are deterministic estimates, not quotes.",
    )
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(
        0,
        8,
        f"Total (avg): ${summary.get('total_avg', 0):,.0f}   Range: ${summary.get('total_low', 0):,.0f} - ${summary.get('total_high', 0):,.0f}",
    )
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "Line items")
    pdf.ln(7)
    pdf.set_font("Helvetica", "", 9)
    for it in (line_items or [])[:80]:
        line = f"[{it.get('severity', '')}] {it.get('system', '')} — {str(it.get('finding', ''))[:90]}  ${it.get('contractor_low', it.get('total_low', 0)):,.0f}-${it.get('contractor_high', it.get('total_high', 0)):,.0f} ({it.get('provenance', 'MODELED')})"
        pdf.multi_cell(0, 5, line)
    return bytes(pdf.output())
