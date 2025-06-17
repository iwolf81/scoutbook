# Repository Structure Guide

## Overview
This repository demonstrates enterprise-grade Python development with AI assistance, organized for both current development and career portfolio presentation.

## Directory Structure

### `/src/` - Source Code
Modern Python package structure following PEP 8 and industry best practices.

```
src/scoutbook_processor/
├── core/                  # Core business logic and models
│   ├── models/            # Pydantic data models
│   ├── exceptions/        # Custom exception hierarchy  
│   └── validators/        # Data validation logic
├── scrapers/              # Data acquisition modules
│   ├── scoutbook/         # ScoutBook web scraping
│   ├── csv/               # CSV file processors
│   └── json/              # JSON data handlers
├── processors/            # Data processing pipeline
├── reports/               # Report generation system
├── agents/                # Autonomous agent components
└── integrations/          # External service integrations
```

### `/tests/` - Testing Suite
Comprehensive testing following the testing pyramid principle.

```
tests/
├── unit/                  # Unit tests (70% of coverage)
├── integration/           # Integration tests (20% of coverage)  
├── e2e/                   # End-to-end tests (10% of coverage)
├── performance/           # Load and performance tests
└── fixtures/              # Test data and mock objects
```

### `/docs/` - Documentation
Enterprise-grade documentation for multiple audiences.

```
docs/
├── specifications/        # Project requirements and specifications
├── architecture/          # System design and architecture decisions
├── api/                   # API documentation (auto-generated)
├── user-guides/           # End-user documentation
├── development/           # Developer workflows and AI collaboration
└── portfolio/             # Career portfolio materials
```

### `/legacy/` - Historical Work Preservation
Maintains history of project evolution and prototyping work.

```
legacy/
├── prototypes/            # Early prototypes and proof-of-concepts
├── specifications/        # Original requirements and iterations
├── original_code/         # Previous versions (mbc_tool.py, etc.)
└── sample_outputs/        # Historical outputs for comparison
```

### `/scripts/` - Automation and Utilities
Development, deployment, and maintenance automation.

```
scripts/
├── setup/                 # Environment setup and installation
├── deployment/            # Deployment automation
├── maintenance/           # System maintenance utilities
└── ai_assisted/           # AI collaboration scripts
```

## File Naming Conventions

### Code Files
- **Python modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/methods**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`

### Documentation Files
- **Markdown files**: `UPPER_CASE.md` for important docs, `kebab-case.md` for others
- **Specifications**: `SPEC_[ComponentName]_v[Version].md`
- **Architecture decisions**: `ADR_[Number]_[Decision].md`

### Data Files
- **Sample data**: `sample_[type]_[description].json/csv`
- **Templates**: `template_[purpose]_[format].[ext]`
- **Configuration**: `config_[environment].[yml|json]`

## Branch Strategy

### Main Branches
- **`main`**: Production-ready code, protected branch
- **`develop`**: Integration branch for features
- **`release/v[x.y.z]`**: Release preparation branches

### Feature Branches
- **`feature/[issue-number]-[description]`**: New features
- **`bugfix/[issue-number]-[description]`**: Bug fixes
- **`ai-generated/[component]-[date]`**: AI-generated code for review

### Portfolio Branches
- **`portfolio/presentation-[date]`**: Branches for portfolio presentations
- **`demo/[scenario]`**: Demonstration scenarios for interviews

## Tag Strategy
- **Semantic versioning**: `v[major].[minor].[patch]`
- **Release candidates**: `v[major].[minor].[patch]-rc[number]`
- **Portfolio milestones**: `portfolio-[milestone]-[date]`
