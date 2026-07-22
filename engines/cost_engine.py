import re
import math
from datetime import datetime, timedelta
from config import (
    MATERIAL_COSTS_2026, ZIP_COST_MODIFIERS, STATE_TAX_MULTIPLIERS,
    DEPRECIATION_TABLES, INSPECTION_SYSTEM_PATTERNS, SeverityLevels
)

def fetch_localized_rates(zip_code):
    zip_data = ZIP_COST_MODIFIERS.get(zip_code)
    if not zip_data:
        base_digits = zip_code[:2] + "001"
        zip_data = ZIP_COST_MODIFIERS.get(base_digits)
    if not zip_data:
        state = _state_from_zip(zip_code)
        modifier = STATE_TAX_MULTIPLIERS.get(state, 1.0) if state else 1.0
        zip_data = {
            "modifier": modifier,
            "city": "Unknown",
            "state": state or "Unknown",
            "avg_labor_rate": 60,
            "avg_material_mult": 1.0
        }
    return {
        "zip_code": zip_code,
        "city": zip_data["city"],
        "state": zip_data["state"],
        "cost_modifier": zip_data["modifier"],
        "avg_labor_rate": zip_data["avg_labor_rate"],
        "avg_material_mult": zip_data["avg_material_mult"],
        "permit_fee_estimate": _estimate_permit_fees(zip_data["state"]),
        "tax_multiplier": STATE_TAX_MULTIPLIERS.get(zip_data.get("state", ""), 1.0),
        "source": "embedded_database"
    }

def _state_from_zip(zip_code):
    if not zip_code:
        return None
    try:
        prefix = int(zip_code[:3])
    except ValueError:
        return None
    ranges = [
        (50, 63, "MA"), (64, 69, "RI"), (70, 89, "ME"), (100, 149, "NY"),
        (150, 196, "PA"), (197, 220, "DE"), (221, 247, "MD"), (248, 268, "WV"),
        (270, 289, "NC"), (290, 299, "SC"), (300, 319, "GA"), (320, 339, "FL"),
        (350, 369, "AL"), (370, 385, "TN"), (386, 397, "MS"), (400, 427, "KY"),
        (430, 458, "OH"), (460, 479, "IN"), (480, 499, "MI"), (500, 528, "IA"),
        (530, 549, "WI"), (550, 567, "MN"), (570, 577, "SD"), (580, 588, "ND"),
        (590, 599, "MT"), (600, 629, "IL"), (630, 658, "MO"), (660, 679, "KS"),
        (680, 693, "NE"), (700, 714, "LA"), (716, 729, "AR"), (730, 749, "OK"),
        (750, 799, "TX"), (800, 816, "CO"), (820, 831, "WY"), (832, 838, "ID"),
        (840, 847, "UT"), (850, 865, "AZ"), (870, 884, "NM"), (889, 898, "NV"),
        (900, 966, "CA"), (967, 968, "HI"), (970, 979, "OR"), (980, 994, "WA"),
        (995, 999, "AK"),
    ]
    for start, end, state in ranges:
        if start <= prefix <= end:
            return state
    return None

def _estimate_permit_fees(state):
    base_fees = {
        "CA": 450, "NY": 400, "TX": 200, "FL": 250, "IL": 300,
        "PA": 275, "OH": 225, "GA": 200, "NC": 250, "MI": 280,
        "default": 275
    }
    return base_fees.get(state, base_fees["default"])

def calculate_cost_bounds(finding, zip_code):
    rates = fetch_localized_rates(zip_code)
    system = finding.get("system_category", "OTHER").upper()
    severity = finding.get("severity", "MEDIUM")
    modifier = rates["cost_modifier"]
    labor_rate = rates["avg_labor_rate"]
    material_mult = rates["avg_material_mult"]
    base_costs = _get_base_costs_for_system(system, finding)
    diy_low = base_costs["low"] * 0.30
    diy_high = base_costs["high"] * 0.55
    contractor_low = base_costs["low"] * modifier
    contractor_high = base_costs["high"] * modifier
    emergency_low = contractor_low * 1.65
    emergency_high = contractor_high * 2.25
    material_low = base_costs["low"] * 0.40 * material_mult
    material_high = base_costs["high"] * 0.45 * material_mult
    labor_low = base_costs["low"] * 0.45 * (labor_rate / 60)
    labor_high = base_costs["high"] * 0.50 * (labor_rate / 60)
    permit = rates["permit_fee_estimate"] if severity in ["CRITICAL", "HIGH"] else 0
    severity_mult = {"CRITICAL": 1.3, "HIGH": 1.15, "MEDIUM": 1.0, "LOW": 0.85, "INFO": 0.7}
    s_mult = severity_mult.get(severity, 1.0)
    result = {
        "finding": finding.get("description", "")[:80],
        "system": system,
        "severity": severity,
        "zip_code": zip_code,
        "city": rates["city"],
        "cost_modifier": modifier,
        "diy_low": round(diy_low * s_mult, 0),
        "diy_high": round(diy_high * s_mult, 0),
        "contractor_low": round(contractor_low * s_mult, 0),
        "contractor_high": round(contractor_high * s_mult, 0),
        "emergency_low": round(emergency_low * s_mult, 0),
        "emergency_high": round(emergency_high * s_mult, 0),
        "material_cost_low": round(material_low * s_mult, 0),
        "material_cost_high": round(material_high * s_mult, 0),
        "labor_cost_low": round(labor_low * s_mult, 0),
        "labor_cost_high": round(labor_high * s_mult, 0),
        "permit_cost": round(permit, 0),
        "total_low": round(contractor_low * s_mult + permit, 0),
        "total_high": round(contractor_high * s_mult + permit, 0),
        "total_avg": round((contractor_low * s_mult + contractor_high * s_mult) / 2 + permit, 0),
        "local_labor_rate": labor_rate,
        "local_material_mult": material_mult,
    }
    return result

def _get_base_costs_for_system(system, finding):
    desc = finding.get("description", "").lower()
    subsystem = finding.get("subsystem", "").lower()
    costs = {
        "HVAC": {
            "heat exchanger": (1200, 3500),
            "inducer motor": (450, 850),
            "blower motor": (400, 800),
            "compressor": (1500, 3000),
            "evaporator coil": (800, 2200),
            "capacitor": (120, 350),
            "thermostat": (150, 400),
            "duct": (500, 2000),
            "refrigerant": (200, 600),
            "filter": (50, 150),
            "default": (300, 1500),
        },
        "ROOF": {
            "flashing": (800, 2500),
            "step flashing": (1200, 2500),
            "shingle": (500, 3000),
            "gutter": (300, 1200),
            "decking": (500, 2000),
            "skylight": (800, 3000),
            "default": (800, 4000),
        },
        "ELECTRICAL": {
            "gfci": (200, 450),
            "panel": (1800, 4000),
            "subpanel": (1500, 3500),
            "outlet": (100, 300),
            "wiring": (500, 5000),
            "breaker": (150, 400),
            "grounding": (300, 1000),
            "default": (250, 1500),
        },
        "PLUMBING": {
            "pipe": (200, 2000),
            "drain": (100, 500),
            "faucet": (150, 500),
            "toilet": (200, 600),
            "water heater": (800, 3000),
            "sewer": (2000, 8000),
            "valve": (150, 500),
            "trap": (100, 350),
            "default": (200, 1500),
        },
        "STRUCTURAL": {
            "foundation": (2000, 15000),
            "crack": (500, 5000),
            "beam": (1000, 5000),
            "joist": (500, 3000),
            "sill": (800, 3000),
            "retaining": (2000, 8000),
            "default": (1000, 8000),
        },
        "EXTERIOR": {
            "siding": (500, 5000),
            "paint": (200, 3000),
            "deck": (500, 5000),
            "railing": (300, 1500),
            "driveway": (500, 5000),
            "grading": (500, 3000),
            "garage": (200, 2000),
            "window": (400, 1500),
            "door": (300, 2000),
            "default": (300, 3000),
        },
        "INSULATION": {
            "default": (500, 4000),
        },
        "APPLIANCES": {
            "stove": (400, 2000),
            "refrigerator": (500, 3000),
            "dishwasher": (300, 1200),
            "washer": (400, 1500),
            "dryer": (300, 1200),
            "default": (200, 2000),
        },
        "WINDOWS_DOORS": {
            "window": (400, 1500),
            "door": (300, 2500),
            "seal": (150, 500),
            "default": (250, 1500),
        },
        "FIRE_SAFETY": {
            "smoke detector": (50, 200),
            "carbon monoxide": (50, 200),
            "fireplace": (300, 2000),
            "chimney": (500, 3000),
            "default": (200, 1500),
        },
        "MOISTURE": {
            "mold": (1000, 8000),
            "water": (300, 3000),
            "vapor": (200, 1500),
            "default": (300, 3000),
        },
    }
    system_costs = costs.get(system, costs.get("STRUCTURAL" if system in ("FOUNDATION",) else "PLUMBING", {"default": (300, 2000)}))
    for keyword, cost_range in system_costs.items():
        if keyword != "default" and (keyword in desc or keyword in subsystem):
            return {"low": cost_range[0], "high": cost_range[1]}
    return {"low": system_costs["default"][0], "high": system_costs["default"][1]}

def generate_cost_matrix(findings, zip_code):
    matrix = []
    total_low = 0
    total_high = 0
    total_avg = 0
    for finding in findings:
        estimate = calculate_cost_bounds(finding, zip_code)
        matrix.append(estimate)
        total_low += estimate["total_low"]
        total_high += estimate["total_high"]
        total_avg += estimate["total_avg"]
    severity_totals = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for est in matrix:
        severity_totals[est["severity"]] = severity_totals.get(est["severity"], 0) + est["total_avg"]
    return {
        "line_items": matrix,
        "summary": {
            "total_items": len(matrix),
            "total_low": round(total_low, 0),
            "total_high": round(total_high, 0),
            "total_avg": round(total_avg, 0),
            "by_severity": severity_totals,
            "zip_code": zip_code,
            "rates_applied": fetch_localized_rates(zip_code),
            "generated_at": datetime.now().isoformat()
        }
    }

def calculate_bulk_material_cost(findings, zip_code):
    rates = fetch_localized_rates(zip_code)
    material_mult = rates["avg_material_mult"]
    bulk_estimate = 0
    for finding in findings:
        est = calculate_cost_bounds(finding, zip_code)
        bulk_estimate += est["material_cost_high"]
    return {
        "estimated_material_total": round(bulk_estimate * material_mult, 0),
        "volume_discount_estimate": round(bulk_estimate * 0.12, 0),
        "net_after_discount": round(bulk_estimate * material_mult - bulk_estimate * 0.12, 0),
    }
