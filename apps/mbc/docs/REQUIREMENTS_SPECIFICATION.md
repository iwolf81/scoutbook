# ScoutBook Merit Badge Counselor V2.0 Requirements Specification

## Project Overview
Create a V2.0 automated scraping and reporting system to replace manual HTML data collection for Merit Badge Counselor reports. The system must extract counselor data from ScoutBook website, process troop rosters, and generate comprehensive reports matching legacy format exactly.

## Target System
- **Primary URL**: `https://scoutbook.scouting.org/mobile/dashboard/admin/counselorresults.asp?UnitID=82190&MeritBadgeID=&formfname=&formlname=&zip=01720&formCouncilID=181&formDistrictID=430&Proximity=25&Availability=Available`
- **Search Parameters**: 25-mile radius from zip code 01720, all merit badges, available counselors only
- **Authentication**: Manual login required (no command-line credentials)
- **Data Source**: Troop 32 Acton ScoutBook unit dashboard

## Technical Requirements

### 1. Browser Automation Framework
- **Technology**: Playwright (replacing legacy Selenium)
- **Mode**: Non-headless browser for manual login
- **Timeout Settings**: 
  - Default operations: 60 seconds
  - Login operations: 30 seconds  
  - Page loads: 45 seconds
- **User Interaction**: Pause for manual login, resume automatically after user confirmation

### 2. Data Extraction Requirements

#### Merit Badge Counselor Data Structure
Extract the following fields for each counselor:
- **Name**: first_name, last_name, alt_first_name (if available)
- **Location**: town, state, zip
- **Contact**: phone, email  
- **Certification**: merit_badges (comma-separated list)
- **Training**: ypt_expiration (Youth Protection Training date)

#### HTML Parsing Specifications
- **Parser**: BeautifulSoup with 'html.parser'
- **Target Elements**: Counselor data in div containers
- **YPT Extraction**: Search parent containers for 'yptDate' class when not found in current div
- **Pagination**: Detect total pages from pageCount field, navigate using direct URLs with Page= parameter

### 3. Pagination Handling
- **Method**: Direct URL navigation (not button clicking)
- **Pattern**: `...&Page=N` where N increments from 1
- **Detection**: Auto-detect total pages from HTML pageCount field
- **Wait Strategy**: 'networkidle' for complete page loads

### 4. Data Archival Requirements
- **HTML Storage**: Save each page as individual HTML file in timestamped directory
- **Directory Structure**: `data/scraped/mbc_search_YYYYMMDD_HHMMSS/`
- **File Naming**: `page_N.html` where N is page number
- **Consolidated Output**: `mbc_counselors_raw.json` and `mbc_counselors_cleaned.json`
- **Timestamp Format**: `YYYYMMDD_HHMMSS` obtained at start of processing and used consistently

## Roster Processing Requirements

### 1. Input Files
- **Location**: `data/input/rosters/`
- **Files**: 
  - `T32 Roster 16Sep2025.html` (Troop 32)
  - `T7012 Roster 16Sep2025.html` (Troop 7012)

### 2. Adult Member Extraction
- **Target Section**: "Adult Members" section in HTML
- **Data Pattern**: `Number \t Name \t\t Address \t Gender \t Position`
- **Name Parsing**: Extract first word as first_name, last word as last_name (ignore middle names/initials)
- **Position Filtering**: Exclude "Unit Participant" positions (18+ scouts, not adult leaders)
- **Output**: Unified list with troop affiliations for multi-troop adults

### 3. Name Matching Logic
- **MBC Key**: `((first_name) or (alt_first_name)) + (last_name)`
- **Roster Key**: `(first_name + last_name)`
- **Matching Rule**: Ignore middle names and initials in both datasets

## Data Filtering Requirements

### 1. Exclusion List Support
- **Input File**: `data/input/exclusion_list.txt` (optional)
- **Format**: One name per line, comments supported with `#` prefix
- **Matching Logic**: Smart name matching ignoring middle names/initials
- **Required Exclusions**: Herbert Philpott, Alison Barker

### 2. Data Cleanup
- Remove counselors pending removal and those with pending removal forms
- Apply exclusions to all generated reports
- Maintain data integrity while filtering

## Report Generation Requirements

### 1. Output Formats
- **HTML Reports**: Professional styling with Eagle badge highlighting
- **PDF Reports**: Full-color PDFs using Playwright's built-in PDF generation
- **File Organization**: Separate html/ and pdf/ subdirectories

### 2. Report Types

#### A. Troop Counselors Report
- **Title**: "T32/T7012 Troop Members who are Merit Badge Counselors"
- **Content**: Adults from rosters who are also MBCs
- **Data**: Troop affiliations, merit badges, contact info, YPT expiration
- **Highlighting**: Eagle-required merit badges with 🦅 symbol

#### B. Non-Counselors Report  
- **Title**: "T32/T7012 Troop Members who are NOT Merit Badge Counselors"
- **Content**: Adults from rosters who are not MBCs
- **Recommendation**: Suggest becoming MBC

#### C. Coverage Report
- **Title**: "T32/T7012 Merit Badge Coverage Analysis"
- **Structure**: Four sections matching legacy format exactly:
  1. Eagle Merit Badges with T32/T7012 Counselors
  2. Eagle Merit Badges without T32/T7012 Counselors  
  3. Non-Eagle Merit Badges with T32/T7012 Counselors
  4. Non-Eagle Merit Badges without T32/T7012 Counselors
- **Merit Badge Universe**: Complete list of 139 current merit badges
- **Counselor Listing**: Show counselors with troop numbers for each badge

### 3. File Naming Convention
**Pattern**: `T32_T7012_MBC_<Report_Name>_YYYYMMDD_HHMMSS`
- **Troop Prefix**: Abbreviated troop numbers (T32, T7012)
- **Report Names**: Troop_Counselors, Non_Counselors, Coverage_Report
- **Timestamp**: Same timestamp for all files in single execution

## Implementation Architecture

### 1. Component Structure
```
apps/mbc/src/
├── merit_badge_counselor_scraper.py  # Browser automation and data extraction
├── roster_processor.py               # Roster parsing and data joining
└── report_generator.py               # HTML/PDF report generation
```

### 2. Execution Sequence
1. **Scraping**: Extract MBC data from ScoutBook with pagination
2. **Processing**: Join roster data with MBC data  
3. **Reporting**: Generate HTML and PDF reports with exclusions

### 3. Data Flow
```
ScoutBook Website → HTML Pages → JSON Data → Roster Join → Filtered Reports
```

## Legacy Compatibility Requirements

### 1. Format Matching
- **Reference**: `legacy/test_outputs/MBC_Reports_2025-06-04_14-51/`
- **Styling**: Match HTML structure and CSS exactly
- **Content**: Identical data presentation and organization
- **Merit Badge List**: Use complete 132-badge universe from legacy code

### 2. Data Validation
- **Cross-Reference**: Compare output with legacy reports
- **Quality Metrics**: Validate counselor counts and merit badge coverage
- **Multi-Troop Handling**: Properly display multiple troop affiliations

## Performance and Reliability Requirements

### 1. Scraping Performance
- **Rate Limiting**: Respect ScoutBook's slow response times
- **Error Handling**: Robust timeout and retry logic
- **Resource Management**: Proper browser cleanup and memory management

### 2. Data Processing
- **Memory Efficiency**: Handle large datasets in memory
- **JSON Serialization**: Convert sets to lists for proper JSON output
- **File I/O**: Efficient reading/writing of HTML and JSON files

## Quality Assurance Requirements

### 1. Data Validation
- **Name Matching**: Verify joins between roster and MBC data
- **Completeness**: Ensure all pages scraped and all adults processed
- **Accuracy**: Validate merit badge counts and counselor listings

### 2. Output Verification
- **Report Content**: Verify all expected sections and data present
- **File Generation**: Confirm both HTML and PDF versions created
- **Exclusion Application**: Verify excluded names removed from all reports

## Success Criteria

### 1. Functional Requirements ✅ COMPLETED
- ✅ Extract all counselor data from ScoutBook with full pagination
- ✅ Process both troop rosters and exclude Unit Participants
- ✅ Successfully join roster and MBC data with 13.1% match rate
- ✅ Generate three report types in both HTML and PDF formats
- ✅ Apply exclusion list filtering to all outputs
- ✅ Professional report formatting with Eagle badge highlighting

### 2. Performance Metrics ✅ ACHIEVED
- **Total Adults Processed**: 61 from both rosters
- **MBC Matches Found**: 8 counselors (13.1% of adults)
- **Merit Badge Coverage**: 139 badges analyzed
- **Execution Time**: 15-30 minutes including manual login
- **File Output**: 6 files generated per execution (3 HTML + 3 PDF)
- **Data Processing**: JSON files with cleaned and joined data

### 3. Quality Indicators ✅ VALIDATED
- **Name Matching Accuracy**: Handles middle initials and alternate names
- **Multi-Troop Support**: Properly tracks adults in multiple troops
- **Data Integrity**: Consistent timestamps and exclusion application
- **Professional Formatting**: Clean, readable reports with consistent styling
- **Eagle Badge Highlighting**: 🦅 symbols correctly applied to Eagle-required badges

## Development Guidelines

### 1. Code Organization
- **Modular Design**: Separate scraping, processing, and reporting components
- **Error Handling**: Comprehensive try-catch blocks with informative messages
- **Logging**: Progress indicators and status messages throughout execution
- **Documentation**: Clear docstrings and inline comments

### 2. Maintainability
- **Configuration**: Externalize key parameters (URLs, timeouts, file paths)
- **Extensibility**: Design for easy addition of new troops or report types
- **Testing**: Structure for unit testing of individual components
- **Version Control**: Clear commit messages documenting each enhancement

## Implementation Status: ✅ COMPLETE

The ScoutBook Merit Badge Counselor V2.0 system has been successfully implemented and tested. All requirements have been met, producing professional reports with full automation of the previously manual process.

### Current Deployment
- **Production Ready**: All three pipeline components operational
- **Tested Output**: Reports generated and validated with real data
- **Data Protection**: Personal information excluded from repository via .gitignore
- **Documentation**: Complete execution guide and technical specifications available