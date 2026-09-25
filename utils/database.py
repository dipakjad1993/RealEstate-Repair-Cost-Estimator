import json
import sqlite3
from datetime import datetime

from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        address TEXT NOT NULL,
        city TEXT,
        state TEXT,
        zip_code TEXT,
        county TEXT,
        parcel_number TEXT,
        property_type TEXT DEFAULT 'Single Family',
        year_built INTEGER,
        square_footage INTEGER,
        lot_size_sqft INTEGER,
        bedrooms INTEGER,
        bathrooms REAL,
        stories INTEGER,
        garage_type TEXT,
        foundation_type TEXT,
        roof_type TEXT,
        hvac_type TEXT,
        plumbing_type TEXT,
        electrical_type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS inspection_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER,
        inspector_name TEXT,
        inspection_date DATE,
        report_type TEXT DEFAULT 'Full Inspection',
        report_filename TEXT,
        raw_text TEXT,
        parsed_findings TEXT,
        total_pages INTEGER,
        status TEXT DEFAULT 'uploaded',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(id)
    );

    CREATE TABLE IF NOT EXISTS findings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER,
        property_id INTEGER,
        system_category TEXT,
        subsystem TEXT,
        component TEXT,
        location TEXT,
        description TEXT,
        severity TEXT,
        severity_score INTEGER,
        estimated_cost_low REAL,
        estimated_cost_high REAL,
        estimated_cost_avg REAL,
        photo_extracted INTEGER DEFAULT 0,
        photo_blob BLOB,
        dedup_group TEXT,
        confidence_score REAL DEFAULT 0.85,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (report_id) REFERENCES inspection_reports(id),
        FOREIGN KEY (property_id) REFERENCES properties(id)
    );

    CREATE TABLE IF NOT EXISTS cost_estimates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        finding_id INTEGER,
        diy_low REAL,
        diy_high REAL,
        contractor_low REAL,
        contractor_high REAL,
        emergency_low REAL,
        emergency_high REAL,
        local_modifier REAL DEFAULT 1.0,
        zip_code TEXT,
        material_cost_low REAL,
        material_cost_high REAL,
        labor_cost_low REAL,
        labor_cost_high REAL,
        permit_cost REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (finding_id) REFERENCES findings(id)
    );

    CREATE TABLE IF NOT EXISTS depreciation_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        finding_id INTEGER,
        asset_type TEXT,
        make TEXT,
        model TEXT,
        serial_number TEXT,
        year_manufactured INTEGER,
        age_years REAL,
        useful_life INTEGER,
        remaining_life REAL,
        depreciation_pct REAL,
        replacement_cost_avg REAL,
        replacement_cost_low REAL,
        replacement_cost_high REAL,
        failure_probability_24mo REAL,
        replacement_urgency TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (finding_id) REFERENCES findings(id)
    );

    CREATE TABLE IF NOT EXISTS capex_projections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER,
        finding_id INTEGER,
        asset_type TEXT,
        current_age INTEGER,
        useful_life INTEGER,
        projected_failure_month INTEGER,
        projected_failure_year INTEGER,
        replacement_cost_avg REAL,
        risk_level TEXT,
        priority INTEGER,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(id),
        FOREIGN KEY (finding_id) REFERENCES findings(id)
    );

    CREATE TABLE IF NOT EXISTS market_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        zip_code TEXT,
        state TEXT,
        city TEXT,
        avg_days_on_market INTEGER,
        inventory_count INTEGER,
        active_listings INTEGER,
        pending_sales INTEGER,
        median_sale_price REAL,
        price_per_sqft REAL,
        yoy_price_change REAL,
        months_of_supply REAL,
        market_type TEXT,
        data_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS negotiation_strategies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER,
        finding_id INTEGER,
        strategy_type TEXT,
        priority_rank INTEGER,
        action TEXT,
        rationale TEXT,
        estimated_credit REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(id)
    );

    CREATE TABLE IF NOT EXISTS environmental_risk (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER,
        risk_type TEXT,
        risk_level TEXT,
        risk_score INTEGER,
        description TEXT,
        insurance_impact REAL,
        estimated_cost REAL,
        mitigation_recommendation TEXT,
        climate_zone TEXT,
        flood_zone TEXT,
        seismic_zone TEXT,
        wildfire_risk TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(id)
    );

    CREATE TABLE IF NOT EXISTS insurance_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        finding_id INTEGER,
        property_id INTEGER,
        red_flag_type TEXT,
        risk_score INTEGER,
        denial_probability REAL,
        annual_premium_impact REAL,
        replacement_cost REAL,
        description TEXT,
        recommendation TEXT,
        insurability_score REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (finding_id) REFERENCES findings(id),
        FOREIGN KEY (property_id) REFERENCES properties(id)
    );

    CREATE TABLE IF NOT EXISTS escrow_holdbacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER,
        finding_id INTEGER,
        defect_description TEXT,
        contractor_bid REAL,
        holdback_amount REAL,
        holdback_multiplier REAL DEFAULT 1.5,
        release_conditions TEXT,
        milestone_1 TEXT,
        milestone_1_pct REAL,
        milestone_2 TEXT,
        milestone_2_pct REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(id)
    );

    CREATE TABLE IF NOT EXISTS legal_addenda (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER,
        addendum_type TEXT,
        addendum_text TEXT,
        selected_findings TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(id)
    );

    CREATE TABLE IF NOT EXISTS permit_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER,
        permit_type TEXT,
        permit_number TEXT,
        permit_date DATE,
        contractor_name TEXT,
        status TEXT,
        description TEXT,
        source TEXT,
        match_status TEXT DEFAULT 'unverified',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(id)
    );

    CREATE TABLE IF NOT EXISTS investor_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER,
        listing_price REAL,
        after_repair_value REAL,
        max_allowable_offer REAL,
        total_repair_cost REAL,
        holding_costs REAL,
        closing_costs REAL,
        profit_target REAL,
        cap_rate REAL,
        cash_on_cash_return REAL,
        monthly_rental_est REAL,
        noi_annual REAL,
        capex_reserve_5yr REAL,
        depreciation_forecast TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(id)
    );

    CREATE TABLE IF NOT EXISTS brokerage_roi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        broker_id TEXT,
        agent_id TEXT,
        property_id INTEGER,
        total_credits_negotiated REAL,
        total_repairs_requested REAL,
        items_requested INTEGER,
        items_granted INTEGER,
        negotiation_success_rate REAL,
        zip_code TEXT,
        transaction_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(id)
    );

    CREATE TABLE IF NOT EXISTS lead_magnet_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        visitor_ip TEXT,
        email TEXT,
        phone TEXT,
        zip_code TEXT,
        report_filename TEXT,
        analysis_preview TEXT,
        lead_captured INTEGER DEFAULT 0,
        conversion_date TIMESTAMP,
        source_page TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS seo_pages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        zip_code TEXT,
        system_type TEXT,
        avg_cost REAL,
        page_slug TEXT,
        impressions INTEGER DEFAULT 0,
        clicks INTEGER DEFAULT 0,
        conversions INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS contractor_bids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        finding_id INTEGER,
        property_id INTEGER,
        contractor_name TEXT,
        contractor_license TEXT,
        contractor_rating REAL,
        bid_amount REAL,
        bid_description TEXT,
        warranty_terms TEXT,
        timeline_days INTEGER,
        bid_status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (finding_id) REFERENCES findings(id),
        FOREIGN KEY (property_id) REFERENCES properties(id)
    );

    CREATE TABLE IF NOT EXISTS spatial_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        finding_id INTEGER,
        property_id INTEGER,
        room TEXT,
        wall TEXT,
        floor_level TEXT,
        x_position REAL,
        y_position REAL,
        zone TEXT,
        photo_reference TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (finding_id) REFERENCES findings(id),
        FOREIGN KEY (property_id) REFERENCES properties(id)
    );

    CREATE TABLE IF NOT EXISTS recall_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        finding_id INTEGER,
        manufacturer TEXT,
        model TEXT,
        serial_number TEXT,
        product_type TEXT,
        recall_status TEXT,
        recall_type TEXT,
        claim_url TEXT,
        description TEXT,
        remedy TEXT,
        cost_savings REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (finding_id) REFERENCES findings(id)
    );

    CREATE TABLE IF NOT EXISTS sandbox_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER,
        finding_id INTEGER,
        selected INTEGER DEFAULT 1,
        repair_type TEXT DEFAULT 'seller_credit',
        override_amount REAL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(id)
    );

    CREATE TABLE IF NOT EXISTS audio_transcripts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER,
        audio_filename TEXT,
        transcript_text TEXT,
        findings_extracted TEXT,
        duration_seconds REAL,
        recorded_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(id)
    );
    """)
    conn.commit()
    conn.close()


def save_property(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO properties (address, city, state, zip_code, county, parcel_number,
            property_type, year_built, square_footage, lot_size_sqft, bedrooms, bathrooms,
            stories, garage_type, foundation_type, roof_type, hvac_type, plumbing_type, electrical_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("address", ""),
            data.get("city", ""),
            data.get("state", ""),
            data.get("zip_code", ""),
            data.get("county", ""),
            data.get("parcel_number", ""),
            data.get("property_type", "Single Family"),
            data.get("year_built", 0),
            data.get("square_footage", 0),
            data.get("lot_size_sqft", 0),
            data.get("bedrooms", 0),
            data.get("bathrooms", 0),
            data.get("stories", 1),
            data.get("garage_type", ""),
            data.get("foundation_type", ""),
            data.get("roof_type", ""),
            data.get("hvac_type", ""),
            data.get("plumbing_type", ""),
            data.get("electrical_type", ""),
        ),
    )
    conn.commit()
    prop_id = cursor.lastrowid
    conn.close()
    return prop_id


def save_inspection_report(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO inspection_reports (property_id, inspector_name, inspection_date,
            report_type, report_filename, raw_text, parsed_findings, total_pages, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("property_id"),
            data.get("inspector_name", ""),
            data.get("inspection_date", datetime.now().strftime("%Y-%m-%d")),
            data.get("report_type", "Full Inspection"),
            data.get("report_filename", ""),
            data.get("raw_text", ""),
            json.dumps(data.get("parsed_findings", [])),
            data.get("total_pages", 0),
            data.get("status", "uploaded"),
        ),
    )
    conn.commit()
    report_id = cursor.lastrowid
    conn.close()
    return report_id


def save_finding(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO findings (report_id, property_id, system_category, subsystem,
            component, location, description, severity, severity_score,
            estimated_cost_low, estimated_cost_high, estimated_cost_avg,
            photo_extracted, dedup_group, confidence_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("report_id"),
            data.get("property_id"),
            data.get("system_category", ""),
            data.get("subsystem", ""),
            data.get("component", ""),
            data.get("location", ""),
            data.get("description", ""),
            data.get("severity", "MEDIUM"),
            data.get("severity_score", 3),
            data.get("estimated_cost_low", 0),
            data.get("estimated_cost_high", 0),
            data.get("estimated_cost_avg", 0),
            data.get("photo_extracted", 0),
            data.get("dedup_group", ""),
            data.get("confidence_score", 0.85),
        ),
    )
    conn.commit()
    finding_id = cursor.lastrowid
    conn.close()
    return finding_id


def save_cost_estimate(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO cost_estimates (finding_id, diy_low, diy_high, contractor_low,
            contractor_high, emergency_low, emergency_high, local_modifier, zip_code,
            material_cost_low, material_cost_high, labor_cost_low, labor_cost_high, permit_cost)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("finding_id"),
            data.get("diy_low", 0),
            data.get("diy_high", 0),
            data.get("contractor_low", 0),
            data.get("contractor_high", 0),
            data.get("emergency_low", 0),
            data.get("emergency_high", 0),
            data.get("local_modifier", 1.0),
            data.get("zip_code", ""),
            data.get("material_cost_low", 0),
            data.get("material_cost_high", 0),
            data.get("labor_cost_low", 0),
            data.get("labor_cost_high", 0),
            data.get("permit_cost", 0),
        ),
    )
    conn.commit()
    est_id = cursor.lastrowid
    conn.close()
    return est_id


def save_depreciation(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO depreciation_data (finding_id, asset_type, make, model,
            serial_number, year_manufactured, age_years, useful_life,
            remaining_life, depreciation_pct, replacement_cost_avg,
            replacement_cost_low, replacement_cost_high, failure_probability_24mo,
            replacement_urgency)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("finding_id"),
            data.get("asset_type", ""),
            data.get("make", ""),
            data.get("model", ""),
            data.get("serial_number", ""),
            data.get("year_manufactured", 0),
            data.get("age_years", 0),
            data.get("useful_life", 15),
            data.get("remaining_life", 0),
            data.get("depreciation_pct", 0),
            data.get("replacement_cost_avg", 0),
            data.get("replacement_cost_low", 0),
            data.get("replacement_cost_high", 0),
            data.get("failure_probability_24mo", 0),
            data.get("replacement_urgency", "N/A"),
        ),
    )
    conn.commit()
    dep_id = cursor.lastrowid
    conn.close()
    return dep_id


def save_capex_projection(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO capex_projections (property_id, finding_id, asset_type,
            current_age, useful_life, projected_failure_month,
            projected_failure_year, replacement_cost_avg, risk_level, priority, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("property_id"),
            data.get("finding_id"),
            data.get("asset_type", ""),
            data.get("current_age", 0),
            data.get("useful_life", 15),
            data.get("projected_failure_month", 0),
            data.get("projected_failure_year", 0),
            data.get("replacement_cost_avg", 0),
            data.get("risk_level", "MEDIUM"),
            data.get("priority", 3),
            data.get("notes", ""),
        ),
    )
    conn.commit()
    capex_id = cursor.lastrowid
    conn.close()
    return capex_id


def save_negotiation_strategy(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO negotiation_strategies (property_id, finding_id, strategy_type,
            priority_rank, action, rationale, estimated_credit)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("property_id"),
            data.get("finding_id"),
            data.get("strategy_type", ""),
            data.get("priority_rank", 0),
            data.get("action", ""),
            data.get("rationale", ""),
            data.get("estimated_credit", 0),
        ),
    )
    conn.commit()
    strat_id = cursor.lastrowid
    conn.close()
    return strat_id


def save_escrow_holdback(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO escrow_holdbacks (property_id, finding_id, defect_description,
            contractor_bid, holdback_amount, holdback_multiplier,
            release_conditions, milestone_1, milestone_1_pct,
            milestone_2, milestone_2_pct)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("property_id"),
            data.get("finding_id"),
            data.get("defect_description", ""),
            data.get("contractor_bid", 0),
            data.get("holdback_amount", 0),
            data.get("holdback_multiplier", 1.5),
            data.get("release_conditions", ""),
            data.get("milestone_1", ""),
            data.get("milestone_1_pct", 50),
            data.get("milestone_2", ""),
            data.get("milestone_2_pct", 50),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def save_environmental_risk(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO environmental_risk (property_id, risk_type, risk_level, risk_score,
            description, insurance_impact, estimated_cost,
            mitigation_recommendation, climate_zone, flood_zone,
            seismic_zone, wildfire_risk)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("property_id"),
            data.get("risk_type", ""),
            data.get("risk_level", "LOW"),
            data.get("risk_score", 0),
            data.get("description", ""),
            data.get("insurance_impact", 0),
            data.get("estimated_cost", 0),
            data.get("mitigation_recommendation", ""),
            data.get("climate_zone", ""),
            data.get("flood_zone", ""),
            data.get("seismic_zone", ""),
            data.get("wildfire_risk", ""),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def save_investor_analysis(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO investor_analysis (property_id, listing_price, after_repair_value,
            max_allowable_offer, total_repair_cost, holding_costs, closing_costs,
            profit_target, cap_rate, cash_on_cash_return, monthly_rental_est,
            noi_annual, capex_reserve_5yr, depreciation_forecast)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("property_id"),
            data.get("listing_price", 0),
            data.get("after_repair_value", 0),
            data.get("max_allowable_offer", 0),
            data.get("total_repair_cost", 0),
            data.get("holding_costs", 0),
            data.get("closing_costs", 0),
            data.get("profit_target", 0),
            data.get("cap_rate", 0),
            data.get("cash_on_cash_return", 0),
            data.get("monthly_rental_est", 0),
            data.get("noi_annual", 0),
            data.get("capex_reserve_5yr", 0),
            json.dumps(data.get("depreciation_forecast", [])),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def save_insurance_analysis(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO insurance_analysis (finding_id, property_id, red_flag_type,
            risk_score, denial_probability, annual_premium_impact,
            replacement_cost, description, recommendation, insurability_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("finding_id"),
            data.get("property_id"),
            data.get("red_flag_type", ""),
            data.get("risk_score", 0),
            data.get("denial_probability", 0),
            data.get("annual_premium_impact", 0),
            data.get("replacement_cost", 0),
            data.get("description", ""),
            data.get("recommendation", ""),
            data.get("insurability_score", 50),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def save_market_data(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO market_data (zip_code, state, city, avg_days_on_market,
            inventory_count, active_listings, pending_sales,
            median_sale_price, price_per_sqft, yoy_price_change,
            months_of_supply, market_type, data_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("zip_code", ""),
            data.get("state", ""),
            data.get("city", ""),
            data.get("avg_days_on_market", 30),
            data.get("inventory_count", 0),
            data.get("active_listings", 0),
            data.get("pending_sales", 0),
            data.get("median_sale_price", 0),
            data.get("price_per_sqft", 0),
            data.get("yoy_price_change", 0),
            data.get("months_of_supply", 3),
            data.get("market_type", "Balanced"),
            data.get("data_date", datetime.now().strftime("%Y-%m-%d")),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def save_permit_record(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO permit_records (property_id, permit_type, permit_number,
            permit_date, contractor_name, status, description, source,
            match_status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("property_id"),
            data.get("permit_type", ""),
            data.get("permit_number", ""),
            data.get("permit_date", ""),
            data.get("contractor_name", ""),
            data.get("status", ""),
            data.get("description", ""),
            data.get("source", "simulated"),
            data.get("match_status", "unverified"),
            data.get("notes", ""),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def save_legal_addendum(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO legal_addenda (property_id, addendum_type, addendum_text, selected_findings)
        VALUES (?, ?, ?, ?)
    """,
        (
            data.get("property_id"),
            data.get("addendum_type", "Repair Request"),
            data.get("addendum_text", ""),
            json.dumps(data.get("selected_findings", [])),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def save_sandbox_item(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO sandbox_items (property_id, finding_id, selected,
            repair_type, override_amount, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("property_id"),
            data.get("finding_id"),
            data.get("selected", 1),
            data.get("repair_type", "seller_credit"),
            data.get("override_amount", 0),
            data.get("notes", ""),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def save_contractor_bid(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO contractor_bids (finding_id, property_id, contractor_name,
            contractor_license, contractor_rating, bid_amount,
            bid_description, warranty_terms, timeline_days, bid_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("finding_id"),
            data.get("property_id"),
            data.get("contractor_name", ""),
            data.get("contractor_license", ""),
            data.get("contractor_rating", 0),
            data.get("bid_amount", 0),
            data.get("bid_description", ""),
            data.get("warranty_terms", ""),
            data.get("timeline_days", 0),
            data.get("bid_status", "pending"),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def save_spatial_data(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO spatial_data (finding_id, property_id, room, wall,
            floor_level, x_position, y_position, zone, photo_reference)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("finding_id"),
            data.get("property_id"),
            data.get("room", ""),
            data.get("wall", ""),
            data.get("floor_level", "Main"),
            data.get("x_position", 0),
            data.get("y_position", 0),
            data.get("zone", ""),
            data.get("photo_reference", ""),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def save_recall_check(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO recall_checks (finding_id, manufacturer, model,
            serial_number, product_type, recall_status, recall_type,
            claim_url, description, remedy, cost_savings)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("finding_id"),
            data.get("manufacturer", ""),
            data.get("model", ""),
            data.get("serial_number", ""),
            data.get("product_type", ""),
            data.get("recall_status", "Not Found"),
            data.get("recall_type", ""),
            data.get("claim_url", ""),
            data.get("description", ""),
            data.get("remedy", ""),
            data.get("cost_savings", 0),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def save_brokerage_roi(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO brokerage_roi (broker_id, agent_id, property_id,
            total_credits_negotiated, total_repairs_requested,
            items_requested, items_granted, negotiation_success_rate,
            zip_code, transaction_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("broker_id", ""),
            data.get("agent_id", ""),
            data.get("property_id"),
            data.get("total_credits_negotiated", 0),
            data.get("total_repairs_requested", 0),
            data.get("items_requested", 0),
            data.get("items_granted", 0),
            data.get("negotiation_success_rate", 0),
            data.get("zip_code", ""),
            data.get("transaction_date", datetime.now().strftime("%Y-%m-%d")),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def save_seo_page(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO seo_pages (zip_code, system_type, avg_cost,
            page_slug, impressions, clicks, conversions)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("zip_code", ""),
            data.get("system_type", ""),
            data.get("avg_cost", 0),
            data.get("page_slug", ""),
            data.get("impressions", 0),
            data.get("clicks", 0),
            data.get("conversions", 0),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def save_lead_activity(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO lead_magnet_activity (visitor_ip, email, phone,
            zip_code, report_filename, analysis_preview,
            lead_captured, source_page)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("visitor_ip", ""),
            data.get("email", ""),
            data.get("phone", ""),
            data.get("zip_code", ""),
            data.get("report_filename", ""),
            data.get("analysis_preview", ""),
            data.get("lead_captured", 0),
            data.get("source_page", ""),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def save_audio_transcript(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO audio_transcripts (property_id, audio_filename,
            transcript_text, findings_extracted, duration_seconds, recorded_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            data.get("property_id"),
            data.get("audio_filename", ""),
            data.get("transcript_text", ""),
            json.dumps(data.get("findings_extracted", [])),
            data.get("duration_seconds", 0),
            data.get("recorded_by", ""),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def query_property(property_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM properties WHERE id = ?", (property_id,))
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None


def query_findings(property_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM findings WHERE property_id = ? ORDER BY severity_score ASC", (property_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_findings_by_report(report_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM findings WHERE report_id = ? ORDER BY severity_score ASC", (report_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_all_properties():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM properties ORDER BY created_at DESC")
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_cost_estimate(finding_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cost_estimates WHERE finding_id = ?", (finding_id,))
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None


def query_depreciation(finding_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM depreciation_data WHERE finding_id = ?", (finding_id,))
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None


def query_capex_projections(property_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM capex_projections WHERE property_id = ? ORDER BY projected_failure_month ASC",
        (property_id,),
    )
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_negotiation_strategies(property_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM negotiation_strategies WHERE property_id = ? ORDER BY priority_rank ASC",
        (property_id,),
    )
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_escrow_holdbacks(property_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM escrow_holdbacks WHERE property_id = ?", (property_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_insurance_analysis(property_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM insurance_analysis WHERE property_id = ?", (property_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_environmental_risk(property_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM environmental_risk WHERE property_id = ?", (property_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_investor_analysis(property_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM investor_analysis WHERE property_id = ?", (property_id,))
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None


def query_permit_records(property_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM permit_records WHERE property_id = ?", (property_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_sandbox_items(property_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s.*, f.description, f.system_category, f.severity
        FROM sandbox_items s
        LEFT JOIN findings f ON s.finding_id = f.id
        WHERE s.property_id = ?
    """,
        (property_id,),
    )
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_contractor_bids(property_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contractor_bids WHERE property_id = ?", (property_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_spatial_data(property_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM spatial_data WHERE property_id = ?", (property_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_recall_checks(finding_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recall_checks WHERE finding_id = ?", (finding_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_legal_addenda(property_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM legal_addenda WHERE property_id = ?", (property_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_brokerage_roi(broker_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if broker_id:
        cursor.execute("SELECT * FROM brokerage_roi WHERE broker_id = ?", (broker_id,))
    else:
        cursor.execute("SELECT * FROM brokerage_roi ORDER BY created_at DESC LIMIT 500")
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_all_seo_pages():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM seo_pages ORDER BY impressions DESC")
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_lead_activity():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lead_magnet_activity ORDER BY created_at DESC LIMIT 100")
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_inspection_reports(property_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inspection_reports WHERE property_id = ?", (property_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def query_audio_transcripts(property_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audio_transcripts WHERE property_id = ?", (property_id,))
    results = cursor.fetchall()
    conn.close()
    return [dict(r) for r in results]


def delete_sandbox_item(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sandbox_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def update_sandbox_item(item_id, data):
    conn = get_connection()
    cursor = conn.cursor()
    sets = []
    vals = []
    for key, val in data.items():
        sets.append(f"{key} = ?")
        vals.append(val)
    vals.append(item_id)
    cursor.execute(f"UPDATE sandbox_items SET {', '.join(sets)} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def get_database_stats():
    conn = get_connection()
    cursor = conn.cursor()
    stats = {}
    tables = [
        "properties",
        "inspection_reports",
        "findings",
        "cost_estimates",
        "depreciation_data",
        "capex_projections",
        "market_data",
        "negotiation_strategies",
        "environmental_risk",
        "insurance_analysis",
        "escrow_holdbacks",
        "legal_addenda",
        "permit_records",
        "investor_analysis",
        "brokerage_roi",
        "lead_magnet_activity",
        "seo_pages",
        "contractor_bids",
        "spatial_data",
        "recall_checks",
        "sandbox_items",
        "audio_transcripts",
    ]
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
        stats[table] = cursor.fetchone()["cnt"]
    conn.close()
    return stats


init_database()
