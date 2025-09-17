# ScoutBook Multi-Application Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Overview

Multi-application platform for ScoutBook data processing, automation, and reporting. Each application focuses on a specific aspect of Scouting data management while sharing common components for efficiency and consistency.

## Applications

### Merit Badge Counselor (MBC) Pipeline
**Location**: `apps/mbc/`

Automated pipeline to scrape Merit Badge Counselor data from ScoutBook, process troop rosters, and generate comprehensive reports.

**Features:**
- Automated ScoutBook scraping with Playwright
- Roster processing and data joining
- HTML/PDF report generation with Eagle badge highlighting  
- Exclusion list support
- Multi-troop affiliation tracking

**Quick Start:**
```bash
cd apps/mbc
python src/merit_badge_counselor_scraper.py  # Scrape MBC data
python src/roster_processor.py               # Process rosters
python src/report_generator.py               # Generate reports
```

**Documentation**: [apps/mbc/README.md](apps/mbc/README.md)

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

| Application | Status | Description |
|-------------|--------|-------------|
| **MBC Pipeline** | ✅ **Production** | Merit Badge Counselor data processing and reporting |
| Training Compliance | 📋 *Planned* | YPT and training requirement tracking |
| Advancement Analytics | 📋 *Planned* | Eagle Scout and merit badge progression analysis |
| Unit Membership | 📋 *Planned* | Charter and membership monitoring |
| Council Analytics | 📋 *Planned* | District-wide reporting and metrics |

## Legacy Reference

The `legacy/` directory contains historical implementations and test outputs from the original development process. These serve as reference materials and examples of expected output formats.

## License

This project is licensed under the MIT License.

---

*Scalable platform for ScoutBook data automation and reporting*