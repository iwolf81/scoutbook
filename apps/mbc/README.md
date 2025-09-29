# Merit Badge Counselor (MBC) Pipeline

Automated pipeline to scrape Merit Badge Counselor data from ScoutBook, process troop rosters, analyze Scout demand, and generate comprehensive reports with merit badge coverage priority analysis.

## Quick Start

### Prerequisites
```bash
cd /Users/iwolf/Repos/scoutbook
pip install -r requirements.txt
```

### Automated Pipeline (Recommended)

Run the complete pipeline with a single command:

```bash
# Full pipeline (includes scraping)
python src/generate_mbc_reports.py

# Skip scraping (use existing data)
python src/generate_mbc_reports.py --skip-scraping

# Include Google Drive preparation
python src/generate_mbc_reports.py --skip-scraping --google-drive

# Run specific stages
python src/generate_mbc_reports.py --stage scout_demand
python src/generate_mbc_reports.py --stage coverage_analysis
python src/generate_mbc_reports.py --stage reporting
```

### Manual Execution (Individual Scripts)

For development or debugging, run individual scripts:

1. **Scrape MBC Data**:
```bash
python src/merit_badge_counselor_scraper.py
```

2. **Process Rosters**:
```bash
python src/roster_processor.py
```

3. **Process Scout Demand** (NEW):
```bash
python src/scout_demand_processor.py
```

4. **Analyze Coverage Gaps** (NEW):
```bash
python src/coverage_gap_analyzer.py
```

5. **Generate Reports**:
```bash
python src/report_generator.py
```

6. **Prepare for Google Drive** (Optional):
```bash
python src/prepare_gdrive_files.py
```

## Features

### Core Capabilities
- **Automated Scraping**: Extract Merit Badge Counselor data from ScoutBook
- **Roster Processing**: Join troop rosters with MBC data
- **Scout Demand Analysis**: Process Scout merit badge requests from signup data
- **Coverage Gap Analysis**: Identify priority Merit Badges needing additional counselors
- **Priority Reports**: Generate actionable recruitment reports based on Scout demand
- **Multi-Troop Support**: Track counselors across multiple troops (T32, T7012)
- **Supplemental MBCs**: Include unit-associated counselors not in rosters

### Priority Analysis System
The pipeline generates a **Merit Badge Coverage Priority Report** that classifies Merit Badges into priority levels:

- **Critical Priority**: Eagle-required Merit Badges with 0 or 1 MBC (highest recruitment priority)
- **High Priority**: Non-Eagle Merit Badges with 3+ Scout requests and no MBC coverage
- **Medium Priority**: Non-Eagle Merit Badges with 1-2 Scout requests and no MBC coverage
- **Adequate Coverage**: Merit Badges with 3+ counselors (not shown as priorities)

Reports include:
- Scouts impacted by coverage gaps
- Merit Badge lists sorted alphabetically within each priority level
- Scout names requesting specific Merit Badges
- Current MBC assignments for Eagle-required badges

## Directory Structure

```
apps/mbc/
├── src/                                    # Core pipeline scripts
│   ├── generate_mbc_reports.py             # Pipeline orchestrator (recommended)
│   ├── merit_badge_counselor_scraper.py    # ScoutBook data extraction
│   ├── roster_processor.py                 # Roster + MBC join
│   ├── scout_demand_processor.py           # Scout request analysis
│   ├── coverage_gap_analyzer.py            # Priority gap identification
│   ├── report_generator.py                 # HTML/PDF report generation
│   ├── gdrive_sync.py                      # Google Drive automated sync
│   └── prepare_gdrive_files.py             # Manual Google Drive prep
├── data/                                   # Application data
│   ├── input/                              # Input files
│   │   ├── rosters/                        # Troop roster HTML files
│   │   ├── exclusion_list.txt              # Names to exclude from reports
│   │   ├── unit_associated_mbcs.txt        # Supplemental MBC input
│   │   ├── all_merit_badges.txt            # Complete MB list
│   │   └── *.csv / *.xlsx                  # Scout merit badge requests
│   ├── scraped/                            # Raw scraped HTML data
│   ├── processed/                          # Cleaned JSON data
│   │   ├── mbc_counselors.json             # Scraped MBC data
│   │   ├── roster_mbc_join.json            # Processed roster data
│   │   ├── scout_demand_analysis_*.json    # Scout request analysis
│   │   └── coverage_priority_analysis_*.json # Priority rankings
│   ├── reports/                            # Generated HTML/PDF reports
│   ├── gdrive/                             # Ready-to-upload files (manual)
│   └── logs/                               # Pipeline execution logs
└── docs/                                   # Documentation
    ├── PIPELINE_EXECUTION_GUIDE.md         # Detailed execution instructions
    └── REQUIREMENTS_SPECIFICATION.md       # Technical requirements
```

## Current Results

- **Total Adults in Rosters**: 61
- **Adults who are MBCs**: 8 (13.1%)
- **Merit Badge Coverage**: 139 official Merit Badges analyzed
- **Reports Generated**: 8 reports per execution (4 HTML + 4 PDF)
- **Priority Analysis**: 4 priority levels (Critical, High, Medium, Adequate)
- **Multi-Troop Support**: Tracks adults in both T32 and T7012
- **Scouts Tracked**: 10 unique Scouts with merit badge requests
- **Coverage Gaps**: 8 Scouts impacted by coverage gaps

## Documentation

- **[Pipeline Execution Guide](docs/PIPELINE_EXECUTION_GUIDE.md)**: Complete step-by-step instructions
- **[Requirements Specification](docs/REQUIREMENTS_SPECIFICATION.md)**: Technical requirements for recreation

## Input Files

### Required for Basic Reports
- `data/input/rosters/*.html` - Troop roster files (T32, T7012)

### Required for Priority Analysis
- `data/input/*.csv` or `*.xlsx` - Scout merit badge request data (e.g., signup spreadsheet)
- `data/input/all_merit_badges.txt` - Complete list of official Merit Badges

### Optional
- `data/input/exclusion_list.txt` - Names to exclude from reports
- `data/input/unit_associated_mbcs.txt` - Supplemental MBC-only counselors associated with units

## Output Files

### Processed Data
- `data/processed/mbc_counselors.json` - Scraped and cleaned MBC data
- `data/processed/roster_mbc_join.json` - Joined roster and MBC data
- `data/processed/scout_demand_analysis_YYYYMMDD_HHMMSS.json` - Scout request analysis
- `data/processed/coverage_priority_analysis_YYYYMMDD_HHMMSS.json` - Priority rankings

### Generated Reports
- `data/reports/T32_T7012_MBC_Reports_YYYYMMDD_HHMMSS/` - Report directory containing:
  - `*_Troop_Counselors_*.html` / `*.pdf` - Adults who are MBCs
  - `*_Non_Counselors_*.html` / `*.pdf` - Adults who are not MBCs
  - `*_Coverage_Report_*.html` / `*.pdf` - Complete Merit Badge coverage analysis
  - `*_Priority_Report_*.html` / `*.pdf` - Priority-based recruitment recommendations
  - `summary_report.json` - Analysis metadata

### Logs
- `data/logs/generate_mbc_reports_YYYYMMDD_HHMMSS.log` - Pipeline execution log
- `data/logs/mbc_pipeline_status_YYYYMMDD_HHMMSS.json` - Stage execution status

---

*Part of the ScoutBook multi-application platform*