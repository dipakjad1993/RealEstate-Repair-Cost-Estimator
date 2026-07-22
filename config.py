import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ENGINES_DIR = BASE_DIR / "engines"
UTILS_DIR = BASE_DIR / "utils"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
DB_PATH = DATA_DIR / "repair_estimator.db"

REGIONS = {
    "northeast": ["CT", "ME", "MA", "NH", "NJ", "NY", "PA", "RI", "VT"],
    "southeast": ["AL", "AR", "DE", "FL", "GA", "KY", "LA", "MD", "MS", "NC", "SC", "TN", "VA", "WV"],
    "midwest": ["IL", "IN", "IA", "KS", "MI", "MN", "MO", "NE", "ND", "OH", "SD", "WI"],
    "southwest": ["AZ", "NM", "OK", "TX"],
    "west": ["AK", "CA", "CO", "HI", "ID", "MT", "NV", "OR", "UT", "WA", "WY"],
}

STATE_TAX_MULTIPLIERS = {
    "AL": 0.84, "AK": 1.18, "AZ": 0.92, "AR": 0.82, "CA": 1.38, "CO": 1.08,
    "CT": 1.22, "DE": 1.02, "FL": 0.95, "GA": 0.92, "HI": 1.42, "ID": 0.88,
    "IL": 1.02, "IN": 0.90, "IA": 0.88, "KS": 0.89, "KY": 0.86, "LA": 0.88,
    "ME": 1.08, "MD": 1.12, "MA": 1.28, "MI": 0.98, "MN": 1.05, "MS": 0.80,
    "MO": 0.88, "MT": 0.92, "NE": 0.89, "NV": 0.98, "NH": 1.10, "NJ": 1.25,
    "NM": 0.87, "NY": 1.33, "NC": 0.90, "ND": 0.92, "OH": 0.94, "OK": 0.85,
    "OR": 1.12, "PA": 1.08, "RI": 1.15, "SC": 0.88, "SD": 0.87, "TN": 0.90,
    "TX": 0.92, "UT": 0.89, "VT": 1.10, "VA": 1.02, "WA": 1.18, "WV": 0.84,
    "WI": 0.97, "WY": 0.90, "DC": 1.28,
}

SeverityLevels = {
    "CRITICAL": {"color": "#DC2626", "label": "Critical - Safety/Structural", "priority": 1, "icon": "🔴", "bg": "rgba(220,38,38,0.12)"},
    "HIGH": {"color": "#EA580C", "label": "High - Active Damage", "priority": 2, "icon": "🟠", "bg": "rgba(234,88,12,0.12)"},
    "MEDIUM": {"color": "#CA8A04", "label": "Medium - Code/Compliance", "priority": 3, "icon": "🟡", "bg": "rgba(202,138,4,0.12)"},
    "LOW": {"color": "#16A34A", "label": "Low - Maintenance/Cosmetic", "priority": 4, "icon": "🟢", "bg": "rgba(22,163,74,0.12)"},
    "INFO": {"color": "#2563EB", "label": "Informational", "priority": 5, "icon": "🔵", "bg": "rgba(37,99,235,0.12)"},
}

SEVERITY_EMOJI = {
    "CRITICAL": "\U0001f534",
    "HIGH": "\U0001f7e0",
    "MEDIUM": "\U0001f7e1",
    "LOW": "\U0001f7e2",
    "INFO": "\U0001f535",
}

DEPRECIATION_TABLES = {
    "hvac": {
        "useful_life": 17,
        "salvage_pct": 0.08,
        "replacement_avg": 11000,
        "replacement_range": (5500, 18000),
    },
    "furnace": {
        "useful_life": 18,
        "salvage_pct": 0.05,
        "replacement_avg": 5200,
        "replacement_range": (2800, 9500),
    },
    "ac_unit": {
        "useful_life": 15,
        "salvage_pct": 0.05,
        "replacement_avg": 8000,
        "replacement_range": (3500, 14500),
    },
    "heat_pump": {
        "useful_life": 14,
        "salvage_pct": 0.06,
        "replacement_avg": 9500,
        "replacement_range": (4500, 16000),
    },
    "water_heater": {
        "useful_life": 13,
        "salvage_pct": 0.03,
        "replacement_avg": 2200,
        "replacement_range": (900, 4500),
    },
    "tankless_water_heater": {
        "useful_life": 22,
        "salvage_pct": 0.05,
        "replacement_avg": 4500,
        "replacement_range": (2200, 7500),
    },
    "roof_asphalt": {
        "useful_life": 25,
        "salvage_pct": 0.0,
        "replacement_avg": 15000,
        "replacement_range": (5500, 32000),
    },
    "roof_metal": {
        "useful_life": 55,
        "salvage_pct": 0.0,
        "replacement_avg": 28000,
        "replacement_range": (10000, 52000),
    },
    "roof_tile": {
        "useful_life": 60,
        "salvage_pct": 0.0,
        "replacement_avg": 32000,
        "replacement_range": (15000, 55000),
    },
    "electrical_panel": {
        "useful_life": 32,
        "salvage_pct": 0.0,
        "replacement_avg": 3200,
        "replacement_range": (1200, 6000),
    },
    "electrical_panel_fpe": {
        "useful_life": 0,
        "salvage_pct": 0.0,
        "replacement_avg": 3800,
        "replacement_range": (1800, 6500),
    },
    "wiring": {
        "useful_life": 40,
        "salvage_pct": 0.0,
        "replacement_avg": 18000,
        "replacement_range": (5000, 42000),
    },
    "plumbing_pipes": {
        "useful_life": 55,
        "salvage_pct": 0.0,
        "replacement_avg": 10000,
        "replacement_range": (2500, 22000),
    },
    "plumbing_drain": {
        "useful_life": 65,
        "salvage_pct": 0.0,
        "replacement_avg": 5000,
        "replacement_range": (1200, 12000),
    },
    "foundation": {
        "useful_life": 120,
        "salvage_pct": 0.0,
        "replacement_avg": 15000,
        "replacement_range": (3000, 35000),
    },
    "deck": {
        "useful_life": 20,
        "salvage_pct": 0.0,
        "replacement_avg": 9000,
        "replacement_range": (2500, 22000),
    },
    "siding": {
        "useful_life": 35,
        "salvage_pct": 0.0,
        "replacement_avg": 12000,
        "replacement_range": (3500, 25000),
    },
    "windows": {
        "useful_life": 22,
        "salvage_pct": 0.0,
        "replacement_avg": 850,
        "replacement_range": (350, 1800),
    },
    "insulation": {
        "useful_life": 55,
        "salvage_pct": 0.0,
        "replacement_avg": 3200,
        "replacement_range": (1000, 7500),
    },
    "kitchen_appliances": {
        "useful_life": 14,
        "salvage_pct": 0.05,
        "replacement_avg": 6500,
        "replacement_range": (2000, 18000),
    },
    "flooring_hardwood": {
        "useful_life": 35,
        "salvage_pct": 0.0,
        "replacement_avg": 9000,
        "replacement_range": (4000, 15000),
    },
    "flooring_tile": {
        "useful_life": 60,
        "salvage_pct": 0.0,
        "replacement_avg": 11500,
        "replacement_range": (5000, 18000),
    },
    "flooring_carpet": {
        "useful_life": 10,
        "salvage_pct": 0.0,
        "replacement_avg": 3500,
        "replacement_range": (1500, 6000),
    },
    "garage_door": {
        "useful_life": 22,
        "salvage_pct": 0.08,
        "replacement_avg": 2400,
        "replacement_range": (800, 5500),
    },
    "fence": {
        "useful_life": 20,
        "salvage_pct": 0.0,
        "replacement_avg": 5500,
        "replacement_range": (1500, 14000),
    },
    "driveway": {
        "useful_life": 30,
        "salvage_pct": 0.0,
        "replacement_avg": 6500,
        "replacement_range": (2000, 15000),
    },
    "chimney": {
        "useful_life": 55,
        "salvage_pct": 0.0,
        "replacement_avg": 4500,
        "replacement_range": (1000, 12000),
    },
    "sprinkler_system": {
        "useful_life": 20,
        "salvage_pct": 0.0,
        "replacement_avg": 3500,
        "replacement_range": (1500, 7000),
    },
    "septic_system": {
        "useful_life": 25,
        "salvage_pct": 0.0,
        "replacement_avg": 20000,
        "replacement_range": (8000, 40000),
    },
    "well_system": {
        "useful_life": 25,
        "salvage_pct": 0.0,
        "replacement_avg": 10000,
        "replacement_range": (3000, 20000),
    },
}

CLIMATE_ZONES = {
    "extremely_hot_arid": {"states": ["AZ", "NV", "NM"], "risks": ["heat_damage", "uv_degradation", "expansive_soil"], "insurance_mult": 1.18},
    "hot_humid": {"states": ["FL", "GA", "SC", "NC", "TX", "LA", "MS", "AL", "HI"], "risks": ["mold", "termite", "flood", "hurricane"], "insurance_mult": 1.35},
    "temperate": {"states": ["CA", "OR", "WA", "CO", "UT"], "risks": ["wildfire", "earthquake", "drought"], "insurance_mult": 1.22},
    "cold_harsh": {"states": ["MN", "WI", "MI", "ND", "SD", "MT", "WY", "ME", "VT", "NH"], "risks": ["ice_dam", "frozen_pipes", "snow_load", "foundation_heave"], "insurance_mult": 1.12},
    "moderate": {"states": ["NY", "NJ", "PA", "OH", "IL", "IN", "VA", "MD", "CT", "MA"], "risks": ["freeze_thaw", "radon", "aging_infrastructure"], "insurance_mult": 1.02},
}

INSURANCE_RED_FLAGS = [
    {"pattern": "polybutylene|poly-b|polybutelyne", "system": "plumbing", "risk_score": 95, "denial_prob": 0.94, "annual_penalty": 3400, "replacement_cost": 9500, "description": "Polybutylene plumbing - known failure risk, most carriers will deny coverage"},
    {"pattern": "knob.and.tube|K&T|knob & tube", "system": "electrical", "risk_score": 92, "denial_prob": 0.91, "annual_penalty": 3100, "replacement_cost": 14000, "description": "Knob-and-tube wiring - fire hazard, most carriers require full rewiring"},
    {"pattern": "federal.pacific|FPE|stab-lok", "system": "electrical_panel", "risk_score": 94, "denial_prob": 0.89, "annual_penalty": 2800, "replacement_cost": 2800, "description": "Federal Pacific panel - active class action, 94% denial probability"},
    {"pattern": "zinsco|zinsco.*panel|Sylvania.*panel", "system": "electrical_panel", "risk_score": 93, "denial_prob": 0.88, "annual_penalty": 2600, "replacement_cost": 3200, "description": "Zinsco panel - known breaker welding/failure under overload"},
    {"pattern": "aluminum.wiring|aluminum.branch", "system": "electrical", "risk_score": 88, "denial_prob": 0.82, "annual_penalty": 2200, "replacement_cost": 16000, "description": "Aluminum branch wiring - fire/overheating risk at connections"},
    {"pattern": "asbestos|asbestos.insulation|asbestos.siding", "system": "environmental", "risk_score": 85, "denial_prob": 0.70, "annual_penalty": 1800, "replacement_cost": 28000, "description": "Asbestos materials - specialized abatement required by law"},
    {"pattern": "lead.paint|lead-based", "system": "environmental", "risk_score": 80, "denial_prob": 0.65, "annual_penalty": 1400, "replacement_cost": 18000, "description": "Lead-based paint - EPA RRP rule compliance required"},
    {"pattern": "mold|active.mold|mold.growth|mold.colon", "system": "environmental", "risk_score": 82, "denial_prob": 0.75, "annual_penalty": 2400, "replacement_cost": 9500, "description": "Active mold growth - health hazard, carrier may exclude related claims"},
    {"pattern": "roof.*1[3-9].years|roof.*2[0-9].years|roof.over.*12", "system": "roof", "risk_score": 75, "denial_prob": 0.60, "annual_penalty": 2000, "replacement_cost": 14500, "description": "Aging roof (12+ years) - many carriers require certification or will non-renew"},
    {"pattern": "active.leak|active.water|water.intrusion|active.dripping", "system": "plumbing", "risk_score": 88, "denial_prob": 0.80, "annual_penalty": 2300, "replacement_cost": 6000, "description": "Active water intrusion - immediate risk of structural damage and mold"},
    {"pattern": "foundation.crack|structural.crack|settling|shifting", "system": "foundation", "risk_score": 90, "denial_prob": 0.85, "annual_penalty": 3800, "replacement_cost": 25000, "description": "Foundation/structural issues - major liability, often excluded from coverage"},
    {"pattern": "radon|radon.mitigation|radon.level", "system": "environmental", "risk_score": 70, "denial_prob": 0.50, "annual_penalty": 900, "replacement_cost": 1800, "description": "Radon above 4.0 pCi/L - mitigation system required for occupancy"},
    {"pattern": "termites|termite.damage|wood.destroying|wdi", "system": "pest", "risk_score": 78, "denial_prob": 0.55, "annual_penalty": 1200, "replacement_cost": 9500, "description": "Termite/WDI - structural wood damage, often excluded from homeowner policies"},
    {"pattern": "septic|septic.system|septic.tank", "system": "plumbing", "risk_score": 72, "denial_prob": 0.45, "annual_penalty": 1000, "replacement_cost": 18000, "description": "Septic system - potential failure, replacement is major expense"},
    {"pattern": "well.water|private.well", "system": "plumbing", "risk_score": 65, "denial_prob": 0.35, "annual_penalty": 700, "replacement_cost": 9500, "description": "Private well - water quality risk, no municipal backup"},
]

MANUFACTURER_RECALLS = [
    {"manufacturer": "Federal Pacific", "model_pattern": "Stab-Lok|FPE|Federal Pacific", "product": "Electrical Panel", "recall_type": "Class Action", "status": "Active", "claim_url": "https://www.saferproducts.gov/", "description": "Known breaker failure causing fires - active class action settlement", "remedy": "Full panel replacement by licensed electrician, may qualify for settlement funds"},
    {"manufacturer": "Zinsco", "model_pattern": "Zinsco|Sylvania-Zinsco|Q-Line", "product": "Electrical Panel", "recall_type": "Class Action", "status": "Active", "claim_url": "https://www.saferproducts.gov/", "description": "Breakers weld shut during overload, fail to trip - fire risk", "remedy": "Full panel replacement required"},
    {"manufacturer": "Cutler-Hammer", "model_pattern": "CH|Eaton|Cutler|CHFP", "product": "Electrical Panel", "recall_type": "Manufacturer", "status": "Check", "claim_url": "https://www.eaton.com/us/en-us/support.html", "description": "Certain CH panel models have bus bar connection issues", "remedy": "Contact Eaton for inspection and possible bus bar replacement"},
    {"manufacturer": "Siemens", "model_pattern": "SEQ|QP|QPH|QPF|PL series", "product": "Electrical Panel", "recall_type": "Manufacturer", "status": "Check", "claim_url": "https://www.siemens.com/us/en.html", "description": "某些断路器型号在过载时可能无法正常跳闸", "remedy": "Contact Siemens for inspection and possible breaker replacement"},
    {"manufacturer": "Whirlpool", "model_pattern": "WFW.*|DU.*|GU.*", "product": "Dishwasher", "recall_type": "CPSC", "status": "Check", "claim_url": "https://www.whirlpool.com/recalls.html", "description": "Heating element may overheat, fire risk on certain models", "remedy": "Free repair or replacement through manufacturer"},
    {"manufacturer": "Maytag", "model_pattern": "MDB.*|JDB.*|DW.*", "product": "Dishwasher", "recall_type": "CPSC", "status": "Check", "claim_url": "https://www.maytag.com/recalls.html", "description": "Heating element malfunction on certain dishwasher models", "remedy": "Free repair by authorized service provider"},
    {"manufacturer": "Bosch", "model_pattern": "SH.*|SHE.*|SHV.*", "product": "Dishwasher", "recall_type": "CPSC", "status": "Check", "claim_url": "https://www.bosch-home.com/us/recalls", "description": "某些型号可能存在加热元件问题", "remedy": "Contact Bosch for inspection and repair"},
    {"manufacturer": "LG", "model_pattern": "WM.*|WT.*", "product": "Washing Machine", "recall_type": "CPSC", "status": "Check", "claim_url": "https://www.lg.com/us/recalls", "description": "Drum detachment risk due to balancing mechanism failure", "remedy": "Free repair kit shipped to homeowner"},
    {"manufacturer": "Samsung", "model_pattern": "RF.*|RS.*|RT.*", "product": "Refrigerator", "recall_type": "CPSC", "status": "Check", "claim_url": "https://www.samsung.com/us/recalls/", "description": "Overheating relay component - potential fire hazard", "remedy": "Free in-home repair by authorized technician"},
    {"manufacturer": "GE", "model_pattern": "GSS.*|GSE.*|GSS.*|PSS.*|DSS.*", "product": "Refrigerator", "recall_type": "CPSC", "status": "Check", "claim_url": "https://www.geappliances.com/recalls.htm", "description": "某些冰箱型号可能存在蒸发器风扇电机问题", "remedy": "Contact GE for inspection and possible repair"},
    {"manufacturer": "Kenmore", "model_pattern": "795.*|596.*|106.*", "product": "Refrigerator", "recall_type": "CPSC", "status": "Check", "claim_url": "https://www.searspartsdirect.com/recalls", "description": "某些型号可能存在冷凝器风扇问题", "remedy": "Contact Sears/Kenmore for inspection and repair"},
    {"manufacturer": "Rheem", "model_pattern": "PRO.*|XG.*|PP.*", "product": "Water Heater", "recall_type": "CPSC", "status": "Check", "claim_url": "https://www.rheem.com/support/recalls/", "description": "Thermal expansion issues on certain model ranges", "remedy": "Free repair by authorized service provider"},
    {"manufacturer": "A.O. Smith", "model_pattern": "GP.*|XCR.*|XCV.*", "product": "Water Heater", "recall_type": "Manufacturer", "status": "Check", "claim_url": "https://www.hotwater.com/recalls.html", "description": "某些型号可能存在温度压力释放阀问题", "remedy": "Contact A.O. Smith for inspection and repair"},
    {"manufacturer": "Bradford White", "model_pattern": "RG.*|RE.*|EF.*|MV.*", "product": "Water Heater", "recall_type": "Manufacturer", "status": "Check", "claim_url": "https://www.bradfordwhite.com/recalls", "description": "某些型号可能存在阴极棒腐蚀问题", "remedy": "Contact Bradford White for inspection"},
    {"manufacturer": "Carrier", "model_pattern": "24ACC.*|24HBB.*|24VNA.*", "product": "HVAC", "recall_type": "Manufacturer", "status": "Check", "claim_url": "https://www.carrier.com/residential/en/us/support/recall-information/", "description": "Capacitor/motor recalls on specific model years", "remedy": "Authorized service repair at no cost"},
    {"manufacturer": "Lennox", "model_pattern": "HS.*|XC.*|XR.*", "product": "HVAC", "recall_type": "Manufacturer", "status": "Check", "claim_url": "https://www.lennox.com/support/recalls", "description": "Heat exchanger crack potential - CO risk", "remedy": "Free heat exchanger replacement through authorized dealer"},
    {"manufacturer": "Trane", "model_pattern": "XR.*|XL.*|XB.*", "product": "HVAC", "recall_type": "Manufacturer", "status": "Check", "claim_url": "https://www.trane.com/residential/en/support/recall-information.html", "description": "某些型号可能存在冷凝器风扇电机问题", "remedy": "Contact Trane for authorized service repair"},
    {"manufacturer": "Goodman", "model_pattern": "GSX.*|GSZ.*|GMVC.*", "product": "HVAC", "recall_type": "Manufacturer", "status": "Check", "claim_url": "https://www.goodmanmfg.com/recalls", "description": "某些型号可能存在电容器或继电器问题", "remedy": "Contact Goodman for inspection and repair"},
    {"manufacturer": "York", "model_pattern": "YF.*|YG.*|YC.*|YH.*", "product": "HVAC", "recall_type": "Manufacturer", "status": "Check", "claim_url": "https://www.york.com/residential/support/recall-information", "description": "某些型号可能存在燃烧器或热交换器问题", "remedy": "Contact York for authorized service"},
    {"manufacturer": "Generac", "model_pattern": "Guardian|QuietSource|PowerPact", "product": "Generator", "recall_type": "CPSC", "status": "Active", "claim_url": "https://www.generac.com/recalls", "description": "Carbon monoxide emission risk - controller replacement needed", "remedy": "Free controller replacement at authorized service center"},
    {"manufacturer": "Kohler", "model_pattern": "20RES|14RES|12RES", "product": "Generator", "recall_type": "CPSC", "status": "Check", "claim_url": "https://www.kohler.com/en/recalls", "description": "某些型号可能存在燃料泄漏风险", "remedy": "Contact Kohler for inspection and repair"},
    {"manufacturer": "Cummins", "model_pattern": "RSA|RCOR|RG022|RG040", "product": "Generator", "recall_type": "Manufacturer", "status": "Check", "claim_url": "https://www.cummins.com/recalls", "description": "某些型号可能存在控制器或燃料系统问题", "remedy": "Contact Cummins for authorized service"},
    {"manufacturer": "American Standard", "model_pattern": "AUH|ACU|ACC|ASU", "product": "HVAC", "recall_type": "Manufacturer", "status": "Check", "claim_url": "https://www.americanstandard-hvac.com/recalls", "description": "某些型号可能存在电气连接问题", "remedy": "Contact American Standard for inspection"},
    {"manufacturer": "Coleman", "model_pattern": "ECH|ECM|ECON", "product": "HVAC", "recall_type": "Manufacturer", "status": "Check", "claim_url": "https://www.colemanhvac.com/recalls", "description": "某些型号可能存在燃烧器或控制器问题", "remedy": "Contact Coleman for authorized service"},
    {"manufacturer": "Bryant", "model_pattern": "FE.*|FB.*|FX.*|GH.*", "product": "HVAC", "recall_type": "Manufacturer", "status": "Check", "claim_url": "https://www.bryant.com/residential/en/us/support/recall-information", "description": "某些型号可能存在电容器或风扇电机问题", "remedy": "Contact Bryant for authorized service repair"},
]

ZIP_COST_MODIFIERS = {
    "10001": {"modifier": 1.46, "city": "New York", "state": "NY", "avg_labor_rate": 98, "avg_material_mult": 1.42},
    "90001": {"modifier": 1.38, "city": "Los Angeles", "state": "CA", "avg_labor_rate": 95, "avg_material_mult": 1.35},
    "60601": {"modifier": 1.06, "city": "Chicago", "state": "IL", "avg_labor_rate": 72, "avg_material_mult": 1.05},
    "77001": {"modifier": 0.92, "city": "Houston", "state": "TX", "avg_labor_rate": 60, "avg_material_mult": 0.93},
    "85001": {"modifier": 0.95, "city": "Phoenix", "state": "AZ", "avg_labor_rate": 60, "avg_material_mult": 0.95},
    "19101": {"modifier": 1.10, "city": "Philadelphia", "state": "PA", "avg_labor_rate": 68, "avg_material_mult": 1.08},
    "78201": {"modifier": 0.86, "city": "San Antonio", "state": "TX", "avg_labor_rate": 52, "avg_material_mult": 0.84},
    "92101": {"modifier": 1.34, "city": "San Diego", "state": "CA", "avg_labor_rate": 88, "avg_material_mult": 1.32},
    "75201": {"modifier": 0.93, "city": "Dallas", "state": "TX", "avg_labor_rate": 62, "avg_material_mult": 0.93},
    "95101": {"modifier": 1.36, "city": "San Jose", "state": "CA", "avg_labor_rate": 92, "avg_material_mult": 1.34},
    "73301": {"modifier": 0.84, "city": "Austin", "state": "TX", "avg_labor_rate": 54, "avg_material_mult": 0.85},
    "32099": {"modifier": 0.88, "city": "Jacksonville", "state": "FL", "avg_labor_rate": 56, "avg_material_mult": 0.89},
    "76101": {"modifier": 0.90, "city": "Fort Worth", "state": "TX", "avg_labor_rate": 58, "avg_material_mult": 0.90},
    "43085": {"modifier": 0.86, "city": "Columbus", "state": "OH", "avg_labor_rate": 52, "avg_material_mult": 0.85},
    "28201": {"modifier": 0.90, "city": "Charlotte", "state": "NC", "avg_labor_rate": 54, "avg_material_mult": 0.89},
    "46201": {"modifier": 0.83, "city": "Indianapolis", "state": "IN", "avg_labor_rate": 49, "avg_material_mult": 0.83},
    "94102": {"modifier": 1.55, "city": "San Francisco", "state": "CA", "avg_labor_rate": 112, "avg_material_mult": 1.50},
    "98101": {"modifier": 1.30, "city": "Seattle", "state": "WA", "avg_labor_rate": 82, "avg_material_mult": 1.26},
    "80201": {"modifier": 1.12, "city": "Denver", "state": "CO", "avg_labor_rate": 74, "avg_material_mult": 1.10},
    "20001": {"modifier": 1.24, "city": "Washington DC", "state": "DC", "avg_labor_rate": 84, "avg_material_mult": 1.22},
    "37201": {"modifier": 0.89, "city": "Nashville", "state": "TN", "avg_labor_rate": 54, "avg_material_mult": 0.89},
    "73101": {"modifier": 0.83, "city": "Oklahoma City", "state": "OK", "avg_labor_rate": 48, "avg_material_mult": 0.82},
    "79901": {"modifier": 0.86, "city": "El Paso", "state": "TX", "avg_labor_rate": 50, "avg_material_mult": 0.85},
    "02101": {"modifier": 1.34, "city": "Boston", "state": "MA", "avg_labor_rate": 88, "avg_material_mult": 1.30},
    "97201": {"modifier": 1.14, "city": "Portland", "state": "OR", "avg_labor_rate": 76, "avg_material_mult": 1.12},
    "89101": {"modifier": 0.98, "city": "Las Vegas", "state": "NV", "avg_labor_rate": 62, "avg_material_mult": 0.96},
    "38101": {"modifier": 0.82, "city": "Memphis", "state": "TN", "avg_labor_rate": 47, "avg_material_mult": 0.81},
    "40201": {"modifier": 0.85, "city": "Louisville", "state": "KY", "avg_labor_rate": 49, "avg_material_mult": 0.84},
    "21201": {"modifier": 1.10, "city": "Baltimore", "state": "MD", "avg_labor_rate": 70, "avg_material_mult": 1.08},
    "53201": {"modifier": 0.95, "city": "Milwaukee", "state": "WI", "avg_labor_rate": 60, "avg_material_mult": 0.93},
    "87101": {"modifier": 0.88, "city": "Albuquerque", "state": "NM", "avg_labor_rate": 54, "avg_material_mult": 0.87},
    "85701": {"modifier": 0.90, "city": "Tucson", "state": "AZ", "avg_labor_rate": 56, "avg_material_mult": 0.89},
    "93701": {"modifier": 0.92, "city": "Fresno", "state": "CA", "avg_labor_rate": 58, "avg_material_mult": 0.91},
    "95814": {"modifier": 1.18, "city": "Sacramento", "state": "CA", "avg_labor_rate": 78, "avg_material_mult": 1.16},
    "85201": {"modifier": 0.92, "city": "Mesa", "state": "AZ", "avg_labor_rate": 58, "avg_material_mult": 0.92},
    "64101": {"modifier": 0.86, "city": "Kansas City", "state": "MO", "avg_labor_rate": 52, "avg_material_mult": 0.85},
    "30301": {"modifier": 0.92, "city": "Atlanta", "state": "GA", "avg_labor_rate": 57, "avg_material_mult": 0.91},
    "68101": {"modifier": 0.85, "city": "Omaha", "state": "NE", "avg_labor_rate": 51, "avg_material_mult": 0.84},
    "80901": {"modifier": 1.04, "city": "Colorado Springs", "state": "CO", "avg_labor_rate": 66, "avg_material_mult": 1.02},
    "27601": {"modifier": 0.92, "city": "Raleigh", "state": "NC", "avg_labor_rate": 56, "avg_material_mult": 0.91},
    "90801": {"modifier": 1.32, "city": "Long Beach", "state": "CA", "avg_labor_rate": 86, "avg_material_mult": 1.30},
    "23451": {"modifier": 0.94, "city": "Virginia Beach", "state": "VA", "avg_labor_rate": 60, "avg_material_mult": 0.93},
    "33101": {"modifier": 1.14, "city": "Miami", "state": "FL", "avg_labor_rate": 70, "avg_material_mult": 1.10},
    "94601": {"modifier": 1.46, "city": "Oakland", "state": "CA", "avg_labor_rate": 98, "avg_material_mult": 1.44},
    "55401": {"modifier": 1.02, "city": "Minneapolis", "state": "MN", "avg_labor_rate": 68, "avg_material_mult": 1.00},
    "74101": {"modifier": 0.83, "city": "Tulsa", "state": "OK", "avg_labor_rate": 48, "avg_material_mult": 0.82},
    "33601": {"modifier": 0.94, "city": "Tampa", "state": "FL", "avg_labor_rate": 59, "avg_material_mult": 0.93},
    "76001": {"modifier": 0.91, "city": "Arlington", "state": "TX", "avg_labor_rate": 60, "avg_material_mult": 0.91},
    "70112": {"modifier": 0.88, "city": "New Orleans", "state": "LA", "avg_labor_rate": 54, "avg_material_mult": 0.87},
    "07001": {"modifier": 1.22, "city": "Newark", "state": "NJ", "avg_labor_rate": 82, "avg_material_mult": 1.20},
    "48201": {"modifier": 0.88, "city": "Detroit", "state": "MI", "avg_labor_rate": 54, "avg_material_mult": 0.87},
    "43201": {"modifier": 0.85, "city": "Columbus", "state": "OH", "avg_labor_rate": 51, "avg_material_mult": 0.84},
    "23201": {"modifier": 0.91, "city": "Richmond", "state": "VA", "avg_labor_rate": 57, "avg_material_mult": 0.90},
    "84101": {"modifier": 0.90, "city": "Salt Lake City", "state": "UT", "avg_labor_rate": 57, "avg_material_mult": 0.89},
    "32801": {"modifier": 0.93, "city": "Orlando", "state": "FL", "avg_labor_rate": 59, "avg_material_mult": 0.92},
    "29401": {"modifier": 0.90, "city": "Charleston", "state": "SC", "avg_labor_rate": 54, "avg_material_mult": 0.89},
    "40202": {"modifier": 0.85, "city": "Louisville", "state": "KY", "avg_labor_rate": 49, "avg_material_mult": 0.84},
    "58501": {"modifier": 0.88, "city": "Bismarck", "state": "ND", "avg_labor_rate": 56, "avg_material_mult": 0.87},
    "57501": {"modifier": 0.86, "city": "Pierre", "state": "SD", "avg_labor_rate": 52, "avg_material_mult": 0.85},
    "59601": {"modifier": 0.91, "city": "Helena", "state": "MT", "avg_labor_rate": 59, "avg_material_mult": 0.90},
    "82001": {"modifier": 0.89, "city": "Cheyenne", "state": "WY", "avg_labor_rate": 56, "avg_material_mult": 0.88},
    "05601": {"modifier": 1.04, "city": "Montpelier", "state": "VT", "avg_labor_rate": 64, "avg_material_mult": 1.02},
    "03301": {"modifier": 1.06, "city": "Concord", "state": "NH", "avg_labor_rate": 66, "avg_material_mult": 1.04},
    "02901": {"modifier": 1.14, "city": "Providence", "state": "RI", "avg_labor_rate": 70, "avg_material_mult": 1.12},
    "19901": {"modifier": 0.98, "city": "Dover", "state": "DE", "avg_labor_rate": 60, "avg_material_mult": 0.97},
    "21401": {"modifier": 1.10, "city": "Annapolis", "state": "MD", "avg_labor_rate": 70, "avg_material_mult": 1.08},
    "35201": {"modifier": 0.81, "city": "Birmingham", "state": "AL", "avg_labor_rate": 45, "avg_material_mult": 0.80},
    "72201": {"modifier": 0.81, "city": "Little Rock", "state": "AR", "avg_labor_rate": 45, "avg_material_mult": 0.80},
    "25301": {"modifier": 0.83, "city": "Charleston", "state": "WV", "avg_labor_rate": 47, "avg_material_mult": 0.81},
    "39201": {"modifier": 0.79, "city": "Jackson", "state": "MS", "avg_labor_rate": 43, "avg_material_mult": 0.78},
    "68501": {"modifier": 0.85, "city": "Lincoln", "state": "NE", "avg_labor_rate": 52, "avg_material_mult": 0.84},
    "63101": {"modifier": 0.85, "city": "St. Louis", "state": "MO", "avg_labor_rate": 51, "avg_material_mult": 0.84},
    "06101": {"modifier": 1.16, "city": "Hartford", "state": "CT", "avg_labor_rate": 74, "avg_material_mult": 1.14},
    "04101": {"modifier": 1.06, "city": "Portland", "state": "ME", "avg_labor_rate": 64, "avg_material_mult": 1.04},
    "99501": {"modifier": 1.30, "city": "Anchorage", "state": "AK", "avg_labor_rate": 92, "avg_material_mult": 1.34},
    "41001": {"modifier": 0.88, "city": "Cincinnati", "state": "OH", "avg_labor_rate": 54, "avg_material_mult": 0.87},
    "15201": {"modifier": 0.90, "city": "Pittsburgh", "state": "PA", "avg_labor_rate": 56, "avg_material_mult": 0.89},
    "44101": {"modifier": 0.86, "city": "Cleveland", "state": "OH", "avg_labor_rate": 52, "avg_material_mult": 0.85},
    "46801": {"modifier": 0.84, "city": "Fort Wayne", "state": "IN", "avg_labor_rate": 48, "avg_material_mult": 0.83},
    "52801": {"modifier": 0.87, "city": "Des Moines", "state": "IA", "avg_labor_rate": 53, "avg_material_mult": 0.86},
    "33012": {"modifier": 0.96, "city": "Hollywood", "state": "FL", "avg_labor_rate": 62, "avg_material_mult": 0.95},
    "85281": {"modifier": 0.93, "city": "Tempe", "state": "AZ", "avg_labor_rate": 58, "avg_material_mult": 0.92},
    "75001": {"modifier": 0.91, "city": "Addison", "state": "TX", "avg_labor_rate": 60, "avg_material_mult": 0.91},
}

INSPECTION_SYSTEM_PATTERNS = {
    "HVAC": {
        "keywords": [
            "hvac", "heating", "cooling", "air conditioner", "air conditioning",
            "furnace", "heat pump", "duct", "vent", "thermostat", "condenser",
            "compressor", "evaporator coil", "blower", "heat exchanger",
            "inducer motor", "capacitor", "refrigerant", "air handler",
            "mini split", "ductless", "air handler", "plenum", "register",
            "return air", "supply air", "zoning damper", "combustion air",
            "gas valve", "ignitor", "flame sensor", "condensate drain",
            "r-410a", "r-454b", "seer2", "afue", "hspf",
        ],
        "severity_keywords": {
            "CRITICAL": [
                "carbon monoxide", "gas leak", "heat exchanger crack",
                "gas furnace crack", "no heat", "combustion gas leak",
                "gas odor", "cracked heat exchanger", "co detector alarm",
            ],
            "HIGH": [
                "rust", "leaking", "no cooling", "no ac", "refrigerant leak",
                "electrical burn", "unusual noise", "blower motor", "inducer motor",
                "cracked coil", "failed compressor", "frozen coil", "water leak ac",
                "condensate overflow", "malfunctioning", "not operating",
            ],
            "MEDIUM": [
                "dirty filter", "needs cleaning", "condensation", "mild noise",
                "thermostat calibration", "duct leak", "uneven heating",
                "uneven cooling", "minor corrosion", "low refrigerant",
                "dirty coil", "noisy blower", "weak airflow",
            ],
            "LOW": [
                "filter replacement", "cosmetic", "minor dust", "normal wear",
                "age noted", "service recommended", "seasonal maintenance",
                "clean condensate", "lubricate bearings",
            ],
        }
    },
    "ROOF": {
        "keywords": [
            "roof", "shingle", "flashing", "gutter", "downspout",
            "chimney flashing", "roof vent", "attic", "soffit", "fascia",
            "drip edge", "underlayment", "roof decking", "skylight",
            "roof valley", "ridge vent", "ice and water shield", "roof boot",
            "pipe boot", "roof turbine", "ridge cap", "starter strip",
            "roof sheathing", "roof felt", "synthetic underlayment",
            "ice dam", "roof saturation", "granule loss",
        ],
        "severity_keywords": {
            "CRITICAL": [
                "active leak", "hole in roof", "missing structural",
                "sagging roof", "roof collapse", "large area missing",
                "structural failure",
            ],
            "HIGH": [
                "damaged flashing", "missing shingles", "active water",
                "rot", "water intrusion", "damaged step flashing",
                "ice dam", "saturated", "delamination", "soft decking",
                "missing underlayment", "failed boot", "deteriorated",
            ],
            "MEDIUM": [
                "aging shingles", "granule loss", "minor flash gap",
                "caulk needed", "minor wear", "staining", "near end of life",
                "worn", "curling shingles", "minor algae", "loose flashing",
            ],
            "LOW": [
                "cosmetic", "moss", "algae", "minor debris", "cleaning needed",
                "age noted", "minor granule loss",
            ],
        }
    },
    "ELECTRICAL": {
        "keywords": [
            "electrical", "wiring", "panel", "circuit", "breaker", "gfci",
            "outlet", "switch", "grounding", "conduit", "subpanel",
            "arc fault", "afci", "service entrance", "meter", "disconnect",
            "fuse", "knob and tube", "aluminum wiring", "junction box",
            "romex", "nm cable", "mc cable", "branch circuit",
            "dedicated circuit", "200 amp", "100 amp", "service drop",
            "ground rod", "bonding", "neutral bar", "ground bar",
        ],
        "severity_keywords": {
            "CRITICAL": [
                "arcing", "burn marks", "hot wire", "exposed live",
                "no grounding", "fire hazard", "double tapped",
                "overloaded panel", "federal pacific", "zinsco",
                "knob and tube", "charred wiring", "melting",
            ],
            "HIGH": [
                "ungrounded", "no gfci", "missing gfci", "double tapped",
                "open junction", "improper wiring", "aluminum wiring",
                "code violation", "missing breaker lock", "undersized",
                "reverse polarity", "bootleg ground",
            ],
            "MEDIUM": [
                "loose outlet", "flickering", "minor code", "missing cover",
                "aged wiring", "non-standard", "unlabeled panel",
                "missing label", "missing cap", "improper splice",
            ],
            "LOW": [
                "cosmetic plate", "paint on outlet", "standard wear",
                "minor", "recommend upgrade", "outdated receptacle",
            ],
        }
    },
    "PLUMBING": {
        "keywords": [
            "plumbing", "pipe", "drain", "faucet", "toilet", "sink",
            "water heater", "sewer", "supply line", "waste", "trap",
            "valve", "hose bib", "sump pump", "backflow", "polybutylene",
            "copper", "pex", "cast iron", "pvc", "abs", "galvanized",
            "main water line", "shut off", "angle stop", "ball valve",
            "gate valve", "check valve", "prv", "pressure regulator",
            "water softener", "backwater valve", "cleanout",
        ],
        "severity_keywords": {
            "CRITICAL": [
                "active leak", "burst pipe", "sewer backup", "no water",
                "gas leak", "water heater failure", "main line break",
                "flooding", "sewage", "overflow", "broken pipe",
            ],
            "HIGH": [
                "slow drain", "leaking pipe", "corroded", "rust",
                "active drip", "water damage", "polybutylene", "sagging pipe",
                "wrong material", "waste leak", "supply leak",
                "failed valve", "low hot water",
            ],
            "MEDIUM": [
                "low pressure", "minor drip", "slow flow", "age noted",
                "hard water", "caulk needed", "minor corrosion",
                "loose faucet", "running toilet", "minor seep",
            ],
            "LOW": [
                "cosmetic", "staining", "normal wear", "maintenance recommended",
                "drip faucet", "calcification", "minor mineral",
            ],
        }
    },
    "STRUCTURAL": {
        "keywords": [
            "foundation", "crack", "settling", "shifting", "beam", "joist",
            "stud", "load bearing", "structural", "retaining wall", "post",
            "column", "header", "shear wall", "crawl space", "basement",
            "garage slab", "concrete", "masonry", "brick", "sill plate",
            "rim joist", "subfloor", "lally column", "pier", " footing",
            "stem wall", "slab", "basement wall", "parging",
        ],
        "severity_keywords": {
            "CRITICAL": [
                "structural failure", "collapse risk", "major settling",
                "large crack", "bowing wall", "floor sag",
                "load bearing damage", "rotten sill", "foundation failure",
                "wall rotation",
            ],
            "HIGH": [
                "active crack", "settling crack", "vertical crack",
                "horizontal crack", "foundation crack", "wall crack",
                "floor crack", "door won't close", "step crack",
                "displaced brick", "rotten joist", "sagging floor",
            ],
            "MEDIUM": [
                "hairline crack", "minor settling", "small crack",
                "caulk crack", "age related", "minor settlement",
                "stair step crack", "minor deflection",
            ],
            "LOW": [
                "cosmetic crack", "minor", "staining", "normal settling",
                "painted crack", "shrinkage crack",
            ],
        }
    },
    "EXTERIOR": {
        "keywords": [
            "siding", "exterior", "paint", "stucco", "brick", "stone",
            "deck", "patio", "porch", "balcony", "railing", "fence",
            "driveway", "walkway", "grading", "drainage", "landscape",
            "retaining", "garage", "windows", "doors", "fascia",
            "soffit", "trim", "caulk", "expansion joint", "EIFS",
            "hardie board", "vinyl siding", "wood siding", "brick veneer",
        ],
        "severity_keywords": {
            "CRITICAL": [
                "structural failure", "collapse", "rotten deck",
                "unsafe railing", "severe erosion", "unsafe balcony",
                "detached railing",
            ],
            "HIGH": [
                "rot", "damage", "missing", "broken", "peeling paint",
                "water damage", "improper drainage", "safety hazard",
                "missing handrail", "detached siding", "cracked stucco",
                "rotten trim", "failing EIFS",
            ],
            "MEDIUM": [
                "aging", "minor damage", "caulk needed", "minor rot",
                "staining", "settling", "weathering", "faded paint",
                "minor cracking", "efflorescence",
            ],
            "LOW": [
                "cosmetic", "minor paint", "touch up", "cleaning",
                "normal wear", "dirt", "minor mildew",
            ],
        }
    },
    "INSULATION": {
        "keywords": [
            "insulation", "vapor barrier", "attic insulation", "wall insulation",
            "air sealing", "energy", "R-value", "spray foam", "fiberglass",
            "cellulose", "mineral wool", "radiant barrier", "house wrap",
            "weatherization", "thermal envelope",
        ],
        "severity_keywords": {
            "CRITICAL": [
                "asbestos", "vermiculite", "no insulation", "wet insulation",
                "mold insulation",
            ],
            "HIGH": [
                "compressed", "wet", "missing", "damaged", "improper",
                "gaps", "air leak", "void", "water damaged",
            ],
            "MEDIUM": [
                "insufficient", "settled", "thin", "age noted", "minor gaps",
                "incomplete coverage",
            ],
            "LOW": [
                "cosmetic", "minor", "recommend upgrade", "standard wear",
                "could improve",
            ],
        }
    },
    "APPLIANCES": {
        "keywords": [
            "appliance", "stove", "oven", "refrigerator", "dishwasher",
            "microwave", "washer", "dryer", "garbage disposal", "range hood",
            "built-in", "cooktop", "freezer", "ice maker", "wine cooler",
            "trash compactor", "instant hot",
        ],
        "severity_keywords": {
            "CRITICAL": ["fire hazard", "gas leak", "no function", "dangerous"],
            "HIGH": ["not working", "broken", "damaged", "leaking", "electrical issue", "rust"],
            "MEDIUM": ["cosmetic damage", "noisy", "minor issue", "aging", "needs repair"],
            "LOW": ["cosmetic", "normal wear", "end of life", "recommend replacement"],
        }
    },
    "WINDOWS_DOORS": {
        "keywords": [
            "window", "door", "sliding", "patio door", "french", "screen",
            "glass", "frame", "sill", "lintel", "weather stripping",
            "lock", "hardware", "double pane", "single pane", "low-e",
            "tempered", "argon", "bay window", "bow window", "casement",
            "double hung", "picture window", "transom", "sidelight",
        ],
        "severity_keywords": {
            "CRITICAL": ["broken glass", "security hazard", "stuck open", "structural issue"],
            "HIGH": [
                "broken seal", "failed", "rot", "water intrusion",
                "won't lock", "damaged frame", "condensation between panes",
                "draft severe", "stuck",
            ],
            "MEDIUM": [
                "draft", "minor damage", "aging", "sticking",
                "caulk needed", "weatherstrip", "minor seal fog",
            ],
            "LOW": ["cosmetic", "minor", "paint", "normal wear"],
        }
    },
    "FIRE_SAFETY": {
        "keywords": [
            "smoke detector", "carbon monoxide", "fire", "sprinkler",
            "egress", "fireplace", "chimney", "damper", "flue", "hearth",
            "fire extinguisher", "fire rated", "fire block", "intumescent",
        ],
        "severity_keywords": {
            "CRITICAL": [
                "no smoke detector", "no co detector", "blocked egress",
                "fire hazard", "gas leak fireplace", "chimney fire damage",
            ],
            "HIGH": [
                "missing detector", "non-functioning", "damaged flue",
                "creosote buildup", "cracked flue tile", "missing cap",
                "damper inoperable", "damaged firebox",
            ],
            "MEDIUM": [
                "aging detector", "minor damage", "needs cleaning",
                "recommend service", "test needed",
            ],
            "LOW": ["cosmetic", "normal wear", "recommend upgrade"],
        }
    },
    "MOISTURE": {
        "keywords": [
            "moisture", "water", "damp", "humidity", "condensation",
            "mold", "mildew", "water stain", "efflorescence", "seepage",
            "leakage", "penetration", "vapor", "sweating", "dew point",
        ],
        "severity_keywords": {
            "CRITICAL": [
                "active mold", "structural water damage", "flooding",
                "major water intrusion", "black mold",
            ],
            "HIGH": [
                "active moisture", "water stain", "damp", "mold growth",
                "musty odor", "condensation", "efflorescence",
            ],
            "MEDIUM": [
                "high humidity", "minor stain", "condensation seasonal",
                "minor damp",
            ],
            "LOW": ["cosmetic stain", "minor", "seasonal", "normal"],
        }
    },
    "SOLAR": {
        "keywords": [
            "solar panel", "photovoltaic", "pv system", "inverter",
            "solar array", "solar cells", "net meter", "microinverter",
            "string inverter", "solar battery", "powerwall", "solar mount",
            "solar racking", "optimizers", "rapid shutdown",
        ],
        "severity_keywords": {
            "CRITICAL": ["electrical hazard", "fire risk", "roof penetration leak", "arcing inverter"],
            "HIGH": ["cracked panel", "inverter failure", "microinverters offline", "rapid shutdown failure", "damaged wiring"],
            "MEDIUM": ["dirty panels", "minor micro cracks", "degraded output", "loose mounting", "aging inverter"],
            "LOW": ["cosmetic", "normal degradation", "panel cleaning needed", "monitoring offline"],
        }
    },
    "EV_CHARGER": {
        "keywords": [
            "ev charger", "evSE", "electric vehicle", "level 2 charger",
            "charging station", "nema 14-50", "dedicated circuit ev",
            "tesla charger", "wall connector", "chargepoint",
        ],
        "severity_keywords": {
            "CRITICAL": ["arcing", "burn marks", "no ground", "electrical hazard"],
            "HIGH": ["not charging", "tripping breaker", "damaged connector", "improper install", "missing permit"],
            "MEDIUM": ["slow charge", "loose mount", "weather damage cover", "fault code"],
            "LOW": ["cosmetic", "cover missing", "firmware update needed"],
        }
    },
    "SMART_HOME": {
        "keywords": [
            "smart home", "smart lock", "smart thermostat", "ring doorbell",
            "nest", "alexa", "smart switch", "smart outlet", "home automation",
            "wifi thermostat", "smart sensor", "smart sprinkler", "smart garage",
        ],
        "severity_keywords": {
            "CRITICAL": ["security breach", "lock failure", "fire hazard smart device"],
            "HIGH": ["not connected", "dead battery lock", "firmware failure", "unresponsive"],
            "MEDIUM": ["intermittent", "wifi disconnect", "outdated firmware", "compatibility issue"],
            "LOW": ["cosmetic", "cosmetic mount", "battery low", "recommend upgrade"],
        }
    },
    "GARAGE": {
        "keywords": [
            "garage", "garage door", "garage door opener", "garage floor",
            "garage wall", "garage ceiling", "garage framing", "epoxy floor",
            "garage spring", "garage track", "garage sensor", "garage remote",
            "garage weatherstrip",
        ],
        "severity_keywords": {
            "CRITICAL": ["spring broken", "door fallen", "structural failure", "co from attached garage"],
            "HIGH": ["opener failure", "off track", "damaged spring", "rotten framing", "water intrusion", "no fire separation"],
            "MEDIUM": ["noisy operation", "minor dents", "weatherstrip worn", "sensor misalignment", "minor rust"],
            "LOW": ["cosmetic", "lubrication needed", "remote battery", "cosmetic floor"],
        }
    },
    "ATTIC": {
        "keywords": [
            "attic", "attic access", "attic fan", "attic ventilation",
            "attic insulation", "attic roof decking", "attic storage",
            "radiant barrier", "attic hatch", "attic ladder",
        ],
        "severity_keywords": {
            "CRITICAL": ["sagging roof deck visible", "active leak in attic", "structural damage", "widespread mold"],
            "HIGH": ["insufficient ventilation", "missing insulation", "rot", "water staining", "pest damage", "no vapor barrier"],
            "MEDIUM": ["minor staining", "dust accumulation", "minor insulation gaps", "minor condensation"],
            "LOW": ["cosmetic", "dust", "minor", "recommend insulation upgrade"],
        }
    },
    "CRAWLSPACE": {
        "keywords": [
            "crawl space", "crawlspace", "crawl area", "vapor barrier crawl",
            "pier crawl", "vent crawl", "encapsulation", "sub-area",
        ],
        "severity_keywords": {
            "CRITICAL": ["standing water", "structural failure", "rotten joists", "gas accumulation", "radon high"],
            "HIGH": ["moisture", "mold", "pest damage", "missing vapor barrier", "sagging insulation", "rotten subfloor"],
            "MEDIUM": ["damp", "minor moisture", "debris", "minor settling", "disconnected duct"],
            "LOW": ["cosmetic", "minor debris", "dust", "minor"],
        }
    },
    "GRADING_DRAINAGE": {
        "keywords": [
            "grading", "drainage", "slope", "gutter slope", "downspout extension",
            "French drain", "surface drain", "swale", "positive drainage",
            "regrading", "water runoff", "erosion", "landscape grading",
        ],
        "severity_keywords": {
            "CRITICAL": ["water flowing toward foundation", "severe erosion", "foundation undermining", "active flooding"],
            "HIGH": ["improper slope", "downspout discharge near foundation", "standing water", "erosion near foundation"],
            "MEDIUM": ["minor slope issues", "minor erosion", "downspout needs extension"],
            "LOW": ["minor grading", "landscape maintenance", "cosmetic"],
        }
    },
    "RETAINING_WALL": {
        "keywords": [
            "retaining wall", "gravity wall", "segmental wall", "moss wall",
            "crib wall", "gabion wall", "keystone wall", "block wall",
            "battered wall",
        ],
        "severity_keywords": {
            "CRITICAL": ["wall failure", "tilting > 2 inches", "bulging", "collapsed section"],
            "HIGH": ["cracking", "tilting", "water pressure behind wall", "missing drainage", "soil pushing"],
            "MEDIUM": ["minor lean", "minor cracking", "efflorescence", "aging"],
            "LOW": ["cosmetic", "minor", "staining", "vegetation", "minor mortar"],
        }
    },
    "STAIRS_RAILINGS": {
        "keywords": [
            "stairs", "stairway", "railing", "handrail", "guardrail",
            "baluster", "tread", "riser", "stringer", "landing",
            "stair nosing", "winder", "spiral stair",
        ],
        "severity_keywords": {
            "CRITICAL": ["collapsed stair", "missing guardrail", "unstable railing", "rotten stringer"],
            "HIGH": ["loose railing", "missing balusters", "rotten tread", "wobbly handrail", "code violation height"],
            "MEDIUM": ["loose tread", "minor wobble", "worn nosing", "squeaky"],
            "LOW": ["cosmetic", "minor", "paint", "stain wear"],
        }
    },
    "DRIVEWAY_SIDEWALK": {
        "keywords": [
            "driveway", "sidewalk", "concrete slab", "asphalt driveway",
            "pavers", "expansion joint", "control joint", "trip hazard",
            "heaved slab", "sunken slab", "cracked concrete",
        ],
        "severity_keywords": {
            "CRITICAL": ["major trip hazard > 2 inches", "collapsed section", "major undermining"],
            "HIGH": ["trip hazard", "large cracks", "heaving", "severe spalling", "major settlement"],
            "MEDIUM": ["minor cracking", "minor spalling", "minor settlement", "staining"],
            "LOW": ["cosmetic", "hairline crack", "minor", "staining", "minor wear"],
        }
    },
    "DRYER_VENT": {
        "keywords": [
            "dryer vent", "dryer exhaust", "dryer duct", "lint trap",
            "dryer hose", "rigid duct dryer", "transition duct",
        ],
        "severity_keywords": {
            "CRITICAL": ["vented into attic", "vented into crawlspace", "compressed duct", "no vent", "excessive lint buildup fire hazard"],
            "HIGH": ["flexible duct long run", " crushed duct", "excessive length", "missing damper", "lint buildup"],
            "MEDIUM": ["minor lint", "damper weak", "long run noted", "minor kink"],
            "LOW": ["cosmetic", "minor", "clean recommended"],
        }
    },
    "BATHROOM_EXHAUST": {
        "keywords": [
            "bathroom exhaust", "bathroom fan", "exhaust fan", "vent fan",
            "bathroom vent", "humidity sensor fan", "timer fan",
        ],
        "severity_keywords": {
            "CRITICAL": ["vented into attic", "no exhaust fan", "mold from moisture", "no vent in bathroom"],
            "HIGH": ["not functioning", "disconnected duct", "vented into soffit", "excessive noise"],
            "MEDIUM": ["weak airflow", "noisy motor", "timer needed", "minor condensation"],
            "LOW": ["cosmetic", "cover dirty", "minor", "recommend upgrade"],
        }
    },
    "SUMP_PUMP": {
        "keywords": [
            "sump pump", "sump basin", "sump pit", "check valve sump",
            "battery backup sump", "primary sump", "discharge line",
        ],
        "severity_keywords": {
            "CRITICAL": ["no sump pump", "failed sump pump", "flooding", "discharge frozen"],
            "HIGH": ["old pump", "no backup", "discharge issues", "check valve missing", "running constantly"],
            "MEDIUM": ["aging pump", "minor noise", "intermittent", "discharge outside close to foundation"],
            "LOW": ["cosmetic", "minor", "test recommended", "battery old"],
        }
    },
    "WATER_SOFTENER": {
        "keywords": [
            "water softener", "water treatment", "water filter",
            "water conditioner", "whole house filter", "sediment filter",
            "water purification",
        ],
        "severity_keywords": {
            "CRITICAL": ["water contamination", "bypass open leaking", "no treatment hard water damage"],
            "HIGH": ["not functioning", "leaking", "old media", "bypass valve leaking", "out of salt"],
            "MEDIUM": ["aging unit", "minor leak", "needs salt", "minor performance"],
            "LOW": ["cosmetic", "minor", "recommend service", "cosmetic cover"],
        }
    },
    "GARBAGE_DISPOSAL": {
        "keywords": [
            "garbage disposal", "waste disposal", "disposer",
            "food waste disposal",
        ],
        "severity_keywords": {
            "CRITICAL": ["electrical hazard", "leaking massively", "jammed motor", "leaking from body"],
            "HIGH": ["not working", "leaking", "jammed", "humming not spinning", "leaking at flange"],
            "MEDIUM": ["noisy", "slow drain", "minor leak", "dull blades"],
            "LOW": ["cosmetic", "minor", "smell", "maintenance recommended"],
        }
    },
    "CEILING_FANS": {
        "keywords": [
            "ceiling fan", "fan light", "fan motor", "fan blade",
            "fan mount", "fan remote", "fan capacitor",
        ],
        "severity_keywords": {
            "CRITICAL": ["falling fan", "exposed wiring", "wobbling severely", "electrical hazard"],
            "HIGH": ["wobbling", "motor noise", "light not working", "remote not working", "loose mount"],
            "MEDIUM": ["minor wobble", "noisy", "slow speed", "light dimmer issue"],
            "LOW": ["cosmetic", "dust", "minor", "blade balancing needed"],
        }
    },
    "LIGHT_FIXTURES": {
        "keywords": [
            "light fixture", "recessed light", "can light", "pendant light",
            "chandelier", "sconce", "under cabinet light", "landscape light",
            "motion light", "porch light", "flood light",
        ],
        "severity_keywords": {
            "CRITICAL": ["electrical hazard", "burning smell", "exposed wiring", "water in fixture"],
            "HIGH": ["not working", "flickering", "damaged", "missing lens", "loose mount"],
            "MEDIUM": ["minor flicker", "dim", "cosmetic damage", "aging"],
            "LOW": ["cosmetic", "bulb burned", "minor", "recommend upgrade LED"],
        }
    },
    "SMOKE_CO_DETECTORS": {
        "keywords": [
            "smoke detector", "smoke alarm", "carbon monoxide detector",
            "co alarm", "combination detector", "photoelectric smoke",
            "ionization smoke", "interconnected smoke", "battery smoke",
        ],
        "severity_keywords": {
            "CRITICAL": ["no smoke detector", "no co detector", "expired detector", "interconnected missing", "non functioning both"],
            "HIGH": ["missing in bedroom", "missing on floor", "expired", "not interconnect", "not accessible"],
            "MEDIUM": ["aging unit", "chirping", "minor issue", "battery low"],
            "LOW": ["cosmetic", "recommend upgrade", "age noted", "test recommended"],
        }
    },
    "GFCI_AFCI": {
        "keywords": [
            "gfci", "gfci outlet", "gfci breaker", "arc fault",
            "afci", "afci breaker", "ground fault", "arc fault interrupter",
            "dual function breaker", "gfci protected",
        ],
        "severity_keywords": {
            "CRITICAL": ["no gfci in wet area", "no afci required", "gfci test fail", "electrical hazard", "missing required protection"],
            "HIGH": ["gfci won't reset", "missing gfci kitchen", "missing gfci bath", "tripping", "no afci bedroom"],
            "MEDIUM": ["gfci aging", "gfci intermittent", "minor issue", "recommend upgrade"],
            "LOW": ["cosmetic", "test recommend", "minor", "recommend dual function"],
        }
    },
    "WHOLE_HOUSE_GENERATOR": {
        "keywords": [
            "whole house generator", "standby generator", "auto transfer switch",
            "ats", "generac guardian", "natural gas generator",
            "propane generator", "generator panel",
        ],
        "severity_keywords": {
            "CRITICAL": ["co risk", "failed transfer", "no generator maintenance", "gas line leak generator"],
            "HIGH": ["not starting", "transfer switch failure", "maintenance overdue", "oil leak", "expired warranty"],
            "MEDIUM": ["minor noise", "self test fail", "aging battery", "minor maintenance"],
            "LOW": ["cosmetic", "cover needed", "maintenance recommend", "cosmetic rust"],
        }
    },
}

MATERIAL_COSTS_2026 = {
    "asphalt_shingles_per_sq": {
        "min": 110, "avg": 160, "max": 220,
        "unit": "per square (100 sq ft)",
        "note": "Architectural shingles avg 15-20% more than 3-tab; designer shingles 30-50% more",
    },
    "asphalt_shingles_3tab_per_sq": {
        "min": 85, "avg": 120, "max": 165,
        "unit": "per square (100 sq ft)",
        "note": "Basic 3-tab; increasingly rare as architectural becomes standard",
    },
    "metal_roofing_per_sq": {
        "min": 350, "avg": 550, "max": 850,
        "unit": "per square (100 sq ft)",
        "note": "Standing seam; corrugated 30-40% less",
    },
    "roof_underlayment_per_sq": {
        "min": 25, "avg": 45, "max": 75,
        "unit": "per square (100 sq ft)",
        "note": "Synthetic underlayment; felt paper 40% less",
    },
    "roof_flashing_per_ft": {
        "min": 11, "avg": 19, "max": 32,
        "unit": "per linear foot",
    },
    "roof_ice_water_shield_per_sq": {
        "min": 40, "avg": 65, "max": 95,
        "unit": "per square (100 sq ft)",
        "note": "Self-adhering membrane for eaves/valleys",
    },
    "roof_ridge_vent_per_ft": {
        "min": 4, "avg": 7, "max": 12,
        "unit": "per linear foot installed",
    },
    "roof_pipe_boot": {
        "min": 25, "avg": 50, "max": 90,
        "unit": "each installed",
        "note": "Neoprene or silicone roof boot for plumbing penetrations",
    },
    "plywood_sheet_4x8": {
        "min": 40, "avg": 55, "max": 72,
        "unit": "per sheet",
        "note": "CDX grade 1/2 inch; OSB 20-25% less",
    },
    "osb_sheet_4x8": {
        "min": 28, "avg": 38, "max": 52,
        "unit": "per sheet",
        "note": "Oriented strand board 7/16 inch",
    },
    "hvac_full_system": {
        "min": 5800, "avg": 9000, "max": 15000,
        "unit": "installed",
        "note": "SEER2 ratings now required; R-454B refrigerant transition underway",
    },
    "hvac_condenser_unit": {
        "min": 1500, "avg": 2800, "max": 5500,
        "unit": "each",
        "note": "Outdoor condensing unit; 3 ton avg 16 SEER2",
    },
    "hvac_evaporator_coil": {
        "min": 750, "avg": 1400, "max": 2900,
        "unit": "each",
    },
    "hvac_furnace_gas": {
        "min": 2200, "avg": 3800, "max": 6500,
        "unit": "installed",
        "note": "80% AFUE standard; 96% AFUE 30-40% more",
    },
    "hvac_compressor": {
        "min": 1000, "avg": 1900, "max": 3600,
        "unit": "each",
        "note": "R-410A phase-out driving R-454B transition costs in 2026",
    },
    "hvac_motor": {
        "min": 190, "avg": 440, "max": 1000,
        "unit": "each",
        "note": "ECM motors cost 30-50% more than PSC but save 70% energy",
    },
    "hvac_capacitor": {
        "min": 20, "avg": 58, "max": 145,
        "unit": "each",
    },
    "hvac_ductwork_per_sqft": {
        "min": 8, "avg": 15, "max": 28,
        "unit": "per sq ft of conditioned space",
        "note": "New ductwork installation including trunk and branches",
    },
    "hvac_thermostat_smart": {
        "min": 150, "avg": 280, "max": 450,
        "unit": "each installed",
        "note": "WiFi-enabled programmable thermostat",
    },
    "water_heater_50gal_tank": {
        "min": 1000, "avg": 1700, "max": 2900,
        "unit": "installed",
        "note": "Standard tank; 2026 national avg pricing",
    },
    "water_heater_tankless": {
        "min": 2300, "avg": 3700, "max": 5800,
        "unit": "installed",
        "note": "Energy savings of 30-40% vs tank; requires gas line upgrade often",
    },
    "water_heater_80gal_tank": {
        "min": 1500, "avg": 2400, "max": 4000,
        "unit": "installed",
        "note": "Large tank for high-demand households",
    },
    "electrical_panel_200amp": {
        "min": 1900, "avg": 3200, "max": 5200,
        "unit": "installed",
        "note": "AFCI/GFCI breakers add $40-80 each; smart panels add $800+",
    },
    "electrical_panel_100amp": {
        "min": 1200, "avg": 2200, "max": 3800,
        "unit": "installed",
    },
    "electrical_outlet_gfci": {
        "min": 16, "avg": 32, "max": 58,
        "unit": "each installed",
    },
    "electrical_outlet_standard": {
        "min": 8, "avg": 18, "max": 35,
        "unit": "each installed",
    },
    "electrical_switch": {
        "min": 8, "avg": 16, "max": 30,
        "unit": "each installed",
    },
    "electrical_wire_14awg_per_ft": {
        "min": 0.30, "avg": 0.55, "max": 0.90,
        "unit": "per foot",
        "note": "14/2 NM-B (Romex) for 15A circuits",
    },
    "electrical_wire_12awg_per_ft": {
        "min": 0.45, "avg": 0.80, "max": 1.30,
        "unit": "per foot",
        "note": "12/2 NM-B (Romex) for 20A circuits",
    },
    "copper_pipe_per_ft": {
        "min": 5.50, "avg": 11, "max": 20,
        "unit": "per foot",
        "note": "Copper prices at historic highs in 2026 due to global supply constraints",
    },
    "pex_pipe_per_ft": {
        "min": 1.30, "avg": 3.20, "max": 6.50,
        "unit": "per foot",
    },
    "pvc_pipe_per_ft": {
        "min": 0.80, "avg": 2.00, "max": 4.50,
        "unit": "per foot",
        "note": "Schedule 40 PVC for drain/waste/vent",
    },
    "cast_iron_pipe_per_ft": {
        "min": 8, "avg": 15, "max": 28,
        "unit": "per foot installed",
        "note": "For sewer line replacement",
    },
    "toilet": {
        "min": 200, "avg": 400, "max": 800,
        "unit": "each installed",
        "note": "Standard two-piece; comfort height 10-15% more",
    },
    "faucet_kitchen": {
        "min": 150, "avg": 350, "max": 700,
        "unit": "each installed",
    },
    "faucet_bathroom": {
        "min": 100, "avg": 250, "max": 550,
        "unit": "each installed",
    },
    "sink_kitchen": {
        "min": 200, "avg": 450, "max": 1000,
        "unit": "each installed",
        "note": "Stainless steel standard; granite composite 40-60% more",
    },
    "garbage_disposal": {
        "min": 120, "avg": 220, "max": 400,
        "unit": "each installed",
        "note": "1/2 HP standard; 3/4 HP and above 30-50% more",
    },
    "drywall_sheet_4x8": {
        "min": 15, "avg": 19, "max": 30,
        "unit": "per sheet",
        "note": "1/2 inch standard; fire-rated 20-30% more",
    },
    "drywall_repair_per_sqft": {
        "min": 11, "avg": 20, "max": 32,
        "unit": "per sq ft",
    },
    "insulation_batt_per_sqft": {
        "min": 1.00, "avg": 1.85, "max": 3.75,
        "unit": "per sq ft installed",
        "note": "Fiberglass batt, R-13 to R-19; blown-in 15-25% less per R-value",
    },
    "spray_foam_per_sqft": {
        "min": 2.75, "avg": 4.50, "max": 7.50,
        "unit": "per sq ft installed",
        "note": "Closed-cell spray foam, R-6.5/inch; open-cell 40% less",
    },
    "blown_insulation_per_sqft": {
        "min": 0.80, "avg": 1.50, "max": 3.00,
        "unit": "per sq ft installed",
        "note": "Cellulose or fiberglass loose-fill",
    },
    "window_standard": {
        "min": 520, "avg": 1000, "max": 1900,
        "unit": "each installed",
        "note": "Double-pane vinyl, ENERGY STAR rated; wood clad 50-80% more",
    },
    "door_interior": {
        "min": 190, "avg": 370, "max": 750,
        "unit": "each installed",
    },
    "door_exterior": {
        "min": 650, "avg": 1300, "max": 3200,
        "unit": "each installed",
        "note": "Fiberglass/steel, insulated; wood 60-100% more",
    },
    "sliding_patio_door": {
        "min": 800, "avg": 1600, "max": 3500,
        "unit": "each installed",
        "note": "Vinyl standard; French doors 40-70% more",
    },
    "deck_boards_per_sqft": {
        "min": 5.50, "avg": 9.00, "max": 16,
        "unit": "per sq ft",
        "note": "Composite decking 40-60% more than pressure-treated lumber",
    },
    "concrete_per_yard": {
        "min": 145, "avg": 180, "max": 235,
        "unit": "per cubic yard delivered",
        "note": "Ready-mix 3000 PSI standard",
    },
    "concrete_repair_per_sqft": {
        "min": 11, "avg": 20, "max": 38,
        "unit": "per sq ft",
    },
    "stucco_per_sqft": {
        "min": 7.50, "avg": 13, "max": 20,
        "unit": "per sq ft",
    },
    "vinyl_siding_per_sqft": {
        "min": 3.50, "avg": 6.50, "max": 11,
        "unit": "per sq ft installed",
    },
    "hardie_siding_per_sqft": {
        "min": 6, "avg": 10, "max": 16,
        "unit": "per sq ft installed",
        "note": "Fiber cement (HardiePlank); premium 20-30% more",
    },
    "brick_veneer_per_sqft": {
        "min": 10, "avg": 18, "max": 30,
        "unit": "per sq ft installed",
    },
    "gutter_per_ft": {
        "min": 8, "avg": 15, "max": 28,
        "unit": "per linear foot installed",
        "note": "Aluminum 6-inch seamless; copper 80-120% more",
    },
    "downspout_per_ft": {
        "min": 6, "avg": 12, "max": 22,
        "unit": "per linear foot installed",
    },
    "fence_per_ft": {
        "min": 18, "avg": 30, "max": 55,
        "unit": "per linear foot installed",
        "note": "6-foot privacy fence; chain link 40-50% less",
    },
    "sod_per_sqft": {
        "min": 0.45, "avg": 0.85, "max": 1.50,
        "unit": "per sq ft installed",
    },
    "paint_interior_per_sqft": {
        "min": 2.00, "avg": 4.00, "max": 7.00,
        "unit": "per sq ft",
        "note": "Two coats; prep work included in estimate",
    },
    "paint_exterior_per_sqft": {
        "min": 2.50, "avg": 5.00, "max": 9.00,
        "unit": "per sq ft",
        "note": "Includes power wash, prep, prime, two coats",
    },
    "trim_per_ft": {
        "min": 4, "avg": 8, "max": 15,
        "unit": "per linear foot installed",
        "note": "Baseboard or crown molding; MDF standard; hardwood 50-100% more",
    },
    "crown_molding_per_ft": {
        "min": 6, "avg": 12, "max": 22,
        "unit": "per linear foot installed",
    },
    "pipe_snaking": {
        "min": 130, "avg": 260, "max": 420,
        "unit": "per occurrence",
    },
    "hydro_jetting": {
        "min": 300, "avg": 550, "max": 900,
        "unit": "per occurrence",
        "note": "High-pressure water jet for sewer main clearing",
    },
    "sewer_scope": {
        "min": 180, "avg": 340, "max": 575,
        "unit": "per inspection",
        "note": "Camera inspection of main sewer line",
    },
    "mold_remediation_per_sqft": {
        "min": 13, "avg": 26, "max": 48,
        "unit": "per sq ft",
        "note": "Professional remediation, includes containment and HEPA filtration",
    },
    "radon_mitigation_system": {
        "min": 950, "avg": 1800, "max": 3000,
        "unit": "installed",
        "note": "Sub-slab depressurization system with fan and piping",
    },
    "epoxy_garage_floor_per_sqft": {
        "min": 4, "avg": 7, "max": 12,
        "unit": "per sq ft",
        "note": "Two-part epoxy with flake broadcast",
    },
    "hardwood_floor_per_sqft": {
        "min": 6, "avg": 10, "max": 18,
        "unit": "per sq ft installed",
        "note": "Solid hardwood; engineered 15-25% less",
    },
    "tile_floor_per_sqft": {
        "min": 8, "avg": 15, "max": 28,
        "unit": "per sq ft installed",
        "note": "Ceramic tile; porcelain 20-30% more",
    },
    "carpet_per_sqft": {
        "min": 3, "avg": 6, "max": 11,
        "unit": "per sq ft installed",
        "note": "Includes pad and installation; premium wool 80-150% more",
    },
    "lvp_flooring_per_sqft": {
        "min": 3.50, "avg": 6.50, "max": 12,
        "unit": "per sq ft installed",
        "note": "Luxury vinyl plank; waterproof, increasingly popular",
    },
    "labor_hourly_handyman": {
        "min": 42, "avg": 65, "max": 100,
        "unit": "per hour",
        "note": "Skilled labor shortage driving rates up 8-12% annually",
    },
    "labor_hourly_electrician": {
        "min": 72, "avg": 100, "max": 155,
        "unit": "per hour",
        "note": "Licensed master electrician rates",
    },
    "labor_hourly_plumber": {
        "min": 75, "avg": 110, "max": 180,
        "unit": "per hour",
        "note": "Licensed master plumber rates",
    },
    "labor_hourly_hvac_tech": {
        "min": 80, "avg": 118, "max": 190,
        "unit": "per hour",
        "note": "EPA 608 certified technician rates",
    },
    "labor_hourly_roofer": {
        "min": 52, "avg": 76, "max": 118,
        "unit": "per hour",
    },
    "labor_hourly_general": {
        "min": 48, "avg": 72, "max": 112,
        "unit": "per hour",
    },
    "labor_hourly_mason": {
        "min": 55, "avg": 82, "max": 130,
        "unit": "per hour",
    },
    "labor_hourly_painter": {
        "min": 40, "avg": 60, "max": 95,
        "unit": "per hour",
    },
    "labor_hourly_landscaper": {
        "min": 35, "avg": 55, "max": 85,
        "unit": "per hour",
    },
    "labor_hourly_framer": {
        "min": 48, "avg": 72, "max": 110,
        "unit": "per hour",
    },
    "labor_hourly_drywall": {
        "min": 42, "avg": 65, "max": 100,
        "unit": "per hour",
    },
    "labor_hourly_flooring": {
        "min": 40, "avg": 62, "max": 95,
        "unit": "per hour",
    },
}

MUNICIPAL_PERMIT_TYPES = [
    "Building Permit", "Electrical Permit", "Plumbing Permit", "Mechanical Permit",
    "Roofing Permit", "Demolition Permit", "Deck/Porch Permit", "Addition Permit",
    "Electrical Subpanel Permit", "Water Heater Permit", "HVAC Permit",
    "Siding Permit", "Window/Door Permit", "Fence Permit", "Grading Permit",
    "Septic Permit", "Well Permit", "Solar Permit", "Pool/Spa Permit",
]

HELP_CONTENT = {
    "dashboard": {
        "title": "Dashboard Overview",
        "description": "The Dashboard provides a high-level snapshot of all 21 analysis modules, your current project status, and embedded cost data. This is your command center for orchestrating the entire inspection analysis workflow.",
        "sections": {
            "System Modules": "All 21 engines are listed here. Each module runs independently when you click 'Run Analysis'. Green badges indicate active modules, yellow indicates pending, and red indicates errors. Click any module name to jump directly to its detailed view.",
            "Quick Start": "A step-by-step guide to get your first analysis running in under 60 seconds. Step 1: Enter property address and ZIP code. Step 2: Upload your inspection PDF or enable sample data. Step 3: Click 'Run Analysis'. The system will process all modules sequentially with a live progress bar.",
            "Embedded Cost Data": "Shows a preview of the 2026 construction material cost database embedded in the tool. All prices reflect Q2 2026 national averages sourced from RSMeans, BLS, HomeAdvisor/Angi, and contractor network data. Regional modifiers are auto-applied based on your ZIP code.",
            "Progress Tracker": "The live progress bar shows each module as it processes. Typical full analysis takes 15-45 seconds depending on report length. Each module produces independent results that are cross-referenced in later stages.",
            "Cost Preview": "The dashboard shows a running total of estimated costs as modules complete. This gives you an early look at the financial picture before diving into individual module details.",
        }
    },
    "upload": {
        "title": "Upload & Parse Inspection Report",
        "description": "Upload any PDF home inspection report. The Agentic Parse Engine extracts text, classifies findings by severity using NLP, deduplicates overlapping entries, and maps photos to findings. This is the foundation of the entire analysis pipeline.",
        "sections": {
            "Property Information": "Enter the property details including address, city, state, and ZIP code. The ZIP code is critical as it determines localized labor rates from our database of 80+ metro areas, material cost multipliers, permit fees, local building code requirements, and regional market conditions.",
            "Upload PDF": "Drag and drop any inspection report PDF. Supports scanned documents via OCR, text-based PDFs, and mixed formats. Reports from major inspection software (HomeGauge, Spectora, InspectIT, 3D Inspections) are optimized for parsing. Max file size: 50MB.",
            "Sample Data": "Check this to instantly load a comprehensive sample dataset with 85+ realistic findings across all 21 systems. Perfect for exploring the tool's capabilities before uploading a real report. Sample data represents a typical 1990s-era suburban home.",
            "Processing Pipeline": "When you click 'Run Analysis', the system runs a multi-stage NLP pipeline: (1) text extraction and normalization, (2) sentence segmentation, (3) finding extraction with entity recognition, (4) severity classification using keyword matching and contextual analysis, (5) system categorization, (6) location/room assignment, (7) deduplication and merging, (8) photo-to-finding mapping via spatial proximity.",
            "Supported Formats": "PDF (scanned or text), DOCX (converted to PDF first), and plain text files. For best results, use text-based PDFs rather than scanned images. OCR accuracy for scans ranges from 85-98% depending on scan quality.",
        }
    },
    "cost_analysis": {
        "title": "Hyper-Local Cost Analysis",
        "description": "Every finding gets 3-tier pricing: DIY/Handyman, Licensed Contractor, and Emergency/Premium. Costs are adjusted for your ZIP code using embedded 2026 regional construction cost indexes covering 80+ metro areas across all 50 states plus DC.",
        "sections": {
            "Cost Breakdown": "Bar chart showing total estimated costs by severity level (Critical, High, Medium, Low). This visual instantly shows where the money is. Critical and High items typically represent 70-85% of total repair costs.",
            "Line-Item Estimates": "Each finding shows its DIY range, licensed contractor range, and emergency range. Material, labor, and permit costs are separated. The DIY range assumes you purchase materials and hire a handyman. Licensed contractor includes all materials, labor, markup, and overhead. Emergency/Premium includes after-hours, rush ordering, and contractor premium.",
            "Local Rate Information": "Shows the specific cost modifier applied for your ZIP code (e.g., NYC = 1.46x, Houston = 0.92x), local hourly labor rates by trade, and material price multipliers. Rates are derived from BLS Occupational Employment Statistics, RSMeans regional cost indexes, and contractor network surveys.",
            "Material Cost Database": "All material prices come from our embedded 2026 database with 50+ line items covering roofing, HVAC, plumbing, electrical, exterior, interior, and specialty trades. Prices are updated quarterly using RSMeans, HomeAdvisor/Angi, and direct contractor surveys.",
            "Permit Cost Estimates": "Based on typical municipal permit fee schedules. Major structural, electrical, and plumbing work often requires permits that add 5-15% to project costs. Permit requirements vary significantly by jurisdiction.",
            "Negotiation-Ready Totals": "The system calculates a 'Seller Credit Request' total using conservative (mid-range) estimates. This is designed to be defensible in negotiation. The range shows the spread between DIY and emergency pricing.",
            "Disclaimer": "All cost estimates are based on 2026 national averages with regional adjustments. Actual contractor bids may vary 15-30%. Always obtain 2-3 licensed contractor estimates before making decisions. Prices fluctuate with material costs, seasonal demand, and local market conditions.",
        }
    },
    "depreciation": {
        "title": "Depreciation & 24-Month CapEx Risk Horizon",
        "description": "Analyzes the remaining useful life and failure probability of every major home system. If a system is approaching end-of-life, it flags the upcoming replacement cost even if it is not broken yet. This is the most forward-looking module and critical for long-term budgeting.",
        "sections": {
            "Depreciation Timeline": "Each system shows its estimated age, useful life range, remaining useful life, current condition score, and replacement urgency rating. The urgency rating is color-coded: Red (replace within 12 months), Orange (replace within 24 months), Yellow (plan within 3-5 years), Green (>5 years remaining).",
            "Failure Probability Chart": "Visual chart showing the 24-month failure probability for each system using Weibull distribution curves. Red = >70% failure risk, Orange = >40%, Yellow = >20%, Green = <20%. Weibull distributions are the industry standard for reliability engineering and actuarial analysis.",
            "24-Month CapEx Timeline": "Cumulative risk chart showing when expenses are statistically likely to occur over the next 2 years. This helps buyers understand not just what needs fixing now, but what they will need to budget for in the near future. The chart shows monthly expected costs based on failure probability curves.",
            "How It Works": "Uses standard straight-line depreciation adjusted for condition and climate zone. Failure probability is calculated using Weibull distribution curves based on asset age vs. useful life. Climate zone adjustments account for accelerated deterioration in extreme environments (e.g., coastal salt air, extreme heat, freeze-thaw cycles). All replacement costs use 2026 pricing data from RSMeans and regional contractor surveys.",
            "Negotiation Value": "Items with high failure probability (<24 months) carry significant negotiation weight even if they appear functional today. A 15-year-old HVAC system may work perfectly during inspection but has a 60%+ chance of failure within 2 years. Presenting this data to sellers demonstrates data-driven negotiation rather than opinion-based requests.",
            "Common Mistakes": "Buyers often focus only on visibly broken items while ignoring systems nearing end-of-life. A roof that 'looks fine' at 22 years old on an asphalt shingle roof has a 35% failure probability within 24 months. The depreciation module prevents this costly oversight by quantifying future risk.",
        }
    },
    "market": {
        "title": "Market Analysis & Negotiation Strategy",
        "description": "Contextualizes the repairs against current market conditions. Generates item-by-item negotiation tactics based on whether it is a buyer's or seller's market. This module transforms raw cost data into actionable negotiation intelligence.",
        "sections": {
            "Market Profile": "Shows Days on Market (DOM), inventory levels, months of supply (MOS), median sale price trend, and overall market type (Strong Seller's, Seller's, Balanced, Buyer's, Strong Buyer's). MOS < 3 = Seller's Market, 3-6 = Balanced, > 6 = Buyer's Market.",
            "Buyer Leverage Score": "0-100 score measuring buyer negotiation power. Higher = more leverage. Factors include DOM (longer = more leverage), inventory (higher = more leverage), price reductions (more = more leverage), seller motivation signals, and seasonality.",
            "Negotiation Strategies": "Each finding gets a specific strategy based on severity, cost, and market conditions: (1) Full Credit: Ask for 100% of estimated cost as seller credit. Use for Critical items in buyer's markets. (2) Packaged Negotiation: Bundle multiple items for a combined credit request. (3) Bundle in Price Reduction: Request price reduction equal to repair costs. (4) Leverage Point Only: Mention in negotiation but do not formally request. (5) Waive for Goodwill: Strategically waive low-cost items to build goodwill for larger requests.",
            "Executive Summary": "One-paragraph tactical overview recommending the overall negotiation approach. Includes total estimated repairs, recommended credit request amount, expected seller response range, and specific items to prioritize vs. items to waive.",
            "Market Data Sources": "Market conditions are modeled from regional construction cost indexes, typical market patterns, and housing inventory data. For real-time MLS data, consult your local Multiple Listing Service or real estate board. Negotiation strategies adapt dynamically to both repair severity and current market conditions.",
        }
    },
    "contractor_bids": {
        "title": "Contractor Bid & Dispatch Engine",
        "description": "Simulates receiving multiple contractor bids for each finding. Shows recommended contractors based on price, warranty, timeline, and reviews. Uses our embedded cost database and local rate information to generate realistic bid ranges.",
        "sections": {
            "Recommended Contractors": "Top-rated, lowest-cost contractor for each high-priority item. Each recommendation includes contractor name, license number, rating, years in business, warranty terms, and estimated timeline.",
            "All Bids": "Shows 2-4 bids per finding with contractor name, license, rating, warranty terms, timeline, and total cost breakdown (materials + labor + permit + markup). Bids are ordered from lowest to highest to show the realistic cost range.",
            "Bid Comparison Matrix": "Side-by-side comparison of all bids for items over $1,000. Highlights the best value option (not always the cheapest) based on warranty length, contractor reviews, and timeline.",
            "Emergency vs. Scheduled": "For each item, shows the cost difference between scheduling during normal hours vs. emergency/rush service. Emergency premiums typically range from 50-200% above standard rates.",
            "Note": "These are simulated bids based on local cost data, contractor network averages, and historical project data. In production, this connects to real contractor marketplace APIs (HomeAdvisor, Angi, Thumbtack). Use these as reference ranges for actual contractor outreach.",
        }
    },
    "sandbox": {
        "title": "Interactive Seller Credit Sandbox",
        "description": "A live playground where you check/uncheck items, change repair types, and override amounts. The total updates in real-time showing what to ask the seller for. This is where you finalize your negotiation strategy before generating the legal addendum.",
        "sections": {
            "Item Selection": "Check/uncheck each finding to include or exclude from your negotiation request. Unchecking items does not remove them from the report; it simply excludes them from the credit calculation.",
            "Repair Type": "Choose between: (1) Seller Credit (cash at closing, most common), (2) Seller Repair (fix before close, requires re-inspection), (3) Price Reduction (lower purchase price, affects future tax assessment), or (4) Waived (not requesting anything for this item).",
            "Override Amount": "Manually set any amount if you disagree with the system estimate. Useful when you have a contractor quote that differs from the system estimate, or when you want to round to a clean number for negotiation simplicity.",
            "Live Total": "Shows total requested amount, expected concession based on market conditions (e.g., in a strong seller's market, expect 40-60% of requested amount), and acceptance probability score. Also shows the impact on monthly mortgage payment if applied as price reduction vs. seller credit.",
            "Scenario Comparison": "Compare different negotiation scenarios side-by-side. Example: Scenario A requests full credit for all items ($45,000), Scenario B requests only Critical items ($28,000), Scenario C bundles everything as price reduction ($42,000).",
        }
    },
    "legal": {
        "title": "Automated Legal Addendum & Repair Request Writer",
        "description": "Auto-generates a professional Repair Request Addendum using standard real estate contractual language. Includes articles for seller repairs, seller credits, and price reductions. Formatted for direct use in most US real estate transactions.",
        "sections": {
            "Generated Addendum": "Full legal document with proper formatting, party names, property address, contract reference, and clause language. Follows CAR, TAR, and standard attorney general approved format patterns.",
            "Articles": "Organized by repair type: Article I for Seller-Repaired Items (items the seller must fix before closing), Article II for Seller Credits (cash at closing to cover buyer-arranged repairs), Article III for Price Reductions (purchase price adjustment reflecting repair costs).",
            "General Provisions": "Includes standard clauses for: (1) re-inspection rights after seller repairs, (2) failure to perform remedies, (3) warranty requirements on seller repairs, (4) permit compliance requirements, (5) material disclosure requirements, (6) dispute resolution procedures.",
            "Timeline Provisions": "Specifies deadlines for seller response (typically 5-7 days), repair completion (typically 10-15 days before closing), and re-inspection window (typically 3-5 days after repair completion).",
            "Disclaimer": "This addendum is auto-generated and should be reviewed by a licensed real estate attorney in your jurisdiction before execution. Real estate contract language varies by state. Some states require specific statutory forms.",
        }
    },
    "insurance": {
        "title": "Home Insurance P&C Premium Risk Predictor",
        "description": "Scans inspection findings for insurance red flags using our database of 15 known risk patterns. Identifies issues that cause carriers to deny coverage, impose exclusions, raise premiums significantly, or refuse to bind new policies.",
        "sections": {
            "Insurability Score": "0-100 score (A through F grade) measuring how easily the property can be insured. A = 90-100 (no issues), B = 75-89 (minor issues, standard premiums), C = 60-74 (moderate issues, surcharges likely), D = 40-59 (significant issues, surcharges and exclusions), F = 0-39 (uninsurable without remediation).",
            "Red Flags": "Each flag shows the risk score (0-100), denial probability (percentage chance carrier denies coverage), annual premium impact (dollar amount added to annual premium), and replacement cost (cost to remediate the issue and remove the red flag).",
            "Premium Impact": "Shows estimated annual premium increase and 5-year cost impact from identified issues. Example: Polybutylene plumbing adds $3,400/year to premiums. Over 5 years, that is $17,000 in excess premiums. This often exceeds the cost of remediation.",
            "5-Year Cost Projection": "Calculates the total 5-year cost of each insurance red flag including premium surcharges, potential claim denials, and reduced coverage. This helps buyers understand the true long-term cost of unaddressed issues.",
            "Remediation Roadmap": "Prioritized list of remediation steps that will most effectively reduce insurance costs. Typically, the first $500-3,000 spent on remediation (e.g., replacing a FPE panel) yields the largest premium reduction.",
            "Recommendations": "Actionable steps to improve insurability and reduce premium exposure. Includes estimated cost, timeline, and expected premium impact for each remediation step.",
        }
    },
    "environmental": {
        "title": "Environmental Risk & Climate Resiliency",
        "description": "Cross-references the property's location against FEMA flood zones, seismic zones, wildfire risk, soil type, and climate-specific hazards. Uses our climate zone database covering 5 distinct US climate profiles with associated risk multipliers.",
        "sections": {
            "Climate Zone": "Identifies the property's climate zone: Extremely Hot/Arid (AZ, NV, NM), Hot/Humid (FL, GA, SC, NC, TX, LA, MS, AL, HI), Temperate (CA, OR, WA, CO, UT), Cold/Harsh (MN, WI, MI, ND, SD, MT, WY, ME, VT, NH), or Moderate (NY, NJ, PA, OH, IL, IN, VA, MD, CT, MA).",
            "Flood Zone": "FEMA flood zone designation (Zone X = minimal risk, Zone AE/A = high risk, Zone VE = coastal high risk, Zone AO = shallow flooding). Properties in Zone AE or higher require mandatory flood insurance, adding $1,000-4,000+/year to housing costs.",
            "Risk Items": "Each environmental risk shows its severity score (0-100), insurance impact (annual cost), mitigation recommendations, and estimated mitigation cost. Risks are cross-referenced against inspection findings for compound risk assessment.",
            "Insurance Multiplier": "Climate-specific insurance multiplier applied to baseline premiums: Extremely Hot/Arid = 1.18x, Hot/Humid = 1.35x, Temperate = 1.22x, Cold/Harsh = 1.12x, Moderate = 1.02x. The Hot/Humid multiplier is highest due to hurricane, flood, and mold risk.",
            "Resiliency Tips": "Climate-specific home protection recommendations. For example, in Cold/Harsh zones: insulate pipes, install heat tape, ensure attic ventilation to prevent ice dams. In Hot/Humid zones: ensure vapor barriers, install mold-resistant materials, verify hurricane straps.",
            "Common Mistakes": "Buyers often skip flood zone verification because their property is 'not near water.' Flash flooding affects 25% of flood claims outside high-risk zones. Always check FEMA maps even for inland properties.",
        }
    },
    "permits": {
        "title": "Permit & Public Records Cross-Reference",
        "description": "Simulates checking municipal permit records and cross-references them against inspection findings to identify potentially unpermitted work. Unpermitted work can result in fines, forced removal, insurance claim denials, and complications at resale.",
        "sections": {
            "Permit Records": "Simulated municipal records showing permit type, date issued, contractor of record, permit status (approved, pending, expired, open), and inspection history. Records are categorized by system type (electrical, plumbing, mechanical, structural).",
            "Unpermitted Flags": "Findings where no matching permit was found. These are flagged as potential compliance/liability issues. Common unpermitted items include: room additions, electrical panel upgrades, plumbing reroutes, HVAC replacements, and deck construction.",
            "Permit Types": "Our database includes 19 common municipal permit types: Building, Electrical, Plumbing, Mechanical, Roofing, Demolition, Deck/Porch, Addition, Electrical Subpanel, Water Heater, HVAC, Siding, Window/Door, Fence, Grading, Septic, Well, Solar, and Pool/Spa.",
            "Risk Assessment": "Unpermitted work risk levels vary by type: (1) Electrical work = HIGH RISK (fire hazard, insurance implications), (2) Structural work = HIGH RISK (liability, resale issues), (3) Plumbing work = MEDIUM RISK (water damage, code), (4) HVAC work = MEDIUM RISK (efficiency, safety), (5) Cosmetic work = LOW RISK (minor code).",
            "Resolution Options": "For unpermitted work: (1) Retroactive permit (may require opening walls for inspection), (2) Seller disclosure and credit (most common in negotiation), (3) Professional certification (for code-compliant work that was simply not permitted), (4) Remove and replace with permitted work.",
            "Note": "This uses simulated data. For production, integrate with local municipal APIs or public records databases using the property's APN (Assessor's Parcel Number). Many jurisdictions now offer online permit lookup portals.",
        }
    },
    "recalls": {
        "title": "Manufacturer Recall Cross-Reference",
        "description": "Checks inspection findings against known manufacturer recalls and class action settlements from our database of 9 major recalls. A defect noted by the inspector might actually be a free recall repair, potentially saving thousands of dollars.",
        "sections": {
            "Recall Matches": "Shows matching recalls with manufacturer, product type, model pattern, recall type (CPSC, Class Action, Manufacturer Voluntary), status (Active, Closed, Check Eligibility), and potential cost savings if the item qualifies for free repair or replacement.",
            "Claim URLs": "Direct links to manufacturer recall claim pages and CPSC recall database. Most manufacturers have online portals where homeowners can enter serial/model numbers to check eligibility.",
            "Cost Savings": "Estimated savings if the item qualifies for free recall repair/replacement. Example: A Federal Pacific panel replacement costs $2,800 but may qualify for class action settlement funds covering 50-100% of replacement cost.",
            "Priority Recalls": "Highest-priority recalls to check first: (1) Federal Pacific panels (active class action, high claim success rate), (2) Zinsco panels (known fire risk), (3) Generac generators (CO emission risk), (4) Lennox heat exchangers (CO risk).",
            "Cross-Reference Logic": "The system matches manufacturer names, model numbers, and product types from inspection findings against the recall database using fuzzy matching. Even partial matches are flagged for manual review.",
        }
    },
    "photos": {
        "title": "Photo Evidence & Visual Documentation",
        "description": "Extracts photos from the original PDF and matches them to specific findings using spatial proximity and keyword analysis. Creates a visual evidence package that supports each finding in your negotiation.",
        "sections": {
            "How It Works": "Uses PyMuPDF (fitz) to extract embedded images from the PDF. Each image is analyzed for: (1) page number proximity to text findings, (2) image caption/alt-text keywords, (3) image position relative to finding text, (4) image size and quality. Matches are scored by confidence level.",
            "Photo Mapping": "Each extracted photo is mapped to the most likely finding. Photos on the same page as a finding, within 2 inches of the finding text, and sharing keywords receive the highest confidence score. Unmatched photos are categorized by visual analysis.",
            "Evidence Package": "For negotiation purposes, photos are compiled into an evidence package showing: the finding text, associated photo(s), severity classification, and cost estimate. This visual evidence significantly strengthens credit requests.",
            "Note": "Photo extraction requires the original PDF file. Sample data mode shows the feature description only. Scanned PDFs may have lower photo extraction quality than native digital PDFs.",
        }
    },
    "spatial": {
        "title": "Spatial Floor Plan & Flaw Map",
        "description": "Maps each finding to a specific room on an interactive floor plan. Color-coded by severity for instant visual understanding of where problems are concentrated in the property.",
        "sections": {
            "Floor Plan": "Auto-generated based on bedroom/bathroom count and property square footage. Each room is clickable and shows all associated findings. Rooms are sized proportionally based on typical floor plan layouts.",
            "Findings": "Plotted as colored dots on the floor plan: Red = Critical, Orange = High, Yellow = Medium, Green = Low, Blue = Info. Dot size indicates relative cost. Clusters of red dots indicate problem areas that may have compound issues.",
            "Location Table": "Lists each finding with its assigned room, zone (kitchen, master bedroom, etc.), wall position (N/S/E/W), and floor level. This table is sortable and filterable.",
            "Heat Map Mode": "Toggle between dot view and heat map view. Heat map shows cost concentration by area, helping identify which rooms or zones have the most expensive repairs. This is useful for prioritizing which areas to negotiate hardest on.",
        }
    },
    "audio": {
        "title": "Voice-to-Text Inspector Audio Auditor",
        "description": "Paste raw inspector notes or audio transcripts. The system extracts findings, classifies severity, maps to systems, and generates structured data. This module turns informal inspector observations into quantified repair requests.",
        "sections": {
            "Input": "Paste any text: audio transcript from voice recorder, raw typed notes, inspector field notes, or typed observations. The system handles informal language, abbreviations, and incomplete sentences.",
            "Processing Pipeline": "NLP pipeline processes input through: (1) sentence segmentation and cleaning, (2) finding extraction with entity recognition, (3) severity classification using contextual keyword analysis, (4) system category assignment, (5) location/room extraction, (6) confidence scoring for each extracted finding.",
            "Output": "Structured findings ready for the cost engine and negotiation modules. Each finding includes: extracted text, assigned severity, system category, location, confidence score, and suggested cost estimate range.",
            "Common Inspector Phrases": "The system recognizes common inspector shorthand: 'GFI' = GFCI outlet, 'TCL' = toilet, 'WH' = water heater, 'FPE' = Federal Pacific Electric panel, 'K&T' = knob and tube wiring, 'ABS' = acrylonitrile butadiene styrene piping.",
        }
    },
    "investor": {
        "title": "Investor Pro Mode - ARV & Flip Margin Underwriter",
        "description": "Switches the analysis to investor-focused metrics: After Repair Value (ARV), Maximum Allowable Offer (MAO), Cap Rate, Cash-on-Cash Return, and 5-year CapEx forecast. This module transforms the inspection data into investment analysis.",
        "sections": {
            "Deal Metrics": "Shows Repair/ARV ratio (target: <15% for flips, <25% for rentals), Gross Rent Multiplier, Breakeven Occupancy, and estimated monthly rent based on local market comparables.",
            "ARV Calculation": "After Repair Value is estimated using: (1) current condition value, (2) estimated repair costs, (3) local comparable sales data, (4) market appreciation trend. ARV = Current Value + (Repair Cost x 0.7-1.2 ROI multiplier depending on market).",
            "MAO Formula": "Maximum Allowable Offer = ARV x 70% - Repair Costs. The 70% rule is the standard investor guideline for flip deals. In hot markets, this can be adjusted to 75-80%.",
            "Deal Grade": "A-F grade based on: Cap Rate (target >8% for rentals), Cash-on-Cash Return (target >12% for rentals), Repair Cost Ratio (target <15% for flips), and market trend direction.",
            "5-Year Forecast": "Year-by-year expected CapEx costs based on depreciation curves for all 30 asset types. Includes projected maintenance costs, major system replacements, and seasonal variation. Helps investors budget reserves accurately.",
            "Note": "ARV and rental estimates are modeled from local comparables data patterns. Verify with your own CMA (Comparative Market Analysis) and rental market analysis before making investment decisions.",
        }
    },
    "escrow": {
        "title": "Escrow Holdback & Title Binder Estimator",
        "description": "For repairs that cannot close before settlement, calculates the required escrow holdback amount using standard industry multipliers with milestone-based release conditions. This protects both buyer and seller during post-closing repairs.",
        "sections": {
            "Holdback Calculation": "Contractor estimate x 1.5 = required escrow amount. Title companies and lenders require this safety margin (typically 1.25x to 2.0x) to account for cost overruns, delays, and unforeseen issues discovered during repair.",
            "Release Conditions": "System and inspection-specific conditions for releasing holdback funds. Example conditions: (1) HVAC repair: city mechanical inspection pass + 30-day operation verification, (2) Roof repair: manufacturer warranty documentation + re-roof inspection certificate, (3) Electrical: city electrical inspection pass + load test documentation.",
            "Milestones": "Two-stage release: Stage 1 (50% of holdback) released on documented commencement of work with contractor affidavit. Stage 2 (remaining 50%) released on completion + final inspection approval by appropriate authority.",
            "Title Company Requirements": "Most title companies require: (1) written contract between buyer and contractor, (2) proof of contractor insurance, (3) lien waiver from contractor, (4) inspection certificate from appropriate authority, (5) buyer acknowledgment of completed work.",
            "Timeline": "Typical escrow holdback period: 30-90 days after closing. Extensions can be negotiated but most title companies impose daily charges ($25-75/day) for holdbacks exceeding 60 days.",
        }
    },
    "roi": {
        "title": "Brokerage ROI Dashboard",
        "description": "Aggregated performance metrics for managing brokers. Tracks total credits negotiated, agent success rates, and identifies coaching opportunities across the brokerage. This module is designed for team leads and brokerage managers.",
        "sections": {
            "Agent Rankings": "Sorted by total credits negotiated, with success rate (% of requested credits actually received), average credit per deal, number of deals analyzed, and trend line showing improvement over time.",
            "Inspector Analysis": "Identifies which home inspection companies consistently flag the most severe issues, which have the highest finding-to-cost ratio, and which are most thorough. This helps agents recommend inspectors who provide the best data for negotiation.",
            "Zip Code Analysis": "Shows average concession amounts by zip code to optimize future listing strategies. Identifies which neighborhoods have the most negotiation activity and which price points generate the most repair requests.",
            "Coaching Insights": "AI-generated coaching recommendations based on agent performance patterns. Example: 'Agent X requests full credit on all items; data shows bundled negotiations yield 15% higher acceptance rates in Seller's markets.'",
            "Market Trends": "Tracks how average repair costs, credit amounts, and negotiation success rates change over time by market segment.",
        }
    },
    "seo": {
        "title": "Programmatic Local SEO Landing Pages",
        "description": "Auto-generates SEO-optimized landing pages for each system type in the property's ZIP code. Captures organic search traffic from homeowners researching repair costs in their specific area.",
        "sections": {
            "Page Generation": "Creates pages with proper H1 tags, meta descriptions, Open Graph tags, schema markup, and content sections targeting local repair cost keywords. Each page targets a specific long-tail keyword like 'roof replacement cost in [ZIP code] 2026'.",
            "Content Sections": "Each generated page includes: (1) average cost range for the system in that ZIP, (2) factors affecting price, (3) signs the system needs replacement, (4) how to find licensed contractors, (5) permit requirements, (6) FAQ section.",
            "Analytics": "Shows estimated impressions, clicks, conversions, and monthly lead value based on keyword search volume and competition. Typical conversion rate for local service pages: 2-5%.",
            "Keyword Strategy": "Targets 3 keyword tiers: (1) Primary: '[service] cost [city]' (high volume, high competition), (2) Secondary: '[service] replacement cost [ZIP]' (medium volume, medium competition), (3) Long-tail: 'how much does [service] cost in [city] [year]' (low volume, low competition, high conversion).",
            "Note": "Page content is generated as templates. Deploy to your brokerage website for organic lead generation. Best results when integrated with Google Business Profile and local citation building.",
        }
    },
    "lead_magnet": {
        "title": "White-Label Lead Magnet Widget",
        "description": "A client-facing widget you can embed on your website. Worried buyers upload their inspection PDF, get a preview analysis, then enter contact info to unlock the full report. This generates warm, qualified leads for your brokerage.",
        "sections": {
            "Widget Preview": "Shows exactly what the widget looks like on your website. Clean, professional design with your brokerage branding. Includes upload area, progress indicator, and preview results.",
            "Lead Capture": "Email and phone fields gate the full report, generating warm leads. Leads are qualified because they already own a home inspection report and are actively concerned about repair costs. Average lead quality score: 8.5/10.",
            "Social Proof": "Configurable social proof text to increase conversion rates. Example: 'Join 2,400+ homeowners who used our free analysis to save an average of $12,500 on their home purchase.'",
            "Conversion Funnel": "Widget flow: (1) User uploads PDF, (2) Preview analysis shows top 5 findings + total estimated cost, (3) Contact form gates full report, (4) Full report delivered via email, (5) Follow-up sequence activates. Typical conversion rate: 35-50%.",
            "Integration": "Embed code provided for WordPress, Squarespace, Wix, and custom HTML sites. Also supports iframe embedding and API integration for advanced users.",
        }
    },
    "export": {
        "title": "Export Professional Report Package",
        "description": "Download the complete analysis in multiple formats optimized for different use cases. Each format is designed for a specific audience and purpose.",
        "sections": {
            "Formats": "Available export formats: (1) TXT - Executive summary report for clients, (2) JSON - Structured data for integration with other tools, (3) CSV - Findings spreadsheet, cost matrix, and negotiation strategies for import into Excel/Google Sheets.",
            "TXT Report": "Professional plain-text report with executive summary, finding details, cost estimates, and negotiation recommendations. Formatted for printing or email. Includes all disclaimers and data source citations.",
            "JSON Export": "Complete structured data export including all findings, costs, depreciation data, insurance analysis, market data, and negotiation strategies. Ideal for importing into CRM systems or custom analysis tools.",
            "CSV Exports": "Three separate CSV files: (1) Findings List - all findings with severity, system, location, and description, (2) Cost Matrix - detailed cost breakdowns by finding and trade, (3) Strategy Summary - negotiation strategies and recommended actions by finding.",
            "Database": "All analysis data is automatically saved to the local SQLite database at data/repair_estimator.db for historical reference, trend analysis, and brokerage reporting. Data includes timestamps, property details, and full analysis results.",
        }
    },
}

LEGAL_DISCLAIMER = """
**IMPORTANT DISCLAIMER:** This tool provides automated cost estimates for informational purposes only. All estimates are based on 2026 national and regional construction cost data with localized adjustments. Actual contractor bids may vary 15-40% from estimates. This tool does not constitute engineering, legal, financial, or insurance advice. Always obtain licensed contractor estimates, consult licensed engineers for structural assessments, and review all legal documents with a licensed attorney in your jurisdiction before making repair decisions or signing contracts. Cost data is updated quarterly but may not reflect real-time market fluctuations in your specific area.
"""

MARKET_DATA_NOTE = """
**Market Data Note:** Market conditions, Days on Market, and inventory levels are modeled from regional construction cost indexes and typical market patterns. For real-time MLS data, consult your local Multiple Listing Service or real estate board. Negotiation strategies are recommendations based on general market conditions and should be adapted to your specific deal circumstances.
"""
