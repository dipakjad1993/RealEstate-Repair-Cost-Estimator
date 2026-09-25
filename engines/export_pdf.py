"""Lazy PDF export (split from export_engine bloat). fpdf2, no heavy deps."""

from datetime import datetime, timezone

# fpdf2 core fonts (Helvetica) are latin-1 only. Inspection text carries
# em-dashes, bullets, arrows, emoji — sanitize every string at the boundary.
_REPLACEMENTS = {
    "\u2014": "-",
    "\u2013": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2022": "-",
    "\u2026": "...",
    "\u2192": "->",
    "\u2190": "<-",
    "\u00a0": " ",
    "\u2713": "v",
    "\u2714": "v",
    "\u2717": "x",
    "\u25cf": "-",
    "\u25a0": "-",
}


def _safe(text) -> str:
    """Coerce to latin-1-safe ASCII-ish text. Never raises on weird input."""
    s = str(text or "")
    for bad, good in _REPLACEMENTS.items():
        s = s.replace(bad, good)
    return s.encode("latin-1", errors="replace").decode("latin-1")


def build_pdf_package(summary: dict, line_items: list, title="Repair Estimate - Lender Package") -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _safe(title[:90]))
    pdf.ln(12)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(
        0,
        6,
        _safe(
            f"Generated {datetime.now(timezone.utc).isoformat()}. "
            "Provenance: VERIFIED gov baselines + USER_PROVIDED quotes where shown. "
            "MODELED figures are deterministic estimates, not quotes."
        ),
    )
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(
        0,
        8,
        _safe(
            f"Total (avg): ${summary.get('total_avg', 0):,.0f}   "
            f"Range: ${summary.get('total_low', 0):,.0f} - ${summary.get('total_high', 0):,.0f}"
        ),
    )
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "Line items")
    pdf.ln(7)
    pdf.set_font("Helvetica", "", 9)
    for it in (line_items or [])[:80]:
        line = (
            f"[{it.get('severity', '')}] {it.get('system', '')} - "
            f"{str(it.get('finding', ''))[:90]}  "
            f"${it.get('contractor_low', it.get('total_low', 0)):,.0f}-"
            f"${it.get('contractor_high', it.get('total_high', 0)):,.0f} "
            f"({it.get('provenance', 'MODELED')})"
        )
        pdf.multi_cell(0, 5, _safe(line))
    return bytes(pdf.output())
