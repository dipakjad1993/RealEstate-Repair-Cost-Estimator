import hashlib
import re
from collections import defaultdict

from config import INSPECTION_SYSTEM_PATTERNS, SeverityLevels
from engines.confidence_engine import score_finding

# ---------------------------------------------------------------------------
# Text hygiene helpers
# ---------------------------------------------------------------------------
# Common report abbreviations whose trailing period must NOT split a sentence
# ("...furnace (mfg. 2012, serial 4318A28479) is cracked..." must stay whole).
_ABBREV_RE = re.compile(
    r"\b(mfg|mgf|mfr|approx|e\.g|i\.e|vs|no|inc|llc|ltd|corp|co|dept|est|min|max|sec|rev"
    r"|attn|ashi|cslb|nec|ul|ansi|u\.s|a\.o|sq|ft|in|yr|dr|mr|mrs|ms|jr|sr|fig|ref"
    r"|cm|mm|kv|amp|gal|psi|hvac)\.",
    re.IGNORECASE,
)
_DOT_SENTINEL = "\u2024"  # one-dot leader: invisible to the sentence splitter

_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]{0,200}>")
_MD_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_MD_NOISE_RE = re.compile(r"(?:^|\n)\s*(?:#{1,6}\s*|[-*_]{3,}\s*$)")
_MD_WRAP_RE = re.compile(r"(\*\*|__|~~|`{1,3})")

# Report chrome (headers/footers/scope/boilerplate) that must never become a finding.
_NOISE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^\s*report\s+no\b",
        r"^\s*rpt[-\s]",
        r"\binspection\s+date\b",
        r"\bpage\s+\d+\s+of\s+\d+\b",
        r"inspector\s+signature",
        r"\bashi\s*#",
        r"sample\s+fixture",
        r"^\s*scope\s*:",
        r"items?(?:\s+were)?\s+photographed\s+for\s+documentation",
        r"opinions?\s+on\s+readily\s+observable",
        r"^\s*(?:findings?\s+)?summary\s*$",
        r"^\s*recommendations?\s*\d*\s*\.?\s*$",
        r"^\s*(?:this\s+)?report\s+(?:is|was|has)\b",
        r"\bliability\s+(?:is|shall|disclaimed)",
        r"^\s*built\s+19\d\d\b",
        r"\bescrow\s+\d",
        r"^\s*(?:reserved|intentionally\s+left)\b",
        r"^\s*(?:inspection|report)\s+(?:scope|overview|objectives?)\b",
        r"\bvisual\s+inspection\s+of\s+readily\s+accessible\b",
        r"^\s*(?:item|system|severity|location|recommended\s+action)\s*$",
    )
]

_SECTION_HEADER_LINE_RE = re.compile(r"^\s*(?:\d+\.\s*)?[A-Z][A-Z0-9 &/()\-]{2,60}$")

# Section-header -> canonical system. Inspection reports are system-organized,
# so the section header is the strongest classification signal — stronger than
# generic stems like 'rust' (which used to steal chimney findings into HVAC).
_SECTION_SYSTEM_MAP = [
    ("roof", "ROOF"),
    ("chimney", "ROOF"),
    ("gutter", "ROOF"),
    ("plumb", "PLUMBING"),
    ("water heater", "PLUMBING"),
    ("sewer", "PLUMBING"),
    ("drain", "PLUMBING"),
    ("electric", "ELECTRICAL"),
    ("gfci", "ELECTRICAL"),
    ("hvac", "HVAC"),
    ("heating", "HVAC"),
    ("cooling", "HVAC"),
    ("furnace", "HVAC"),
    ("structur", "STRUCTURAL"),
    ("foundation", "STRUCTURAL"),
    ("exterior", "EXTERIOR"),
    ("siding", "EXTERIOR"),
    ("deck", "EXTERIOR"),
    ("interior", "INTERIOR"),
    ("attic", "ATTIC"),
    ("insulation", "INSULATION"),
    ("appliance", "APPLIANCES"),
    ("window", "WINDOWS_DOORS"),
    ("door", "WINDOWS_DOORS"),
    ("fireplace", "ROOF"),
    ("moisture", "MOISTURE"),
    ("mold", "MOISTURE"),
]

_SECTION_KEYWORDS = (
    "heating",
    "cooling",
    "roofing",
    "roof",
    "chimney",
    "plumbing",
    "electrical",
    "hvac",
    "interior",
    "exterior",
    "attic",
    "insulation",
    "structural",
    "foundation",
    "appliance",
    "window",
    "door",
    "moisture",
    "fireplace",
    "summary",
    "recommendation",
    "deficienc",
    "observation",
)


def _sanitize_extracted_text(text):
    """Strip markup residue so table/HTML/markdown never leaks into findings.

    PDF text layers regularly contain HTML tags (print-to-PDF reports),
    markdown table pipes (pymupdf4llm), page markers, and emphasis wrappers.
    """
    if not text:
        return ""
    text = _HTML_TAG_RE.sub(" ", text)
    lines = []
    for line in text.splitlines():
        if _MD_TABLE_ROW_RE.match(line):
            line = re.sub(r"^\s*\||\|\s*$", "", line)
            line = re.sub(r"\s*\|\s*", " ", line)
        lines.append(line)
    text = "\n".join(lines)
    text = _MD_NOISE_RE.sub("\n", text)
    text = _MD_WRAP_RE.sub("", text)
    text = re.sub(r"---\s*end of page=\d+\s*---", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"&;", "&", text)
    text = re.sub(r"\f", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _split_sentences_safe(text):
    """Sentence split that respects report abbreviations and merges fragments."""
    protected = _ABBREV_RE.sub(lambda m: m.group(1) + _DOT_SENTINEL, text)
    parts = re.split(r"(?<=[.!?])\s+", protected)
    sentences = []
    for part in parts:
        part = part.replace(_DOT_SENTINEL, ".").strip()
        if not part:
            continue
        while sentences and _needs_continuation(part):
            sentences[-1] = f"{sentences[-1]} {part}".strip()
            part = None
        if part is not None:
            sentences.append(part)
    return sentences


def _needs_continuation(sentence):
    """True when a split fragment clearly continues the previous sentence."""
    if not sentence:
        return False
    if sentence.count("(") != sentence.count(")"):
        return True
    if sentence[0].islower():
        return True
    # "2012, serial 4318A28479) is cracked..." — year-led continuation
    if re.match(r"^(?:19|20)\d\d\s*[,)]", sentence):
        return True
    return False


def _kw_hit(keyword, text_lower):
    """Word-START keyword match.

    Fixed-stem keywords ('rot', 'thin', 'rust') must never match inside
    unrelated words ('protected', 'within', 'robust'). Prefix-at-word-start
    still matches inflections: 'crack' -> 'cracked'/'cracking',
    'deteriorat' -> 'deteriorating', 'recommend' -> 'recommended'.
    """
    kw = str(keyword or "").strip().lower()
    if not kw or not text_lower:
        return False
    if not re.search(r"[a-z]", kw):
        return kw in text_lower
    return re.search(r"(?<![a-z])" + re.escape(kw), text_lower) is not None


def _is_noise_finding(text):
    """Drop report chrome, fragments, and header rows before they become findings."""
    raw = text or ""
    # Flattened table blob: standalone header cells on their own lines.
    # Checked against RAW text — newlines carry the signal.
    if re.search(r"(?im)^\s*(?:item|system|severity|location|recommended action)\s*$", raw):
        return True
    stripped = re.sub(r"\s+", " ", raw).strip()
    if len(stripped) < 15:
        return True
    lowered = stripped.lower()
    for pattern in _NOISE_PATTERNS:
        if pattern.search(lowered):
            return True
    tokens = [t for t in re.findall(r"[a-zA-Z']+", lowered) if len(t) > 1]
    if len(tokens) < 3:
        return True
    if stripped[0].islower():
        return True
    if stripped.endswith(":") or stripped.endswith(","):
        return True
    if stripped.count("(") != stripped.count(")"):
        return True
    # Header row: short, all-caps run with no sentence body ("2. ROOFING & CHIMNEY")
    if len(stripped) < 70 and _SECTION_HEADER_LINE_RE.match(stripped) and "." not in stripped[1:]:
        return True
    # "RECOMMENDATIONS 1." / "FINDINGS SUMMARY Item" leftovers
    if (
        re.match(r"^(?:findings?\s+)?(?:summary|recommendations?|observations?|deficiencies)\b", lowered)
        and len(tokens) < 8
    ):
        return True
    return False


def _normalize_for_dupe(text):
    text = re.sub(r"\s+", " ", (text or "").lower().strip())
    text = re.sub(r"\d+", "n", text)
    text = re.sub(r"[^a-zn\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _dup_similarity(text1, text2):
    """Jaccard AND containment — containment catches summary-table restatements."""
    words1 = set(text1.split())
    words2 = set(text2.split())
    if not words1 or not words2:
        return 0.0
    inter = len(words1.intersection(words2))
    union = len(words1.union(words2))
    jaccard = inter / union if union else 0.0
    containment = inter / min(len(words1), len(words2))
    return max(jaccard, containment)


def assign_finding_ids(findings, prefix="f"):
    """Stable per-dossier ids so bids/legal/escrow can join on exact keys."""
    for idx, finding in enumerate(findings, 1):
        if isinstance(finding, dict):
            finding.setdefault("id", f"{prefix}{idx:03d}")
            finding.setdefault("key", finding["id"])
    return findings


def extract_text_from_pdf(pdf_file):
    """Chunk-perfect extraction via PyMuPDF + pymupdf4llm (single stack).

    pdfplumber retired (duplicate). pymupdf4llm yields markdown with page
    chunks ideal for RAG; raw fitz text is the fallback. Tables via
    page.find_tables().
    """
    text_content = []
    page_texts = []
    tables_found = []
    extractor_used = "fitz"
    try:
        import fitz

        data = pdf_file.read() if hasattr(pdf_file, "read") else bytes(pdf_file)
        if hasattr(pdf_file, "seek"):
            try:
                pdf_file.seek(0)
            except Exception:
                pass
        # Preferred: pymupdf4llm markdown (chunk-perfect for RAG)
        try:
            import pymupdf4llm

            doc = fitz.open(stream=data, filetype="pdf")
            md = pymupdf4llm.to_markdown(doc)
            extractor_used = "pymupdf4llm+fitz"
            pages = re.split(r"\n\s*---\s*end of page=\d+\s*---\s*|\n\s*---\s*\n\s*|\f", md)
            for i, p in enumerate(pages):
                p = _sanitize_extracted_text(p)
                if not p.strip():
                    continue
                text_content.append(p)
                page_texts.append({"page": i + 1, "text": p, "char_count": len(p)})
            # Structured tables ride along regardless of extractor, so summary
            # rows survive as real findings even when the flattened blob is
            # filtered out as noise.
            for i, page in enumerate(doc):
                try:
                    for tb in page.find_tables():
                        df = tb.to_pandas()
                        tables_found.append(
                            {
                                "page": i + 1,
                                "rows": len(df),
                                "cols": len(df.columns),
                                "data": df.values.tolist(),
                            }
                        )
                except Exception:
                    pass
            doc.close()
        except Exception:
            doc = fitz.open(stream=data, filetype="pdf")
            for i, page in enumerate(doc):
                t = _sanitize_extracted_text(page.get_text("text") or "")
                text_content.append(t)
                page_texts.append({"page": i + 1, "text": t, "char_count": len(t)})
                try:
                    tabs = page.find_tables()
                    for tb in tabs:
                        df = tb.to_pandas()
                        tables_found.append(
                            {
                                "page": i + 1,
                                "rows": len(df),
                                "cols": len(df.columns),
                                "data": df.values.tolist(),
                            }
                        )
                except Exception:
                    pass
            doc.close()
    except Exception as e:
        text_content = [f"Error extracting text: {str(e)}"]
    return {
        "full_text": "\n\n".join(text_content),
        "page_texts": page_texts,
        "total_pages": len(text_content),
        "tables_found": tables_found,
        "char_count": sum(len(t) for t in text_content),
        "has_text_layer": any(len(t) > 50 for t in text_content),
        "extractor": extractor_used,
    }


def extract_images_from_pdf(pdf_file):
    import fitz

    images = []
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        pdf_file.seek(0)
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            for img_idx, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                if base_image:
                    images.append(
                        {
                            "page": page_num + 1,
                            "index": img_idx,
                            "image_data": base_image["image"],
                            "ext": base_image.get("ext", "png"),
                            "width": base_image.get("width", 0),
                            "height": base_image.get("height", 0),
                            "bbox": list(img[1:5]) if len(img) > 5 else None,
                        }
                    )
        doc.close()
    except Exception:
        pass
    return images


def classify_severity(text):
    text_lower = text.lower()
    for system_name, system_data in INSPECTION_SYSTEM_PATTERNS.items():
        for severity, keywords in system_data["severity_keywords"].items():
            for kw in keywords:
                if _kw_hit(kw, text_lower):
                    return severity, system_name
    if any(
        _kw_hit(w, text_lower)
        for w in [
            "dangerous",
            "immediate",
            "safety hazard",
            "fire risk",
            "gas leak",
            "collapse",
            "structural failure",
            "emergency",
            "hazardous",
            "life-threatening",
            "toxic",
            "severe risk",
            "critical condition",
            "inoperable",
            "total failure",
            "active leak",
            "flooding",
            "electrocution",
            "carbon monoxide",
        ]
    ):
        return "CRITICAL", "UNCLASSIFIED"
    if any(
        _kw_hit(w, text_lower)
        for w in [
            "broken",
            "damaged",
            "failing",
            "leak",
            "crack",
            "malfunction",
            "defective",
            "compromised",
            "severe",
            "corroded",
            "rot",
            "rust",
            "not working",
            "inoperable",
            "missing",
            "failed",
            "fractured",
            "water damage",
            "mold",
            "active moisture",
            "code violation",
            "improper",
            "unsafe",
            "hazard",
            "deteriorated",
            "deteriorating",
            "should be replaced",
            "past useful life",
            "end of useful life",
            "nearing end",
            "approaching end",
            "service life exceeded",
            "requires replacement",
            "needs immediate",
            "urgent repair",
            "substantial damage",
            "significant deterioration",
            "widespread",
            "system failure",
            "major deficiency",
            "numerous deficiencies",
        ]
    ):
        return "HIGH", "UNCLASSIFIED"
    if any(
        _kw_hit(w, text_lower)
        for w in [
            "worn",
            "aging",
            "maintenance",
            "minor",
            "recommend",
            "needs attention",
            "requires repair",
            "not functioning properly",
            "inadequate",
            "deficient",
            "substandard",
            "non-compliant",
            "outdated",
            "caulk",
            "sealant",
            "should be repaired",
            "should be serviced",
            "needs cleaning",
            "needs replacement",
            "past warranty",
            "warranty expired",
            "minor damage",
            "moderate",
            "slight",
            "partial",
            "limited",
            "maintenance item",
            "service needed",
            "service recommended",
            "operational with issues",
            "reduced efficiency",
            "declining performance",
            "should be upgraded",
            "does not meet current",
            "no longer adequate",
            "near end",
            "nearing end of life",
            "approaching end of life",
            "end of useful life",
            "past expected life",
            "overdue for",
            "neglected",
            "overdue maintenance",
            "deferred maintenance",
        ]
    ):
        return "MEDIUM", "UNCLASSIFIED"
    if any(
        _kw_hit(w, text_lower)
        for w in [
            "cosmetic",
            "normal wear",
            "routine",
            "cleaning",
            "minor paint",
            "optional",
            "suggested",
            "noted",
            "informational",
            "for reference",
            "end of life",
            "expected",
            "typical",
            "standard",
            "age noted",
            "operational",
            "functioning",
            "serviceable",
            "acceptable condition",
            "minor cosmetic",
            "superficial",
            "surface",
            "aesthetic",
            "decoration",
            "general",
            "observation",
            "informational only",
            "note",
        ]
    ):
        return "LOW", "UNCLASSIFIED"
    return "INFO", "UNCLASSIFIED"


def extract_severity_block(text):
    severity_markers = {
        "CRITICAL": [
            r"(?:safety|structural|immediate|dangerous|urgent|critical|hazard|emergency)[^.]*\.",
            r"(?:fire|gas|carbon monoxide|electrocution|collapse)[^.]*\.",
            r"(?:active leak|active water|active damage|active failure)[^.]*\.",
            r"(?:must be (?:replaced|repaired|addressed|corrected|remedied))[^.]*\.",
            r"(?:poses (?:a |an )?(?:serious |significant )?(?:risk|threat|hazard))[^.]*\.",
            r"(?:not (?:safe|habitable|usable|functional|operational))[^.]*\.",
            r"(?:requires? (?:immediate|urgent|emergency))[^.]*\.",
            r"(?:life[- ]?(?:threatening|safety))[^.]*\.",
            r"(?:in (?:danger|jeopardy|peril))[^.]*\.",
            r"(?:total (?:failure|loss|destruction))[^.]*\.",
            r"(?:active (?:gas|water|sewage|electrical))[^.]*\.",
            r"(?:exposed (?:wire|live wire|electrical|gas))[^.]*\.",
            r"(?:risk of (?:fire|collapse|flood|injury|death|electrocution))[^.]*\.",
            r"(?:do not (?:use|occupy|enter|operate))[^.]*\.",
            r"(?:condemned|red[- ]tagged|unsafe to)[^.]*\.",
        ],
        "HIGH": [
            r"(?:damaged|broken|failing|malfunction|defective|compromised|severe)[^.]*\.",
            r"(?:rust|corrosion|rot|water damage|mold|leaking|cracked|fractured)[^.]*\.",
            r"(?:code violation|not up to code|non-compliant|ungrounded)[^.]*\.",
            r"(?:should be (?:replaced|repaired|remedied|addressed|updated|upgraded))[^.]*\.",
            r"(?:past (?:useful life|end of life|warranty|expected life))[^.]*\.",
            r"(?:end of (?:useful life|service life|expected life|rated life))[^.]*\.",
            r"(?:nearing end|approaching end|near end of life)[^.]*\.",
            r"(?:service life exceeded|life expectancy exceeded)[^.]*\.",
            r"(?:needs? (?:immediate|urgent) (?:attention|repair|service|replacement))[^.]*\.",
            r"(?:requires? (?:repair|replacement|professional|certified))[^.]*\.",
            r"(?:not functioning properly|not operating correctly|not working as intended)[^.]*\.",
            r"(?:inadequate|deficient|substandard|non[- ]?compliant|outdated)[^.]*\.",
            r"(?:significant (?:damage|deterioration|wear|concern|issue|problem))[^.]*\.",
            r"(?:extensive (?:damage|deterioration|wear|cracking|leaking))[^.]*\.",
            r"(?:active (?:dripping|seepage|penetration|intrusion))[^.]*\.",
            r"(?:potential (?:hazard|danger|fire|structural))[^.]*\.",
            r"(?:may (?:cause|lead to|result in) (?:damage|failure|injury))[^.]*\.",
            r"(?:beyond (?:repair|serviceable|economic repair|reasonable repair))[^.]*\.",
            r"(?:unsanitary|unhygienic|health (?:risk|concern|hazard))[^.]*\.",
            r"(?:evidence of (?:leak|water|pest|termite|mold|rot|damage))[^.]*\.",
            r"(?:signs? of (?:leak|water|pest|termite|mold|rot|damage|failure))[^.]*\.",
            r"(?:deteriorated|degraded|degraded condition|poor condition)[^.]*\.",
            r"(?:multiple (?:deficiencies|issues|problems|failures|violations))[^.]*\.",
            r"(?:widespread (?:damage|deterioration|wear|issues|problems))[^.]*\.",
            r"(?:unable to (?:verify|confirm|determine|test|inspect))[^.]*\.",
            r"(?:missing|absent|lacking|not present|not installed)[^.]*\.",
        ],
        "MEDIUM": [
            r"(?:worn|aging|needs? (?:attention|repair|service)|should be|recommend)[^.]*\.",
            r"(?:minor|slight|moderate|partial|limited)[^.]*\.",
            r"(?:maintenance item|service item|condition|observation)[^.]*\.",
            r"(?:should be (?:inspected|monitored|evaluated|serviced|cleaned))[^.]*\.",
            r"(?:caulk(?:ing)? needed|seal(?:ant)? needed|weather(?:strip(?:ping)?)? needed)[^.]*\.",
            r"(?:shows? (?:early|some|minor|slight|moderate) (?:signs? of )?(?:wear|aging|deterioration))[^.]*\.",
            r"(?:operational with (?:limitations|concerns|issues))[^.]*\.",
            r"(?:reduced (?:efficiency|performance|capacity|lifespan))[^.]*\.",
            r"(?:declining (?:performance|efficiency|condition))[^.]*\.",
            r"(?:past (?:warranty|manufacturers? warranty))[^.]*\.",
            r"(?:does not meet (?:current|modern|updated|existing) (?:code|standard|requirement))[^.]*\.",
            r"(?:no longer (?:adequate|sufficient|optimal|effective))[^.]*\.",
            r"(?:near (?:end|capacity|maximum))[^.]*\.",
            r"(?:overdue (?:for|maintenance|service|inspection|replacement))[^.]*\.",
            r"(?:deferred (?:maintenance|repair|service))[^.]*\.",
            r"(?:neglected|mishandled|poorly (?:maintained|installed|repaired))[^.]*\.",
            r"(?:age (?:related|noted|apparent|evident))[^.]*\.",
            r"(?:minor (?:damage|crack|leak|stain|deterioration|issue|problem|concern))[^.]*\.",
            r"(?:recommended (?:to be |for )?(?:replaced|repaired|serviced|inspected|updated|upgraded))[^.]*\.",
            r"(?:suggested (?:to be |for )?(?:replaced|repaired|serviced|inspected|updated|upgraded))[^.]*\.",
            r"(?:may (?:need|require|benefit from))(?: (?:repair|replacement|service|attention|inspection|monitoring))[^.]*\.",
            r"(?:uneven|misaligned|sagging|settling|shifting|leaning)[^.]*\.",
            r"(?:loose|detached|separated|disconnected|unsecured)[^.]*\.",
            r"(?:sticking|binding|difficult to (?:open|close|operate|turn))[^.]*\.",
            r"(?:noisy|unusual noise|grinding|squeaking|rattling|vibrating)[^.]*\.",
            r"(?:fading|discoloration|staining|discolored|yellowed)[^.]*\.",
            r"(?:insufficient|inadequate|subpar|below standard|below code)[^.]*\.",
            r"(?:missing (?:cover|cap|shield|guard|grille|screen|flashing|trim))[^.]*\.",
            r"(?:intermittent|inconsistent|unreliable|erratic)[^.]*\.",
        ],
        "LOW": [
            r"(?:cosmetic|normal wear|routine|cleaning|minor paint)[^.]*\.",
            r"(?:optional|suggested|noted|informational|for reference)[^.]*\.",
            r"(?:end of life|near end|expected|typical|standard)[^.]*\.",
            r"(?:cosmetic (?:damage|issue|concern|imperfection|blemish|defect))[^.]*\.",
            r"(?:superficial|surface[- ]level|aesthetic|decorative|appearance)[^.]*\.",
            r"(?:touch[- ]?up (?:paint|caulk|sealant|grout))[^.]*\.",
            r"(?:operational|functioning|serviceable|acceptable condition|adequate)[^.]*\.",
            r"(?:minor (?:cosmetic|paint|scratch|dent|ding|chip|scuff))[^.]*\.",
            r"(?:general (?:condition|wear|maintenance|cleaning))[^.]*\.",
            r"(?:age noted|age apparent|age visible|typical wear)[^.]*\.",
            r"(?:clean(?:ing)? needed|dusting needed|washing needed)[^.]*\.",
            r"(?:routine (?:maintenance|inspection|service|care))[^.]*\.",
            r"(?:as expected|consistent with age|normal for (?:age|type))[^.]*\.",
            r"(?:no (?:significant|major|material|notable) (?:issues?|deficiencies|concerns))[^.]*\.",
            r"(?:within (?:normal|acceptable|typical|expected) (?:range|parameters|limits))[^.]*\.",
        ],
        "INFO": [
            r"(?:note|comment|observation|remark|item)[^.]*\.",
            r"(?:refer to|see (?:also|below|attached)|referenced)[^.]*\.",
            r"(?:not (?:tested|inspected|evaluated|observed|examined|checked))[^.]*\.",
            r"(?:outside (?:the )?(?:scope|inspection|visual))[^.]*\.",
            r"(?:beyond (?:the )?(?:scope|inspection|visual))[^.]*\.",
            r"(?:not (?:included|part of|covered by) (?:this )?(?:inspection|report))[^.]*\.",
            r"(?:for (?:informational|reference|documentation))[^.]*\.",
            r"(?:photograph(?:ed)? for (?:documentation|reference|record))[^.]*\.",
        ],
    }
    blocks = []
    for severity, patterns in severity_markers.items():
        for pattern in patterns:
            # Word-start guard: the stem 'rot' must never fire inside 'protected'.
            compiled = re.compile(r"(?<![a-z])" + pattern, re.IGNORECASE | re.MULTILINE)
            for match in compiled.finditer(text):
                block_text = match.group().strip()
                # Regexes cross newlines (`[^.]*`) — in flattened tables that
                # glues adjacent cells ("Utility room\nReplace furnace…").
                # Real wrapped prose reaches findings via parse_structured_
                # findings anyway, so drop cross-line blocks.
                if "\n" in block_text:
                    continue
                if len(block_text) < 25 or _is_noise_finding(block_text):
                    continue
                blocks.append(
                    {
                        "text": block_text,
                        "severity": severity,
                        "start_pos": match.start(),
                        "end_pos": match.end(),
                    }
                )
    blocks.sort(key=lambda x: x["start_pos"])
    return blocks


def classify_finding_system(text):
    text_lower = text.lower()
    direct_map = {
        "FOUNDATION": "STRUCTURAL",
        "STRUCTURAL": "STRUCTURAL",
    }
    for key, mapped in direct_map.items():
        if key.lower() in text_lower:
            return mapped
    best_match = "OTHER"
    best_score = 0
    for system_name, system_data in INSPECTION_SYSTEM_PATTERNS.items():
        score = 0
        for kw in system_data["keywords"]:
            if _kw_hit(kw, text_lower):
                score += len(kw)
        if score > best_score:
            best_score = score
            best_match = system_name
    return best_match


def extract_location_info(text):
    location_patterns = [
        r"(?:in the|located in|at the|inside the)\s+([\w\s]+(?:room|bathroom|kitchen|bedroom|basement|attic|garage|exterior|roof|crawl space|utility|laundry|hallway|closet|den|office|family room|living room|dining room|master|guest|half bath|full bath))",
        r"(?:north|south|east|west|northeast|northwest|southeast|southwest)\s+(?:wall|side|corner|section|area)\s*(?:of\s+)?([\w\s]+)?",
        r"(?:1st|2nd|3rd|4th|first|second|third|fourth|upper|lower|main)\s+floor",
        r"(?:front|rear|back|side)\s+(?:of|area|section|yard|exterior)",
    ]
    locations = []
    for pattern in location_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            loc = match.group().strip()
            if loc and len(loc) > 3:
                locations.append(loc)
    return locations[0] if locations else "Not specified"


def extract_appliance_metadata(text):
    metadata = []
    make_model_patterns = [
        r"(?:brand|make|manufacturer)[:\s]+([A-Za-z\s]+)",
        r"(Carrier|Lennox|Trane|Goodman|Rheem|A.O.\s*Smith|Bradford\s*White|GE|Samsung|LG|Whirlpool|Maytag|Kenmore|Frigidaire|Bosch|KitchenAid|Sub-Zero|Wolf|Fisher\s*&\s*Paykel|Daikin|Mitsubishi|Bryant|York|Coleman|Ruud|Payne|Armstrong|ClimateMaster)",
        r"model[:\s]+([A-Za-z0-9\-]+)",
        r"serial(?:\s+number|[:\s])[\s:]+([A-Za-z0-9]+)",
        r"(?:manufactured|mfg|built|installed|dated?)[:\s]+(\d{4})",
        r"(?:age|years old)[:\s]+(\d+)",
        r"(?:warranty|warranted)\s+(?:until|through|expires?)[:\s]+(\d{4})",
    ]
    for pattern in make_model_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            metadata.append(
                {
                    "type": pattern.split("(")[0].strip()[:20] if "(" in pattern else "info",
                    "value": match.group(1).strip() if match.lastindex else match.group().strip(),
                }
            )
    year_pattern = r"(?:20[0-2]\d|19[89]\d)"
    year_matches = re.findall(year_pattern, text)
    for ym in year_matches:
        metadata.append({"type": "year", "value": ym})
    return metadata


def deduplicate_findings(findings):
    """Collapse restatements of the same defect (narrative vs summary table vs
    recommendation list vs severity-block scrap) into ONE finding.

    Survivor = highest severity, then longest description. Group members are
    drained once — the old loop appended the survivor once per group member.
    """
    survivors = []
    seen = []  # entry per processed finding — lets late restatements join groups
    groups = defaultdict(list)
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        normalized = _normalize_for_dupe(finding.get("description", ""))
        f_sys = (finding.get("system_category") or "").strip().upper()
        f_sub = (finding.get("subsystem") or "").strip().lower()
        matched = None
        for entry in seen:
            if _dup_similarity(normalized, entry["normalized"]) > 0.55:
                matched = entry
                break
            # Same specific part + same system = same defect, different phrasing
            # ("Replace the furnace heat exchanger…" vs the narrative CRITICAL).
            e_sub = entry["subsystem"]
            if f_sub and f_sub == e_sub and f_sys and f_sys == entry["system"]:
                matched = entry
                break
        if matched is None:
            group_id = f"grp_{len(seen)}"
            finding["dedup_group"] = group_id
            seen.append(
                {
                    "normalized": normalized,
                    "group_id": group_id,
                    "system": f_sys,
                    "subsystem": f_sub,
                }
            )
            survivors.append(finding)
        else:
            group_id = matched["group_id"]
            finding["dedup_group"] = group_id
            groups[group_id].append(finding)
            seen.append(
                {
                    "normalized": normalized,
                    "group_id": group_id,
                    "system": f_sys,
                    "subsystem": f_sub,
                }
            )
    for group_id, dupes in groups.items():
        members = dupes
        primary = next((s for s in survivors if s.get("dedup_group") == group_id), None)
        if primary is None:
            continue
        all_in_group = [primary] + members
        all_in_group.sort(
            key=lambda x: (
                SeverityLevels.get(x.get("severity", "LOW"), {}).get("priority", 5),
                -len(x.get("description", "")),
            )
        )
        best = all_in_group[0]
        best["merged_count"] = len(all_in_group)
        best["merged_descriptions"] = [f.get("description", "") for f in all_in_group]
        if primary is not best:
            primary_idx = survivors.index(primary)
            survivors[primary_idx] = best
    return survivors


def _text_similarity(text1, text2):
    """Back-compat wrapper — canonical matcher is _dup_similarity."""
    return _dup_similarity(_normalize_for_dupe(text1), _normalize_for_dupe(text2))


def _is_section_header_line(line):
    """True for '2. ROOFING & CHIMNEY' / 'HEATING & COOLING (HVAC)' — never prose."""
    stripped = (line or "").strip()
    if not stripped or len(stripped) > 80:
        return False
    if re.search(r"[.;,]$|^\d+\.\d", stripped):
        return False
    if _SECTION_HEADER_LINE_RE.match(stripped):
        return True
    lower = stripped.lower()
    # Short keyword title without sentence punctuation ("Interior / General").
    # ';' / ',' means prose ("Re-flash and seal; roofing repair"), not a header.
    return (
        len(stripped.split()) <= 8
        and not re.search(r"[,;|]|[-.]$", stripped)
        and any(h in lower for h in _SECTION_KEYWORDS)
        and not stripped[0].islower()
    )


def parse_structured_findings(text, page_texts):
    findings = []
    current_section = "General"
    current_section_system = None

    def emit(buffer):
        if not buffer:
            return
        # Flattened-table region: several short terminal-less cells on
        # consecutive lines ("Utility room" / "Replace furnace, CO test…").
        # find_tables extracts those rows structurally — skip the mush here.
        cell_like = [len(ln) <= 60 and not re.search(r"[.!?;:\"]$", ln.strip()) for ln in buffer]
        if len(buffer) >= 2 and all(cell_like):
            return
        block = "\n".join(buffer).strip()
        if len(block) < 15:
            return
        for sentence in _split_sentences_safe(block):
            sentence = sentence.strip()
            # Noise check sees RAW newlines (flattened-table signal),
            # then wrap newlines collapse to spaces for display.
            if _is_noise_finding(sentence):
                continue
            sentence = re.sub(r"\s*\n\s*", " ", sentence).strip()
            if len(sentence) < 15:
                continue
            if any(
                skip in sentence.lower()
                for skip in [
                    " inspector",
                    " this report",
                    " the buyer",
                    " the seller",
                    " disclaimer",
                    "limitation of liability",
                ]
            ):
                continue
            severity, system = classify_severity(sentence)
            loc = extract_location_info(sentence)
            # System priority: section header > multi-keyword scoring >
            # single-keyword severity hit (which misfiles chimney prose as
            # EXTERIOR because 'damaged' fires before any ROOF keyword).
            if current_section_system:
                sys_cat = current_section_system
            else:
                scored = classify_finding_system(sentence)
                if scored != "OTHER":
                    sys_cat = scored
                else:
                    sys_cat = system if system != "UNCLASSIFIED" else "OTHER"
            findings.append(
                {
                    "description": sentence,
                    "severity": severity,
                    "severity_score": SeverityLevels.get(severity, {}).get("priority", 5),
                    "system_category": sys_cat,
                    "location": loc,
                    "component": current_section,
                    "subsystem": _extract_sub_component(sentence),
                    "source_section": current_section,
                    "confidence_score": score_finding(
                        sentence,
                        severity=severity,
                        location=loc,
                        system=sys_cat,
                        source_type="pdf",
                    ),
                }
            )

    # A1: line-based header scan — headers ride single newlines in real PDFs,
    # so blank-line section splitting left them glued to the first finding.
    buffer = []
    for line in (text or "").splitlines():
        if _is_section_header_line(line):
            emit(buffer)
            buffer = []
            current_section = line.strip()
            current_section_system = None
            lower = current_section.lower()
            for needle, sysname in _SECTION_SYSTEM_MAP:
                if needle in lower:
                    current_section_system = sysname
                    break
            continue
        if not line.strip():
            emit(buffer)
            buffer = []
            continue
        buffer.append(line)
    emit(buffer)
    return findings


def _extract_sub_component(text):
    text_lower = text.lower()
    sub_components = {
        "heat exchanger": "heat exchanger",
        "inducer motor": "inducer motor",
        "blower motor": "blower motor",
        "compressor": "compressor",
        "evaporator": "evaporator coil",
        "condenser": "condenser",
        "capacitor": "capacitor",
        "thermostat": "thermostat",
        "flashing": "flashing",
        "shingle": "shingles",
        "gutter": "gutters",
        "soffit": "soffit",
        "fascia": "fascia",
        "step flashing": "step flashing",
        "gfci": "GFCI outlet",
        "afci": "AFCI breaker",
        "panel": "electrical panel",
        "subpanel": "subpanel",
        "breaker": "breaker",
        "outlet": "outlet",
        "switch": "switch",
        "pipe": "pipe",
        "drain": "drain",
        "faucet": "faucet",
        "toilet": "toilet",
        "water heater": "water heater",
        "sewer": "sewer line",
        "trap": "trap",
        "valve": "valve",
        "foundation": "foundation",
        "crack": "crack",
        "beam": "beam",
        "joist": "joist",
        "siding": "siding",
        "paint": "paint",
        "deck": "deck",
        "railing": "railing",
        "window": "window",
        "door": "door",
        "insulation": "insulation",
        "vapor barrier": "vapor barrier",
        "mold": "mold",
        "moisture": "moisture",
        "water stain": "water stain",
        "smoke detector": "smoke detector",
        "carbon monoxide": "CO detector",
        "fireplace": "fireplace",
        "chimney": "chimney",
    }
    for keyword, component in sub_components.items():
        if keyword in text_lower:
            return component
    return ""


def extract_findings_from_tables(tables_found):
    findings = []
    finding_keywords = [
        "deficien",
        "issue",
        "problem",
        "concern",
        "damage",
        "defect",
        "fail",
        "broken",
        "missing",
        "leak",
        "crack",
        "corrosion",
        "rot",
        "mold",
        "unsafe",
        "hazard",
        "replace",
        "repair",
        "maintenance",
        "service",
        "inadequate",
        "deficient",
        "substandard",
        "non-compliant",
        "outdated",
        "deteriorat",
        "worn",
        "aging",
        "end of life",
        "past useful life",
        "needs attention",
        "requires repair",
        "should be",
        "recommend",
        "not functioning",
        "improper",
        "code violation",
        "observation",
    ]
    severity_keywords = {
        "CRITICAL": [
            "critical",
            "immediate",
            "dangerous",
            "hazard",
            "emergency",
            "safety",
            "structural failure",
            "active leak",
            "fire",
            "gas leak",
            "collapse",
            "unsafe",
            "do not use",
            "red tag",
        ],
        "HIGH": [
            "high",
            "severe",
            "damaged",
            "broken",
            "failing",
            "leaking",
            "cracked",
            "corroded",
            "rot",
            "mold",
            "replacement needed",
            "end of life",
            "past useful life",
            "not functioning",
            "code violation",
            "major",
            "significant",
        ],
        "MEDIUM": [
            "medium",
            "moderate",
            "worn",
            "aging",
            "maintenance",
            "service needed",
            "needs attention",
            "recommend",
            "caulk",
            "seal",
            "should be repaired",
            "minor issue",
            "monitoring",
        ],
        "LOW": [
            "low",
            "cosmetic",
            "minor",
            "normal wear",
            "routine",
            "cleaning",
            "optional",
            "suggested",
            "informational",
        ],
        "INFO": ["informational", "note", "observation", "comment", "noted"],
    }
    for table_info in tables_found:
        rows = table_info.get("data", [])
        if not rows or len(rows) < 2:
            continue
        header_row = rows[0]
        severity_col = -1
        desc_col = -1
        item_col = -1
        for idx, cell in enumerate(header_row):
            if not cell:
                continue
            cell_lower = str(cell).lower()
            if any(w in cell_lower for w in ["severity", "priority", "rating", "risk", "level"]):
                severity_col = idx
            if any(
                w in cell_lower
                for w in [
                    "description",
                    "finding",
                    "detail",
                    "comment",
                    "note",
                    "observation",
                    "item",
                    "condition",
                ]
            ):
                desc_col = idx
            if any(w in cell_lower for w in ["item", "component", "system", "area", "location"]):
                if item_col == -1:
                    item_col = idx
        if desc_col == -1:
            desc_col = 0
        for row in rows[1:]:
            if not row or all(not cell for cell in row):
                continue
            description = str(row[desc_col]).strip() if desc_col < len(row) and row[desc_col] else ""
            if not description or len(description) < 10:
                continue
            description = re.sub(r"\s+", " ", description)
            if _is_noise_finding(description):
                continue
            has_finding_keyword = any(_kw_hit(kw, description.lower()) for kw in finding_keywords)
            if not has_finding_keyword:
                continue
            table_severity = "INFO"
            if severity_col >= 0 and severity_col < len(row) and row[severity_col]:
                sev_text = str(row[severity_col]).lower().strip()
                for sev, kw_list in severity_keywords.items():
                    if any(kw in sev_text for kw in kw_list):
                        table_severity = sev
                        break
                if table_severity == "INFO":
                    if any(w in sev_text for w in ["1", "a", "critical"]):
                        table_severity = "CRITICAL"
                    elif any(w in sev_text for w in ["2", "b", "high"]):
                        table_severity = "HIGH"
                    elif any(w in sev_text for w in ["3", "c", "medium", "moderate"]):
                        table_severity = "MEDIUM"
                    elif any(w in sev_text for w in ["4", "d", "low", "minor"]):
                        table_severity = "LOW"
            if table_severity == "INFO":
                _, sys_guess = classify_severity(description)
                classified_sev, _ = classify_severity(description)
                if classified_sev != "INFO":
                    table_severity = classified_sev
            component = ""
            if item_col >= 0 and item_col < len(row) and row[item_col]:
                component = str(row[item_col]).strip()
            system = classify_finding_system(description)
            full_text = f"{component}: {description}" if component else description
            finding = {
                "description": full_text,
                "severity": table_severity,
                "severity_score": SeverityLevels.get(table_severity, {}).get("priority", 5),
                "system_category": system,
                "location": extract_location_info(full_text),
                "component": component or "Table Finding",
                "subsystem": _extract_sub_component(full_text),
                "source_section": f"Table (Page {table_info.get('page', '?')})",
                "confidence_score": score_finding(
                    full_text,
                    severity=table_severity,
                    location=extract_location_info(full_text),
                    system=system,
                    source_type="pdf",
                ),
            }
            findings.append(finding)
    return findings


def _extract_list_items(text):
    findings = []
    list_patterns = [
        r"(?:^|\n)\s*(?:\d+[\.\)]\s+)(.+?)(?=\n|\d+[\.\)]|$)",
        r"(?:^|\n)\s*(?:[-\u2013\u2014]\s+)(.+?)(?=\n|$)",
        r"(?:^|\n)\s*(?:[•\u2022\u25cf\u25cb]\s+)(.+?)(?=\n|$)",
        r"(?:^|\n)\s*(?:[a-z][\.\)]\s+)(.+?)(?=\n|$)",
        r"(?:^|\n)\s*(?:\([a-z]\)\s+)(.+?)(?=\n|$)",
    ]
    finding_keywords = [
        "deficien",
        "issue",
        "problem",
        "concern",
        "damage",
        "defect",
        "fail",
        "broken",
        "missing",
        "leak",
        "crack",
        "corrosion",
        "rot",
        "mold",
        "unsafe",
        "hazard",
        "replace",
        "repair",
        "maintenance",
        "service",
        "inadequate",
        "deficient",
        "substandard",
        "non-compliant",
        "outdated",
        "deteriorat",
        "worn",
        "aging",
        "end of life",
        "past useful life",
        "needs attention",
        "requires repair",
        "should be",
        "recommend",
        "not functioning",
        "improper",
        "code violation",
        "observation",
        "caulk",
        "seal",
        "stain",
        "cosmetic",
        "damage",
        "not operating",
    ]
    seen = set()
    for pattern in list_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            item_text = match.group(1).strip() if match.lastindex else match.group(0).strip()
            item_text = re.sub(r"\s+", " ", item_text).strip()
            if len(item_text) < 12:
                continue
            item_lower = item_text.lower()
            if _is_noise_finding(item_text):
                continue
            has_keyword = any(_kw_hit(kw, item_lower) for kw in finding_keywords)
            if not has_keyword:
                continue
            text_hash = hashlib.md5(item_lower.encode()).hexdigest()[:10]
            if text_hash in seen:
                continue
            seen.add(text_hash)
            severity, system = classify_severity(item_text)
            finding = {
                "description": item_text,
                "severity": severity,
                "severity_score": SeverityLevels.get(severity, {}).get("priority", 5),
                "system_category": system if system != "UNCLASSIFIED" else classify_finding_system(item_text),
                "location": extract_location_info(item_text),
                "component": "List Item",
                "subsystem": _extract_sub_component(item_text),
                "source_section": "List Extraction",
                "confidence_score": score_finding(
                    item_text,
                    severity=severity,
                    location=extract_location_info(item_text),
                    system=system,
                    source_type="pdf",
                ),
            }
            findings.append(finding)
    return findings


def _already_present(candidate_text, findings):
    """Cross-source duplicate guard: containment, not just shared prefix."""
    norm = _normalize_for_dupe(candidate_text)
    for f in findings:
        if _dup_similarity(norm, _normalize_for_dupe(f.get("description", ""))) > 0.55:
            return True
    return False


def process_uploaded_report(pdf_file):
    extraction_result = extract_text_from_pdf(pdf_file)
    images = extract_images_from_pdf(pdf_file)
    text = extraction_result["full_text"]
    findings = parse_structured_findings(text, extraction_result["page_texts"])
    severity_blocks = extract_severity_block(text)
    for block in severity_blocks:
        if _is_noise_finding(block["text"]) or _already_present(block["text"], findings):
            continue
        system = classify_finding_system(block["text"])
        findings.append(
            {
                "description": block["text"],
                "severity": block["severity"],
                "severity_score": SeverityLevels.get(block["severity"], {}).get("priority", 5),
                "system_category": system,
                "location": extract_location_info(block["text"]),
                "component": "Parsed Block",
                "subsystem": _extract_sub_component(block["text"]),
                "source_section": "Severity Parser",
                "confidence_score": score_finding(
                    block["text"],
                    severity=block["severity"],
                    location=extract_location_info(block["text"]),
                    system=system,
                    source_type="pdf",
                ),
            }
        )
    for tf in extract_findings_from_tables(extraction_result["tables_found"]):
        if _already_present(tf["description"], findings):
            continue
        findings.append(tf)
    for lf in _extract_list_items(text):
        if _already_present(lf["description"], findings):
            continue
        findings.append(lf)
    deduplicated = deduplicate_findings(findings)
    for finding in deduplicated:
        finding["photos_matched"] = _match_photos_to_finding(finding, images, text)
    assign_finding_ids(deduplicated, prefix="f")
    return {
        "full_text": text,
        "page_texts": extraction_result["page_texts"],
        "total_pages": extraction_result["total_pages"],
        "tables_found": extraction_result["tables_found"],
        "images": images,
        "findings": deduplicated,
        "severity_blocks": severity_blocks,
        "extraction_stats": {
            "char_count": extraction_result["char_count"],
            "image_count": len(images),
            "table_count": len(extraction_result["tables_found"]),
            "finding_count": len(deduplicated),
            "has_text_layer": extraction_result["has_text_layer"],
            "extractor": extraction_result.get("extractor", "unknown"),
        },
    }


def _match_photos_to_finding(finding, images, full_text):
    matched = []
    desc = finding["description"]
    desc_words = set(desc.lower().split())
    desc_words = {w for w in desc_words if len(w) > 3}
    for img in images:
        page_text = ""
        for pt in [{"page": i + 1, "text": t} for i, t in enumerate(full_text.split("\n\n"))]:
            if pt["page"] == img["page"]:
                page_text = pt["text"]
                break
        page_words = set(page_text.lower().split())
        overlap = len(desc_words.intersection(page_words))
        if overlap >= 2 or finding["system_category"].lower() in page_text.lower():
            matched.append(img)
    return matched[:3] if matched else []
