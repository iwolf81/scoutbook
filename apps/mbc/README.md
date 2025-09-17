# Merit Badge Counselor (MBC) Pipeline

Automated pipeline to scrape Merit Badge Counselor data from ScoutBook, process troop rosters, and generate comprehensive reports.

## Quick Start

### Prerequisites
```bash
cd /Users/iwolf/Repos/scoutbook
pip install -r requirements.txt
```

### Basic Usage

1. **Scrape MBC Data**:
```bash
python src/merit_badge_counselor_scraper.py
```

2. **Process Rosters**:
```bash  
python src/roster_processor.py
```

3. **Generate Reports**:
```bash
python src/report_generator.py
```

## Directory Structure

```
apps/mbc/
├── src/                               # Core pipeline scripts
│   ├── merit_badge_counselor_scraper.py
│   ├── roster_processor.py
│   └── report_generator.py
├── data/                              # Application data
│   ├── input/                         # Input files
│   │   ├── rosters/                   # Troop roster HTML files
│   │   └── exclusion_list.txt         # Names to exclude from reports
│   ├── scraped/                       # Raw scraped HTML data
│   ├── processed/                     # Cleaned JSON data
│   └── reports/                       # Generated HTML/PDF reports
└── docs/                              # Documentation
    ├── PIPELINE_EXECUTION_GUIDE.md    # Detailed execution instructions
    └── REQUIREMENTS_SPECIFICATION.md  # Technical requirements
```

## Current Results

- **Total Adults in Rosters**: 61
- **Adults who are MBCs**: 8 (13.1%)  
- **Merit Badge Coverage**: 132 total badges analyzed
- **Multi-Troop Support**: Tracks adults in both T32 and T7012

## Documentation

- **[Pipeline Execution Guide](docs/PIPELINE_EXECUTION_GUIDE.md)**: Complete step-by-step instructions
- **[Requirements Specification](docs/REQUIREMENTS_SPECIFICATION.md)**: Technical requirements for recreation

## Input Files

### Required
- `data/input/rosters/T32 Roster 16Sep2025.html`
- `data/input/rosters/T7012 Roster 16Sep2025.html`

### Optional  
- `data/input/exclusion_list.txt` (names to exclude from reports)

## Output Files

- `data/processed/mbc_counselors_cleaned.json` - Cleaned counselor data
- `data/processed/roster_mbc_join.json` - Joined roster and MBC data
- `data/reports/T32_T7012_MBC_YYYYMMDD_HHMMSS/` - Generated reports (HTML + PDF)

---

*Part of the ScoutBook multi-application platform*