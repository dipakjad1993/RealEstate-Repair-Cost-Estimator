import re
import json
import hashlib
from collections import defaultdict
from config import INSPECTION_SYSTEM_PATTERNS, SeverityLevels

def extract_text_from_pdf(pdf_file):
    import pdfplumber
    text_content = []
    page_texts = []
    tables_found = []
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                text_content.append(page_text)
                page_texts.append({"page": i + 1, "text": page_text, "char_count": len(page_text)})
                page_tables = page.extract_tables()
                if page_tables:
                    for table in page_tables:
                        if table:
                            tables_found.append({"page": i + 1, "rows": len(table), "cols": len(table[0]) if table else 0, "data": table})
    except Exception as e:
        text_content = [f"Error extracting text: {str(e)}"]
    return {
        "full_text": "\n\n".join(text_content),
        "page_texts": page_texts,
        "total_pages": len(text_content),
        "tables_found": tables_found,
        "char_count": sum(len(t) for t in text_content),
        "has_text_layer": any(len(t) > 50 for t in text_content)
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
                    images.append({
                        "page": page_num + 1,
                        "index": img_idx,
                        "image_data": base_image["image"],
                        "ext": base_image.get("ext", "png"),
                        "width": base_image.get("width", 0),
                        "height": base_image.get("height", 0),
                        "bbox": list(img[1:5]) if len(img) > 5 else None
                    })
        doc.close()
    except Exception:
        pass
    return images

def classify_severity(text):
    text_lower = text.lower()
    for system_name, system_data in INSPECTION_SYSTEM_PATTERNS.items():
        for severity, keywords in system_data["severity_keywords"].items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    return severity, system_name
    if any(w in text_lower for w in [
        "dangerous", "immediate", "safety hazard", "fire risk", "gas leak",
        "collapse", "structural failure", "emergency", "hazardous", "life-threatening",
        "toxic", "severe risk", "critical condition", "inoperable", "total failure",
        "active leak", "flooding", "electrocution", "carbon monoxide",
    ]):
        return "CRITICAL", "UNCLASSIFIED"
    if any(w in text_lower for w in [
        "broken", "damaged", "failing", "leak", "crack", "malfunction",
        "defective", "compromised", "severe", "corroded", "rot", "rust",
        "not working", "inoperable", "missing", "failed", "fractured",
        "water damage", "mold", "active moisture", "code violation",
        "improper", "unsafe", "hazard", "deteriorated", "deteriorating",
        "should be replaced", "past useful life", "end of useful life",
        "nearing end", "approaching end", "service life exceeded",
        "requires replacement", "needs immediate", "urgent repair",
        "substantial damage", "significant deterioration", "widespread",
        "system failure", "major deficiency", "numerous deficiencies",
    ]):
        return "HIGH", "UNCLASSIFIED"
    if any(w in text_lower for w in [
        "worn", "aging", "maintenance", "minor", "recommend", "needs attention",
        "requires repair", "not functioning properly", "inadequate", "deficient",
        "substandard", "non-compliant", "outdated", "caulk", "sealant",
        "should be repaired", "should be serviced", "needs cleaning",
        "needs replacement", "past warranty", "warranty expired",
        "minor damage", "moderate", "slight", "partial", "limited",
        "maintenance item", "service needed", "service recommended",
        "operational with issues", "reduced efficiency", "declining performance",
        "should be upgraded", "does not meet current", "no longer adequate",
        "near end", "nearing end of life", "approaching end of life",
        "end of useful life", "past expected life", "overdue for",
        "neglected", "overdue maintenance", "deferred maintenance",
    ]):
        return "MEDIUM", "UNCLASSIFIED"
    if any(w in text_lower for w in [
        "cosmetic", "normal wear", "routine", "cleaning", "minor paint",
        "optional", "suggested", "noted", "informational", "for reference",
        "end of life", "expected", "typical", "standard", "age noted",
        "operational", "functioning", "serviceable", "acceptable condition",
        "minor cosmetic", "superficial", "surface", "aesthetic", "decoration",
        "general", "observation", "informational only", "note",
    ]):
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
        ]
    }
    blocks = []
    for severity, patterns in severity_markers.items():
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                blocks.append({
                    "text": match.group().strip(),
                    "severity": severity,
                    "start_pos": match.start(),
                    "end_pos": match.end()
                })
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
            if kw.lower() in text_lower:
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
            metadata.append({
                "type": pattern.split("(")[0].strip()[:20] if "(" in pattern else "info",
                "value": match.group(1).strip() if match.lastindex else match.group().strip()
            })
    year_pattern = r"(?:20[0-2]\d|19[89]\d)"
    year_matches = re.findall(year_pattern, text)
    for ym in year_matches:
        metadata.append({"type": "year", "value": ym})
    return metadata

def deduplicate_findings(findings):
    seen_hashes = {}
    deduplicated = []
    duplicate_groups = defaultdict(list)
    for finding in findings:
        desc = finding.get("description", "")
        normalized = re.sub(r'\s+', ' ', desc.lower().strip())
        normalized = re.sub(r'\d+', 'N', normalized)
        text_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]
        similar = False
        for existing_hash in list(seen_hashes.keys()):
            if _text_similarity(normalized, seen_hashes[existing_hash]["normalized"]) > 0.65:
                similar = True
                group_id = seen_hashes[existing_hash]["group"]
                duplicate_groups[group_id].append(finding)
                finding["dedup_group"] = group_id
                break
        if not similar:
            group_id = f"grp_{len(seen_hashes)}"
            finding["dedup_group"] = group_id
            seen_hashes[text_hash] = {"normalized": normalized, "group": group_id}
        deduplicated.append(finding)
    unique_findings = []
    for finding in deduplicated:
        group = finding.get("dedup_group", "")
        if group in duplicate_groups:
            all_in_group = [finding] + duplicate_groups[group]
            all_in_group.sort(key=lambda x: SeverityLevels.get(x.get("severity", "LOW"), {}).get("priority", 5))
            best = all_in_group[0]
            best["merged_count"] = len(all_in_group)
            best["merged_descriptions"] = [f.get("description", "") for f in all_in_group]
            unique_findings.append(best)
        else:
            unique_findings.append(finding)
    return unique_findings

def _text_similarity(text1, text2):
    words1 = set(text1.split())
    words2 = set(text2.split())
    if not words1 or not words2:
        return 0.0
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union) if union else 0.0

def parse_structured_findings(text, page_texts):
    findings = []
    sections = re.split(r'\n{2,}|\r\n{2,}', text)
    section_headers = [
        "roofing", "roof", "plumbing", "electrical", "hvac", "heating", "cooling",
        "structural", "foundation", "exterior", "interior", "insulation", "windows",
        "doors", "fireplace", "chimney", "garage", "appliance", "moisture",
        "ventilation", "grading", "drainage", "siding", "deck", "porch", "balcony",
        "crawl space", "basement", "attic", "summary", "findings", "deficiencies",
        "recommendations", "concerns", "observations", "conditions", "items",
        "issues", "problems", "repair", "maintenance", "safety", "code",
        "deficiency", "deficiencies", "note", "notes", "comment", "comments",
    ]
    current_section = "General"
    for section in sections:
        section_stripped = section.strip()
        if not section_stripped or len(section_stripped) < 15:
            continue
        first_line = section_stripped.split('\n')[0].lower().strip().rstrip(':')
        for header in section_headers:
            if header in first_line and len(first_line) < 60:
                current_section = header.title()
                break
        sentences = re.split(r'(?<=[.!?])\s+', section_stripped)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 15:
                continue
            if any(skip in sentence.lower() for skip in [" inspector", " this report", " the buyer", " the seller", " disclaimer"]):
                continue
            severity, system = classify_severity(sentence)
            finding = {
                "description": sentence,
                "severity": severity,
                "severity_score": SeverityLevels.get(severity, {}).get("priority", 5),
                "system_category": system if system != "UNCLASSIFIED" else classify_finding_system(sentence),
                "location": extract_location_info(sentence),
                "component": current_section,
                "subsystem": _extract_sub_component(sentence),
                "source_section": current_section,
                "confidence_score": 0.85 if severity in ["CRITICAL", "HIGH"] else 0.75
            }
            findings.append(finding)
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
        "deficien", "issue", "problem", "concern", "damage", "defect", "fail",
        "broken", "missing", "leak", "crack", "corrosion", "rot", "mold",
        "unsafe", "hazard", "replace", "repair", "maintenance", "service",
        "inadequate", "deficient", "substandard", "non-compliant", "outdated",
        "deteriorat", "worn", "aging", "end of life", "past useful life",
        "needs attention", "requires repair", "should be", "recommend",
        "not functioning", "improper", "code violation", "observation",
    ]
    severity_keywords = {
        "CRITICAL": ["critical", "immediate", "dangerous", "hazard", "emergency",
                      "safety", "structural failure", "active leak", "fire", "gas leak",
                      "collapse", "unsafe", "do not use", "red tag"],
        "HIGH": ["high", "severe", "damaged", "broken", "failing", "leaking",
                 "cracked", "corroded", "rot", "mold", "replacement needed",
                 "end of life", "past useful life", "not functioning",
                 "code violation", "major", "significant"],
        "MEDIUM": ["medium", "moderate", "worn", "aging", "maintenance",
                   "service needed", "needs attention", "recommend", "caulk",
                   "seal", "should be repaired", "minor issue", "monitoring"],
        "LOW": ["low", "cosmetic", "minor", "normal wear", "routine",
                "cleaning", "optional", "suggested", "informational"],
        "INFO": ["informational", "note", "observation", "comment", "noted"],
    }
    for table_info in tables_found:
        rows = table_info.get("data", [])
        if not rows or len(rows) < 2:
            continue
        header_row = rows[0]
        header_text = " ".join(str(cell).lower() for cell in header_row if cell)
        severity_col = -1
        desc_col = -1
        item_col = -1
        for idx, cell in enumerate(header_row):
            if not cell:
                continue
            cell_lower = str(cell).lower()
            if any(w in cell_lower for w in ["severity", "priority", "rating", "risk", "level"]):
                severity_col = idx
            if any(w in cell_lower for w in ["description", "finding", "detail", "comment", "note", "observation", "item", "condition"]):
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
            has_finding_keyword = any(kw in description.lower() for kw in finding_keywords)
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
                "confidence_score": 0.70
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
        "deficien", "issue", "problem", "concern", "damage", "defect", "fail",
        "broken", "missing", "leak", "crack", "corrosion", "rot", "mold",
        "unsafe", "hazard", "replace", "repair", "maintenance", "service",
        "inadequate", "deficient", "substandard", "non-compliant", "outdated",
        "deteriorat", "worn", "aging", "end of life", "past useful life",
        "needs attention", "requires repair", "should be", "recommend",
        "not functioning", "improper", "code violation", "observation",
        "caulk", "seal", "stain", "cosmetic", "damage", "not operating",
    ]
    seen = set()
    for pattern in list_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            item_text = match.group(1).strip() if match.lastindex else match.group(0).strip()
            item_text = re.sub(r'\s+', ' ', item_text).strip()
            if len(item_text) < 12:
                continue
            item_lower = item_text.lower()
            has_keyword = any(kw in item_lower for kw in finding_keywords)
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
                "confidence_score": 0.65
            }
            findings.append(finding)
    return findings

def process_uploaded_report(pdf_file):
    extraction_result = extract_text_from_pdf(pdf_file)
    images = extract_images_from_pdf(pdf_file)
    text = extraction_result["full_text"]
    findings = parse_structured_findings(text, extraction_result["page_texts"])
    severity_blocks = extract_severity_block(text)
    for block in severity_blocks:
        already_found = any(
            _text_similarity(block["text"][:100], f["description"][:100]) > 0.5
            for f in findings
        )
        if not already_found:
            system = classify_finding_system(block["text"])
            findings.append({
                "description": block["text"],
                "severity": block["severity"],
                "severity_score": SeverityLevels.get(block["severity"], {}).get("priority", 5),
                "system_category": system,
                "location": extract_location_info(block["text"]),
                "component": "Parsed Block",
                "subsystem": _extract_sub_component(block["text"]),
                "source_section": "Severity Parser",
                "confidence_score": 0.80
            })
    table_findings = extract_findings_from_tables(extraction_result["tables_found"])
    for tf in table_findings:
        already_found = any(
            _text_similarity(tf["description"][:100], f["description"][:100]) > 0.5
            for f in findings
        )
        if not already_found:
            findings.append(tf)
    list_findings = _extract_list_items(text)
    for lf in list_findings:
        already_found = any(
            _text_similarity(lf["description"][:100], f["description"][:100]) > 0.5
            for f in findings
        )
        if not already_found:
            findings.append(lf)
    deduplicated = deduplicate_findings(findings)
    for finding in deduplicated:
        finding["photos_matched"] = _match_photos_to_finding(finding, images, text)
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
            "has_text_layer": extraction_result["has_text_layer"]
        }
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
