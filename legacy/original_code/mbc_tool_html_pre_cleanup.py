#!/usr/bin/env python3
"""
Merit Badge Counselor Lists Tool

This tool processes Scouting America data to generate comprehensive lists of:
1. T12/T32 Merit Badge Counselors
2. T12/T32 Leaders not Merit Badge Counselors  
3. T12/T32 Merit Badge Counselor Coverage

Input data includes:
- CSV rosters for Troops 12 and 32
- HTML files containing Merit Badge Counselor listings from ScoutBook search results
- Web-scraped merit badge lists from scouting.org

Output formats: HTML, CSV, PDF, Excel, WordPress
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError
import copy

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    print("BeautifulSoup not found. Install with: pip install beautifulsoup4")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mbc_tool.log', mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MeritBadgeProcessor:
    """Main class for processing Merit Badge Counselor data."""
    
    def __init__(self):
        self.all_merit_badges = []
        self.eagle_required_badges = []
        self.t12_roster = []
        self.t32_roster = []
        self.merit_badge_counselors = []
        self.output_dir = None
        
        # Cache for scouting.org data - UPDATED with missing badges
        self.cached_all_badges = [
            "Aerospace", "American Business", "American Cultures", "American Heritage", 
            "American Labor", "Animal Science", "Animation", "Archaeology", "Archery", 
            "Architecture", "Art", "Astronomy", "Athletics", "Automotive", 
            "Aviation", "Backpacking", "Basketry", "Bird Study", "Bugling", 
            "Camping", "Canoeing", "Chemistry", "Chess", "Citizenship in the Community",
            "Citizenship in the Nation", "Citizenship in Society", "Citizenship in the World", 
            "Climbing", "Coin Collecting", "Collections", "Communication", "Composite Materials",
            "Cooking", "Crime Prevention", "Cycling", "Dentistry", "Digital Technology",
            "Disabilities Awareness", "Dog Care", "Drafting", "Drama",
            "Electricity", "Electronics", "Emergency Preparedness", "Energy", 
            "Engineering", "Entrepreneurship", "Environmental Science", "Family Life",
            "Farm Mechanics", "Fingerprinting", "Fire Safety", "First Aid", 
            "Fish and Wildlife Management", "Fishing", "Forestry", "Game Design",
            "Gardening", "Genealogy", "Geocaching", "Geology", "Golf", "Graphic Arts",
            "Hiking", "Home Repairs", "Horsemanship", "Indian Lore", "Insect Study",
            "Inventions", "Journalism", "Kayaking", "Landscape Architecture", 
            "Law", "Leatherwork", "Lifesaving", "Mammal Study", "Medicine", 
            "Metalwork", "Mining", "Model Design and Building", "Motorboating",
            "Moviemaking", "Multisport", "Music", "Nature", "Nuclear Science", 
            "Oceanography", "Orienteering", "Painting", "Personal Fitness", 
            "Personal Management", "Pets", "Photography", "Pioneering", "Plant Science", 
            "Plumbing", "Pottery", "Programming", "Public Health", "Public Speaking", 
            "Pulp and Paper", "Radio", "Railroading", "Reading", "Reptile and Amphibian Study", 
            "Rifle Shooting", "Robotics", "Rowing", "Safety", "Salesmanship", 
            "Scholarship", "Scouting Heritage", "Scuba Diving", "Sculpture", 
            "Search and Rescue", "Shotgun Shooting", "Signs, Signals, and Codes",
            "Skating", "Small-Boat Sailing", "Snow Sports", "Soil and Water Conservation",
            "Space Exploration", "Sports", "Stamp Collecting", "Surveying", 
            "Sustainability", "Swimming", "Textile", "Theater", "Traffic Safety",
            "Truck Transportation", "Veterinary Medicine", "Water Sports", 
            "Weather", "Welding", "Whitewater", "Wilderness Survival", "Wood Carving",
            "Woodwork"
        ]
        
        self.cached_eagle_required = [
            "Camping", "Citizenship in the Community", "Citizenship in the Nation",
            "Citizenship in Society", "Citizenship in the World", "Communication", 
            "Cooking", "Cycling", "Emergency Preparedness", "Environmental Science", "Family Life",
            "First Aid", "Hiking", "Lifesaving", "Personal Fitness", 
            "Personal Management", "Sustainability", "Swimming"
        ]

    def create_output_directory(self) -> str:
        """Create timestamped output directory."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        self.output_dir = f"MBC_Reports_{timestamp}"
        
        # Create main directory and subdirectories
        directories = [
            self.output_dir,
            f"{self.output_dir}/html",
            f"{self.output_dir}/csv", 
            f"{self.output_dir}/pdf",
            f"{self.output_dir}/excel",
            f"{self.output_dir}/wordpress"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            
        logger.info(f"Created output directory: {self.output_dir}")
        return self.output_dir

    def fetch_merit_badges_from_web(self) -> Tuple[List[str], List[str]]:
        """Fetch merit badge lists from scouting.org with fallback to cached data."""
        all_badges = []
        eagle_badges = []
        
        try:
            # Fetch all merit badges
            logger.info("Fetching all merit badges from scouting.org...")
            all_url = "https://www.scouting.org/skills/merit-badges/all/"
            
            with urllib.request.urlopen(all_url, timeout=10) as response:
                html = response.read().decode('utf-8')
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find merit badges after "Merit Badges A-Z" heading
                started = False
                for element in soup.find_all(['h2', 'h3', 'li', 'a']):
                    if element.text and "Merit Badges A-Z" in element.text:
                        started = True
                        continue
                    if started and isinstance(element, Tag) and element.name == 'a':
                        href = element.get('href')
                        if href and '/merit-badge/' in str(href):
                            badge_name = element.text.strip()
                            if badge_name and badge_name not in all_badges:
                                all_badges.append(badge_name)
                            
            logger.info(f"Retrieved {len(all_badges)} merit badges from web")
            
        except (URLError, HTTPError, Exception) as e:
            logger.warning(f"Failed to fetch all merit badges from web: {e}")
            logger.info("Using cached merit badge list")
            all_badges = self.cached_all_badges.copy()
            
        try:
            # Fetch Eagle-required merit badges
            logger.info("Fetching Eagle-required merit badges from scouting.org...")
            eagle_url = "https://www.scouting.org/skills/merit-badges/eagle-required/"
            
            with urllib.request.urlopen(eagle_url, timeout=10) as response:
                html = response.read().decode('utf-8')
                soup = BeautifulSoup(html, 'html.parser')
                
                for element in soup.find_all('a'):
                    if isinstance(element, Tag):
                        href = element.get('href')
                        if href and '/merit-badge/' in str(href):
                            badge_name = element.text.strip()
                            if badge_name and badge_name not in eagle_badges:
                                eagle_badges.append(badge_name)
                            
            logger.info(f"Retrieved {len(eagle_badges)} Eagle-required badges from web")
            
        except (URLError, HTTPError, Exception) as e:
            logger.warning(f"Failed to fetch Eagle-required badges from web: {e}")
            logger.info("Using cached Eagle-required badge list")
            eagle_badges = self.cached_eagle_required.copy()
        
        # Update cached data if web fetch was successful
        if len(all_badges) > len(self.cached_all_badges) * 0.8:  # At least 80% of expected
            self.all_merit_badges = sorted(all_badges)
        else:
            self.all_merit_badges = sorted(self.cached_all_badges)
            
        if len(eagle_badges) > len(self.cached_eagle_required) * 0.8:
            self.eagle_required_badges = sorted(eagle_badges)
        else:
            self.eagle_required_badges = sorted(self.cached_eagle_required)
            
        return self.all_merit_badges, self.eagle_required_badges

    def parse_roster_csv(self, filepath: str) -> List[Dict]:
        """Parse a troop roster CSV file."""
        roster = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Find the line beginning with "..memberid" to identify headers
            lines = content.split('\n')
            header_line_idx = None
            
            for i, line in enumerate(lines):
                if line.strip().startswith('..memberid'):
                    header_line_idx = i
                    break
                    
            if header_line_idx is None:
                logger.error(f"Could not find header line starting with '..memberid' in {filepath}")
                return roster
                
            # Parse CSV starting from header line
            csv_content = '\n'.join(lines[header_line_idx:])
            csv_reader = csv.DictReader(csv_content.splitlines())
            
            for row in csv_reader:
                # Extract required fields
                member = {
                    'firstname': row.get('firstname', '').strip(),
                    'lastname': row.get('lastname', '').strip(), 
                    'positionname': row.get('positionname', '').strip(),
                    'primaryemail': row.get('primaryemail', '').strip(),
                    'primaryphone': row.get('primaryphone', '').strip(),
                    'is_youth': 'Youth Member' in row.get('positionname', ''),
                    'is_adult': 'Youth Member' not in row.get('positionname', '')
                }
                
                # Skip empty rows
                if member['firstname'] or member['lastname']:
                    roster.append(member)
                    logger.debug(f"Processed roster entry: {member['firstname']} {member['lastname']} - {member['positionname']}")
                    
            logger.info(f"Parsed {len(roster)} members from {filepath}")
            
        except Exception as e:
            logger.error(f"Error parsing roster CSV {filepath}: {e}")
            
        return roster

    def parse_merit_badge_html_files(self, html_paths: List[str]) -> List[Dict]:
        """Parse Merit Badge Counselor HTML files from ScoutBook search results."""
        counselors = []
        
        logger.info(f"Processing {len(html_paths)} HTML files...")
        
        for html_index, html_path in enumerate(html_paths, 1):
            try:
                logger.info(f"Processing HTML {html_index}/{len(html_paths)}: {html_path}")
                
                with open(html_path, 'r', encoding='utf-8') as file:
                    html_content = file.read()
                    
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Find all counselor entries - each is in a div with margin-left: 65px
                counselor_divs = soup.find_all('div', style=lambda value: value and 'margin-left: 65px' in value)
                
                logger.info(f"  Found {len(counselor_divs)} counselor entries in {html_path}")
                
                for div_index, counselor_div in enumerate(counselor_divs):
                    try:
                        counselor = self._parse_html_counselor_entry(counselor_div)
                        if counselor and counselor['firstname'] and counselor['lastname']:
                            counselors.append(counselor)
                            logger.info(f"  Extracted counselor: {counselor['firstname']} {counselor['lastname']} - {len(counselor['merit_badges'])} badges")
                        else:
                            logger.debug(f"  Skipped incomplete counselor entry {div_index}")
                            
                    except Exception as e:
                        logger.error(f"  Error processing counselor entry {div_index}: {e}")
                        
            except Exception as e:
                logger.error(f"Error reading HTML file {html_path}: {e}")
                
        logger.info(f"HTML processing complete: extracted {len(counselors)} total merit badge counselors")
        
        # Log summary of extracted counselors
        if counselors:
            logger.info("Sample of extracted counselors:")
            for i, counselor in enumerate(counselors[:5]):  # Show first 5
                badges_preview = counselor['merit_badges'][:3]
                if len(counselor['merit_badges']) > 3:
                    badges_preview_str = f"{badges_preview}..."
                else:
                    badges_preview_str = str(badges_preview)
                logger.info(f"  {i+1}. {counselor['firstname']} {counselor['lastname']} - {len(counselor['merit_badges'])} badges: {badges_preview_str}")
        else:
            logger.warning("No counselors were extracted from any HTML files!")
            
        return counselors

    def _parse_html_counselor_entry(self, counselor_div) -> Dict:
        """Parse individual counselor entry from HTML div."""
        counselor = {
            'firstname': '',
            'alt_firstname': '',
            'lastname': '',
            'phones': [],
            'emails': [],
            'merit_badges': [],
            'expiration': ''
        }
        
        try:
            # Extract name - first text node in the div
            name_text = None
            for content in counselor_div.contents:
                if isinstance(content, str) and content.strip():
                    name_text = content.strip()
                    break
                    
            if name_text:
                # Parse name - handle formats like:
                # "Karen MacQuilken"
                # "Christopher (Chris) White" 
                name_parts = name_text.split()
                if len(name_parts) >= 2:
                    # Check for alternate name in parentheses
                    alt_name_match = re.search(r'\(([^)]+)\)', name_text)
                    counselor['alt_firstname'] = alt_name_match.group(1) if alt_name_match else ""
                    
                    # Remove parentheses and split
                    clean_name = re.sub(r'\s*\([^)]+\)\s*', ' ', name_text).strip()
                    clean_parts = clean_name.split()
                    
                    counselor['firstname'] = clean_parts[0]
                    counselor['lastname'] = ' '.join(clean_parts[1:])
                    
                    logger.debug(f"    Parsed name: {counselor['firstname']} ({counselor['alt_firstname']}) {counselor['lastname']}")
            
            # Extract address/contact info
            address_div = counselor_div.find('div', class_='address')
            if address_div:
                # Extract phone numbers
                address_text = address_div.get_text()
                
                # Home phone
                home_match = re.search(r'Home \((\d{3})\) (\d{3}-\d{4})', address_text)
                if home_match:
                    home_phone = f"({home_match.group(1)}) {home_match.group(2)}"
                    counselor['phones'].append(home_phone)
                    logger.debug(f"    Found home phone: {home_phone}")
                
                # Mobile phone  
                mobile_match = re.search(r'Mobile \((\d{3})\) (\d{3}-\d{4})', address_text)
                if mobile_match:
                    mobile_phone = f"({mobile_match.group(1)}) {mobile_match.group(2)}"
                    counselor['phones'].append(mobile_phone)
                    logger.debug(f"    Found mobile phone: {mobile_phone}")
                
                # Email - extract from mailto link
                email_link = address_div.find('a', href=lambda href: href and href.startswith('mailto:'))
                if email_link:
                    email = email_link.get_text().strip()
                    counselor['emails'].append(email)
                    logger.debug(f"    Found email: {email}")
            
            # Extract merit badges
            mb_container = counselor_div.find('div', class_='mbContainer')
            if mb_container:
                # Find all merit badge divs
                mb_divs = mb_container.find_all('div', class_='mb')
                for mb_div in mb_divs:
                    # Get the merit badge name (text content after the img tag)
                    badge_text = mb_div.get_text().strip()
                    if badge_text:
                        counselor['merit_badges'].append(badge_text)
                        logger.debug(f"    Found merit badge: {badge_text}")
            
            # Sort merit badges for consistency
            counselor['merit_badges'] = sorted(counselor['merit_badges'])
            
            logger.debug(f"    Final counselor: {counselor}")
            
        except Exception as e:
            logger.error(f"    Error parsing counselor entry: {e}")
            
        return counselor

    def cross_reference_counselors(self) -> List[Dict]:
        """Cross-reference troop rosters with merit badge counselors."""
        troop_counselors = []
        
        # Combine T12 and T32 rosters, excluding youth members
        all_adults = []
        
        for member in self.t12_roster:
            if member['is_adult']:
                member['troop'] = 'T12'
                all_adults.append(member)
                
        for member in self.t32_roster:
            if member['is_adult']:
                member['troop'] = 'T32'
                all_adults.append(member)
        
        logger.info(f"Found {len(all_adults)} adult leaders across both troops")
        
        # Create a map to track counselors by name and merge troop memberships
        counselor_map = {}
        
        # Match adults with merit badge counselors
        for adult in all_adults:
            for counselor in self.merit_badge_counselors:
                # Match first name (including alternate) and last name
                first_match = (
                    adult['firstname'].lower() == counselor['firstname'].lower() or
                    (counselor['alt_firstname'] and adult['firstname'].lower() == counselor['alt_firstname'].lower())
                )
                last_match = adult['lastname'].lower() == counselor['lastname'].lower()
                
                if first_match and last_match:
                    # Create unique key for this person
                    person_key = (adult['firstname'].lower(), adult['lastname'].lower())
                    
                    if person_key not in counselor_map:
                        # First time seeing this counselor
                        counselor_map[person_key] = {
                            'firstname': adult['firstname'],
                            'lastname': adult['lastname'],
                            'positionname': adult['positionname'],
                            'troops': [adult['troop']],
                            'roster_emails': [adult['primaryemail']] if adult['primaryemail'] else [],
                            'roster_phones': [adult['primaryphone']] if adult['primaryphone'] else [],
                            'counselor_emails': counselor.get('emails', []),
                            'counselor_phones': counselor.get('phones', []),
                            'merit_badges': counselor.get('merit_badges', [])
                        }
                    else:
                        # Person already exists, merge troop info
                        existing = counselor_map[person_key]
                        if adult['troop'] not in existing['troops']:
                            existing['troops'].append(adult['troop'])
                        # Add any additional contact info from other roster
                        if adult['primaryemail'] and adult['primaryemail'] not in existing['roster_emails']:
                            existing['roster_emails'].append(adult['primaryemail'])
                        if adult['primaryphone'] and adult['primaryphone'] not in existing['roster_phones']:
                            existing['roster_phones'].append(adult['primaryphone'])
                    
                    logger.debug(f"Matched counselor: {adult['firstname']} {adult['lastname']} from {adult['troop']}")
                    break
        
        # Convert map to list and clean up contact info
        for person_key, counselor_data in counselor_map.items():
            # Clean and deduplicate phone numbers
            all_phones = counselor_data['roster_phones'] + counselor_data['counselor_phones']
            clean_phones = self._clean_and_dedupe_phones(all_phones)
            
            # Clean and deduplicate emails
            all_emails = counselor_data['roster_emails'] + counselor_data['counselor_emails']
            clean_emails = self._clean_and_dedupe_emails(all_emails)
            
            # Create final counselor record
            final_counselor = {
                'firstname': counselor_data['firstname'],
                'lastname': counselor_data['lastname'],
                'positionname': counselor_data['positionname'],
                'troop': ', '.join(sorted(counselor_data['troops'])),  # Join multiple troops
                'all_emails': clean_emails,
                'all_phones': clean_phones,
                'merit_badges': counselor_data['merit_badges']
            }
            
            troop_counselors.append(final_counselor)
        
        logger.info(f"Found {len(troop_counselors)} troop members who are also merit badge counselors")
        return troop_counselors

    def _clean_and_dedupe_phones(self, phone_list: List[str]) -> List[str]:
        """Clean and deduplicate phone numbers, formatting as XXX-XXX-XXXX."""
        cleaned_phones = set()
        
        for phone in phone_list:
            if not phone:
                continue
                
            # Remove "~~" prefix if present
            phone = phone.replace('~~', '')
            
            # Extract just the digits
            digits = re.sub(r'\D', '', phone)
            
            # Handle 11-digit numbers starting with 1 (remove the 1 prefix)
            if len(digits) == 11 and digits.startswith('1'):
                digits = digits[1:]
                logger.debug(f"Removed 1- prefix: {phone} -> {digits}")
            
            # Skip if not 10 digits (US phone number)
            if len(digits) != 10:
                logger.debug(f"Skipping invalid phone number: {phone} (digits: {digits})")
                continue
                
            # Format as XXX-XXX-XXXX
            formatted_phone = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
            cleaned_phones.add(formatted_phone)
            logger.debug(f"Cleaned phone: {phone} -> {formatted_phone}")
        
        return sorted(list(cleaned_phones))

    def _clean_and_dedupe_emails(self, email_list: List[str]) -> List[str]:
        """Clean and deduplicate email addresses."""
        cleaned_emails = set()
        
        for email in email_list:
            if not email:
                continue
                
            # Basic email validation pattern
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            
            # Check if it looks like a valid email
            if re.match(email_pattern, email):
                cleaned_emails.add(email.lower())
                logger.debug(f"Valid email: {email}")
            else:
                # Try to extract valid email from malformed string
                # Look for pattern like "something@domain.com" within the string
                email_matches = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', email)
                if email_matches:
                    for match in email_matches:
                        cleaned_emails.add(match.lower())
                        logger.debug(f"Extracted email from malformed string '{email}': {match}")
                else:
                    logger.debug(f"Skipping malformed email: {email}")
        
        return sorted(list(cleaned_emails))

    def find_non_counselor_leaders(self) -> List[Dict]:
        """Find troop leaders who are not merit badge counselors."""
        logger.info("=== STARTING find_non_counselor_leaders() ===")
        non_counselors = []
        
        # Get all adult leaders and merge duplicates across troops
        all_adults = []
        for member in self.t12_roster:
            if member['is_adult']:
                member['troop'] = 'T12'
                all_adults.append(member)
                
        for member in self.t32_roster:
            if member['is_adult']:
                member['troop'] = 'T32'
                all_adults.append(member)
        
        logger.info(f"TOTAL ADULT ENTRIES FROM ROSTERS: {len(all_adults)}")
        
        # Create a map to merge adults who are in both troops
        adult_map = {}
        
        for adult in all_adults:
            person_key = (adult['firstname'].lower(), adult['lastname'].lower())
            
            if person_key not in adult_map:
                # First time seeing this person
                adult_map[person_key] = {
                    'firstname': adult['firstname'],
                    'lastname': adult['lastname'],
                    'positionname': adult['positionname'],
                    'troops': [adult['troop']],
                    'emails': [adult['primaryemail']] if adult['primaryemail'] else [],
                    'phones': [adult['primaryphone']] if adult['primaryphone'] else []
                }
                logger.debug(f"Added new adult: {adult['firstname']} {adult['lastname']} from {adult['troop']}")
            else:
                # Person already exists, merge troop info
                existing = adult_map[person_key]
                if adult['troop'] not in existing['troops']:
                    existing['troops'].append(adult['troop'])
                    logger.debug(f"Merged {adult['firstname']} {adult['lastname']} - now in {existing['troops']}")
                # Add any additional contact info from other roster
                if adult['primaryemail'] and adult['primaryemail'] not in existing['emails']:
                    existing['emails'].append(adult['primaryemail'])
                if adult['primaryphone'] and adult['primaryphone'] not in existing['phones']:
                    existing['phones'].append(adult['primaryphone'])
        
        logger.info(f"UNIQUE ADULTS AFTER MERGING: {len(adult_map)}")
        
        # Build set of merit badge counselor names
        counselor_names = set()
        for counselor in self.merit_badge_counselors:
            counselor_names.add((counselor['firstname'].lower(), counselor['lastname'].lower()))
            if counselor['alt_firstname']:
                counselor_names.add((counselor['alt_firstname'].lower(), counselor['lastname'].lower()))
                
        logger.info(f"MERIT BADGE COUNSELOR NAMES FOUND: {len(counselor_names)}")
        
        logger.info("=== STARTING PERSON-BY-PERSON ANALYSIS ===")
        # Convert map to list, excluding counselors
        excluded_count = 0
        for person_key, adult_data in adult_map.items():
            # Debug logging for each person
            is_counselor = person_key in counselor_names
            logger.debug(f"CHECKING {person_key}: {'COUNSELOR' if is_counselor else 'NOT COUNSELOR'}")
            
            if not is_counselor:
                # Clean phone numbers
                clean_phones = self._clean_and_dedupe_phones(adult_data['phones'])
                clean_emails = adult_data['emails']  # Keep emails as-is for roster data
                
                final_leader = {
                    'firstname': adult_data['firstname'],
                    'lastname': adult_data['lastname'],
                    'positionname': adult_data['positionname'],
                    'troop': ', '.join(sorted(adult_data['troops'])),  # Join multiple troops
                    'primaryemail': clean_emails[0] if clean_emails else '',
                    'primaryphone': clean_phones[0] if clean_phones else ''
                }
                non_counselors.append(final_leader)
                logger.debug(f"Added {person_key} to non-counselors list")
            else:
                excluded_count += 1
                logger.debug(f"EXCLUDED {person_key} - identified as merit badge counselor")
        
        logger.info(f"ADULTS EXCLUDED AS COUNSELORS: {excluded_count}")
        logger.info(f"FINAL NON-COUNSELOR LEADERS: {len(non_counselors)}")
        
        # Sort the final list alphabetically by last name, then first name
        non_counselors.sort(key=lambda x: (x['lastname'].lower(), x['firstname'].lower()))
        
        logger.info("=== FINISHED find_non_counselor_leaders() ===")
        return non_counselors

    def generate_coverage_report(self, troop_counselors: List[Dict]) -> Dict:
        """Generate merit badge coverage report."""
        coverage = {
            'eagle_with_counselors': [],
            'eagle_without_counselors': [],
            'non_eagle_with_counselors': [],
            'non_eagle_without_counselors': []
        }
        
        # Get all merit badges covered by troop counselors
        covered_badges = set()
        badge_counselor_map = {}
        
        for counselor in troop_counselors:
            for badge in counselor['merit_badges']:
                covered_badges.add(badge)
                if badge not in badge_counselor_map:
                    badge_counselor_map[badge] = []
                badge_counselor_map[badge].append(counselor)
        
        # Categorize merit badges
        for badge in sorted(self.all_merit_badges):
            is_eagle_required = badge in self.eagle_required_badges
            has_counselors = badge in covered_badges
            
            counselor_list = badge_counselor_map.get(badge, [])
            
            badge_entry = {
                'badge_name': badge,
                'counselors': counselor_list
            }
            
            if is_eagle_required:
                if has_counselors:
                    coverage['eagle_with_counselors'].append(badge_entry)
                else:
                    coverage['eagle_without_counselors'].append(badge_entry)
            else:
                if has_counselors:
                    coverage['non_eagle_with_counselors'].append(badge_entry)
                else:
                    coverage['non_eagle_without_counselors'].append(badge_entry)
        
        logger.info(f"Coverage report: {len(coverage['eagle_with_counselors'])} Eagle badges with counselors, "
                   f"{len(coverage['eagle_without_counselors'])} Eagle badges without counselors")
        
        return coverage

    def generate_html_report(self, report_type: str, data: Any, title: str) -> str:
        """Generate HTML report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #003f7f;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .timestamp {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .controls {{
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .btn {{
            background-color: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
            text-decoration: none;
            display: inline-block;
        }}
        .btn:hover {{
            background-color: #0056b3;
        }}
        .content {{
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            color: #003f7f;
            border-bottom: 2px solid #003f7f;
            padding-bottom: 10px;
        }}
        .badge-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-top: 5px;
        }}
        .badge {{
            background-color: #e9ecef;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
        }}
        .eagle-badge {{
            background-color: #ffd700;
            color: #000;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <div class="timestamp">Generated: {timestamp}</div>
    </div>
    
    <div class="controls">
        <button class="btn" onclick="downloadCSV()">Download CSV File</button>
        <button class="btn" onclick="window.print()">Print</button>
    </div>
    
    <div class="content">
        {self._generate_html_content(report_type, data)}
    </div>
    
    <script>
        function downloadCSV() {{
            const csvData = {self._generate_csv_data(report_type, data)};
            const blob = new Blob([csvData], {{ type: 'text/csv' }});
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '{report_type.replace(" ", "_").lower()}.csv';
            a.click();
            window.URL.revokeObjectURL(url);
        }}
    </script>
</body>
</html>
        """
        
        return html

    def _generate_html_content(self, report_type: str, data: Any) -> str:
        """Generate HTML content based on report type."""
        if report_type == "T12/T32 Merit Badge Counselors":
            return self._generate_counselors_html(data)
        elif report_type == "T12/T32 Leaders not Merit Badge Counselors":
            return self._generate_non_counselors_html(data)
        elif report_type == "T12/T32 Merit Badge Counselor Coverage":
            return self._generate_coverage_html(data)
        return "<p>Unknown report type</p>"

    def _generate_counselors_html(self, counselors: List[Dict]) -> str:
        """Generate HTML for merit badge counselors list."""
        html = f"<h2>Merit Badge Counselors ({len(counselors)} total)</h2>"
        html += "<table>"
        html += "<tr><th>Name</th><th>Troop</th><th>Position</th><th>Contact</th><th>Merit Badges</th></tr>"
        
        for counselor in counselors:
            # Use cleaned contact info
            emails = counselor.get('all_emails', [])
            phones = counselor.get('all_phones', [])
            
            email_parts = [f"📧 {email}" for email in emails]
            phone_parts = [f"📞 {phone}" for phone in phones]
            contact_info = "<br>".join(email_parts + phone_parts)
            
            badges_html = '<div class="badge-list">'
            for badge in sorted(counselor.get('merit_badges', [])):
                badge_class = "badge eagle-badge" if badge in self.eagle_required_badges else "badge"
                badges_html += f'<span class="{badge_class}">{badge}</span>'
            badges_html += '</div>'
            
            html += f"""
            <tr>
                <td>{counselor['firstname']} {counselor['lastname']}</td>
                <td>{counselor['troop']}</td>
                <td>{counselor['positionname']}</td>
                <td>{contact_info}</td>
                <td>{badges_html}</td>
            </tr>
            """
        
        html += "</table>"
        return html

    def _generate_non_counselors_html(self, non_counselors: List[Dict]) -> str:
        """Generate HTML for non-merit badge counselors list."""
        html = f"<h2>Leaders not Merit Badge Counselors ({len(non_counselors)} total)</h2>"
        html += "<table>"
        html += "<tr><th>Name</th><th>Troop</th><th>Position</th><th>Contact</th></tr>"
        
        for leader in non_counselors:
            contact_parts = []
            if leader['primaryemail']:
                contact_parts.append(f"📧 {leader['primaryemail']}")
            if leader['primaryphone']:
                contact_parts.append(f"📞 {leader['primaryphone']}")
            contact_info = "<br>".join(contact_parts)
            
            html += f"""
            <tr>
                <td>{leader['firstname']} {leader['lastname']}</td>
                <td>{leader['troop']}</td>
                <td>{leader['positionname']}</td>
                <td>{contact_info}</td>
            </tr>
            """
        
        html += "</table>"
        return html

    def _generate_coverage_html(self, coverage: Dict) -> str:
        """Generate HTML for coverage report."""
        html = "<h2>Merit Badge Coverage Report</h2>"
        
        sections = [
            ("Eagle-Required Merit Badges with T12/T32 Counselors", coverage['eagle_with_counselors'], True),
            ("Eagle-Required Merit Badges without T12/T32 Counselors", coverage['eagle_without_counselors'], False),
            ("Non-Eagle Merit Badges with T12/T32 Counselors", coverage['non_eagle_with_counselors'], True),
            ("Non-Eagle Merit Badges without T12/T32 Counselors", coverage['non_eagle_without_counselors'], False)
        ]
        
        for section_title, badges, has_counselors in sections:
            html += f'<div class="section">'
            html += f'<h3>{section_title} ({len(badges)} badges)</h3>'
            
            if has_counselors:
                html += "<table>"
                html += "<tr><th>Merit Badge</th><th>Counselors</th></tr>"
                
                for badge_entry in badges:
                    counselors_info = "<br>".join([
                        f"{c['firstname']} {c['lastname']} ({c['troop']})" 
                        for c in badge_entry['counselors']
                    ])
                    
                    html += f"""
                    <tr>
                        <td>{badge_entry['badge_name']}</td>
                        <td>{counselors_info}</td>
                    </tr>
                    """
                html += "</table>"
            else:
                badge_names = [badge_entry['badge_name'] for badge_entry in badges]
                badges_html = '<div class="badge-list">'
                for badge in badge_names:
                    badge_class = "badge eagle-badge" if badge in self.eagle_required_badges else "badge"
                    badges_html += f'<span class="{badge_class}">{badge}</span>'
                badges_html += '</div>'
                html += badges_html
            
            html += '</div>'
        
        return html

    def _generate_csv_data(self, report_type: str, data: Any) -> str:
        """Generate CSV data for download."""
        # This is a simplified version - in full implementation would generate proper CSV
        return f'"Report Type","{report_type}"\n"Generated","{datetime.now()}"\n"Data","See HTML report for details"'

    def save_reports(self, troop_counselors: List[Dict], non_counselors: List[Dict], coverage: Dict):
        """Save all reports to HTML files."""
        if not self.output_dir:
            self.create_output_directory()
        
        reports = [
            ("T12/T32 Merit Badge Counselors", troop_counselors, "troop_counselors.html"),
            ("T12/T32 Leaders not Merit Badge Counselors", non_counselors, "non_counselors.html"),
            ("T12/T32 Merit Badge Counselor Coverage", coverage, "coverage_report.html")
        ]
        
        for title, data, filename in reports:
            html_content = self.generate_html_report(title, data, title)
            if self.output_dir:
                filepath = os.path.join(self.output_dir, "html", filename)
                
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    logger.info(f"Saved {title} to {filepath}")
                except Exception as e:
                    logger.error(f"Error saving {title}: {e}")
        
        # Save summary report
        self._save_summary_report(troop_counselors, non_counselors, coverage)

    def _save_summary_report(self, troop_counselors: List[Dict], non_counselors: List[Dict], coverage: Dict):
        """Save a summary report with statistics."""
        summary = {
            "generation_time": datetime.now().isoformat(),
            "statistics": {
                "total_merit_badges": len(self.all_merit_badges),
                "eagle_required_badges": len(self.eagle_required_badges),
                "troop_counselors": len(troop_counselors),
                "non_counselor_leaders": len(non_counselors),
                "eagle_badges_covered": len(coverage['eagle_with_counselors']),
                "eagle_badges_not_covered": len(coverage['eagle_without_counselors']),
                "total_badges_covered": len(coverage['eagle_with_counselors']) + len(coverage['non_eagle_with_counselors'])
            },
            "validation": {
                "total_adults_processed": len(troop_counselors) + len(non_counselors),
                "merit_badge_html_processed": len(self.merit_badge_counselors) > 0,
                "web_data_retrieved": len(self.all_merit_badges) > 0
            }
        }
        
        if self.output_dir:
            summary_path = os.path.join(self.output_dir, "summary_report.json")
            try:
                with open(summary_path, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2)
                logger.info(f"Saved summary report to {summary_path}")
            except Exception as e:
                logger.error(f"Error saving summary report: {e}")

    def process_all_data(self, t12_roster_path: str, t32_roster_path: str, html_paths: List[str]):
        """Main processing function."""
        logger.info("Starting Merit Badge Counselor processing...")
        
        # Create output directory
        self.create_output_directory()
        
        # Step 1: Fetch merit badge lists from web
        logger.info("Step 1: Fetching merit badge lists...")
        self.fetch_merit_badges_from_web()
        
        # Step 2: Parse roster files
        logger.info("Step 2: Processing roster files...")
        self.t12_roster = self.parse_roster_csv(t12_roster_path)
        self.t32_roster = self.parse_roster_csv(t32_roster_path)
        
        # Step 3: Parse merit badge counselor HTML files
        logger.info("Step 3: Processing merit badge counselor HTML files...")
        self.merit_badge_counselors = self.parse_merit_badge_html_files(html_paths)
        
        # Step 4: Cross-reference data
        logger.info("Step 4: Cross-referencing data...")
        troop_counselors = self.cross_reference_counselors()
        non_counselors = self.find_non_counselor_leaders()
        coverage = self.generate_coverage_report(troop_counselors)
        
        # Step 5: Generate reports
        logger.info("Step 5: Generating reports...")
        self.save_reports(troop_counselors, non_counselors, coverage)
        
        # Print summary
        self._print_summary(troop_counselors, non_counselors, coverage)
        
        logger.info(f"Processing complete! Reports saved to: {self.output_dir}")
        return self.output_dir

    def _print_summary(self, troop_counselors: List[Dict], non_counselors: List[Dict], coverage: Dict):
        """Print processing summary to console."""
        print("\n" + "="*60)
        print("PROCESSING SUMMARY")
        print("="*60)
        print(f"Merit Badges Total: {len(self.all_merit_badges)}")
        print(f"Eagle-Required Badges: {len(self.eagle_required_badges)}")
        print(f"T12 Roster Members: {len(self.t12_roster)}")
        print(f"T32 Roster Members: {len(self.t32_roster)}")
        print(f"Merit Badge Counselors Extracted: {len(self.merit_badge_counselors)}")
        print(f"Troop Merit Badge Counselors: {len(troop_counselors)}")
        print(f"Leaders Not Merit Badge Counselors: {len(non_counselors)}")
        print(f"Eagle Badges with Troop Counselors: {len(coverage['eagle_with_counselors'])}")
        print(f"Eagle Badges without Troop Counselors: {len(coverage['eagle_without_counselors'])}")
        print("="*60)


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Merit Badge Counselor Lists Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mbc_tool.py --t12-roster t12.csv --t32-roster t32.csv --html-files counselors1.html counselors2.html
  python mbc_tool.py --t12-roster /path/to/t12.csv --t32-roster /path/to/t32.csv --html-files /path/to/html/*.html
  
Input Requirements:
  - T12/T32 roster CSV files exported from ScoutBook
  - HTML files saved from ScoutBook Merit Badge Counselor search results
  - Internet connection for merit badge list updates (optional - uses cached data as fallback)
        """
    )
    
    parser.add_argument(
        '--t12-roster', 
        required=True,
        help='Path to T12 roster CSV file exported from ScoutBook'
    )
    
    parser.add_argument(
        '--t32-roster',
        required=True, 
        help='Path to T32 roster CSV file exported from ScoutBook'
    )
    
    parser.add_argument(
        '--html-files',
        nargs='+',
        required=True,
        help='Paths to Merit Badge Counselor HTML files saved from ScoutBook search results'
    )
    
    parser.add_argument(
        '--output-dir',
        help='Custom output directory (default: auto-generated timestamp)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input files
    input_files = [args.t12_roster, args.t32_roster] + args.html_files
    for filepath in input_files:
        if not os.path.exists(filepath):
            print(f"Error: File not found: {filepath}")
            sys.exit(1)
    
    # Validate HTML files can be read
    for html_path in args.html_files:
        if not html_path.lower().endswith('.html'):
            print(f"Warning: {html_path} does not appear to be an HTML file")
            
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if len(content) < 100:  # Very small file might be empty
                    print(f"Warning: HTML file {html_path} appears to be very small or empty")
        except Exception as e:
            print(f"Error: Cannot read HTML file {html_path}: {e}")
            sys.exit(1)
    
    # Initialize processor
    processor = MeritBadgeProcessor()
    
    # Set custom output directory if provided
    if args.output_dir:
        processor.output_dir = args.output_dir
        os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        # Process all data
        output_dir = processor.process_all_data(
            args.t12_roster,
            args.t32_roster, 
            args.html_files
        )
        
        print(f"\nSuccess! Reports generated in: {output_dir}")
        print("\nGenerated files:")
        print("- html/troop_counselors.html")
        print("- html/non_counselors.html") 
        print("- html/coverage_report.html")
        print("- summary_report.json")
        print("- mbc_tool.log")
        
        # Auto-open output directory (platform-specific)
        try:
            import subprocess
            import platform
            
            if platform.system() == "Windows":
                subprocess.run(["explorer", output_dir], check=False)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", output_dir], check=False)
            elif platform.system() == "Linux":
                subprocess.run(["xdg-open", output_dir], check=False)
        except Exception:
            pass  # Silently fail if can't open directory
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()