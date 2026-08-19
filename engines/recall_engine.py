"""
Product Recall Engine - Real Data
=================================
Uses real CPSC SaferProducts.gov API for product recall data.

Data Source:
- U.S. Consumer Product Safety Commission (CPSC) Recall Retrieval Web Services
- API: https://www.saferproducts.gov/RestWebServices/Recall
- Docs: https://www.cpsc.gov/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information

All recall data comes directly from the official CPSC database.
"""

import logging
from engines.real_data_fetcher import (
    search_cpsc_recalls,
)

logger = logging.getLogger(__name__)

# Mapping of inspection finding keywords to CPSC recall search terms
FINDING_TO_RECALL_MAP = {
    "federal pacific": {"keyword": "Federal Pacific", "product": "electrical panel"},
    "zinsco": {"keyword": "Zinsco", "product": "electrical panel"},
    "stab-lok": {"keyword": "Stab-Lok", "product": "circuit breaker"},
    "stab lok": {"keyword": "Stab-Lok", "product": "circuit breaker"},
    "fire": {"keyword": "fire hazard", "product": ""},
    "carbon monoxide": {"keyword": "carbon monoxide", "product": "detector"},
    "whirlpool": {"keyword": "Whirlpool", "product": ""},
    "water heater": {"keyword": "water heater", "product": ""},
    "furnace": {"keyword": "furnace", "product": ""},
    "hvac": {"keyword": "HVAC", "product": ""},
    "dryer": {"keyword": "dryer", "product": ""},
    "dishwasher": {"keyword": "dishwasher", "product": ""},
    "refrigerator": {"keyword": "refrigerator", "product": ""},
    "stove": {"keyword": "stove", "product": ""},
    "oven": {"keyword": "oven", "product": ""},
    "microwave": {"keyword": "microwave", "product": ""},
    "smoke detector": {"keyword": "smoke detector", "product": ""},
    "smoke alarm": {"keyword": "smoke alarm", "product": ""},
    "space heater": {"keyword": "space heater", "product": ""},
    "generator": {"keyword": "generator", "product": ""},
    "pressure cooker": {"keyword": "pressure cooker", "product": ""},
    "battery": {"keyword": "battery fire", "product": ""},
    "lithium": {"keyword": "lithium battery", "product": ""},
    "window": {"keyword": "window blind", "product": ""},
    "blind": {"keyword": "window blind", "product": ""},
    "crib": {"keyword": "crib", "product": ""},
    "baby": {"keyword": "baby", "product": ""},
    "child": {"keyword": "child safety", "product": ""},
    "lead": {"keyword": "lead paint", "product": ""},
    "asbestos": {"keyword": "asbestos", "product": ""},
}


def check_recalls_for_findings(findings):
    """
    Check inspection findings against REAL CPSC recall database.
    
    Queries the official CPSC SaferProducts.gov API to find active recalls
    matching the inspection findings.
    
    Source: U.S. Consumer Product Safety Commission (CPSC) - LIVE DATA
    """
    results = []
    already_checked = set()
    
    for finding in findings:
        desc = finding.get("description", "").lower()
        subsystem = finding.get("subsystem", "").lower()
        combined_text = f"{desc} {subsystem}"
        
        # Find matching recall search terms
        matched_searches = []
        for keyword, recall_info in FINDING_TO_RECALL_MAP.items():
            if keyword in combined_text:
                search_key = recall_info["keyword"]
                if search_key not in already_checked:
                    matched_searches.append(recall_info)
                    already_checked.add(search_key)
        
        # Query CPSC API for each matched recall type
        for search in matched_searches:
            try:
                keyword = search["keyword"]
                product = search["product"]
                
                recall_data = search_cpsc_recalls(
                    keyword=keyword,
                    product=product,
                    max_results=5,
                )
                
                recall_value = recall_data.value if recall_data else None
                
                if recall_value:
                    for recall in recall_value:
                        results.append({
                            "finding_id": finding.get("id"),
                            "finding_description": finding.get("description", "")[:100],
                            "system": finding.get("system_category", "OTHER"),
                            "recall_number": recall.get("recall_number", ""),
                            "recall_title": recall.get("title", ""),
                            "recall_date": recall.get("recall_date", ""),
                            "recall_url": recall.get("url", ""),
                            "hazard_types": recall.get("hazard_types", []),
                            "product_names": recall.get("product_names", []),
                            "manufacturers": recall.get("manufacturers", []),
                            "remedy": recall.get("remedy", ""),
                            "remedy_type": recall.get("remedy_type", ""),
                            "injury_reports": recall.get("injury_descriptions", []),
                            "description": recall.get("description", "")[:500],
                            "source": "CPSC SaferProducts.gov - U.S. Consumer Product Safety Commission (LIVE DATA)",
                            "action_required": _get_recall_action(recall),
                            "cost_savings": _estimate_recall_savings(finding, recall),
                        })
                        
            except Exception as e:
                logger.error(f"CPSC API error for keyword '{search['keyword']}': {e}")
                continue
    
    total_savings = sum(r["cost_savings"] for r in results)
    
    return {
        "recall_results": results,
        "summary": {
            "total_recalls_found": len(results),
            "total_potential_savings": round(total_savings, 0),
            "active_recalls": len([r for r in results if "recall" in r.get("action_required", "").lower()]),
            "source": "CPSC SaferProducts.gov API - LIVE DATA",
            "api_status": "connected" if results else "no_matches",
        },
    }


def check_specific_product(product_name: str, manufacturer: str = ""):
    """
    Check a specific product against the CPSC recall database.
    Useful for checking a specific model/brand found during inspection.
    """
    res = search_cpsc_recalls(keyword=product_name or manufacturer, max_results=10)
    return {"status": res.provenance.status, "source": res.provenance.source,
            "recalls": res.value or []}


def _get_recall_action(recall):
    """Generate action recommendation based on real recall data."""
    remedy_type = recall.get("remedy_type", "")
    if remedy_type:
        return f"CPSC RECALL: {remedy_type}. File claim at {recall.get('url', 'www.cpsc.gov/Recalls')}"
    return f"CPSC ACTIVE RECALL: Check eligibility at {recall.get('url', 'www.cpsc.gov/Recalls')}"


def _estimate_recall_savings(finding, recall):
    """
    HEURISTIC ESTIMATE (labeled): potential avoided repair cost if the CPSC
    recall provides free repair/replacement. Not a guaranteed value.
    """
    severity = finding.get("severity", "MEDIUM")
    savings_map = {
        "CRITICAL": 3000,
        "HIGH": 2000,
        "MEDIUM": 1200,
        "LOW": 600,
    }
    return savings_map.get(severity, 800)
