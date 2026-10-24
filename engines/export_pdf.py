"""Lazy PDF export (split from export_engine bloat). fpdf2, no heavy deps.

Enterprise skin: self-hosted Google Sans Flex (TTF instances converted from
the Variable woff2 in static/fonts), brand header band, severity color bars.
Falls back to core Helvetica when TTFs are absent (CI/minimal installs).
"""

from datetime import datetime, timezone
from pathlib import Path

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

# Brand + severity palette (mirrors data/severity_levels.json)
_BRAND = (0, 113, 227)
_INK = (29, 29, 31)
_INK_2 = (110, 110, 115)
_PAPER = (245, 245, 247)
_SEV_COLORS = {
    "CRITICAL": (220, 38, 38),
    "HIGH": (234, 88, 12),
    "MEDIUM": (202, 138, 4),
    "LOW": (22, 163, 74),
    "INFO": (37, 99, 235),
}

_FONT_DIR = Path(__file__).resolve().parents[1] / "static" / "fonts"
_FONT_FAMILY = "GoogleSansFlex"


def _safe(text) -> str:
    """Coerce to latin-1-safe ASCII-ish text. Never raises on weird input."""
    s = str(text or "")
    for bad, good in _REPLACEMENTS.items():
        s = s.replace(bad, good)
    return s.encode("latin-1", errors="replace").decode("latin-1")


def _register_fonts(pdf) -> str:
    """Embed Google Sans Flex; return the family to use ('Helvetica' = fallback)."""
    regular = _FONT_DIR / "GoogleSansFlex-Regular.ttf"
    bold = _FONT_DIR / "GoogleSansFlex-Bold.ttf"
    if not (regular.is_file() and bold.is_file()):
        return "Helvetica"
    try:
        pdf.add_font(_FONT_FAMILY, "", str(regular))
        pdf.add_font(_FONT_FAMILY, "B", str(bold))
        return _FONT_FAMILY
    except Exception:
        return "Helvetica"


def build_pdf_package(summary: dict, line_items: list, title="Repair Estimate - Lender Package") -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    family = _register_fonts(pdf)

    # Brand header band (gradient is not available in fpdf — solid accent)
    pdf.set_fill_color(*_BRAND)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(family, "B", 15)
    pdf.cell(0, 15, "  " + _safe(title[:88]), fill=True)
    pdf.ln(17)

    pdf.set_text_color(*_INK_2)
    pdf.set_font(family, "", 9)
    pdf.multi_cell(
        0,
        5.5,
        _safe(
            f"Generated {datetime.now(timezone.utc).isoformat()}. "
            "Provenance: VERIFIED gov baselines + USER_PROVIDED quotes where shown. "
            "MODELED figures are deterministic estimates, not quotes."
        ),
    )
    pdf.ln(3)

    # Summary metrics strip
    pdf.set_fill_color(*_PAPER)
    pdf.set_text_color(*_INK)
    pdf.set_font(family, "B", 11)
    cell_w = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.cell(cell_w / 3, 11, f"  AVG  ${summary.get('total_avg', 0):,.0f}", fill=True)
    pdf.cell(
        cell_w / 3,
        11,
        f"  LOW  ${summary.get('total_low', 0):,.0f}",
        fill=True,
    )
    pdf.cell(
        cell_w / 3,
        11,
        f"  HIGH  ${summary.get('total_high', 0):,.0f}",
        fill=True,
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(5)

    pdf.set_text_color(*_INK)
    pdf.set_font(family, "B", 12)
    pdf.cell(0, 8, "Line items")
    pdf.ln(8)

    for it in (line_items or [])[:80]:
        pdf.set_x(pdf.l_margin)  # multi_cell leaves x at the right margin
        sev = str(it.get("severity", "") or "").upper()
        sev_color = _SEV_COLORS.get(sev, _INK_2)
        detail = (
            f" {it.get('system', '')} - "
            f"{str(it.get('finding', ''))[:86]}  "
            f"${it.get('contractor_low', it.get('total_low', 0)):,.0f}-"
            f"${it.get('contractor_high', it.get('total_high', 0)):,.0f} "
            f"({it.get('provenance', 'MODELED')})"
        )
        # Severity color bar: filled chip, then the detail on the same row
        pdf.set_fill_color(*sev_color)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font(family, "B", 7.5)
        pdf.cell(24, 5.4, (sev or "-")[:8], fill=True, align="C")
        pdf.set_text_color(*_INK)
        pdf.set_font(family, "", 8.5)
        pdf.multi_cell(0, 5.4, _safe(detail))
    pdf.set_text_color(*_INK_2)
    pdf.set_font(family, "", 7.5)
    pdf.ln(2)
    pdf.cell(
        0,
        4,
        _safe(
            "Estimates are deterministic model outputs, not contractor quotes. "
            "All figures carry provenance badges."
        ),
    )
    return bytes(pdf.output())
