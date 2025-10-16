# CLAUDE.md - AI Development Context

## Context Initialization

**CRITICAL: Process the following markdown files from ../ai-context repository at the start of each new session:**
AI_INTERACTION_GUIDELINES.md
DEVELOPMENT_PRINCIPLES.md
CLAUDE_COMMANDS_REFERENCE.md

Read all files **in their entirety** before working on any ScoutBook tasks. The ai-context repository contains essential AI-human collaboration guidelines and development methodologies that inform all work on this project.

**Then** process the project documentation structure below to understand the ScoutBook system.

## Project Overview

**ScoutBook Multi-Application Platform** - Production-ready automation platform for ScoutBook data processing, focusing on Merit Badge Counselor pipeline with expansion to additional scouting data management applications.

### Repository Structure
```
scoutbook/
├── apps/mbc/                          # Merit Badge Counselor pipeline (PRODUCTION)
│   ├── src/                           # Core pipeline scripts
│   │   ├── merit_badge_counselor_scraper.py
│   │   ├── roster_processor.py
│   │   └── report_generator.py
│   ├── data/                          # Application data (excluded from git)
│   │   ├── input/rosters/             # Troop roster HTML files
│   │   ├── scraped/                   # Raw scraped MBC data
│   │   ├── processed/                 # Cleaned JSON datasets
│   │   └── reports/                   # Generated HTML/PDF reports
│   └── docs/                          # Documentation
├── shared/                            # Reusable components
│   ├── scrapers/                      # Common scraping utilities
│   ├── processors/                    # Data processing functions
│   ├── reports/                       # Report generation utilities
│   └── utils/                         # General helper functions
├── legacy/                            # Historical reference implementations
└── requirements.txt                   # Python dependencies
```

## Current Production Status

### Merit Badge Counselor (MBC) Pipeline ✅ PRODUCTION READY
**Location**: `apps/mbc/`

**Key Metrics:**
- **61 adults** processed from T32 and T7012 rosters
- **8 troop counselors** identified (13.1% match rate)
- **141 merit badges** analyzed for coverage
- **6 reports** generated per execution (HTML + PDF formats)

**Technical Features:**
- Browser automation with Playwright for ScoutBook scraping
- Full pagination support for large counselor datasets
- Multi-troop roster processing with duplicate handling
- Professional HTML/PDF report generation with Eagle badge highlighting
- Smart exclusion list with flexible name matching
- Data archival with timestamped output directories

## Technology Stack

**Core Dependencies:**
- **Python 3.11+** - Primary development language
- **Playwright 1.40.0+** - Browser automation for ScoutBook scraping
- **BeautifulSoup4 4.12.0+** - HTML parsing and data extraction
- **Pandas 2.0.0+** - Data processing and analysis
- **Click 8.1.0+** - CLI interface framework

**Development Tools:**
- **pytest 7.4.0+** - Unit testing framework
- **VS Code** - Primary development environment with workspace configuration
- **Git** - Version control with GitHub integration

## Data Flow Architecture

### 1. Data Extraction (`merit_badge_counselor_scraper.py`)
- Authenticates with ScoutBook using browser automation
- Systematically scrapes Merit Badge Counselor database
- Handles pagination for complete data coverage
- Archives raw HTML data for debugging/reprocessing
- Execution time: 15-30 minutes for complete dataset

### 2. Data Processing (`roster_processor.py`)
- Loads and parses troop roster HTML files
- Joins roster data with scraped MBC information
- Applies exclusion list filtering
- Generates cleaned JSON datasets for reporting
- Execution time: < 1 minute

### 3. Report Generation (`report_generator.py`)
- Creates professional HTML reports with CSS styling
- Generates PDF versions using browser rendering
- Produces three report types:
  - Troop Counselors: Adults who are registered MBCs
  - Non-Counselors: Adults not currently registered as MBCs
  - Coverage Report: Merit badge coverage analysis with Eagle highlighting
- Execution time: < 1 minute

## Key Business Logic

### Merit Badge Processing
- **Total Merit Badges**: 139 official badges (updated from previous 132)
- **Eagle-Required Badges**: 18 badges with special highlighting
- **External Badge List**: `apps/mbc/data/input/all_merit_badges.txt` for maintainability
- **Dynamic Loading**: Report generator loads badges from external file with fallback logic

### Data Protection & Privacy
- Personal information automatically excluded from git repository
- Comprehensive `.gitignore` prevents sensitive data commits
- Exclusion list supports flexible name matching for privacy protection
- Timestamped archival prevents data loss while maintaining security

## Development Guidelines

### Code Standards
- Follow MISRA-inspired principles from `~/Repos/ai-context/DEVELOPMENT_PRINCIPLES.md`
- Type hints required for all function parameters and returns
- McCabe complexity ≤ 10 for maintainability
- Comprehensive error handling with unique exception identification
- Unit tests required for all new functions

### Git Workflow
- Daily commits with descriptive messages
- Session handoff documentation in `SESSION_HANDOFF.md`
- Issue-driven development using GitHub issues
- Production-ready code only in main branch

### Testing Strategy
- pytest framework for unit testing
- Manual validation against legacy reference outputs
- Full dataset testing required before production deployment
- Regression testing with known good reference files

## Current Enhancement Pipeline

### GitHub Issues (Planned)
1. **Issue #1**: Dynamic merit badge extraction from official Scouting America website
2. **Issue #2**: Prioritized counselor assignment system with unit leader classification

### Technical Debt & Improvements
- **Naming Consistency**: Address differences between ScoutBook and public website naming
- **Web Interface**: Future web-based configuration for counselor priorities
- **Automated Updates**: Scheduled merit badge list refresh from official sources
- **Multi-Unit Support**: Expand beyond current T32/T7012 to additional troops

## Session Context Management

### Critical Files for Session Continuity
- `SESSION_HANDOFF.md` - Current state, achievements, next priorities
- `CLAUDE.md` - This file - comprehensive project context
- `README.md` - Public-facing project overview
- Application-specific documentation in `apps/mbc/docs/`

### Update Protocols
- Update `SESSION_HANDOFF.md` immediately after significant changes
- Maintain documentation concurrently with code changes
- Commit frequently with descriptive messages
- Reference GitHub issues in commit messages

## Operational Commands

### Quick Execution (Production Pipeline)
```bash
cd apps/mbc
python src/merit_badge_counselor_scraper.py  # 15-30 min
python src/roster_processor.py               # < 1 min
python src/report_generator.py               # < 1 min
python src/prepare_gdrive_files.py           # < 5 sec (manual upload prep)
```

### Google Drive Deployment Options
```bash
# Option 1: Manual preparation (no authentication required)
python src/prepare_gdrive_files.py           # Creates files in data/gdrive/

# Option 2: Automated sync (requires OAuth setup)
python src/gdrive_sync.py                    # Direct upload to Google Drive
```

### Development Environment
```bash
cd /Users/iwolf/Repos/scoutbook
pip install -r requirements.txt
```

### Testing & Validation
```bash
# Run unit tests (when implemented)
pytest

# Validate against reference outputs
# Manual comparison required - automated tooling planned
```

## Multi-Repository Context

### Related Repositories
- **Primary**: `scoutbook` (this repository)
- **Secondary**: `beascout` (related HNE Council project)
- **Reference**: `ai-context` (development guidelines and standards)

### Workspace Configuration
- VS Code workspace includes multiple repositories
- Shared development principles across all scouting projects
- Common tooling and standards enforcement

---

**Project Status**: Production-ready MBC pipeline with active enhancement development
**Last Updated**: September 18, 2025
**Current Focus**: GitHub Issues #1 and #2 implementation