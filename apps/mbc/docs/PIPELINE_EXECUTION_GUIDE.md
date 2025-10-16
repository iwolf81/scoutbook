# Merit Badge Counselor Pipeline Execution Guide

## Overview

This guide covers two ways to execute the Merit Badge Counselor (MBC) pipeline:
1. **Pipeline Manager** (Recommended) - Automated execution with error handling
2. **Individual Scripts** - Manual step-by-step execution for debugging

The pipeline extracts MBC data from ScoutBook, processes troop rosters, analyzes Scout merit badge requests, identifies coverage gaps, and generates comprehensive reports including priority-based recruitment recommendations.

## Quick Start (Recommended)

```bash
# Go to the Merit Badge Counselor app in Scoutbook
cd apps/mbc

# Full automated pipeline
python src/generate_mbc_reports.py

# Include Google Drive preparation
python src/generate_mbc_reports.py --google-drive

# Skip scraping (use existing MBC data)
python src/generate_mbc_reports.py --skip-scraping
```

## Prerequisites

- Python 3.11+
- Playwright browser automation library
- Required roster HTML files in `data/input/rosters/`
- Internet connection for ScoutBook scraping
- ScoutBook account credentials for manual login

## Input Files

### Required Input Files
| File | Location | Description |
|------|----------|-------------|
| Troop Rosters | `data/input/rosters/` | Unit rosters downloaded from ScoutBook |
| Merit Badge List | `data/input/all_merit_badges.txt` | Official merit badge list |

**Roster Download Instructions**:
1. Navigate to https://advancements.scouting.org/roster
2. Select "Quick Report" -> "Unit Roster" for each unit
3. Save page via browser as "text files" (current requirement for roster processor)

### Optional Input Files
| File | Location | Description |
|------|----------|-------------|
| Scout Requests | `data/input/requested_merit_badges/*.csv` or `*.xlsx` | Scout merit badge request data (for demand and priority analysis) |
| Exclusion List | `data/input/exclusion_list.txt` | Names to exclude from all reports |
| Supplemental MBCs | `data/input/unit_associated_mbcs.txt` | MBC-only registrations associated with units |
| MBC Signup Forms | `data/input/mbc_signup/*.csv` or `*.xlsx` | Merit Badge signup form submissions (alternative to requested_merit_badges) |
| Configuration | `config.json` | Pipeline configuration (future feature) |

**Supplemental MBC Format**:
```
# Unit-Associated MBC Supplemental Input
# Format: FirstName LastName, UnitID
John Smith, T32
Jane Doe, T7012
Bob Wilson, Troop 32
```

## Pipeline Manager (Recommended)

### Command Line Interface

```bash
# Go to the Merit Badge Counselor app in Scoutbook
cd apps/mbc

# Basic usage
python src/generate_mbc_reports.py                     # Full pipeline
python src/generate_mbc_reports.py --google-drive      # Include Google Drive prep
python src/generate_mbc_reports.py --skip-scraping     # Use existing MBC data

# Stage-specific execution
python src/generate_mbc_reports.py --stage scraping          # Scrape MBC data only
python src/generate_mbc_reports.py --stage processing        # Process rosters only
python src/generate_mbc_reports.py --stage scout_demand      # Process Scout requests only
python src/generate_mbc_reports.py --stage coverage_analysis # Analyze coverage gaps only
python src/generate_mbc_reports.py --stage reporting         # Generate reports only
python src/generate_mbc_reports.py --stage gdrive_prep --google-drive  # Prepare Google Drive files
```

### Arguments Reference

| Argument | Description | Default |
|----------|-------------|---------|
| `--stage` | Pipeline stage to run (`scraping`, `processing`, `scout_demand`, `coverage_analysis`, `reporting`, `gdrive_prep`, `all`) | `all` |
| `--skip-scraping` | Skip scraping stage and use existing MBC data | `false` |
| `--google-drive` | Include Google Drive file preparation stage | `false` |

### Pipeline Stages

The pipeline consists of 6 stages that execute in sequence:

**Stage 1: Scraping** (15-30 minutes)
- Scrapes Merit Badge Counselor data from ScoutBook
- Requires manual browser login to ScoutBook
- Creates `data/processed/mbc_counselors.json`
- Can be skipped with `--skip-scraping` flag

**Stage 2: Processing** (< 1 minute)
- Auto-detects latest roster files in `data/input/rosters/`
- Joins roster data with MBC data
- Processes supplemental MBCs from `unit_associated_mbcs.txt`
- Creates `data/processed/roster_mbc_join.json`

**Stage 3: Scout Demand Analysis** (< 1 minute)
- Auto-detects Scout request files (CSV/XLSX) in `data/input/requested_merit_badges/` and `data/input/mbc_signup/`
- Parses Scout merit badge requests from both signup forms and request lists
- Classifies Eagle-required vs. non-Eagle badges
- Aggregates demand across all Scouts by merit badge
- Creates `data/processed/scout_demand_analysis_YYYYMMDD_HHMMSS.json`

**Stage 4: Coverage Gap Analysis** (< 1 minute)
- Auto-detects latest scout demand analysis and MBC coverage data
- Calculates priority scores based on Scout demand and MBC availability
- Identifies coverage gap levels: Critical (no MBCs), High (1-2 MBCs), Medium (3+ MBCs)
- Ranks merit badges by recruitment priority (Eagle-required given higher weight)
- Creates `data/processed/coverage_priority_analysis_YYYYMMDD_HHMMSS.json`

**Stage 5: Reporting** (< 3 seconds)
- Auto-detects latest priority analysis file
- Generates HTML and PDF reports
- Creates 4 reports:
  - **Troop Counselors**: Unit members who are registered MBCs
  - **Non-Counselors**: Unit members not currently registered as MBCs
  - **Coverage Report**: All 139 merit badges with current MBC coverage
  - **Priority Report**: Merit badges ranked by recruitment priority with Scout demand data
- Applies exclusion list filtering to all reports
- Creates timestamped report directory in `data/reports/`

**Stage 6: Google Drive Prep** (< 1 second, optional)
- Prepares PDF files for Google Drive upload
- Only runs when `--google-drive` flag is specified
- Creates standardized filenames in `data/gdrive/`
- Copy these files to the "T12+T32 Troop Committee / Merit Badge Resources" folder in Google Drive:
```bash
https://drive.google.com/drive/u/0/folders/1bC3_71dlmp0CvoDFisRpb-Y3WoKHvpiD
```

### Status Tracking

Each pipeline execution creates:
- **Session ID**: `YYYYMMDD_HHMMSS` timestamp
- **Log file**: `data/logs/generate_mbc_reports_YYYYMMDD_HHMMSS.log`
- **Status file**: `data/logs/mbc_pipeline_status_YYYYMMDD_HHMMSS.json`

### Explicit File Passing

The pipeline ensures data consistency by explicitly passing file paths between stages:
- **Scraping** → **Processing**: `--mbc-data data/processed/mbc_counselors.json`
- **Processing** → **Reporting**: `--data-file data/processed/roster_mbc_join.json`
- **Reporting** → **Google Drive**: `--reports-dir` with latest report directory

## Individual Scripts (For Debugging)

### Step 1: Merit Badge Counselor Scraping

```bash
cd apps/mbc

python src/merit_badge_counselor_scraper.py
```

**What it does:**
- Authenticates with ScoutBook using browser automation
- Systematically scrapes Merit Badge Counselor database
- Handles pagination for complete data coverage
- Archives raw HTML data for debugging/reprocessing

**Manual Login Required:** Browser will open for interactive ScoutBook login

**Outputs Created:**
- `data/scraped/mbc_search_YYYYMMDD_HHMMSS/` (timestamped directory)
- `data/processed/mbc_counselors.json` (cleaned and processed data)

**Command Line Options:**
```bash
python src/merit_badge_counselor_scraper.py --help
python src/merit_badge_counselor_scraper.py --output custom_output.json
```

### Step 2: Roster Processing and Data Joining

```bash
python src/roster_processor.py
```

**What it does:**
- **Auto-detects roster files** by scanning `data/input/rosters/` directory
- **Selects latest rosters** automatically per unit (e.g., Sep 21 > Sep 16)
- **Supports any Scout units** (not limited to T32/T7012)
- Extracts adult members from roster HTML files
- Excludes "Unit Participant" positions (18+ scouts, not adult leaders)
- Creates unified adult list with troop affiliations
- Joins roster data with MBC data using name matching logic
- **Includes supplemental MBCs** from `unit_associated_mbcs.txt` (MBC-only registrations)
- Handles multi-troop affiliations for adults in both troops

**Name Matching Logic:**
- **MBC Keys**: Creates multiple keys per counselor for flexible matching:
  - Primary: `(alt_first_name + last_name)` (if alt_first_name exists and differs from first_name)
  - Fallback: `(first_name + last_name)` (always created)
- **Roster Key**: `(first_name + last_name)` (ignoring middle names/initials)
- **Matching Process**: Roster key is looked up against all available MBC keys

**Outputs Created:**
- `data/processed/roster_mbc_join.json` (joined dataset with supplemental MBCs)

**Command Line Options:**
```bash
# Basic usage (auto-detects latest rosters)
python src/roster_processor.py

# Specify units
python src/roster_processor.py --units T32,T7012

# Custom roster directory
python src/roster_processor.py --roster-dir /path/to/rosters

# Use specific MBC data file
python src/roster_processor.py --mbc-data data/processed/mbc_counselors.json

# Use configuration file
python src/roster_processor.py --config config.json
```

**Auto-Detection Behavior:**
- **File Pattern**: Looks for files matching `{UNIT} Roster {DATE}.html`
- **Date Parsing**: Supports formats like `16Sep2025`, `2025-09-16`, `20250916`
- **Latest Selection**: Automatically chooses most recent file per unit
- **Unit Discovery**: Discovers available units from existing filenames

### Step 3: Report Generation

```bash
python src/report_generator.py
```

**What it does:**
- Loads joined data and applies exclusion list filtering
- **Combines unit members and supplemental MBCs** into unified reports
- Generates HTML reports with Eagle badge highlighting
- **Marks supplemental MBCs** with "(MBC-only)" indicator
- Creates PDF versions using Playwright's built-in PDF generation
- Uses consistent timestamp across all generated files

**Outputs Created:**
- `data/reports/T32_T7012_MBC_Reports_YYYYMMDD_HHMMSS/`
  - `T32_T7012_MBC_Troop_Counselors_YYYYMMDD_HHMMSS.html` + `.pdf`
  - `T32_T7012_MBC_Non_Counselors_YYYYMMDD_HHMMSS.html` + `.pdf`
  - `T32_T7012_MBC_Coverage_Report_YYYYMMDD_HHMMSS.html` + `.pdf`
  - `T32_T7012_MBC_Priority_Report_YYYYMMDD_HHMMSS.html` + `.pdf` (if priority analysis available)
  - `summary_report.json`

**Command Line Options:**
```bash
# Basic usage (uses default data file)
python src/report_generator.py

# Use specific data file
python src/report_generator.py --data-file path/to/data.json

# Use specific exclusion file
python src/report_generator.py --exclusion-file path/to/exclusions.txt

# Use specific priority analysis file
python src/report_generator.py --priority-file data/processed/coverage_priority_analysis_20251015_120000.json
```

### Step 4: Google Drive File Preparation

```bash
python src/prepare_gdrive_files.py
```

**What it does:**
- Auto-detects latest report directory
- Copies PDF files with standardized names
- Removes timestamps for consistent unit website linking
- Prepares files for manual drag-and-drop upload

**Outputs Created:**
- `data/gdrive/T32_T7012_MBC_Troop_Counselors.pdf`
- `data/gdrive/T32_T7012_MBC_Non_Counselors.pdf`
- `data/gdrive/T32_T7012_MBC_Coverage_Report.pdf`
- `data/gdrive/T32_T7012_MBC_Priority_Report.pdf` (if priority report was generated)

**Command Line Options:**
```bash
# Basic usage (finds latest report automatically)
python src/prepare_gdrive_files.py

# Specify custom reports directory
python src/prepare_gdrive_files.py --reports-dir /path/to/reports
```

**Manual Upload Process:**
1. Run the preparation script
2. Open `data/gdrive/` folder
3. Select all 3 PDF files
4. Drag and drop to [Google Drive folder](https://drive.google.com/drive/folders/1bC3_71dlmp0CvoDFisRpb-Y3WoKHvpiD)

## Error Handling and Troubleshooting

### Common Issues and Solutions

**🔥 "Network connectivity failed"**
- Check internet connection
- BeAScout.org may be temporarily unavailable
- Retry scraping after a few minutes

**🔥 "Roster File Not Found"**
- Verify roster files exist in `data/input/rosters/`
- Check filename matches pattern `{UNIT} Roster {DATE}.html`
- Use `--roster-dir` to specify custom directory
- Run with `--units` to see which units are detected

**🔥 "Missing MBC Data"**
- Ensure Step 1 (scraping) completed successfully
- Check `data/processed/mbc_counselors.json` exists
- Use `--mbc-data` to specify explicit file path

**🔥 "PDF Generation Fails"**
- Playwright browser may need reinstallation: `playwright install`
- Check system resources for large PDF generation
- Try HTML generation first to isolate PDF issues

**🔥 "Name Matching Issues"**
- Check roster file format (should be "text files" not HTML)
- Verify exclusion list format (one name per line)
- Review name matching logic in processing logs

**🔥 "Google Drive Prep Fails"**
- Ensure reporting stage completed successfully
- Check reports directory exists and contains PDFs
- Verify file permissions on output directories

### Pipeline-Specific Debugging

**Pipeline won't start:**
```bash
# Check working directory
pwd  # Should be in apps/mbc/

# Verify script exists
ls src/generate_mbc_reports.py

# Check Python environment
python --version  # Should be 3.11+
```

**Stage dependency failures:**
```bash
# Check what files exist
ls data/processed/
ls data/input/rosters/

# Run specific stage with explicit files
python src/generate_mbc_reports.py --stage processing
```

**File path issues:**
- Pipeline logs show exact arguments passed to each script
- Check log file: `data/logs/generate_mbc_reports_YYYYMMDD_HHMMSS.log`
- Look for "📄 Using explicit file" messages

### Data Quality Validation

**Verify MBC Data Quality:**
```bash
# Check number of counselors scraped
jq '.counselors | length' data/processed/mbc_counselors.json

# Check specific counselor
grep -i "will garnett" data/processed/mbc_counselors.json
```

**Verify Roster Processing:**
```bash
# Check join statistics
jq '.total_adults, .mbc_matches' data/processed/roster_mbc_join.json

# Find specific person in joined data
jq '.troop_counselors[] | select(.name | contains("Garnett"))' data/processed/roster_mbc_join.json
```

**Verify Report Generation:**
```bash
# Check latest report directory
ls -la data/reports/ | tail -1

# Verify all expected files exist
ls data/reports/T32_T7012_MBC_Reports_*/
```

## Data Flow Architecture

### 1. Data Extraction
- **Input**: ScoutBook counselor search results
- **Processing**: Browser automation with pagination handling
- **Output**: `data/processed/mbc_counselors.json`
- **Duration**: 15-30 minutes

### 2. Data Processing
- **Input**: MBC data + roster HTML files
- **Processing**: Name matching and troop affiliation tracking
- **Output**: `data/processed/roster_mbc_join.json`
- **Duration**: < 1 minute

### 3. Report Generation
- **Input**: Joined data + exclusion list + merit badge list
- **Processing**: HTML template rendering + PDF conversion
- **Output**: Timestamped report directory with HTML + PDF files
- **Duration**: < 1 minute

### 4. Google Drive Preparation
- **Input**: Latest report directory
- **Processing**: File copying with name standardization
- **Output**: `data/gdrive/` with standardized filenames
- **Duration**: < 5 seconds

## Performance Expectations

| Operation | Duration | Notes |
|-----------|----------|-------|
| Full Pipeline | 15-35 minutes | Mostly scraping time |
| Scraping Only | 15-30 minutes | Depends on ScoutBook response |
| Processing Only | < 1 minute | Fast roster/MBC join |
| Reporting Only | < 1 minute | HTML + PDF generation |
| Google Drive Prep | < 5 seconds | File copying only |

### File Size Expectations
- Scraped HTML: ~2-5MB total
- MBC JSON data: ~100-200KB
- Joined data: ~50-100KB
- PDF reports: ~200-500KB each
- HTML reports: ~10-50KB each

## Best Practices

### Regular Execution
- **Weekly runs** to keep MBC data current
- **After roster updates** when new adults join
- **Before committee meetings** for current reports

### Data Management
- **Archive old reports** periodically to save disk space
- **Keep exclusion list current** for privacy protection
- **Backup pipeline logs** for troubleshooting

### Quality Assurance
- **Review reports manually** before distribution
- **Verify MBC match counts** against expectations
- **Check exclusion list effectiveness** in generated reports
- **Validate name matching** for new counselors

## File Locations Reference

**Input Files:**
- Rosters: `data/input/rosters/`
- Exclusion list: `data/input/exclusion_list.txt`
- Supplemental MBCs: `data/input/unit_associated_mbcs.txt`
- Merit badges: `data/input/all_merit_badges.txt`

**Processing Files:**
- MBC data: `data/processed/mbc_counselors.json`
- Joined data: `data/processed/roster_mbc_join.json`
- Scout demand analysis: `data/processed/scout_demand_analysis_YYYYMMDD_HHMMSS.json`
- Coverage priority analysis: `data/processed/coverage_priority_analysis_YYYYMMDD_HHMMSS.json`

**Output Files:**
- Reports: `data/reports/T32_T7012_MBC_Reports_YYYYMMDD_HHMMSS/`
- Google Drive: `data/gdrive/`
- Logs: `data/logs/`

**Pipeline Status:**
- Execution logs: `data/logs/generate_mbc_reports_YYYYMMDD_HHMMSS.log`
- Status tracking: `data/logs/mbc_pipeline_status_YYYYMMDD_HHMMSS.json`

---

**Pipeline Version:** 1.0.0
**Last Updated:** September 22, 2025
**Next Enhancement:** Dynamic unit configuration (Issue #5)