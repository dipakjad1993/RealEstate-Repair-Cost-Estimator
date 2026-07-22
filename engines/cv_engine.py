from engines.parser_engine import extract_images_from_pdf, _match_photos_to_finding

def analyze_photo_evidence(pdf_file, findings):
    images = extract_images_from_pdf(pdf_file)
    photo_analysis = {
        "total_images_extracted": len(images),
        "images_by_page": {},
        "matched_photos": {},
        "unmatched_photos": [],
        "photo_quality_notes": [],
    }
    for img in images:
        page = img.get("page", 0)
        if page not in photo_analysis["images_by_page"]:
            photo_analysis["images_by_page"][page] = []
        photo_analysis["images_by_page"][page].append({
            "index": img.get("index", 0),
            "width": img.get("width", 0),
            "height": img.get("height", 0),
            "ext": img.get("ext", "png"),
            "has_bbox": img.get("bbox") is not None,
        })
        w = img.get("width", 0)
        h = img.get("height", 0)
        if w > 0 and h > 0:
            aspect = w / h
            if aspect > 3 or aspect < 0.33:
                photo_analysis["photo_quality_notes"].append(f"Page {page}: Unusual aspect ratio ({aspect:.1f}) - may be diagram/figure")
            if w < 100 or h < 100:
                photo_analysis["photo_quality_notes"].append(f"Page {page}: Small image ({w}x{h}) - likely icon/logo")
        if img.get("bbox"):
            photo_analysis["photo_quality_notes"].append(f"Page {page}: Image has position data - likely embedded photo with layout context")
    for finding in findings:
        matched = finding.get("photos_matched", [])
        if matched:
            photo_analysis["matched_photos"][finding.get("description", "")[:60]] = {
                "finding": finding.get("description", "")[:100],
                "severity": finding.get("severity", "N/A"),
                "system": finding.get("system_category", "N/A"),
                "photo_count": len(matched),
                "photo_details": [{
                    "page": m.get("page", 0),
                    "size": f"{m.get('width', 0)}x{m.get('height', 0)}",
                } for m in matched],
            }
    total_matched = sum(len(v.get("photo_details", [])) for v in photo_analysis["matched_photos"].values())
    photo_analysis["unmatched_count"] = max(0, len(images) - total_matched)
    photo_analysis["match_rate"] = round(total_matched / max(len(images), 1) * 100, 1)
    return photo_analysis

def create_evidence_summary(findings, photo_analysis):
    summary = {
        "critical_with_photos": [],
        "high_with_photos": [],
        "medium_with_photos": [],
        "findings_missing_photos": [],
    }
    for finding in findings:
        severity = finding.get("severity", "LOW")
        desc = finding.get("description", "")[:80]
        has_photo = desc[:60] in photo_analysis.get("matched_photos", {})
        entry = {"description": desc, "severity": severity, "system": finding.get("system_category", "N/A")}
        if has_photo:
            entry["photo_count"] = photo_analysis["matched_photos"][desc[:60]].get("photo_count", 0)
            if severity == "CRITICAL":
                summary["critical_with_photos"].append(entry)
            elif severity == "HIGH":
                summary["high_with_photos"].append(entry)
            else:
                summary["medium_with_photos"].append(entry)
        else:
            summary["findings_missing_photos"].append(entry)
    return summary
