"""Load Sample Data (Page 1) — deterministic, realistic demo fixture.

Fills every Page-1 input (Step 0 + Sections 1-8) for a plausible Beverly Hills
property and builds the matching evidence files: inspection-report PDF, three
damage photos, a voice-note WAV, a floorplan JSON, and a closed-deals CSV.

Everything here is an honest SAMPLE: the property is fictional-but-plausible,
the photos/audio are synthetic and labeled, and the report is a fixture so the
parsing pipeline can be demonstrated without anyone's real documents or PII.
"""

from __future__ import annotations

import csv
import io
import json
import math
import wave
from functools import partial

SAMPLE_ADDRESS = "1428 Elm Street, Beverly Hills CA"

PDF_NAME = "SRC-2026-1012_Elm1428_Inspection.pdf"
PHOTO_NAMES = (
    "heat_exchanger_rust_sample.jpg",
    "chimney_step_flashing_sample.jpg",
    "carrier_nameplate_2012_sample.jpg",
)
AUDIO_NAME = "walkthrough_voice_note_sample.wav"
FLOORPLAN_NAME = "elm1428_floorplan_rooms.json"
TXNS_NAME = "brokerage_closed_deals_2026.csv"

SAMPLE_QUOTES = """heat exchanger | Pacific Coast Heating & Air Inc | CSLB C-20 1084552 | 1800 | 2600 | 5
chimney step flashing | Golden State Roofing Co | CSLB C-43 1023884 | 1200 | 1850 | 7
GFCI protection | BrightWire Electric Inc | CSLB C-10 1045229 | 220 | 400 | 2
slow drain | Rooter Bros Plumbing | CSLB C-36 991204 | 75 | 150 | 1
T&P valve | Rooter Bros Plumbing | CSLB C-36 991204 | 180 | 320 | 2"""

SAMPLE_PERMITS = """Electrical Permit | EL-2021-4412 | 2021-03-15 | Closed | 200A service panel upgrade, Square D Loadcenter
Roofing Permit | RF-2019-0876 | 2019-05-22 | Closed | Composition re-roof over 8:12 pitch
HVAC Permit | HV-2024-2210 | 2024-08-03 | Open | Furnace replacement - city inspection pending
Building Permit | BP-2016-3391 | 2016-06-10 | Closed | Kitchen remodel, non-structural
Water Heater Permit | WH-2019-5514 | 2019-07-19 | Closed | 40-gal water heater install"""

SAMPLE_COMPS = """1395000 | 1845 | 0.2 | 21 | 28
1275000 | 1720 | 0.4 | 45 | 41
1460000 | 1995 | 0.5 | 63 | 19
1180000 | 1610 | 0.6 | 74 | 52
1520000 | 2140 | 0.8 | 88 | 36"""

SAMPLE_BROKERAGE_ROWS = [
    ["S. Patel", "90210", "2026-01-17", "12500", "6", "4", "1485000"],
    ["M. Chen", "90048", "2026-02-28", "8200", "4", "3", "1120000"],
    ["J. Alvarez", "90211", "2026-03-14", "15750", "7", "5", "1875000"],
    ["R. Thompson", "90069", "2026-04-02", "22100", "9", "6", "2450000"],
    ["S. Patel", "90210", "2026-05-21", "9400", "5", "4", "1349000"],
    ["M. Chen", "90036", "2026-06-30", "6100", "3", "2", "985000"],
    ["J. Alvarez", "90212", "2026-07-18", "11300", "5", "4", "1650000"],
    ["R. Thompson", "90048", "2026-09-05", "13900", "6", "5", "1290000"],
]

# Widget keys (Page 1) -> values. Types must match each widget's default type.
SAMPLE_FIELDS: dict[str, object] = {
    # Step 0 - address-only ballpark
    "q_addr": "1428 Elm Street",
    "q_state": "CA",
    "q_zip": "90210",
    "q_sqft": 1800,
    # Section 1 - property metadata
    "f_addr": "1428 Elm Street",
    "f_city": "Beverly Hills",
    "f_state": "CA",
    "f_zip9": "90210-4801",
    "f_apn": "44-33-12-08-1024",
    "f_ptype": "Single Family",
    "f_beds": 3,
    "f_baths": 2.0,
    "f_sqft": 1800,
    "f_year": 1995,
    # Section 2 - market & geospatial feeds
    "f_list_price": 1_349_000,
    "f_price_psf": 749.0,
    "f_dom": 34,
    "f_last_sale": 810_000,
    "f_mls_zone": "C08",
    "f_mls_source": "CRMLS",
    # Section 3 - price & underwriting (investor mode)
    "f_premium": 2850,
    "f_arv": 1_485_000,
    "f_interest": 7.0,
    "f_rent": 3950,
    "f_holding": 6,
    # Section 4/5/6/8 - paste fields
    "f_quotes": SAMPLE_QUOTES,
    "f_permits": SAMPLE_PERMITS,
    "f_matterport": "https://my.matterport.com/show/?m=8uTsPM3MvkJ",
    "comps_txt": SAMPLE_COMPS,
}


def sample_file_names() -> list[str]:
    return [PDF_NAME, *PHOTO_NAMES, AUDIO_NAME, FLOORPLAN_NAME, TXNS_NAME]


# ------------------------------------------------------------------
# Evidence files
# ------------------------------------------------------------------
def inspection_pdf_bytes() -> bytes:
    """2-page realistic inspection fixture (reportlab, deterministic bytes)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9.5, leading=13)
    head = ParagraphStyle("Head", parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4)
    note = ParagraphStyle("Note", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#444444"))

    def p(text, style=body):
        return Paragraph(text, style)

    story = [
        Paragraph("RESIDENTIAL PRE-PURCHASE INSPECTION REPORT", styles["Title"]),
        Table(
            [
                [p("<b>Report no.</b> RPT-2026-1012-8841"), p("<b>Inspection date</b> October 12, 2026")],
                [
                    p("<b>Property</b> 1428 Elm Street, Beverly Hills, CA 90210-4801"),
                    p("<b>Built</b> 1995 · 1,800 sqft · SFR"),
                ],
                [
                    p("<b>Inspector</b> Dana Ramirez, ASHI #T-2418"),
                    p("<b>Client</b> Buyer's agent (escrow 4419-B)"),
                ],
            ],
            colWidths=[3.6 * inch, 3.6 * inch],
            style=TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#888888"))]),
        ),
        Spacer(1, 8),
        p(
            "Scope: visual inspection of readily accessible systems. Items photographed for "
            "documentation. The following observations are opinions on readily observable conditions."
        ),
        Paragraph("1. HEATING & COOLING (HVAC)", head),
        p(
            "Carbon monoxide risk: the heat exchanger on the Carrier furnace (mfg. 2012, serial "
            "4318A28479) is cracked, and the system must be shut off until it is replaced by a "
            "licensed HVAC contractor."
        ),
        p(
            "The condensate drain line is soiled and the filter requires routine cleaning; HVAC "
            "service is recommended. The inducer motor is noisy during cycling."
        ),
        Paragraph("2. ROOFING & CHIMNEY", head),
        p(
            "Rust corrosion is visible on the chimney step flashing; the adjacent shingles are "
            "cracked and lifting, allowing water penetration into the attic where the moisture "
            "reading is 18%."
        ),
        Paragraph("3. PLUMBING", head),
        p(
            "Corrosion at the water heater T&P valve is leaking slowly; the valve should be "
            "replaced. The Rheem 40-gallon unit (mfg. 2019) is within its expected service life."
        ),
        p(
            "Slow drain response in the secondary bathroom sink basin; the trap should be cleared "
            "and the line snaked (routine maintenance)."
        ),
        Paragraph("4. ELECTRICAL", head),
        p(
            "Two kitchen counter receptacles are not GFCI-protected; a service upgrade is "
            "recommended by the electrical contractor. The 200A Square D panel shows no double-taps."
        ),
        Paragraph("5. INTERIOR / GENERAL", head),
        p(
            "Cosmetic scuff marks are present on the living room baseboards; touch-up paint is "
            "suggested. The following items were photographed for documentation: attic hatch and "
            "insulation depth."
        ),
        Paragraph("FINDINGS SUMMARY", head),
        Table(
            [
                ["Item", "System", "Severity", "Location", "Recommended action"],
                [
                    "Heat exchanger cracked; furnace shut down",
                    "HVAC",
                    "CRITICAL",
                    "Utility room",
                    "Replace furnace, CO test before close",
                ],
                [
                    "Chimney step flashing damaged, shingles cracked",
                    "Roofing",
                    "HIGH",
                    "North chimney",
                    "Re-flash and seal; roofing repair",
                ],
                [
                    "Secondary bath sink drains slowly",
                    "Plumbing",
                    "MEDIUM",
                    "Bathroom",
                    "Snake drain, clear P-trap",
                ],
                [
                    "Kitchen counter receptacles lack GFCI",
                    "Electrical",
                    "MEDIUM",
                    "Kitchen",
                    "Install GFCI protection",
                ],
                ["Baseboard scuff marks", "Interior", "LOW", "Living room", "Touch-up paint (cosmetic)"],
            ],
            colWidths=[2.5 * inch, 0.9 * inch, 0.85 * inch, 1.05 * inch, 1.9 * inch],
            style=TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#888888")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                ]
            ),
        ),
        Paragraph("RECOMMENDATIONS", head),
        p("1. Replace the furnace heat exchanger assembly and re-certify the system before close of escrow."),
        p(
            "2. Re-flash the chimney step flashing and replace damaged shingles; re-check attic moisture after repair."
        ),
        p("3. Install GFCI protection at the two kitchen counter receptacles."),
        p("4. Clear the secondary bathroom drain and service the water heater T&P valve."),
        Spacer(1, 10),
        p("Inspector signature: D. Ramirez, ASHI #T-2418 - Page 1 of 2 - Sample fixture (demo data)", note),
    ]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title="Inspection Report - 1428 Elm Street (sample)")
    doc.build(story, canvasmaker=partial(rl_canvas.Canvas, invariant=1))
    return buf.getvalue()


def _sample_photo(title: str, defect: str, base: tuple, accent: tuple) -> bytes:
    """Synthetic but legible 640x480 evidence photo (labeled SAMPLE)."""
    from PIL import Image, ImageDraw, ImageFont

    w, h = 640, 480
    img = Image.new("RGB", (w, h), base)
    d = ImageDraw.Draw(img)
    for y in range(h):  # deterministic vertical gradient (metal panel feel)
        t = y / (h - 1)
        row = tuple(int(base[i] + (255 - base[i]) * 0.10 * (1 - t)) for i in range(3))
        d.line([(0, y), (w, y)], fill=row)
    # fixed "defect" shapes — rust patches / lifted flashing / nameplate plate
    d.ellipse([210, 150, 430, 330], outline=accent, width=6)
    d.ellipse([250, 185, 330, 255], fill=accent)
    d.ellipse([340, 230, 400, 290], fill=accent)
    d.rectangle([40, 60, 600, 130], outline=accent, width=3)
    try:
        font_big = ImageFont.load_default(size=24)
        font_sm = ImageFont.load_default(size=16)
    except TypeError:
        font_big = ImageFont.load_default()
        font_sm = ImageFont.load_default()
    d.text((52, 78), title, fill=(240, 240, 240), font=font_big)
    d.rectangle([0, h - 58, w, h], fill=(15, 15, 15))
    d.text((14, h - 48), defect, fill=(255, 210, 90), font=font_sm)
    d.text((14, h - 24), "SAMPLE PHOTO (synthetic) - demo evidence", fill=(160, 160, 160), font=font_sm)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88)
    return out.getvalue()


def _sample_photos() -> list[tuple[str, bytes]]:
    return [
        (
            PHOTO_NAMES[0],
            _sample_photo(
                "FURNACE HEAT EXCHANGER",
                "Defect: rust + hairline crack (Carrier 2012) - CO risk",
                (70, 66, 60),
                (150, 78, 30),
            ),
        ),
        (
            PHOTO_NAMES[1],
            _sample_photo(
                "CHIMNEY STEP FLASHING",
                "Defect: lifted flashing, cracked shingles, wet attic deck",
                (95, 95, 100),
                (60, 60, 65),
            ),
        ),
        (
            PHOTO_NAMES[2],
            _sample_photo(
                "NAMEPLATE: CARRIER 58MCR (2012)",
                "Serial 4318A28479 - mfg 09/2012 - 96% eff. (sample)",
                (40, 44, 52),
                (190, 190, 200),
            ),
        ),
    ]


def voice_note_wav_bytes() -> bytes:
    """0.75s synthetic voice-note placeholder (labeled by filename as sample)."""
    rate = 8000
    frames = int(rate * 0.75)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        payload = bytearray()
        for i in range(frames):
            t = i / rate
            env = min(1.0, t * 8) * max(0.0, 1.0 - (t - 0.55) / 0.2)
            env = max(0.0, min(1.0, env))
            sample = int(11000 * env * math.sin(2 * math.pi * 220 * t))
            payload += sample.to_bytes(2, "little", signed=True)
        wf.writeframes(bytes(payload))
    return buf.getvalue()


def floorplan_json_bytes() -> bytes:
    rooms = [
        {
            "name": "Living Room",
            "x": 3.5,
            "y": 3.0,
            "width": 4.5,
            "height": 3.5,
            "floor": "Main",
            "type": "common",
        },
        {
            "name": "Kitchen",
            "x": 8.5,
            "y": 3.0,
            "width": 3.5,
            "height": 3.0,
            "floor": "Main",
            "type": "common",
        },
        {
            "name": "Dining Room",
            "x": 3.5,
            "y": 7.0,
            "width": 3.5,
            "height": 2.5,
            "floor": "Main",
            "type": "common",
        },
        {
            "name": "Hallway",
            "x": 7.5,
            "y": 6.5,
            "width": 4.5,
            "height": 1.2,
            "floor": "Main",
            "type": "circulation",
        },
        {
            "name": "Laundry",
            "x": 8.5,
            "y": 8.2,
            "width": 2.0,
            "height": 1.6,
            "floor": "Main",
            "type": "utility",
        },
        {
            "name": "Garage",
            "x": 3.0,
            "y": 10.5,
            "width": 4.5,
            "height": 3.0,
            "floor": "Main",
            "type": "utility",
        },
        {
            "name": "Basement",
            "x": 8.5,
            "y": 10.5,
            "width": 3.5,
            "height": 3.0,
            "floor": "Below",
            "type": "utility",
        },
        {
            "name": "Attic",
            "x": 6.0,
            "y": 0.5,
            "width": 3.5,
            "height": 2.0,
            "floor": "Above",
            "type": "utility",
        },
        {
            "name": "Bedroom 1",
            "x": 12.5,
            "y": 3.0,
            "width": 3.0,
            "height": 3.0,
            "floor": "Main",
            "type": "bedroom",
        },
        {
            "name": "Bedroom 2",
            "x": 12.5,
            "y": 6.5,
            "width": 3.0,
            "height": 3.0,
            "floor": "Main",
            "type": "bedroom",
        },
        {
            "name": "Bedroom 3",
            "x": 12.5,
            "y": 10.0,
            "width": 3.0,
            "height": 3.0,
            "floor": "Main",
            "type": "bedroom",
        },
        {
            "name": "Bathroom",
            "x": 16.5,
            "y": 3.0,
            "width": 2.2,
            "height": 2.4,
            "floor": "Main",
            "type": "bath",
        },
        {
            "name": "Primary Bath",
            "x": 16.5,
            "y": 6.0,
            "width": 2.2,
            "height": 2.4,
            "floor": "Main",
            "type": "bath",
        },
    ]
    return json.dumps(
        {
            "property": "1428 Elm Street (sample)",
            "source": "sample fixture",
            "rooms": rooms,
        },
        indent=2,
    ).encode("utf-8")


def brokerage_csv_bytes() -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["agent", "zip_code", "date", "credits_negotiated", "items_requested", "items_granted", "deal_value"]
    )
    writer.writerows(SAMPLE_BROKERAGE_ROWS)
    return buf.getvalue().encode("utf-8")


def build_sample_files() -> dict[str, object]:
    """UploadedFile-shaped evidence objects (in-memory; Streamlit cannot set
    file_uploader widget state, so app.py falls back to these when empty)."""
    from streamlit.proto.Common_pb2 import FileURLs
    from streamlit.runtime.uploaded_file_manager import UploadedFile, UploadedFileRec

    def uf(name: str, mime: str, data: bytes) -> UploadedFile:
        rec = UploadedFileRec(f"sample-{name}", name, mime, data)
        urls = FileURLs()
        urls.file_id = rec.file_id
        urls.upload_url = "sample://local"
        urls.delete_url = "sample://local"
        return UploadedFile(rec, urls)

    return {
        "pdfs": [uf(PDF_NAME, "application/pdf", inspection_pdf_bytes())],
        "photos": [uf(name, "image/jpeg", data) for name, data in _sample_photos()],
        "audios": [uf(AUDIO_NAME, "audio/wav", voice_note_wav_bytes())],
        "floorplan": uf(FLOORPLAN_NAME, "application/json", floorplan_json_bytes()),
        "txns": uf(TXNS_NAME, "text/csv", brokerage_csv_bytes()),
    }
