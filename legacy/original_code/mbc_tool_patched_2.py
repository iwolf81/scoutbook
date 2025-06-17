"""
Merit Badge Counselor Lists Tool
Generates reports for Scout Troops 12 and 32 in Acton, MA

This tool processes troop rosters and merit badge counselor data to generate
comprehensive reports for tracking merit badge coverage and counselor availability.
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import PyPDF2

# Version info
__version__ = "1.0.0"
__author__ = "Merit Badge Counselor Lists Tool"

class MBCToolError(Exception):
    """Base exception for MBC Tool errors"""
    pass

class InputValidationError(MBCToolError):
    """Raised when input validation fails"""
    pass

class DataProcessingError(MBCToolError):
    """Raised when data processing fails"""
    pass

class Config:
    """Configuration settings for the MBC Tool"""
    
    # Default URLs
    ALL_MERIT_BADGES_URL = "https://www.scouting.org/skills/merit-badges/all/"
    EAGLE_REQUIRED_URL = "https://www.scouting.org/skills/merit-badges/eagle-required/"
    
    # File settings
    MAX_FILE_SIZE_MB = 100
    TIMEOUT_SECONDS = 30
    
    # Output settings
    OUTPUT_TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M"
    
    # Required CSV columns
    REQUIRED_CSV_COLUMNS = {
        'firstname', 'lastname', 'positionname', 'primaryemail', 'primaryphone'
    }
    
    def __init__(self, config_file: Optional[str] = None):
        if config_file and os.path.exists(config_file):
            self.load_from_file(config_file)
    
    def load_from_file(self, config_file: str):
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
                for key, value in config_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
        except Exception as e:
            logging.warning(f"Could not load config file {config_file}: {e}")

class ProgressTracker:
    """Tracks and displays progress for long-running operations"""
    
    def __init__(self, total_steps: int, description: str = "Processing"):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.start_time = datetime.now()
    
    def update(self, step_name: str, increment: int = 1):
        """Update progress and log current step"""
        self.current_step += increment
        percentage = (self.current_step / self.total_steps) * 100
        elapsed = datetime.now() - self.start_time
        
        logging.info(f"Progress: {percentage:.1f}% - {step_name}")
        if self.current_step < self.total_steps:
            eta_seconds = (elapsed.total_seconds() / self.current_step) * (self.total_steps - self.current_step)
            eta = f"ETA: {int(eta_seconds//60)}m {int(eta_seconds%60)}s"
            print(f"\r{self.description}: {percentage:.1f}% - {step_name} ({eta})", end="", flush=True)
        else:
            print(f"\r{self.description}: Complete! Total time: {elapsed}", flush=True)

class DataValidator:
    """Validates input data and files"""
    
    @staticmethod
    def validate_csv_file(file_path: str, config: Config) -> bool:
        """Validate CSV file format and required columns"""
        try:
            print(f"DEBUG: *** USING NEW FIXED VERSION OF CSV VALIDATION ***")
            print(f"DEBUG: Starting validation of {file_path}")
            logging.debug(f"Starting CSV validation for: {file_path}")
            
            # Check file existence first
            if not os.path.exists(file_path):
                raise InputValidationError(f"File does not exist: {file_path}")
            
            print(f"DEBUG: File exists, checking size...")
            
            # Check file size
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > config.MAX_FILE_SIZE_MB:
                raise InputValidationError(f"CSV file too large: {file_size_mb:.1f}MB > {config.MAX_FILE_SIZE_MB}MB")
            
            print(f"DEBUG: File size OK ({file_size_mb:.1f}MB), trying to read...")
            
            # Try to detect encoding
            encodings_to_try = ['utf-8', 'windows-1252', 'iso-8859-1']
            content = None
            
            for encoding in encodings_to_try:
                try:
                    print(f"DEBUG: Trying encoding {encoding}...")
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    logging.debug(f"Successfully read CSV with {encoding} encoding")
                    print(f"DEBUG: Successfully read with {encoding}")
                    break
                except UnicodeDecodeError as e:
                    print(f"DEBUG: Failed with {encoding}: {e}")
                    continue
            
            if content is None:
                raise InputValidationError(f"Could not decode CSV file with any supported encoding")
            
            print(f"DEBUG: File read successfully, content length: {len(content)}")
            print(f"DEBUG: First 200 chars: {repr(content[:200])}")
            
            print(f"DEBUG: Starting header detection...")
            
            # Find header line starting with "..memberid" or containing "memberid"
            lines = content.split('\n')
            header_line = None
            header_index = -1
            
            print(f"DEBUG: Split into {len(lines)} lines")
            print(f"DEBUG: First line: {repr(lines[0])}")
            
            logging.debug(f"CSV validation - file has {len(lines)} lines")
            logging.debug(f"First 3 lines of CSV:")
            for i, line in enumerate(lines[:3]):
                logging.debug(f"  Line {i}: '{line[:100]}...' (length: {len(line)})")
            
            print(f"DEBUG: About to start line-by-line checking...")
            
            for i, line in enumerate(lines):
                line_lower = line.lower()
                starts_with_memberid = line.strip().startswith('..memberid')
                contains_memberid = 'memberid' in line_lower
                
                print(f"DEBUG: Line {i}: starts_with='..memberid'? {starts_with_memberid}, contains 'memberid'? {contains_memberid}")
                logging.debug(f"Line {i}: starts with '..memberid'? {starts_with_memberid}, contains 'memberid'? {contains_memberid}")
                
                # Look for line starting with "..memberid" or containing "memberid"
                if starts_with_memberid or contains_memberid:
                    header_line = line
                    header_index = i
                    print(f"DEBUG: FOUND header line at index {i}")
                    logging.debug(f"FOUND header line at index {i}: '{line}'")
                    break
            
            print(f"DEBUG: Header detection complete. Found header? {header_line is not None}")
            
            if header_line is None:
                print("DEBUG: No header found - this should not happen!")
                logging.error("VALIDATION FAILED - Could not find header line!")
                logging.error("All lines in file:")
                for i, line in enumerate(lines[:10]):  # Show first 10 lines
                    logging.error(f"  Line {i}: '{repr(line)}'")  # Use repr to show hidden chars
                raise InputValidationError("Could not find header line containing 'memberid' or starting with '..memberid'")
            
            print(f"DEBUG: Header found, proceeding with delimiter detection...")
            
            # Detect delimiter (comma, space, or tab)
            delimiter = ','
            if ',' not in header_line:
                if '\t' in header_line:
                    delimiter = '\t'
                elif ' ' in header_line:
                    delimiter = ' '
            
            logging.debug(f"Detected delimiter: '{delimiter}'")
            print(f"DEBUG: Detected delimiter: '{delimiter}'")
            
            # Parse headers manually - NO csv.DictReader!
            print(f"DEBUG: About to parse headers with delimiter '{delimiter}'")
            if delimiter == ' ':
                # For space-delimited, split on whitespace
                headers = header_line.strip().split()
                print(f"DEBUG: Space-delimited parsing complete")
            else:
                # For comma or tab delimited, split manually
                headers = [h.strip() for h in header_line.split(delimiter)]
                print(f"DEBUG: Manual split parsing complete")
            
            print(f"DEBUG: Successfully parsed {len(headers)} headers")
            print(f"DEBUG: First 5 headers: {headers[:5] if len(headers) >= 5 else headers}")
            logging.debug(f"Parsed headers: {headers}")
            
            headers_set = {h.lower().strip() for h in headers}
            print(f"DEBUG: Converted to lowercase set: {len(headers_set)} unique headers")
            
            # Check required columns (convert ..memberid to memberid for comparison)
            normalized_headers = {h.replace('..', '') for h in headers_set}
            print(f"DEBUG: Normalized headers (removed ..): {len(normalized_headers)} headers")
            print(f"DEBUG: Required columns: {config.REQUIRED_CSV_COLUMNS}")
            
            missing_columns = config.REQUIRED_CSV_COLUMNS - normalized_headers
            print(f"DEBUG: Missing columns check: {missing_columns}")
            
            if missing_columns:
                raise InputValidationError(f"Missing required columns: {missing_columns}")
            
            logging.info(f"CSV validation passed for {file_path}")
            logging.debug(f"Found headers: {sorted(headers_set)}")
            print(f"DEBUG: CSV validation completed successfully!")
            return True
            
        except Exception as e:
            print(f"DEBUG: CSV validation failed with error: {e}")
            logging.error(f"CSV validation error: {e}")
            raise InputValidationError(f"CSV validation failed for {file_path}: {e}")
    
    @staticmethod
    def validate_pdf_files(pdf_paths: List[str], config: Config) -> bool:
        """Validate PDF files can be processed"""
        for pdf_path in pdf_paths:
            try:
                # Check file size
                file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
                if file_size_mb > config.MAX_FILE_SIZE_MB:
                    raise InputValidationError(f"PDF file too large: {file_size_mb:.1f}MB > {config.MAX_FILE_SIZE_MB}MB")
                
                # Try to open and read PDF
                with open(pdf_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    
                    # Check if encrypted
                    if pdf_reader.is_encrypted:
                        raise InputValidationError(f"PDF file is password protected: {pdf_path}")
                    
                    # Try to extract text from first page
                    if len(pdf_reader.pages) == 0:
                        raise InputValidationError(f"PDF file has no pages: {pdf_path}")
                    
                    first_page_text = pdf_reader.pages[0].extract_text()
                    if not first_page_text.strip():
                        raise InputValidationError(f"PDF appears to be image-based (no extractable text): {pdf_path}")
                    
                    logging.debug(f"PDF validation passed for {pdf_path}")
                    
            except Exception as e:
                raise InputValidationError(f"PDF validation failed for {pdf_path}: {e}")
        
        logging.info(f"All {len(pdf_paths)} PDF files validated successfully")
        return True
    
    @staticmethod
    def check_web_connectivity(config: Config) -> bool:
        """Check if scouting.org is accessible"""
        try:
            response = requests.get(config.ALL_MERIT_BADGES_URL, timeout=config.TIMEOUT_SECONDS)
            response.raise_for_status()
            logging.info("Web connectivity check passed")
            return True
        except Exception as e:
            raise InputValidationError(f"Cannot access scouting.org: {e}")

class MeritBadgeDataFetcher:
    """Fetches current merit badge data from scouting.org"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Merit Badge Counselor Lists Tool)'
        })
    
    def fetch_all_merit_badges(self) -> List[str]:
        """Fetch list of all merit badges from scouting.org"""
        try:
            logging.info("Fetching all merit badges from scouting.org...")
            response = self.session.get(self.config.ALL_MERIT_BADGES_URL, timeout=self.config.TIMEOUT_SECONDS)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the "Merit Badges A-Z" section
            merit_badges = []
            found_az_section = False
            
            # Look for headings that contain "Merit Badges A-Z"
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                if 'merit badges a-z' in heading.get_text().lower():
                    found_az_section = True
                    break
            
            if not found_az_section:
                # Fallback: look for any section with merit badge links
                logging.warning("Could not find 'Merit Badges A-Z' heading, using fallback method")
            
            # Extract merit badge names from links
            for link in soup.find_all('a', href=True):
                try:
                    href = getattr(link, 'href', '') or ''
                    if href and '/skills/merit-badges/' in href and href != self.config.ALL_MERIT_BADGES_URL:
                        badge_name = link.get_text().strip()
                        if badge_name and badge_name not in merit_badges:
                            # Skip generic navigation links
                            if badge_name.lower() not in ['merit badges', 'all', 'eagle-required', 'requirements update']:
                                merit_badges.append(badge_name)
                except (AttributeError, TypeError):
                    continue
            
            # Sort alphabetically
            merit_badges.sort()
            
            logging.info(f"Fetched {len(merit_badges)} merit badges")
            logging.debug(f"Merit badges: {merit_badges[:10]}..." if len(merit_badges) > 10 else f"Merit badges: {merit_badges}")
            
            return merit_badges
            
        except Exception as e:
            raise DataProcessingError(f"Failed to fetch merit badges: {e}")
    
    def fetch_eagle_required_badges(self) -> List[str]:
        """Fetch list of Eagle-required merit badges from scouting.org"""
        try:
            logging.info("Fetching Eagle-required merit badges from scouting.org...")
            response = self.session.get(self.config.EAGLE_REQUIRED_URL, timeout=self.config.TIMEOUT_SECONDS)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            eagle_badges = []
            
            # Extract merit badge names from links in the Eagle-required page
            for link in soup.find_all('a', href=True):
                try:
                    href = getattr(link, 'href', '') or ''
                    if href and '/skills/merit-badges/' in href and '/eagle-required/' not in href:
                        badge_name = link.get_text().strip()
                        if badge_name and badge_name not in eagle_badges:
                            # Skip generic navigation links
                            if badge_name.lower() not in ['merit badges', 'all', 'eagle-required']:
                                eagle_badges.append(badge_name)
                except (AttributeError, TypeError):
                    continue
            
            # Sort alphabetically
            eagle_badges.sort()
            
            logging.info(f"Fetched {len(eagle_badges)} Eagle-required merit badges")
            logging.debug(f"Eagle-required badges: {eagle_badges}")
            
            return eagle_badges
            
        except Exception as e:
            raise DataProcessingError(f"Failed to fetch Eagle-required merit badges: {e}")

class RosterProcessor:
    """Processes troop roster CSV files"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def process_roster(self, csv_path: str, troop_number: str) -> Dict:
        """Process a single roster CSV file"""
        try:
            logging.info(f"Processing roster for Troop {troop_number}: {csv_path}")
            
            # Detect encoding
            encodings_to_try = ['utf-8', 'windows-1252', 'iso-8859-1']
            content = None
            
            for encoding in encodings_to_try:
                try:
                    with open(csv_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                raise DataProcessingError(f"Could not decode roster file: {csv_path}")
            
            # Find header line
            lines = content.split('\n')
            header_line = None
            data_start_index = -1
            
            for i, line in enumerate(lines):
                # Look for line starting with "..memberid" or containing "memberid"
                if line.strip().startswith('..memberid') or 'memberid' in line.lower():
                    header_line = line
                    data_start_index = i
                    break
            
            if header_line is None:
                raise DataProcessingError(f"Could not find header line in roster: {csv_path}")
            
            logging.debug(f"Found header at line {data_start_index + 1}: {header_line[:100]}...")
            
            # Detect delimiter (comma, space, or tab)
            delimiter = ','
            if ',' not in header_line:
                if '\t' in header_line:
                    delimiter = '\t'
                elif ' ' in header_line:
                    delimiter = ' '
            
            logging.debug(f"Using delimiter: '{delimiter}'")
            
            # Parse headers manually - NO csv.DictReader
            if delimiter == ' ':
                headers = header_line.strip().split()
            else:
                headers = [h.strip() for h in header_line.split(delimiter)]
            
            # Process data rows manually - NO csv.DictReader
            registered_adults = []
            youth_members = []
            
            for row_num, line in enumerate(lines[data_start_index + 1:], start=data_start_index + 2):
                if not line.strip():
                    continue
                
                # Split line based on delimiter
                if delimiter == ' ':
                    values = line.strip().split()
                else:
                    values = [v.strip() for v in line.split(delimiter)]
                
                # Ensure we have the right number of values
                if len(values) < len(headers):
                    values.extend([''] * (len(headers) - len(values)))
                elif len(values) > len(headers):
                    values = values[:len(headers)]
                
                # Create row dictionary manually
                row = dict(zip(headers, values))
                
                try:
                    # Extract and clean data
                    first_name = row.get('firstname', '').strip()
                    last_name = row.get('lastname', '').strip()
                    position = row.get('positionname', '').strip()
                    email = row.get('primaryemail', '').strip()
                    phone = row.get('primaryphone', '').strip()
                    
                    if not first_name or not last_name:
                        logging.debug(f"Skipping row {row_num} - missing name")
                        continue
                    
                    person_data = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'position': position,
                        'email': email,
                        'phone': phone,
                        'troop': troop_number
                    }
                    
                    # Debug logging for each processed row
                    logging.debug(f"Row {row_num}: {first_name} {last_name} - {position}")
                    
                    # Categorize as youth member or registered adult
                    if 'youth member' in position.lower():
                        youth_members.append(person_data)
                    else:
                        registered_adults.append(person_data)
                        
                except Exception as e:
                    logging.warning(f"Error processing row {row_num} in {csv_path}: {e}")
                    continue
            
            result = {
                'troop': troop_number,
                'registered_adults': registered_adults,
                'youth_members': youth_members,
                'total_members': len(registered_adults) + len(youth_members)
            }
            
            logging.info(f"Processed Troop {troop_number}: {len(registered_adults)} adults, {len(youth_members)} youth")
            
            return result
            
        except Exception as e:
            raise DataProcessingError(f"Failed to process roster {csv_path}: {e}")

class PDFProcessor:
    """Processes Merit Badge Counselor PDF files"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def extract_counselor_data(self, pdf_paths: List[str]) -> List[Dict]:
        """Extract merit badge counselor data from PDF files"""
        try:
            logging.info(f"Processing {len(pdf_paths)} PDF files for merit badge counselor data...")
            
            all_counselors = []
            
            for pdf_path in pdf_paths:
                logging.info(f"Processing PDF: {pdf_path}")
                counselors = self._process_single_pdf(pdf_path)
                all_counselors.extend(counselors)
                logging.info(f"Extracted {len(counselors)} counselors from {pdf_path}")
            
            # Remove duplicates based on name and contact info
            unique_counselors = self._deduplicate_counselors(all_counselors)
            
            logging.info(f"Total unique merit badge counselors: {len(unique_counselors)}")
            
            return unique_counselors
            
        except Exception as e:
            raise DataProcessingError(f"Failed to extract counselor data: {e}")
    
    def _process_single_pdf(self, pdf_path: str) -> List[Dict]:
        """Process a single PDF file and extract counselor data"""
        counselors = []
        
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                full_text = ""
                for page in pdf_reader.pages:
                    full_text += page.extract_text() + "\n"
                
                # Parse the text to extract counselor information
                counselors = self._parse_counselor_text(full_text)
                
        except Exception as e:
            logging.error(f"Error processing PDF {pdf_path}: {e}")
            raise DataProcessingError(f"Failed to process PDF {pdf_path}: {e}")
        
        return counselors
    
    def _parse_counselor_text(self, text: str) -> List[Dict]:
        """Parse extracted text to find counselor information"""
        counselors = []
        
        # This is a simplified parser - in practice, you'd need to analyze 
        # the actual PDF format from ScoutBook to create proper parsing rules
        lines = text.split('\n')
        
        current_counselor = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Debug logging for each line processed
            logging.debug(f"Processing line: {line[:100]}...")
            
            # Look for patterns that indicate counselor data
            # This is a placeholder implementation - you'll need to adjust
            # based on actual ScoutBook PDF format
            
            # Example patterns to look for:
            # - Names (first line of counselor entry)
            # - Phone numbers (###-###-####)
            # - Email addresses (contains @)
            # - Merit badge lists
            
            # Phone pattern
            phone_match = re.search(r'(\d{3}[-.]?\d{3}[-.]?\d{4})', line)
            if phone_match:
                if 'phones' not in current_counselor:
                    current_counselor['phones'] = []
                current_counselor['phones'].append(phone_match.group(1))
            
            # Email pattern
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', line)
            if email_match:
                current_counselor['email'] = email_match.group(1)
            
            # This is a simplified implementation
            # In practice, you'd need to analyze the actual PDF structure
            # from ScoutBook to create proper parsing rules
        
        # Add any completed counselor
        if current_counselor:
            counselors.append(current_counselor)
        
        logging.warning("PDF parsing is using simplified implementation - needs actual ScoutBook PDF format analysis")
        
        return counselors
    
    def _deduplicate_counselors(self, counselors: List[Dict]) -> List[Dict]:
        """Remove duplicate counselors based on name and contact info"""
        seen = set()
        unique_counselors = []
        
        for counselor in counselors:
            # Create a key based on name and primary contact info
            key = (
                counselor.get('first_name', '').lower(),
                counselor.get('last_name', '').lower(),
                counselor.get('email', '').lower()
            )
            
            if key not in seen and any(key):  # Ensure we have some identifying info
                seen.add(key)
                unique_counselors.append(counselor)
        
        return unique_counselors

class ReportGenerator:
    """Generates various reports and output formats"""
    
    def __init__(self, config: Config):
        self.config = config
        self.generation_time = datetime.now()
    
    def generate_all_reports(self, data: Dict, output_dir: str) -> Dict[str, str]:
        """Generate all required reports in specified formats"""
        try:
            logging.info("Generating reports...")
            
            # Create output directory structure
            os.makedirs(output_dir, exist_ok=True)
            html_dir = os.path.join(output_dir, 'html')
            os.makedirs(html_dir, exist_ok=True)
            
            # Generate the three main reports
            reports = {}
            
            # 1. T12/T32 Merit Badge Counselors
            counselors_report = self._generate_counselors_report(data)
            reports['counselors'] = self._generate_html_report(
                counselors_report, 
                "T12/T32 Merit Badge Counselors",
                os.path.join(html_dir, 'troop_counselors.html')
            )
            
            # 2. T12/T32 Leaders not Merit Badge Counselors
            non_counselors_report = self._generate_non_counselors_report(data)
            reports['non_counselors'] = self._generate_html_report(
                non_counselors_report,
                "T12/T32 Leaders not Merit Badge Counselors", 
                os.path.join(html_dir, 'leaders_not_counselors.html')
            )
            
            # 3. T12/T32 Merit Badge Counselor Coverage
            coverage_report = self._generate_coverage_report(data)
            reports['coverage'] = self._generate_html_report(
                coverage_report,
                "T12/T32 Merit Badge Counselor Coverage",
                os.path.join(html_dir, 'merit_badge_coverage.html')
            )
            
            # Generate summary report
            summary = self._generate_summary_report(data, reports)
            summary_path = os.path.join(output_dir, 'summary_report.html')
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(summary)
            
            logging.info(f"All reports generated successfully in {output_dir}")
            
            return {
                'summary': summary_path,
                'counselors': reports['counselors'],
                'non_counselors': reports['non_counselors'], 
                'coverage': reports['coverage']
            }
            
        except Exception as e:
            raise DataProcessingError(f"Failed to generate reports: {e}")
    
    def _generate_counselors_report(self, data: Dict) -> Dict:
        """Generate T12/T32 Merit Badge Counselors report data"""
        counselors = []
        
        # Cross-reference rosters with merit badge counselors
        all_adults = []
        if 't12_roster' in data:
            all_adults.extend(data['t12_roster']['registered_adults'])
        if 't32_roster' in data:
            all_adults.extend(data['t32_roster']['registered_adults'])
        
        mbc_list = data.get('merit_badge_counselors', [])
        
        for adult in all_adults:
            # Try to match with merit badge counselors
            for mbc in mbc_list:
                if self._names_match(adult, mbc):
                    counselor_info = {
                        'first_name': adult['first_name'],
                        'last_name': adult['last_name'],
                        'position': adult['position'],
                        'troop': adult['troop'],
                        'email': adult['email'],
                        'phone': adult['phone'],
                        'merit_badges': mbc.get('merit_badges', [])
                    }
                    counselors.append(counselor_info)
                    break
        
        return {
            'title': 'T12/T32 Merit Badge Counselors',
            'data': counselors,
            'count': len(counselors)
        }
    
    def _generate_non_counselors_report(self, data: Dict) -> Dict:
        """Generate T12/T32 Leaders not Merit Badge Counselors report data"""
        non_counselors = []
        
        # Get all adults from rosters
        all_adults = []
        if 't12_roster' in data:
            all_adults.extend(data['t12_roster']['registered_adults'])
        if 't32_roster' in data:
            all_adults.extend(data['t32_roster']['registered_adults'])
        
        mbc_list = data.get('merit_badge_counselors', [])
        
        for adult in all_adults:
            # Check if they are NOT a merit badge counselor
            is_counselor = False
            for mbc in mbc_list:
                if self._names_match(adult, mbc):
                    is_counselor = True
                    break
            
            if not is_counselor:
                non_counselors.append({
                    'first_name': adult['first_name'],
                    'last_name': adult['last_name'],
                    'position': adult['position'],
                    'troop': adult['troop'],
                    'email': adult['email'],
                    'phone': adult['phone']
                })
        
        return {
            'title': 'T12/T32 Leaders not Merit Badge Counselors',
            'data': non_counselors,
            'count': len(non_counselors)
        }
    
    def _generate_coverage_report(self, data: Dict) -> Dict:
        """Generate T12/T32 Merit Badge Counselor Coverage report data"""
        all_badges = data.get('all_merit_badges', [])
        eagle_badges = data.get('eagle_required_badges', [])
        
        # Get T12/T32 counselors and their badges
        troop_counselors = self._get_troop_counselors(data)
        counselor_badges = {}
        
        for counselor in troop_counselors:
            for badge in counselor.get('merit_badges', []):
                if badge not in counselor_badges:
                    counselor_badges[badge] = []
                counselor_badges[badge].append(counselor)
        
        # Categorize badges
        coverage_data = {
            'eagle_with_counselors': [],
            'eagle_without_counselors': [],
            'non_eagle_with_counselors': [],
            'non_eagle_without_counselors': []
        }
        
        for badge in all_badges:
            has_counselor = badge in counselor_badges
            is_eagle = badge in eagle_badges
            
            badge_info = {
                'name': badge,
                'counselors': counselor_badges.get(badge, [])
            }
            
            if is_eagle:
                if has_counselor:
                    coverage_data['eagle_with_counselors'].append(badge_info)
                else:
                    coverage_data['eagle_without_counselors'].append(badge_info)
            else:
                if has_counselor:
                    coverage_data['non_eagle_with_counselors'].append(badge_info)
                else:
                    coverage_data['non_eagle_without_counselors'].append(badge_info)
        
        # Sort all categories alphabetically
        for category in coverage_data:
            coverage_data[category].sort(key=lambda x: x['name'])
        
        return {
            'title': 'T12/T32 Merit Badge Counselor Coverage',
            'data': coverage_data,
            'totals': {
                'total_badges': len(all_badges),
                'eagle_badges': len(eagle_badges),
                'covered_badges': len(counselor_badges),
                'eagle_covered': len(coverage_data['eagle_with_counselors']),
                'eagle_uncovered': len(coverage_data['eagle_without_counselors'])
            }
        }
    
    def _get_troop_counselors(self, data: Dict) -> List[Dict]:
        """Get all counselors from T12/T32"""
        counselors_report = self._generate_counselors_report(data)
        return counselors_report['data']
    
    def _names_match(self, person1: Dict, person2: Dict) -> bool:
        """Check if two people have matching names"""
        first1 = person1.get('first_name', '').lower().strip()
        last1 = person1.get('last_name', '').lower().strip()
        
        first2 = person2.get('first_name', '').lower().strip()
        alt_first2 = person2.get('alternate_first_name', '').lower().strip()
        last2 = person2.get('last_name', '').lower().strip()
        
        # Match last names and either first name or alternate first name
        return (last1 == last2 and 
                (first1 == first2 or (alt_first2 and first1 == alt_first2)))
    
    def _generate_html_report(self, report_data: Dict, title: str, output_path: str) -> str:
        """Generate HTML report file"""
        html_content = self._create_html_template(report_data, title)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logging.info(f"Generated HTML report: {output_path}")
        return output_path
    
    def _create_html_template(self, report_data: Dict, title: str) -> str:
        """Create HTML template with embedded CSS and JavaScript"""
        generation_time = self.generation_time.strftime("%Y-%m-%d %H:%M:%S")
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f4f4f4;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #333;
        }}
        .header h1 {{
            color: #333;
            margin: 0;
        }}
        .generation-info {{
            color: #666;
            font-size: 0.9em;
            margin-top: 10px;
        }}
        .actions {{
            margin: 20px 0;
            text-align: center;
        }}
        .btn {{
            display: inline-block;
            padding: 10px 20px;
            margin: 5px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            border: none;
            cursor: pointer;
            font-size: 14px;
        }}
        .btn:hover {{
            background-color: #0056b3;
        }}
        .btn-secondary {{
            background-color: #6c757d;
        }}
        .btn-secondary:hover {{
            background-color: #545b62;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-box {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            text-align: center;
            border-left: 4px solid #007bff;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .data-table th,
        .data-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .data-table th {{
            background-color: #f8f9fa;
            font-weight: bold;
            color: #333;
        }}
        .data-table tr:hover {{
            background-color: #f5f5f5;
        }}
        .section {{
            margin: 30px 0;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }}
        .badge-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin: 5px 0;
        }}
        .merit-badge {{
            background-color: #e9ecef;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            color: #495057;
        }}
        .eagle-badge {{
            background-color: #ffd700;
            color: #856404;
        }}
        .no-coverage {{
            color: #dc3545;
            font-style: italic;
        }}
        @media print {{
            .actions {{ display: none; }}
            body {{ background: white; }}
            .container {{ box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <div class="generation-info">
                Generated on: {generation_time}<br>
                Troops 12 & 32, Acton, MA
            </div>
        </div>
        
        <div class="actions">
            <button class="btn" onclick="downloadCSV()">Download CSV File</button>
            <button class="btn btn-secondary" onclick="window.print()">Print</button>
        </div>
        
        {self._generate_report_content(report_data)}
    </div>
    
    <script>
        function downloadCSV() {{
            const data = {self._generate_csv_data(report_data)};
            const csv = convertToCSV(data);
            downloadFile(csv, '{title.replace(" ", "_").lower()}.csv', 'text/csv');
        }}
        
        function convertToCSV(data) {{
            if (!data || data.length === 0) return '';
            
            const headers = Object.keys(data[0]);
            const csvHeaders = headers.join(',');
            
            const csvRows = data.map(row => 
                headers.map(header => {{
                    const value = row[header] || '';
                    return `"${{String(value).replace(/"/g, '""')}}"`;
                }}).join(',')
            );
            
            return [csvHeaders, ...csvRows].join('\\n');
        }}
        
        function downloadFile(content, filename, contentType) {{
            const blob = new Blob([content], {{ type: contentType }});
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        }}
    </script>
</body>
</html>"""
        
        return html
    
    def _generate_report_content(self, report_data: Dict) -> str:
        """Generate the main content area of the report"""
        if report_data['title'] == 'T12/T32 Merit Badge Counselors':
            return self._generate_counselors_content(report_data)
        elif report_data['title'] == 'T12/T32 Leaders not Merit Badge Counselors':
            return self._generate_non_counselors_content(report_data)
        elif report_data['title'] == 'T12/T32 Merit Badge Counselor Coverage':
            return self._generate_coverage_content(report_data)
        else:
            return "<p>Unknown report type</p>"
    
    def _generate_counselors_content(self, report_data: Dict) -> str:
        """Generate content for counselors report"""
        counselors = report_data['data']
        count = report_data['count']
        
        content = f"""
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number">{count}</div>
                <div class="stat-label">Total Merit Badge Counselors</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Merit Badge Counselors</h2>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Troop</th>
                        <th>Position</th>
                        <th>Contact</th>
                        <th>Merit Badges</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for counselor in counselors:
            badges_html = ""
            if counselor.get('merit_badges'):
                badges_html = '<div class="badge-list">'
                for badge in counselor['merit_badges']:
                    badges_html += f'<span class="merit-badge">{badge}</span>'
                badges_html += '</div>'
            
            contact_info = []
            if counselor.get('email'):
                contact_info.append(f"📧 {counselor['email']}")
            if counselor.get('phone'):
                contact_info.append(f"📞 {counselor['phone']}")
            contact_str = "<br>".join(contact_info)
            
            content += f"""
                    <tr>
                        <td>{counselor['first_name']} {counselor['last_name']}</td>
                        <td>T{counselor['troop']}</td>
                        <td>{counselor['position']}</td>
                        <td>{contact_str}</td>
                        <td>{badges_html}</td>
                    </tr>
            """
        
        content += """
                </tbody>
            </table>
        </div>
        """
        
        return content
    
    def _generate_non_counselors_content(self, report_data: Dict) -> str:
        """Generate content for non-counselors report"""
        non_counselors = report_data['data']
        count = report_data['count']
        
        content = f"""
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number">{count}</div>
                <div class="stat-label">Leaders Not Merit Badge Counselors</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Leaders Not Registered as Merit Badge Counselors</h2>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Troop</th>
                        <th>Position</th>
                        <th>Contact</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for leader in non_counselors:
            contact_info = []
            if leader.get('email'):
                contact_info.append(f"📧 {leader['email']}")
            if leader.get('phone'):
                contact_info.append(f"📞 {leader['phone']}")
            contact_str = "<br>".join(contact_info)
            
            content += f"""
                    <tr>
                        <td>{leader['first_name']} {leader['last_name']}</td>
                        <td>T{leader['troop']}</td>
                        <td>{leader['position']}</td>
                        <td>{contact_str}</td>
                    </tr>
            """
        
        content += """
                </tbody>
            </table>
        </div>
        """
        
        return content
    
    def _generate_coverage_content(self, report_data: Dict) -> str:
        """Generate content for coverage report"""
        data = report_data['data']
        totals = report_data['totals']
        
        content = f"""
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number">{totals['total_badges']}</div>
                <div class="stat-label">Total Merit Badges</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{totals['eagle_badges']}</div>
                <div class="stat-label">Eagle Required</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{totals['covered_badges']}</div>
                <div class="stat-label">Badges with T12/T32 Counselors</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{totals['eagle_covered']}</div>
                <div class="stat-label">Eagle Badges Covered</div>
            </div>
        </div>
        """
        
        # Eagle-required badges with counselors
        if data['eagle_with_counselors']:
            content += """
            <div class="section">
                <h2>Eagle-Required Merit Badges (With T12/T32 Counselors)</h2>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Merit Badge</th>
                            <th>Counselors</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for badge_info in data['eagle_with_counselors']:
                counselors_list = []
                for counselor in badge_info['counselors']:
                    counselors_list.append(f"{counselor['first_name']} {counselor['last_name']} (T{counselor['troop']})")
                counselors_str = "<br>".join(counselors_list)
                
                content += f"""
                        <tr>
                            <td><span class="merit-badge eagle-badge">{badge_info['name']}</span></td>
                            <td>{counselors_str}</td>
                        </tr>
                """
            
            content += """
                    </tbody>
                </table>
            </div>
            """
        
        # Eagle-required badges without counselors
        if data['eagle_without_counselors']:
            content += """
            <div class="section">
                <h2>Eagle-Required Merit Badges (No T12/T32 Counselors)</h2>
                <div class="badge-list">
            """
            
            for badge_info in data['eagle_without_counselors']:
                content += f'<span class="merit-badge eagle-badge no-coverage">{badge_info["name"]}</span>'
            
            content += """
                </div>
            </div>
            """
        
        # Non-Eagle badges with counselors
        if data['non_eagle_with_counselors']:
            content += """
            <div class="section">
                <h2>Other Merit Badges (With T12/T32 Counselors)</h2>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Merit Badge</th>
                            <th>Counselors</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for badge_info in data['non_eagle_with_counselors']:
                counselors_list = []
                for counselor in badge_info['counselors']:
                    counselors_list.append(f"{counselor['first_name']} {counselor['last_name']} (T{counselor['troop']})")
                counselors_str = "<br>".join(counselors_list)
                
                content += f"""
                        <tr>
                            <td><span class="merit-badge">{badge_info['name']}</span></td>
                            <td>{counselors_str}</td>
                        </tr>
                """
            
            content += """
                    </tbody>
                </table>
            </div>
            """
        
        # Non-Eagle badges without counselors (collapsed view for space)
        if data['non_eagle_without_counselors']:
            uncovered_count = len(data['non_eagle_without_counselors'])
            content += f"""
            <div class="section">
                <h2>Other Merit Badges (No T12/T32 Counselors) - {uncovered_count} badges</h2>
                <div class="badge-list">
            """
            
            for badge_info in data['non_eagle_without_counselors']:
                content += f'<span class="merit-badge no-coverage">{badge_info["name"]}</span>'
            
            content += """
                </div>
            </div>
            """
        
        return content
    
    def _generate_csv_data(self, report_data: Dict) -> str:
        """Generate CSV data for JavaScript download function"""
        import json
        
        csv_data = []
        
        if report_data['title'] == 'T12/T32 Merit Badge Counselors':
            for counselor in report_data['data']:
                badges = ", ".join(counselor.get('merit_badges', []))
                csv_data.append({
                    'First Name': counselor['first_name'],
                    'Last Name': counselor['last_name'],
                    'Troop': f"T{counselor['troop']}",
                    'Position': counselor['position'],
                    'Email': counselor.get('email', ''),
                    'Phone': counselor.get('phone', ''),
                    'Merit Badges': badges
                })
        
        elif report_data['title'] == 'T12/T32 Leaders not Merit Badge Counselors':
            for leader in report_data['data']:
                csv_data.append({
                    'First Name': leader['first_name'],
                    'Last Name': leader['last_name'],
                    'Troop': f"T{leader['troop']}",
                    'Position': leader['position'],
                    'Email': leader.get('email', ''),
                    'Phone': leader.get('phone', '')
                })
        
        elif report_data['title'] == 'T12/T32 Merit Badge Counselor Coverage':
            for category_name, badges in report_data['data'].items():
                category_label = {
                    'eagle_with_counselors': 'Eagle Required - Covered',
                    'eagle_without_counselors': 'Eagle Required - Not Covered',
                    'non_eagle_with_counselors': 'Other - Covered',
                    'non_eagle_without_counselors': 'Other - Not Covered'
                }.get(category_name, category_name)
                
                for badge_info in badges:
                    counselors = []
                    for counselor in badge_info.get('counselors', []):
                        counselors.append(f"{counselor['first_name']} {counselor['last_name']} (T{counselor['troop']})")
                    
                    csv_data.append({
                        'Merit Badge': badge_info['name'],
                        'Category': category_label,
                        'Counselors': "; ".join(counselors) if counselors else 'None'
                    })
        
        return json.dumps(csv_data)
    
    def _generate_summary_report(self, data: Dict, reports: Dict) -> str:
        """Generate a summary report with statistics and links"""
        generation_time = self.generation_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate statistics
        total_adults = 0
        total_youth = 0
        
        if 't12_roster' in data:
            total_adults += len(data['t12_roster']['registered_adults'])
            total_youth += len(data['t12_roster']['youth_members'])
        
        if 't32_roster' in data:
            total_adults += len(data['t32_roster']['registered_adults'])
            total_youth += len(data['t32_roster']['youth_members'])
        
        # Count counselors from reports (simplified approach)
        total_badges = len(data.get('all_merit_badges', []))
        eagle_badges = len(data.get('eagle_required_badges', []))
        
        validation_results = []
        if total_adults > 0:
            validation_results.append(f"✓ Processed {total_adults} registered adults")
        if total_youth > 0:
            validation_results.append(f"✓ Processed {total_youth} youth members")
        if total_badges > 0:
            validation_results.append(f"✓ Fetched {total_badges} merit badges from scouting.org")
        if eagle_badges > 0:
            validation_results.append(f"✓ Identified {eagle_badges} Eagle-required merit badges")
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Merit Badge Counselor Reports - Summary</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f4f4f4;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #333;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-box {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            text-align: center;
            border-left: 4px solid #007bff;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .reports-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .report-card {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }}
        .report-card h3 {{
            margin-top: 0;
            color: #333;
        }}
        .btn {{
            display: inline-block;
            padding: 10px 20px;
            margin: 5px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            border: none;
            cursor: pointer;
        }}
        .btn:hover {{
            background-color: #0056b3;
        }}
        .validation-results {{
            background: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 4px;
            padding: 15px;
            margin: 20px 0;
        }}
        .validation-results h3 {{
            margin-top: 0;
            color: #155724;
        }}
        .validation-results ul {{
            margin: 0;
            color: #155724;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Merit Badge Counselor Reports</h1>
            <p>Troops 12 & 32, Acton, MA</p>
            <p><strong>Generated:</strong> {generation_time}</p>
        </div>
        
        <div class="validation-results">
            <h3>Processing Results</h3>
            <ul>
                {"".join(f"<li>{result}</li>" for result in validation_results)}
            </ul>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number">{total_adults}</div>
                <div class="stat-label">Registered Adults</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{total_youth}</div>
                <div class="stat-label">Youth Members</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{total_badges}</div>
                <div class="stat-label">Total Merit Badges</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{eagle_badges}</div>
                <div class="stat-label">Eagle-Required Badges</div>
            </div>
        </div>
        
        <div class="reports-grid">
            <div class="report-card">
                <h3>T12/T32 Merit Badge Counselors</h3>
                <p>List of troop members who are registered merit badge counselors, including their contact information and authorized merit badges.</p>
                <a href="html/troop_counselors.html" class="btn">View Report</a>
            </div>
            
            <div class="report-card">
                <h3>Leaders Not Merit Badge Counselors</h3>
                <p>List of troop leaders who are not currently registered as merit badge counselors and could potentially become counselors.</p>
                <a href="html/leaders_not_counselors.html" class="btn">View Report</a>
            </div>
            
            <div class="report-card">
                <h3>Merit Badge Coverage</h3>
                <p>Comprehensive view of all merit badges showing which ones have T12/T32 counselors available and which ones need coverage.</p>
                <a href="html/merit_badge_coverage.html" class="btn">View Report</a>
            </div>
        </div>
        
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; font-size: 0.9em;">
            <p>Generated by Merit Badge Counselor Lists Tool v{__version__}</p>
        </div>
    </div>
</body>
</html>"""
        
        return html

class MBCTool:
    """Main application class for Merit Badge Counselor Lists Tool"""
    
    def __init__(self, config_file: Optional[str] = None, debug_mode: bool = False):
        self.report_generator = ReportGenerator(self.config)
    
    def setup_logging(self, debug_mode: bool = False):
        """Configure logging"""
        log_level = logging.DEBUG if debug_mode else logging.INFO
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('mbc_tool.log', mode='w')
            ],
            force=True  # Force reconfiguration
        )
        
        logging.info(f"Merit Badge Counselor Lists Tool v{__version__} starting...")
        if debug_mode:
            logging.debug("Debug logging enabled")
    
    def process_data(self, t12_roster: str, t32_roster: str, mbc_pdfs: List[str]) -> Dict:
        """Main data processing workflow"""
        try:
            progress = ProgressTracker(8, "Processing Merit Badge Data")
            
            # Step 1: Validate inputs
            progress.update("Validating input files")
            self.validate_inputs(t12_roster, t32_roster, mbc_pdfs)
            
            # Step 2: Fetch merit badge data from web
            progress.update("Fetching merit badge lists from scouting.org")
            all_badges = self.fetcher.fetch_all_merit_badges()
            eagle_badges = self.fetcher.fetch_eagle_required_badges()
            
            # Step 3: Process rosters
            progress.update("Processing T12 roster")
            t12_data = self.roster_processor.process_roster(t12_roster, "12")
            
            progress.update("Processing T32 roster")
            t32_data = self.roster_processor.process_roster(t32_roster, "32")
            
            # Step 4: Process merit badge counselor PDFs
            progress.update("Extracting merit badge counselor data from PDFs")
            mbc_data = self.pdf_processor.extract_counselor_data(mbc_pdfs)
            
            # Step 5: Compile all data
            progress.update("Compiling data for analysis")
            compiled_data = {
                't12_roster': t12_data,
                't32_roster': t32_data,
                'merit_badge_counselors': mbc_data,
                'all_merit_badges': all_badges,
                'eagle_required_badges': eagle_badges
            }
            
            # Step 6: Validate compiled data
            progress.update("Validating compiled data")
            self.validate_compiled_data(compiled_data)
            
            # Step 7: Print debug information
            progress.update("Generating debug output")
            self.print_debug_info(compiled_data)
            
            progress.update("Data processing complete")
            
            logging.info("Data processing completed successfully")
            return compiled_data
            
        except Exception as e:
            logging.error(f"Data processing failed: {e}")
            logging.debug(traceback.format_exc())
            raise DataProcessingError(f"Failed to process data: {e}")
    
    def validate_inputs(self, t12_roster: str, t32_roster: str, mbc_pdfs: List[str]):
        """Validate all input files"""
        logging.info("Validating input files...")
        
        # Check file existence
        for file_path in [t12_roster, t32_roster] + mbc_pdfs:
            if not os.path.exists(file_path):
                raise InputValidationError(f"File not found: {file_path}")
        
        # Validate CSV files
        self.validator.validate_csv_file(t12_roster, self.config)
        self.validator.validate_csv_file(t32_roster, self.config)
        
        # Validate PDF files
        self.validator.validate_pdf_files(mbc_pdfs, self.config)
        
        # Check web connectivity
        self.validator.check_web_connectivity(self.config)
        
        logging.info("All input validation passed")
    
    def validate_compiled_data(self, data: Dict):
        """Validate the compiled data meets expected criteria"""
        logging.info("Validating compiled data...")
        
        # Check we have data
        if not data.get('all_merit_badges'):
            raise DataProcessingError("No merit badges fetched from scouting.org")
        
        if not data.get('eagle_required_badges'):
            raise DataProcessingError("No Eagle-required merit badges fetched")
        
        # Check roster data
        t12_adults = len(data.get('t12_roster', {}).get('registered_adults', []))
        t32_adults = len(data.get('t32_roster', {}).get('registered_adults', []))
        
        if t12_adults == 0 and t32_adults == 0:
            raise DataProcessingError("No registered adults found in either roster")
        
        logging.info(f"Validation passed: {len(data['all_merit_badges'])} merit badges, "
                    f"{len(data['eagle_required_badges'])} Eagle-required, "
                    f"{t12_adults + t32_adults} total adults")
    
    def print_debug_info(self, data: Dict):
        """Print debug information about processed data"""
        logging.info("=== DEBUG INFORMATION ===")
        
        # Roster debug info
        for troop in ['t12_roster', 't32_roster']:
            if troop in data:
                roster_data = data[troop]
                troop_num = roster_data['troop']
                adults = roster_data['registered_adults']
                youth = roster_data['youth_members']
                
                logging.info(f"Troop {troop_num} Roster:")
                logging.info(f"  Registered Adults: {len(adults)}")
                logging.info(f"  Youth Members: {len(youth)}")
                
                # Sample of adults
                for i, adult in enumerate(adults[:3]):
                    logging.debug(f"  Adult {i+1}: {adult['first_name']} {adult['last_name']} - {adult['position']}")
                
                if len(adults) > 3:
                    logging.debug(f"  ... and {len(adults) - 3} more adults")
        
        # Merit badge counselor debug info
        mbc_data = data.get('merit_badge_counselors', [])
        logging.info(f"Merit Badge Counselors extracted: {len(mbc_data)}")
        
        for i, counselor in enumerate(mbc_data[:3]):
            logging.debug(f"  Counselor {i+1}: {counselor}")
        
        if len(mbc_data) > 3:
            logging.debug(f"  ... and {len(mbc_data) - 3} more counselors")
        
        # Merit badge lists
        logging.info(f"Total Merit Badges: {len(data.get('all_merit_badges', []))}")
        logging.info(f"Eagle-Required Merit Badges: {len(data.get('eagle_required_badges', []))}")
        
        logging.info("=== END DEBUG INFORMATION ===")
    
    def generate_reports(self, data: Dict, output_dir: str) -> Dict[str, str]:
        """Generate all reports"""
        try:
            logging.info(f"Generating reports in {output_dir}...")
            
            # Create timestamped output directory
            timestamp = datetime.now().strftime(self.config.OUTPUT_TIMESTAMP_FORMAT)
            timestamped_dir = os.path.join(output_dir, f"MBC_Reports_{timestamp}")
            
            # Generate all reports
            report_paths = self.report_generator.generate_all_reports(data, timestamped_dir)
            
            logging.info(f"Reports generated successfully in {timestamped_dir}")
            
            # Auto-open output folder (platform-specific)
            try:
                import subprocess
                import platform
                
                if platform.system() == "Windows":
                    subprocess.run(["explorer", timestamped_dir])
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", timestamped_dir])
                elif platform.system() == "Linux":
                    subprocess.run(["xdg-open", timestamped_dir])
            except Exception as e:
                logging.debug(f"Could not auto-open output folder: {e}")
            
            return report_paths
            
        except Exception as e:
            logging.error(f"Report generation failed: {e}")
            raise DataProcessingError(f"Failed to generate reports: {e}")
    
    def run_cli(self, args):
        """Run the command-line interface"""
        try:
            logging.info("Starting CLI mode")
            logging.info(f"T12 Roster: {args.t12_roster}")
            logging.info(f"T32 Roster: {args.t32_roster}")
            logging.info(f"MBC PDFs: {args.mbc_pdfs}")
            logging.info(f"Output Directory: {args.output}")
            
            # Process data
            data = self.process_data(args.t12_roster, args.t32_roster, args.mbc_pdfs)
            
            # Generate reports
            report_paths = self.generate_reports(data, args.output)
            
            # Print summary
            print("\n" + "="*60)
            print("REPORT GENERATION COMPLETE")
            print("="*60)
            print(f"Summary Report: {report_paths['summary']}")
            print(f"Counselors Report: {report_paths['counselors']}")
            print(f"Non-Counselors Report: {report_paths['non_counselors']}")
            print(f"Coverage Report: {report_paths['coverage']}")
            print("="*60)
            
            return True
            
        except Exception as e:
            print(f"\nERROR: {e}")
            logging.error(f"CLI execution failed: {e}")
            return False

def setup_cli():
    """Setup command-line interface"""
    parser = argparse.ArgumentParser(
        description="Merit Badge Counselor Lists Tool - Generate reports for Scout Troops",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --t12-roster t12_roster.csv --t32-roster t32_roster.csv --mbc-pdfs counselors1.pdf counselors2.pdf
  %(prog)s --t12-roster t12_roster.csv --t32-roster t32_roster.csv --mbc-pdfs *.pdf --output ./reports
        """
    )
    
    parser.add_argument(
        '--t12-roster',
        required=True,
        help='Path to T12 roster CSV file'
    )
    
    parser.add_argument(
        '--t32-roster', 
        required=True,
        help='Path to T32 roster CSV file'
    )
    
    parser.add_argument(
        '--mbc-pdfs',
        nargs='+',
        required=True,
        help='Paths to Merit Badge Counselor PDF files'
    )
    
    parser.add_argument(
        '--output',
        default='./output',
        help='Output directory for generated reports (default: ./output)'
    )
    
    parser.add_argument(
        '--config',
        help='Path to configuration JSON file'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'Merit Badge Counselor Lists Tool v{__version__}'
    )
    
    return parser

def main():
    """Main entry point"""
    print("=== Merit Badge Counselor Lists Tool Starting ===")
    parser = setup_cli()
    args = parser.parse_args()
    
    print(f"Arguments parsed successfully:")
    print(f"  T12 Roster: {args.t12_roster}")
    print(f"  T32 Roster: {args.t32_roster}")
    print(f"  MBC PDFs: {args.mbc_pdfs}")
    print(f"  Output: {args.output}")
    print(f"  Debug: {args.debug}")
    
    if args.debug:
        print("Debug logging will be enabled")
    
    try:
        # Initialize tool with debug mode
        tool = MBCTool(args.config, debug_mode=args.debug)
        
        # Run CLI
        success = tool.run_cli(args)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        logging.critical(f"Fatal error: {e}")
        logging.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()config = Config(config_file)
        self.setup_logging(debug_mode)
        
        # Initialize components
        self.validator = DataValidator()
        self.fetcher = MeritBadgeDataFetcher(self.config)
        self.roster_processor = RosterProcessor(self.config)
        self.pdf_processor = PDFProcessor(self.config)
        self.#!/usr/bin/env python3
