# ScoutBook Multi-Application Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Overview

Multi-application platform for ScoutBook data processing, automation, and reporting. Each application focuses on a specific aspect of Scouting data management while sharing common components for efficiency and consistency.

## Applications

### Merit Badge Counselor (MBC) Pipeline ✅ **PRODUCTION READY**
**Location**: `apps/mbc/`

Complete automated pipeline that scrapes Merit Badge Counselor data from ScoutBook, processes troop rosters, and generates professional reports.

**Features:**
- ✅ Browser automation with Playwright (handles slow ScoutBook responses)
- ✅ Full pagination support for counselor search results
- ✅ Intelligent roster processing with multi-troop support
- ✅ Professional HTML/PDF reports with Eagle badge highlighting 🦅
- ✅ Smart exclusion list with flexible name matching
- ✅ Data archival with timestamped directories

**Current Results:**
- **61 adults** processed from T32 and T7012 rosters
- **8 troop counselors** identified (13.1% of adults)
- **139 merit badges** analyzed for coverage
- **6 reports** generated per run (HTML + PDF)

**Quick Start:**
```bash
cd apps/mbc
python src/merit_badge_counselor_scraper.py  # Scrape MBC data (15-30 min)
python src/roster_processor.py               # Process rosters (< 1 min)
python src/report_generator.py               # Generate reports (< 1 min)
```

**Documentation**: [Complete Guide](apps/mbc/README.md) | [Execution Steps](apps/mbc/docs/PIPELINE_EXECUTION_GUIDE.md)

## Repository Structure

```
scoutbook/
├── apps/                              # ScoutBook applications
│   └── mbc/                           # Merit Badge Counselor pipeline
│       ├── src/                       # Application code
│       ├── data/                      # Application data
│       ├── docs/                      # Application documentation
│       └── README.md                  # Application overview
├── shared/                            # Reusable components
│   ├── scrapers/                      # Common scraping utilities
│   ├── processors/                    # Data processing functions
│   ├── reports/                       # Report generation utilities
│   └── utils/                         # General helper functions
├── legacy/                            # Historical reference implementations
├── requirements.txt                   # Python dependencies
└── README.md                          # This file
```

## Shared Components

### Scrapers (`shared/scrapers/`)
Reusable ScoutBook scraping utilities including authentication, pagination, HTML archiving, and common scraping patterns.

### Processors (`shared/processors/`)  
Common data processing functions for cleaning, validation, name matching, exclusion filtering, and data transformation.

### Reports (`shared/reports/`)
Shared report generation utilities including templates, PDF generation, HTML formatting, and consistent styling.

### Utils (`shared/utils/`)
General helper functions for authentication, file handling, timestamp management, and other common tasks.

## Development Guidelines

### Adding New Applications

1. **Create Application Directory:**
```bash
mkdir -p apps/{app_name}/{src,data,docs}
mkdir -p apps/{app_name}/data/{input,scraped,processed,reports}
```

2. **Follow Standard Structure:**
- `src/` - Application-specific code
- `data/input/` - Input files (including exclusion lists)
- `data/scraped/` - Raw scraped data
- `data/processed/` - Cleaned/transformed data  
- `data/reports/` - Generated outputs
- `docs/` - Application documentation

3. **Leverage Shared Components:**
- Import utilities from `shared/` packages
- Follow established patterns from existing applications
- Contribute reusable code back to shared components

4. **Documentation Requirements:**
- `README.md` - Application overview and usage
- `docs/EXECUTION_GUIDE.md` - Step-by-step instructions
- `docs/REQUIREMENTS.md` - Technical specifications

## Prerequisites

```bash
pip install -r requirements.txt
```

## Current Applications Status

| Application | Status | Key Metrics | Description |
|-------------|--------|-------------|-------------|
| **MBC Pipeline** | ✅ **Production** | 61 adults, 8 MBCs, 139 badges | Complete automation of Merit Badge Counselor reporting |
| Training Compliance | 📋 *Planned* | - | YPT and training requirement tracking |
| Advancement Analytics | 📋 *Planned* | - | Eagle Scout and merit badge progression analysis |
| Unit Membership | 📋 *Planned* | - | Charter and membership monitoring |
| Council Analytics | 📋 *Planned* | - | District-wide reporting and metrics |

## Production Results

### MBC Pipeline (Production)
- **Total Adults Processed**: 61 from T32 and T7012 rosters
- **Troop Members who are MBCs**: 8 (13.1% of adults)
- **Merit Badge Coverage Analysis**: 139 total badges categorized
- **Multi-Troop Support**: Proper tracking of adults in multiple units
- **Report Generation**: 3 reports × 2 formats = 6 files per execution
- **Data Protection**: Personal information automatically excluded from repository

## Legacy Reference

The `legacy/` directory contains historical implementations and test outputs from the original development process. These serve as reference materials and examples of expected output formats.

## License

This project is licensed under the MIT License.

---

*Scalable platform for ScoutBook data automation and reporting*