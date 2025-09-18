# ScoutBook Merit Badge Counselor Pipeline Execution Guide

## Overview
This pipeline extracts Merit Badge Counselor data from ScoutBook, processes troop rosters, joins the data, and generates comprehensive reports in both HTML and PDF formats.

## Pipeline Architecture
The pipeline consists of three main components that must be executed in sequence:

1. **Data Acquisition**: Scrape MBC data from ScoutBook website
2. **Data Processing**: Extract roster data and join with MBC data  
3. **Report Generation**: Create HTML and PDF reports with exclusion filtering

## Prerequisites
- Python 3.7+
- Playwright browser automation library
- Required roster HTML files in `data/input/rosters/`
- Internet connection for ScoutBook scraping
- ScoutBook account credentials for manual login

## Input Files

### Required Input Files
| File | Default Location | Description |
|------|------------------|-------------|
| Troop Rosters | `data/input/rosters/T32 Roster 16Sep2025.html` | T32 adult member roster |
| | `data/input/rosters/T7012 Roster 16Sep2025.html` | T7012 adult member roster |

### Optional Input Files
| File | Default Location | Description |
|------|------------------|-------------|
| Exclusion List | `data/input/exclusion_list.txt` | Names to exclude from all reports |

### Configuration Parameters
| Parameter | Default Value | Description |
|-----------|---------------|-------------|
| Search URL | `https://scoutbook.scouting.org/mobile/dashboard/admin/counselorresults.asp?UnitID=82190&MeritBadgeID=&formfname=&formlname=&zip=01720&formCouncilID=181&formDistrictID=430&Proximity=25&Availability=Available` | ScoutBook MBC search query |
| Proximity | 25 miles | Search radius from zip code 01720 |
| Browser Mode | Non-headless | Allows manual login without command-line credentials |

## Execution Steps

### Step 1: Merit Badge Counselor Scraping
```bash
cd /Users/iwolf/Repos/scoutbook/apps/mbc
python src/merit_badge_counselor_scraper.py
```

**What it does:**
- Opens browser in non-headless mode for manual login
- Navigates to ScoutBook MBC search results
- Extracts counselor data from all pages (auto-detects page count)
- Saves individual HTML pages and consolidated JSON data

**User Interaction Required:**
- Manual login to ScoutBook when browser opens
- Wait for "Press Enter after you've logged in..." prompt

**Outputs Created:**
- `data/scraped/mbc_search_YYYYMMDD_HHMMSS/` (timestamped directory)
  - `page_N.html` (one file per page, e.g., page_1.html, page_2.html, etc.)
  - `mbc_counselors_raw.json` (consolidated raw data)
- `data/processed/mbc_counselors_cleaned.json` (cleaned and processed data)

**Data Extracted Per Counselor:**
- Name (first_name, last_name, alt_first_name if available)
- Location (town, state, zip)
- Contact (phone, email)
- Merit badges certified for
- YPT (Youth Protection Training) expiration date

### Step 2: Roster Processing and Data Joining
```bash
python src/roster_processor.py
```

**What it does:**
- Extracts adult members from T32 and T7012 roster HTML files
- Excludes "Unit Participant" positions (18+ scouts, not adult leaders)
- Creates unified adult list with troop affiliations
- Joins roster data with MBC data using name matching logic
- Handles multi-troop affiliations for adults in both troops

**Name Matching Logic:**
- **MBC Key**: `((first_name) or (alt_first_name)) + (last_name)`
- **Roster Key**: `(first_name + last_name)` (ignoring middle names/initials)

**Outputs Created:**
- `data/processed/roster_mbc_join.json` (joined dataset)

**Data Structure:**
```json
{
  "troop_counselors": [...],     // Adults who are MBCs
  "non_counselor_leaders": [...], // Adults who are not MBCs  
  "total_adults": 61,
  "mbc_matches": 8
}
```

### Step 3: Report Generation
```bash
python src/report_generator.py
```

**What it does:**
- Loads joined data and applies exclusion list filtering
- Generates HTML reports with Eagle badge highlighting
- Creates PDF versions using Playwright's built-in PDF generation
- Uses consistent timestamp across all generated files

**Exclusion List Processing:**
- Reads `data/input/exclusion_list.txt` (optional)
- Supports comments with `#` prefix
- Uses smart name matching (ignores middle names/initials)
- Currently excludes: Herbert Philpott, Alison Barker

**Outputs Created:**

#### HTML Reports (in `data/reports/T32_T7012_MBC_YYYYMMDD_HHMMSS/html/`)
- `T32_T7012_MBC_Troop_Counselors_YYYYMMDD_HHMMSS.html`
- `T32_T7012_MBC_Non_Counselors_YYYYMMDD_HHMMSS.html`  
- `T32_T7012_MBC_Coverage_Report_YYYYMMDD_HHMMSS.html`

#### PDF Reports (in `data/reports/T32_T7012_MBC_YYYYMMDD_HHMMSS/pdf/`)
- `T32_T7012_MBC_Troop_Counselors_YYYYMMDD_HHMMSS.pdf`
- `T32_T7012_MBC_Non_Counselors_YYYYMMDD_HHMMSS.pdf`
- `T32_T7012_MBC_Coverage_Report_YYYYMMDD_HHMMSS.pdf`

## Report Contents

### 1. Troop Counselors Report
**Heading**: "T32/T7012 Troop Members who are Merit Badge Counselors"
- Lists adults from rosters who are also MBCs
- Shows troop affiliation(s) for each person
- Displays merit badges, contact info, YPT expiration
- Highlights Eagle-required merit badges with 🦅 symbol

### 2. Non-Counselors Report  
**Heading**: "T32/T7012 Troop Members who are NOT Merit Badge Counselors"
- Lists adults from rosters who are not MBCs
- Shows troop affiliation(s) for each person
- Provides recommendation to become MBC

### 3. Coverage Report
**Heading**: "T32/T7012 Merit Badge Coverage Analysis"
- **Total Merit Badges**: 132 badges analyzed
- **Four main sections**:
  1. **Eagle Merit Badges with T32/T7012 Counselors** (X badges)
  2. **Eagle Merit Badges without T32/T7012 Counselors** (Y badges)  
  3. **Non-Eagle Merit Badges with T32/T7012 Counselors** (Z badges)
  4. **Non-Eagle Merit Badges without T32/T7012 Counselors** (W badges)
- Lists counselors with troop numbers for each merit badge
- Matches legacy format exactly

## File Naming Convention
All generated files use the format:
`T32_T7012_MBC_<Report_Name>_YYYYMMDD_HHMMSS`

Where:
- `T32_T7012`: Abbreviated troop numbers from processed rosters
- `MBC`: Merit Badge Counselor identifier
- `<Report_Name>`: Capitalized report type (Troop_Counselors, Non_Counselors, Coverage_Report)
- `YYYYMMDD_HHMMSS`: Timestamp from when report generation started

## Temporary Files Created

### During Scraping
- Browser session files (automatically cleaned up)
- Network cache files (automatically cleaned up)

### During Processing  
- In-memory data structures (no temporary files)

### During Report Generation
- HTML template rendering (in-memory)
- PDF conversion buffers (in-memory)

## Error Handling

### Common Issues and Solutions

**1. Browser Login Timeout**
- Increase login timeout if needed
- Ensure stable internet connection
- Manually complete login when prompted

**2. Roster File Not Found**
- Verify roster files exist in `data/input/rosters/`
- Check exact filename matches expected format

**3. Missing MBC Data**
- Ensure Step 1 (scraping) completed successfully
- Check `data/processed/mbc_counselors_cleaned.json` exists

**4. PDF Generation Fails**
- Playwright browser may need reinstallation
- Check system resources for large PDF generation

## Data Quality Metrics

### Current Results (as of last run)
- **Total Adults in Rosters**: 61
- **Adults who are MBCs**: 8 (13.1%)
- **Adults who are not MBCs**: 53 (86.9%)
- **Merit Badge Coverage**: 132 total badges analyzed
- **Exclusions Applied**: 2 counselors pending removal

### Name Matching Accuracy
- Successfully matches names despite middle initials in rosters
- Handles alternate first names in MBC data
- Accounts for multi-troop affiliations

## Legacy Compatibility
This V2.0 pipeline generates reports that exactly match the legacy format found in:
`legacy/test_outputs/MBC_Reports_2025-06-04_14-51/`

Key improvements over legacy:
- Automated scraping (no manual HTML saving)
- Dynamic page detection (no hardcoded page limits)  
- Enhanced name matching logic
- PDF generation capability
- Exclusion list functionality
- Multi-troop affiliation support

## Complete Pipeline Execution
To run the entire pipeline from scratch:

```bash
# Step 1: Scrape current MBC data
python src/merit_badge_counselor_scraper.py

# Step 2: Process rosters and join data  
python src/roster_processor.py

# Step 3: Generate reports
python src/report_generator.py
```

**Total Execution Time**: ~15-30 minutes (depending on ScoutBook response times and number of pages)

**Manual Intervention Required**: Only during Step 1 for ScoutBook login

**Final Output**: Complete set of HTML and PDF reports ready for distribution

## Optional Step 4: Google Drive Sync (Production Deployment)

⚠️ **Note**: This step is only for production deployment to make reports available via unit website links.

### Prerequisites for Google Drive Sync
- Google Cloud Project with Drive API enabled
- Service account credentials OR OAuth credentials
- Credentials file saved as `credentials.json` in apps/mbc/ directory

### Installation of Google Drive Dependencies
```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

### Execution
```bash
python src/gdrive_sync.py
```

**What it does:**
- Finds the latest report directory (most recent timestamp)
- Uploads only PDF reports to Google Drive with standardized filenames
- Overwrites existing files for consistent unit website linking

**File Mapping:**
```
Local (timestamped)                                    → Google Drive (standardized)
T32_T7012_MBC_Troop_Counselors_YYYYMMDD_HHMMSS.pdf   → T32_T7012_MBC_Troop_Counselors.pdf
T32_T7012_MBC_Non_Counselors_YYYYMMDD_HHMMSS.pdf     → T32_T7012_MBC_Non_Counselors.pdf
T32_T7012_MBC_Coverage_Report_YYYYMMDD_HHMMSS.pdf    → T32_T7012_MBC_Coverage_Report.pdf
```

**Target Location**: [Unit MBC Reports Folder](https://drive.google.com/drive/folders/1bC3_71dlmp0CvoDFisRpb-Y3WoKHvpiD)

### Authentication Setup

#### Option 1: Service Account (Recommended for automation)
1. Create service account in Google Cloud Console
2. Download service account key as `credentials.json`
3. Share Google Drive folder with service account email

#### Option 2: OAuth (User authentication)
1. Create OAuth 2.0 credentials in Google Cloud Console
2. Download as `credentials.json`
3. First run will open browser for authorization
4. Token saved as `token.json` for future runs

### Safety Features
- **Manual execution only** - prevents accidental uploads during development
- **Separate script** - isolated from main pipeline to avoid interference
- **Error handling** - graceful failure if Google Drive unavailable
- **File verification** - validates files before upload

### Complete Production Workflow
```bash
# Run main pipeline
python src/merit_badge_counselor_scraper.py
python src/roster_processor.py
python src/report_generator.py

# Verify reports are correct, then deploy to Google Drive
python src/gdrive_sync.py
```

**Execution Time**: < 1 minute (for 3 PDF files)

**Manual Verification**: Always review generated reports before running Google Drive sync

### Alternative: Manual File Preparation (No Authentication Required)

For users who prefer manual upload control or cannot set up OAuth authentication:

```bash
python src/prepare_gdrive_files.py
```

**What it does:**
- Finds the latest report directory automatically
- Copies PDF files to `data/gdrive/` with standardized filenames
- Removes timestamps for consistent unit website linking
- Clears old files each run to avoid confusion

**Manual Upload Process:**
1. Run the preparation script
2. Open `data/gdrive/` folder
3. Select all 3 PDF files
4. Drag and drop to [Google Drive folder](https://drive.google.com/drive/folders/1bC3_71dlmp0CvoDFisRpb-Y3WoKHvpiD)

**File Mapping (Manual Process):**
```
Local (timestamped)                                    → data/gdrive/ (standardized)
T32_T7012_MBC_Troop_Counselors_YYYYMMDD_HHMMSS.pdf   → T32_T7012_MBC_Troop_Counselors.pdf
T32_T7012_MBC_Non_Counselors_YYYYMMDD_HHMMSS.pdf     → T32_T7012_MBC_Non_Counselors.pdf
T32_T7012_MBC_Coverage_Report_YYYYMMDD_HHMMSS.pdf    → T32_T7012_MBC_Coverage_Report.pdf
```

**Execution Time**: < 5 seconds (file preparation only)