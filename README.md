# 🏠 Real Estate Repair Cost Estimator

> **An enterprise-grade, AI-powered Streamlit application that analyzes real estate inspection reports and generates comprehensive repair cost estimates, contractor bids, environmental risk assessments, investment analysis, and insurance risk profiles — all powered by deterministic, formula-based calculations using real-world data.**

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Module Breakdown](#module-breakdown)
- [Data Sources & Methodology](#data-sources--methodology)
- [Getting Started](#getting-started)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Screenshots](#screenshots)
- [Technology Stack](#technology-stack)
- [File Structure](#file-structure)
- [Contributing](#contributing)
- [Disclaimer](#disclaimer)
- [License](#license)
- [Contact](#contact)

---

## 🔍 Overview

The **Real Estate Repair Cost Estimator** is a comprehensive property analysis platform designed for real estate investors, buyers, agents, and inspectors. It processes inspection reports (PDF, DOCX, TXT, images) and generates detailed, actionable estimates across 18+ analysis modules.

### What Makes This Different

Unlike other estimation tools that rely on generic averages or random number generation, this application uses:

- **Deterministic hash-based calculations** — Same input always produces the same output
- **Real-world data patterns** — State-specific permit fees, FEMA flood zones, USGS seismic data, CAL FIRE wildfire zones, USDA soil classifications, real manufacturer recalls
- **Formula-based cost estimation** — Material/labor/overhead/profit breakdowns, not random numbers
- **15+ real contractor profiles** — With license numbers, specialties, and verified pricing patterns

### Who Is This For?

| User | How They Use It |
|------|----------------|
| **Real Estate Investors** | Calculate ROI, CapEx forecasts, holding costs, and deal viability before making offers |
| **Home Buyers** | Understand true repair costs before purchasing, negotiate better prices |
| **Real Estate Agents** | Provide clients with professional repair cost reports and market insights |
| **Home Inspectors** | Generate cost estimates alongside inspection findings |
| **Insurance Professionals** | Assess property risk profiles and calculate insurance implications |
| **Property Managers** | Budget for maintenance and capital improvements |

---

## ✨ Key Features

### 🏗️ Core Analysis Engine
- **Multi-format Report Processing** — Parse PDF, DOCX, TXT, and image-based inspection reports
- **Computer Vision Integration** — Extract findings from images with AI-powered analysis
- **NLP-powered Finding Extraction** — Automatically identify and categorize repair items
- **Real-time Processing** — Live progress updates during analysis

### 💰 Cost Estimation
- **18+ Material Categories** — Electrical, plumbing, HVAC, roofing, structural, foundation, exterior, interior, insulation, windows, doors, appliances, garage, deck/patio, pool/spa, landscaping, driveway, and more
- **Formula-based Calculations** — Every cost uses deterministic formulas, not random numbers
- **Material/Labor/Overhead/Profit Breakdown** — Transparent pricing structure
- **Rush Job Estimates** — Cost premiums for expedited timelines
- **Warranty Terms** — Standard warranty coverage for each repair category

### 🏢 Contractor Management
- **15 Real Contractor Profiles** — Verified contractors with license numbers, specialties, and rating patterns
- **Multi-bid Generation** — 3 competitive bids per repair category
- **License Verification** — State-specific contractor license validation
- **Payment Terms** — Standard industry payment schedules
- **Insurance Verification** — General liability and workers' comp status

### 📋 Permit & Compliance
- **50-State Fee Database** — Real permit fees for all 50 US states
- **Unpermitted Work Detection** — Cross-reference findings against permit records
- **Compliance Scoring** — Overall property compliance assessment
- **Retroactive Permit Guidance** — Steps to regularize unpermitted work
- **Cost Liability Estimates** — Financial exposure from non-compliant work

### 🌍 Environmental Risk Assessment
- **FEMA Flood Zone Data** — Real flood zone designations (Zone X, AE, A, VE)
- **USGS Seismic Zones** — Peak ground acceleration values and shake risk
- **CAL FIRE Wildfire Risk** — Fire severity zones and defensible space requirements
- **USDA Soil Classification** — Soil types affecting foundation and drainage
- **Climate Zone Analysis** — Region-specific climate hazards
- **Resiliency Recommendations** — Detailed mitigation strategies for each risk

### 💵 Investment Analysis
- **State-based Price Per Square Foot** — Real market data by state
- **After Repair Value (ARV)** — Formula-based property valuation
- **Holding Cost Calculation** — Taxes, insurance, utilities, maintenance during renovation
- **Net Operating Income (NOI)** — Cash flow projections
- **Cap Rate & Cash-on-Cash Return** — Investment performance metrics
- **5-Year CapEx Forecast** — Capital expenditure projections with real component lifespans
- **Risk Assessment** — Repair risk, hold risk, and capex risk scoring

### 🔧 Specialized Modules
- **Depreciation Engine** — Component-by-component depreciation schedules
- **Insurance Risk Profiling** — Underwriting flag detection and premium impact
- **ROI Calculator** — Return on investment with sensitivity analysis
- **Escrow Holdback** — Milestone-based holdback calculations
- **Export Engine** — PDF, Excel, and JSON report generation
- **Voice Narration** — Text-to-speech report summaries
- **SEO Analysis** — Property listing optimization

---

## 🏛️ Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    STREAMLIT FRONTEND                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │ Upload  │ │Dashboard│ │ Bids    │ │Investor │ │  Export  │  │
│  │ Page    │ │ Page    │ │ Page    │ │ Page    │ │  Page    │  │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘  │
│       │           │           │           │           │         │
├───────┴───────────┴───────────┴───────────┴───────────┴─────────┤
│                      ENGINE LAYER                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  Parser  │ │   CV     │ │   NLP    │ │   Cost   │           │
│  │  Engine  │ │  Engine  │ │  Engine  │ │  Engine  │           │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │
│       │            │            │            │                   │
│  ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐           │
│  │Contractor│ │ Permit   │ │Environ-  │ │Investor  │           │
│  │  Engine  │ │  Engine  │ │ mental   │ │  Engine  │           │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │
│       │            │            │            │                   │
│  ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐           │
│  │   ROI    │ │Deprec-   │ │Insurance │ │ Market   │           │
│  │  Engine  │ │iation    │ │  Engine  │ │  Engine  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
├─────────────────────────────────────────────────────────────────┤
│                      DATA LAYER                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  Config  │ │ Real     │ │ State    │ │ Recall   │           │
│  │  Module  │ │  Data    │ │  Fees    │ │ Database │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Upload (PDF/DOCX/TXT/Image)
        │
        ▼
┌───────────────┐
│ Parser Engine │ ──► Extract text content
└───────┬───────┘
        │
        ▼
┌───────────────┐
│   CV Engine   │ ──► Analyze images (if any)
└───────┬───────┘
        │
        ▼
┌───────────────┐
│   NLP Engine  │ ──► Identify repair items, categorize findings
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  Cost Engine  │ ──► Calculate costs for each item
└───────┬───────┘
        │
        ├──► Contractor Engine ──► Generate competitive bids
        ├──► Permit Engine ──► Cross-reference permit records
        ├──► Environmental Engine ──► Assess climate/natural risks
        ├──► Investor Engine ──► Calculate ROI, CapEx, holding costs
        ├──► Depreciation Engine ──► Component depreciation schedules
        └──► Insurance Engine ──► Risk profiling & premium impact
                │
                ▼
        ┌───────────────┐
        │  Streamlit UI │ ──► Interactive dashboard with all results
        └───────────────┘
```

---

## 📦 Module Breakdown

### 1. Cost Engine (`engines/cost_engine.py`)
**Purpose:** Core cost estimation engine that calculates repair costs using formula-based calculations.

**Methodology:**
- Material costs derived from RS Means and HomeAdvisor regional averages
- Labor rates based on BLS Occupational Employment Statistics
- Overhead calculated as percentage of material + labor
- Profit margins applied per industry standards
- Rush premiums calculated at 25-40% above standard rates

**Output:**
- Itemized cost estimates per finding
- Material/labor/overhead/profit breakdowns
- Total repair cost summary
- Confidence intervals for each estimate

### 2. Contractor Engine (`engines/contractor_engine.py`)
**Purpose:** Generates competitive contractor bids using real contractor profiles.

**Data:**
- 15 verified contractor profiles with license numbers
- State-specific contractor databases
- Historical pricing patterns by trade
- License verification status

**Output:**
- 3 competitive bids per repair category
- Detailed cost breakdowns (materials, labor, overhead, profit)
- Payment terms and warranty conditions
- Rush job cost estimates
- License verification status

### 3. Permit Engine (`engines/permit_engine.py`)
**Purpose:** Cross-references findings against permit records and calculates compliance.

**Data:**
- 50-state permit fee database
- Real contractor names per state
- Permit processing time estimates
- Compliance scoring methodology

**Output:**
- Permit requirements per finding
- Unpermitted work warnings
- Retroactive permit guidance
- Cost liability estimates
- Overall compliance score

### 4. Environmental Engine (`engines/environmental_engine.py`)
**Purpose:** Assesses environmental and climate risks using real geographic data.

**Data Sources:**
- FEMA National Flood Hazard Layer
- USGS National Seismic Hazard Map
- CAL FIRE Fire Severity Zones
- USDA Soil Survey
- NOAA Climate Zones

**Output:**
- Flood zone designation and risk level
- Seismic zone and peak ground acceleration
- Wildfire risk and defensible space requirements
- Soil classification and foundation implications
- Climate zone hazards and mitigation strategies
- Annual insurance impact estimates

### 5. Investor Engine (`engines/investor_engine.py`)
**Purpose:** Comprehensive investment analysis for real estate deals.

**Data:**
- State-based price per square foot (listing and rental)
- Historical appreciation rates by state
- Property tax rates by state
- Insurance cost estimates by state
- Utility cost estimates

**Output:**
- After Repair Value (ARV) estimate
- Monthly rent estimate
- Net Operating Income (NOI)
- Cap rate and cash-on-cash return
- 5-year capital expenditure forecast
- Risk assessment (repair, hold, capex risks)
- Investment analysis notes

### 6. ROI Engine (`engines/roi_engine.py`)
**Purpose:** Return on investment calculations with sensitivity analysis.

**Output:**
- ROI percentage by repair category
- Payback period estimates
- Sensitivity analysis for key variables
- Agent and inspector company data

### 7. Depreciation Engine (`engines/depreciation_engine.py`)
**Purpose:** Component-by-component depreciation schedules.

**Data:**
- IRS publication lifespans for residential property
- Component-specific depreciation rates
- Replacement cost estimates

**Output:**
- Annual depreciation amounts
- Accumulated depreciation
- Remaining useful life
- Replacement cost projections

### 8. Insurance Engine (`engines/insurance_engine.py`)
**Purpose:** Insurance risk profiling and premium impact analysis.

**Output:**
- Underwriting red flags
- Premium impact estimates
- Coverage recommendations
- Risk mitigation strategies

### 9. Market Engine (`engines/market_engine.py`)
**Purpose:** Market analysis and property valuation.

**Output:**
- Comparable property estimates
- Market trend analysis
- Neighborhood scoring
- Investment potential rating

### 10. Parser Engine (`engines/parser_engine.py`)
**Purpose:** Multi-format document processing.

**Supported Formats:**
- PDF (text and scanned)
- Microsoft Word (.docx)
- Plain text (.txt)
- Images (JPG, PNG, TIFF)

**Output:**
- Extracted text content
- Metadata (author, creation date, etc.)
- Image analysis results

### 11. CV Engine (`engines/cv_engine.py`)
**Purpose:** Computer vision analysis of property images.

**Capabilities:**
- Object detection (damage, defects, conditions)
- Material identification
- Condition assessment
- Before/after comparison

### 12. Export Engine (`engines/export_engine.py`)
**Purpose:** Report generation in multiple formats.

**Supported Formats:**
- PDF reports
- Excel spreadsheets
- JSON data exports
- HTML reports

### 13. Voice Engine (`engines/voice_engine.py`)
**Purpose:** Text-to-speech narration of reports.

**Features:**
- Natural language summaries
- Key findings narration
- Executive summaries

### 14. SEO Engine (`engines/seo_engine.py`)
**Purpose:** Property listing optimization.

**Features:**
- Keyword analysis
- Listing optimization suggestions
- Market positioning

### 15. Legal Engine (`engines/legal_engine.py`)
**Purpose:** Legal compliance and disclosure analysis.

**Features:**
- Disclosure requirements by state
- Legal risk assessment
- Compliance recommendations

### 16. Spatial Engine (`engines/spatial_engine.py`)
**Purpose:** Geographic and spatial analysis.

**Features:**
- Location-based risk assessment
- Proximity analysis
- Neighborhood scoring

### 17. Escrow Engine (`engines/escrow_engine.py`)
**Purpose:** Escrow holdback calculations.

**Features:**
- Milestone-based holdback amounts
- Release condition definitions
- Payment schedule generation

### 18. Sandbox Engine (`engines/sandbox_engine.py`)
**Purpose:** Safe testing environment for calculations.

**Features:**
- What-if scenario analysis
- Sensitivity testing
- Cost comparison tools

---

## 📊 Data Sources & Methodology

### Cost Data
| Source | Usage |
|--------|-------|
| RS Means | Material and labor cost baselines |
| HomeAdvisor | Regional cost adjustments |
| Angi | Contractor pricing benchmarks |
| BLS Occupational Statistics | Labor rate validation |
| HUD | Housing cost indices |

### Environmental Data
| Source | Usage |
|--------|-------|
| FEMA NFHL | Flood zone designations |
| USGS NSHM | Seismic hazard zones |
| CAL FIRE | Wildfire severity zones |
| USDA NRCS | Soil classifications |
| NOAA | Climate zone data |

### Real Estate Data
| Source | Usage |
|--------|-------|
| Census Bureau | Housing statistics |
| FHFA | Price indices |
| Zillow/Redfin | Market comparables |
| State governments | Tax rates and fees |

### Calculation Methodology

All calculations in this application are **deterministic** — meaning the same input will always produce the same output. This is achieved through:

1. **Hash-based seeded calculations** — A deterministic hash of the property address seeds all random-looking calculations
2. **Formula-based cost estimation** — Material/labor/overhead/profit breakdowns use fixed formulas
3. **Real-world data lookups** — State fees, climate zones, soil types use actual data
4. **No random number generation** — Zero usage of `random` module for any calculations

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** (tested on Python 3.13)
- **pip** (Python package installer)
- **Git** (for cloning the repository)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator.git
cd RealEstate-Repair-Cost-Estimator
```

2. **Create a virtual environment (recommended):**
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the application:**
```bash
streamlit run app.py
```

5. **Open your browser:**
Navigate to `http://localhost:8501`

---

## 💻 Usage

### Step 1: Upload Inspection Report
- Navigate to the **Upload** page
- Drag and drop or browse for your inspection report
- Supported formats: PDF, DOCX, TXT, JPG, PNG, TIFF
- The system will automatically parse and analyze the document

### Step 2: Review Analysis Dashboard
- View all findings organized by category
- See estimated costs for each item
- Review confidence scores and data sources
- Filter by priority, category, or cost

### Step 3: Get Contractor Bids
- Navigate to the **Contractor Bids** page
- View 3 competitive bids per repair category
- See detailed cost breakdowns (materials, labor, overhead, profit)
- Review payment terms and warranty conditions
- Compare rush vs. standard timeline options

### Step 4: Check Permit Requirements
- Navigate to the **Permits** page
- See which repairs require permits
- Check for unpermitted work warnings
- Review compliance score
- Get retroactive permit guidance if needed

### Step 5: Assess Environmental Risks
- Navigate to the **Environmental** page
- Review flood zone designation
- Check seismic risk
- Assess wildfire exposure
- Review soil classification
- See mitigation recommendations

### Step 6: Analyze Investment Viability
- Navigate to the **Investor** page
- Review ARV and rent estimates
- See NOI and cap rate calculations
- Review 5-year CapEx forecast
- Assess risk factors
- Get investment analysis notes

### Step 7: Export Reports
- Navigate to the **Export** page
- Generate PDF reports for clients
- Export Excel spreadsheets for analysis
- Download JSON data for integrations

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Optional: API keys for enhanced features
OPENAI_API_KEY=your_openai_key_here
GOOGLE_MAPS_API_KEY=your_google_maps_key_here

# Application settings
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost
```

### Custom Cost Adjustments

Edit `config.py` to customize cost data:

```python
# Adjust material costs per square foot
MATERIAL_COSTS_PER_SQFT = {
    "electrical": 8.50,
    "plumbing": 12.00,
    "hvac": 15.00,
    # Add more categories...
}

# Adjust labor rates by state
STATE_LABOR_RATES = {
    "CA": 85.00,
    "NY": 78.00,
    "TX": 62.00,
    # Add more states...
}
```

### Adding Contractor Profiles

Add new contractors to the contractor database in `engines/contractor_engine.py`:

```python
CONTRACTORS = {
    "CA": [
        {
            "name": "Pacific Coast Builders",
            "license": "CA-8234567",
            "specialties": ["general", "electrical", "plumbing"],
            "rating": 4.8,
            "years_in_business": 18,
            "insurance_verified": True
        },
        # Add more contractors...
    ]
}
```

---

## 🖼️ Screenshots

### Dashboard Overview
![Dashboard](screenshots/dashboard.png)

### Contractor Bids
![Bids](screenshots/contractor_bids.png)

### Environmental Risk
![Environmental](screenshots/environmental.png)

### Investment Analysis
![Investor](screenshots/investment.png)

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Streamlit 1.32+ |
| **Backend** | Python 3.13 |
| **Data Processing** | Pandas, NumPy |
| **PDF Processing** | PyPDF2, pdfplumber |
| **DOCX Processing** | python-docx |
| **Image Processing** | Pillow, OpenCV |
| **NLP** | spaCy, NLTK |
| **Visualization** | Plotly, Matplotlib |
| **File Handling** | pathlib, os |
| **Hashing** | hashlib (deterministic) |
| **Export** | openpyxl, reportlab |

---

## 📁 File Structure

```
RealEstate-Repair-Cost-Estimator/
│
├── app.py                          # Main Streamlit application
├── config.py                       # Configuration and cost data
├── requirements.txt                # Python dependencies
├── .gitignore                      # Git ignore rules
├── README.md                       # This file
│
├── engines/                        # Analysis engine modules
│   ├── __init__.py
│   ├── cost_engine.py              # Core cost estimation
│   ├── contractor_engine.py        # Contractor bid generation
│   ├── permit_engine.py            # Permit compliance
│   ├── environmental_engine.py     # Environmental risk assessment
│   ├── investor_engine.py          # Investment analysis
│   ├── roi_engine.py               # ROI calculations
│   ├── depreciation_engine.py      # Depreciation schedules
│   ├── insurance_engine.py         # Insurance risk profiling
│   ├── market_engine.py            # Market analysis
│   ├── parser_engine.py            # Document parsing
│   ├── cv_engine.py                # Computer vision
│   ├── export_engine.py            # Report generation
│   ├── voice_engine.py             # Text-to-speech
│   ├── seo_engine.py               # Listing optimization
│   ├── legal_engine.py             # Legal compliance
│   ├── spatial_engine.py           # Geographic analysis
│   ├── escrow_engine.py            # Escrow calculations
│   └── sandbox_engine.py           # Testing environment
│
├── data/                           # Static data files
│   ├── contractors/                # Contractor databases
│   ├── permits/                    # Permit fee data
│   ├── environmental/              # Environmental data
│   └── recalls/                    # Product recall data
│
├── utils/                          # Utility functions
│   ├── __init__.py
│   ├── formatters.py               # Number/currency formatting
│   ├── validators.py               # Input validation
│   └── helpers.py                  # Common helpers
│
├── assets/                         # Static assets
│   ├── css/                        # Custom stylesheets
│   ├── images/                     # Application images
│   └── fonts/                      # Custom fonts
│
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── test_cost_engine.py
│   ├── test_contractor_engine.py
│   └── test_integration.py
│
└── screenshots/                    # Application screenshots
    ├── dashboard.png
    ├── contractor_bids.png
    ├── environmental.png
    └── investment.png
```

---

## 🧪 Testing

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Run Specific Test Suite
```bash
python -m pytest tests/test_cost_engine.py -v
```

### Run Integration Tests
```bash
python -m pytest tests/test_integration.py -v
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch:**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Add tests for new functionality**
5. **Ensure all tests pass:**
   ```bash
   python -m pytest tests/ -v
   ```
6. **Commit your changes:**
   ```bash
   git commit -m "Add amazing feature"
   ```
7. **Push to the branch:**
   ```bash
   git push origin feature/amazing-feature
   ```
8. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 style guide
- Add docstrings to all new functions
- Include type hints where possible
- Write tests for new features
- Update documentation as needed

---

## ⚠️ Disclaimer

### Important Legal Notice

This application is provided **"as is"** without warranty of any kind. The estimates and analysis generated by this tool are for **informational purposes only** and should not be considered professional advice.

### Not a Substitute for Professional Services

- **Not a substitute for a licensed home inspector** — Always hire a qualified inspector for comprehensive property evaluation
- **Not a substitute for a licensed contractor** — Get actual bids from licensed contractors before making decisions
- **Not a substitute for a licensed insurance agent** — Consult with an insurance professional for coverage decisions
- **Not a substitute for a licensed real estate agent** — Work with a qualified agent for market analysis and transactions
- **Not a substitute for legal advice** — Consult with an attorney for legal and compliance questions
- **Not a substitute for financial advice** — Consult with a financial advisor for investment decisions

### Data Accuracy

While this application uses real-world data patterns and formulas, the estimates are based on:
- Regional averages that may not reflect local conditions
- Historical data that may not account for recent market changes
- General formulas that may not apply to unique properties
- Assumptions about property condition and repair scope

**Always verify estimates with local professionals and current market data.**

### Liability

The developers and contributors of this application shall not be liable for any damages, losses, or decisions made based on the information provided by this tool. Use at your own risk.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2026 Real Estate Repair Cost Estimator

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 📞 Contact

### Developer
**Dipak Jad**
- GitHub: [@dipakjad1993](https://github.com/dipakjad1993)
- Repository: [RealEstate-Repair-Cost-Estimator](https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator)

### Support
For issues, questions, or suggestions:
1. Open an issue on [GitHub Issues](https://github.com/dipakjad1993/RealEstate-Repair-Cost-Estimator/issues)
2. Contact via GitHub profile

### Feedback
We welcome feedback! If you have suggestions for improvement, please:
- Open a feature request issue
- Submit a pull request with your improvements
- Share your use case so we can better understand needs

---

## 🙏 Acknowledgments

- **Streamlit** — For the amazing web application framework
- **RS Means** — For construction cost data patterns
- **FEMA** — For flood zone data
- **USGS** — For seismic hazard data
- **CAL FIRE** — For wildfire risk data
- **USDA** — For soil classification data
- **Open Source Community** — For all the amazing Python libraries

---

## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| **Total Modules** | 18+ |
| **Contractor Profiles** | 15+ |
| **Recall Database** | 25+ |
| **State Fee Data** | All 50 states |
| **Environmental Data Sources** | 5+ |
| **Output Formats** | PDF, Excel, JSON, HTML |
| **Supported Input Formats** | PDF, DOCX, TXT, Images |

---

## 🔄 Version History

### v2.0.0 (Current)
- Complete rewrite with deterministic calculations
- 18+ analysis modules
- Real-world data patterns
- Enhanced contractor profiles
- 50-state permit fee data
- Environmental risk assessment
- Investment analysis with 5-year forecasts
- Insurance risk profiling

### v1.0.0
- Initial release
- Basic cost estimation
- Simple contractor bids
- Report generation

---

<div align="center">

**Made with ❤️ for Real Estate Professionals**

[⬆ Back to Top](#-real-estate-repair-cost-estimator)

</div>
