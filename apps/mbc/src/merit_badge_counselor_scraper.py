#!/usr/bin/env python3
"""
ScoutBook Merit Badge Counselor Scraper V2.0

Automated scraper for ScoutBook Merit Badge Counselor data using Playwright
browser automation. Leverages patterns from BeAScout project for reliable,
human-like scraping with proper authentication and pagination handling.

Target URL: https://scoutbook.scouting.org/mobile/dashboard/admin/counselorlist.asp?UnitID=82190

Requirements:
- Login credentials provided via command line (not saved)
- Default search parameters except 25-mile proximity to ZIP code
- Handle pagination for complete results
- Generate output compatible with legacy report format
"""

import asyncio
import json
import time
import random
import argparse
import getpass
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


class ScoutBookMBCScraper:
    """ScoutBook Merit Badge Counselor scraper using Playwright automation"""
    
    def __init__(self, headless=False, wait_timeout=60000, max_retries=3):  # Default non-headless for easier auth
        self.headless = headless
        self.wait_timeout = wait_timeout
        self.max_retries = max_retries
        self.playwright = None
        self.browser = None
        self.page = None
        self.session_data = {}
        
    async def setup_browser(self):
        """Initialize Playwright browser with human-like settings"""
        try:
            self.playwright = await async_playwright().start()
            
            # Launch browser with stealth options
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage', 
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # Create new page with realistic user agent
            self.page = await self.browser.new_page(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            
            # Set viewport to common resolution
            await self.page.set_viewport_size({"width": 1366, "height": 768})
            
            print("✅ Browser initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Browser setup failed: {e}")
            return False
    
    async def human_delay(self, min_seconds=2, max_seconds=5):
        """Add human-like delay between actions"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    async def login_to_scoutbook(self, username: str, password: str) -> bool:
        """Authenticate with ScoutBook using provided credentials"""
        try:
            print("🔐 Navigating to ScoutBook login...")
            
            # Navigate to ScoutBook login page
            await self.page.goto('https://scoutbook.scouting.org', wait_until='networkidle')
            await self.human_delay()
            
            # Debug: Take screenshot and log page content for troubleshooting
            print(f"📸 Current URL: {self.page.url}")
            await self.page.screenshot(path='debug_login_page.png')
            
            # Look for ScoutBook specific login form elements (wait for visible, not just present)
            print("🔍 Checking for overlays or modals that might be hiding the form...")
            
            # Check if there's a modal or overlay hiding the form
            await self.page.wait_for_timeout(3000)  # Give page time to fully load
            
            # Try to dismiss any overlays/modals
            overlay_selectors = ['.modal', '.overlay', '.popup', '[role="dialog"]', '.close-btn', 'button:has-text("×")', 'button:has-text("Close")']
            for selector in overlay_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        print(f"🎯 Found potential overlay: {selector}")
                        if 'close' in selector.lower() or '×' in selector:
                            await element.click()
                            await self.human_delay(1, 2)
                        break
                except:
                    continue
            
            # Try scrolling to make form visible
            await self.page.evaluate("window.scrollTo(0, 0)")
            await self.human_delay(1, 2)
            
            # Look for login button/link that might reveal the form
            login_triggers = ['a:has-text("Login")', 'a:has-text("Sign In")', 'button:has-text("Login")', 'button:has-text("Sign In")', '.login-trigger']
            for trigger in login_triggers:
                try:
                    element = await self.page.query_selector(trigger)
                    if element:
                        print(f"🎯 Found login trigger: {trigger}")
                        await element.click()
                        await self.human_delay(2, 3)
                        break
                except:
                    continue
            
            # Check if already logged in (login trigger might have redirected us)
            await self.human_delay(2, 3)
            current_url = self.page.url
            if 'dashboard' in current_url or 'mobile' in current_url:
                print("✅ Already logged in after clicking login trigger")
                return True
            
            print("🔍 Waiting for login form to become visible...")
            try:
                username_field = await self.page.wait_for_selector('input[name="Email"]', state='visible', timeout=10000)
                password_field = await self.page.wait_for_selector('input[name="Password"]', state='visible', timeout=10000)
                
                # Fill in credentials with human-like typing
                await username_field.type(username, delay=random.randint(50, 150))
                await self.human_delay(1, 2)
                
                await password_field.type(password, delay=random.randint(50, 150))
                await self.human_delay(1, 2)
                
                # Submit login form
                login_button = await self.page.wait_for_selector('input[type="submit"], button[type="submit"], .login-btn', timeout=5000)
                await login_button.click()
                
                # Wait for navigation after login (longer timeout for slow ScoutBook)
                await self.page.wait_for_load_state('networkidle', timeout=45000)
                
            except PlaywrightTimeoutError:
                # Form might not be visible, but check if we're already logged in
                print("⚠️ Login form not found, checking if already authenticated...")
            
            # Verify successful login
            current_url = self.page.url
            if 'dashboard' in current_url or 'mobile' in current_url:
                print("✅ Login successful")
                return True
            else:
                print(f"❌ Login may have failed - current URL: {current_url}")
                return False
                
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False
    
    async def navigate_to_counselor_search(self, unit_id: str = "82190", zip_code: str = "01720", 
                                           council_id: str = "181", district_id: str = "430", proximity: int = 25) -> bool:
        """Navigate directly to Merit Badge Counselor search results"""
        try:
            # Use direct search URL to bypass form configuration
            search_url = (f"https://scoutbook.scouting.org/mobile/dashboard/admin/counselorresults.asp?"
                         f"UnitID={unit_id}&MeritBadgeID=&formfname=&formlname=&zip={zip_code}&"
                         f"formCouncilID={council_id}&formDistrictID={district_id}&Proximity={proximity}&"
                         f"Availability=Available")
            
            print(f"🔍 Navigating directly to search results: {search_url}")
            
            await self.page.goto(search_url, wait_until='networkidle')
            await self.human_delay()
            
            # Wait for results to load
            await self.page.wait_for_selector('table, .counselor, .result, body', timeout=30000)
            print("✅ Search results page loaded")
            return True
            
        except Exception as e:
            print(f"❌ Failed to navigate to search results: {e}")
            return False
    
    async def configure_search_parameters(self, zip_code: str = None, radius_miles: int = 25) -> bool:
        """Configure search form with 25-mile radius and ZIP code if provided"""
        try:
            print("⚙️ Configuring search parameters...")
            
            # Set proximity radius to 25 miles
            radius_select = await self.page.wait_for_selector('select[name*="radius"], select[name*="proximity"], select[name*="miles"]', timeout=5000)
            if radius_select:
                await radius_select.select_option(str(radius_miles))
                print(f"✅ Set radius to {radius_miles} miles")
            
            # Set ZIP code if provided
            if zip_code:
                zip_field = await self.page.query_selector('input[name*="zip"], input[name*="postal"]')
                if zip_field:
                    await zip_field.fill(zip_code)
                    print(f"✅ Set ZIP code to {zip_code}")
            
            await self.human_delay()
            return True
            
        except Exception as e:
            print(f"❌ Failed to configure search parameters: {e}")
            return False
    
    async def execute_search(self) -> bool:
        """Execute the search with configured parameters"""
        try:
            print("🔍 Executing search...")
            
            # Look for search/submit button
            search_button = await self.page.wait_for_selector(
                'input[type="submit"], button[type="submit"], input[value*="Search"], button:has-text("Search")',
                timeout=5000
            )
            
            await search_button.click()
            await self.page.wait_for_load_state('networkidle', timeout=45000)  # Increased for slow ScoutBook
            
            print("✅ Search executed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Search execution failed: {e}")
            return False
    
    async def extract_counselor_data(self, page_number: int = 1) -> List[Dict[str, Any]]:
        """Extract Merit Badge Counselor data from current page"""
        counselors = []
        
        try:
            print("📊 Extracting counselor data from page...")
            
            # Debug: Take screenshot and analyze page structure
            await self.page.screenshot(path='debug_search_results.png')
            print(f"📸 Screenshot saved: debug_search_results.png")
            
            # Wait longer for slow ScoutBook results
            print("⏳ Waiting for search results to load (ScoutBook is slow)...")
            await self.page.wait_for_timeout(10000)  # Give ScoutBook extra time
            
            # Debug: Check what elements are actually on the page
            print("🔍 Analyzing page structure...")
            page_text = await self.page.inner_text('body')
            print(f"📝 Page contains {len(page_text)} characters")
            
            # Look for common result patterns
            tables = await self.page.query_selector_all('table')
            print(f"📋 Found {len(tables)} tables")
            
            divs = await self.page.query_selector_all('div')
            print(f"📦 Found {len(divs)} divs")
            
            # Try broader selectors first
            try:
                await self.page.wait_for_selector('table, .counselor, .result, div, td, tr', timeout=5000)
                print("✅ Found some content elements")
            except:
                print("❌ No standard content elements found")
            
            # Extract counselor data based on ScoutBook mobile results structure
            # From screenshot: each counselor is in a block with name, location, contact, badges, expiration
            
            page_content = await self.page.content()
            
            # Save HTML file using run timestamp and page number
            html_file = f"{self.scraped_dir}/counselor_search_results_page_{page_number}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(page_content)
            print(f"💾 HTML saved to {html_file}")
            
            # Look for counselor result blocks - they seem to be in a repeating pattern
            # Try to find sections that contain counselor information
            counselor_sections = await self.page.query_selector_all('div[style*="border"], .result-item, .counselor-item')
            print(f"🔍 Found {len(counselor_sections)} potential counselor sections")
            
            if True:  # Force regex approach for now
                # Try broader approach - look for divs that contain email addresses
                print("🔍 Trying alternative approach - searching by content patterns...")
                
                # Get all text content and parse it for counselor data
                import re
                
                # Parse using BeautifulSoup for better structure detection (from legacy code)
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(page_content, 'html.parser')
                
                # Look for counselor entries using legacy patterns
                counselor_selectors = [
                    'div[style*="margin-left: 65px"]',  # Legacy pattern
                    '.counselor-entry',
                    '.mb-counselor', 
                    'div.counselor'
                ]
                
                counselor_divs = []
                for selector in counselor_selectors:
                    counselor_divs = soup.select(selector)
                    if counselor_divs:
                        print(f"🎯 Found {len(counselor_divs)} counselor divs using selector: {selector}")
                        break
                
                if not counselor_divs:
                    # Fallback: look for any div containing email patterns
                    all_divs = soup.find_all('div')
                    counselor_divs = [div for div in all_divs if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', div.get_text())]
                    print(f"🔍 Fallback: Found {len(counselor_divs)} divs with email patterns")
                
                # Parse each counselor div using adapted legacy logic
                structured_counselors = []
                for i, div in enumerate(counselor_divs[:10]):  # Limit for testing
                    counselor = self._parse_counselor_div_legacy(div, i+1)
                    if counselor:
                        structured_counselors.append(counselor)
                
                if structured_counselors:
                    return structured_counselors
                
                # If structured parsing fails, fall back to regex patterns
                name_location_pattern = r'([A-Z][a-z]+ (?:\([A-Z][a-z]+\) )?[A-Z][a-z]+)\s*\n([A-Za-z,\s]+\d{5})'
                matches = re.findall(name_location_pattern, page_content)
                print(f"👤 Regex fallback: Found {len(matches)} name-location pairs")
                
                # Email pattern for extracting contact info
                email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
                emails = re.findall(email_pattern, page_content)
                print(f"📧 Found {len(emails)} email addresses")
                
                # Phone pattern (XXX) XXX-XXXX
                phone_pattern = r'\((\d{3})\)\s(\d{3})-(\d{4})'
                phones = re.findall(phone_pattern, page_content)
                print(f"📞 Found {len(phones)} phone numbers")
                
                # Expiration date pattern (MM/DD/YYYY)
                expiry_pattern = r'Expires:\s*(\d{1,2}/\d{1,2}/\d{4})'
                expiries = re.findall(expiry_pattern, page_content)
                print(f"📅 Found {len(expiries)} expiration dates")
                
                # Merit badge patterns - look for checked boxes or badge names
                badge_pattern = r'(Coin Collecting|Cooking|Golf|Painting|Skating|Citizenship|Communication|Family Life|Genealogy|Personal Management|Camping|Cycling|Hiking|Personal Fitness)'
                badges = re.findall(badge_pattern, page_content)
                print(f"🏅 Found {len(badges)} merit badge mentions")
                
                # Try to correlate the data - for now, create entries based on what we found
                max_counselors = max(len(matches), len(emails), len(expiries))
                print(f"📊 Attempting to extract {max_counselors} counselor records")
                
                for i in range(min(max_counselors, 10)):  # Limit to 10 for testing
                    counselor = {
                        'name': matches[i][0] if i < len(matches) else 'Unknown',
                        'location': matches[i][1] if i < len(matches) else 'Unknown',
                        'email': emails[i] if i < len(emails) else '',
                        'phone': f"({phones[i][0]}) {phones[i][1]}-{phones[i][2]}" if i < len(phones) else '',
                        'ypt_expiration': expiries[i] if i < len(expiries) else '',
                        'merit_badges': ', '.join(badges[i:i+3]) if badges else '',  # Take a few badges
                        'extraction_timestamp': datetime.now().isoformat()
                    }
                    counselors.append(counselor)
            
            else:
                # Process individual counselor sections
                for i, section in enumerate(counselor_sections[:3]):  # Just first 3 for debugging
                    try:
                        section_text = await section.inner_text()
                        print(f"🔍 Section {i+1} text (first 200 chars): {section_text[:200]}...")
                        counselor = self._parse_counselor_section(section_text)
                        if counselor:
                            print(f"✅ Successfully parsed counselor: {counselor['name']}")
                            counselors.append(counselor)
                        else:
                            print(f"❌ Failed to parse section {i+1}")
                    except Exception as e:
                        print(f"⚠️ Failed to process counselor section {i+1}: {e}")
                        continue
            
            print(f"✅ Extracted {len(counselors)} counselors from current page")
            return counselors
            
        except Exception as e:
            print(f"❌ Data extraction failed: {e}")
            return []
    
    async def check_for_pagination(self) -> bool:
        """Check if there are more pages of results"""
        try:
            # Look for ScoutBook pagination controls - page number input and Go to Page button
            page_input = await self.page.query_selector('input[name="PageNumber2"], input[name="pageNumber2"]')
            go_button = await self.page.query_selector('input[name="gotoPageNumber2"], input[value*="Go to Page"]')
            
            if page_input and go_button:
                # Check current page vs total pages
                current_page = await page_input.get_attribute('value')
                page_count_input = await self.page.query_selector('input[name="pageCount"], #pageCount')
                if page_count_input:
                    total_pages = await page_count_input.get_attribute('value')
                    print(f"📄 Pagination: Page {current_page} of {total_pages}")
                    return int(current_page) < int(total_pages)
                else:
                    # Fallback: assume more pages if we have pagination controls
                    print(f"📄 Found pagination controls, current page: {current_page}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"⚠️ Pagination check failed: {e}")
            return False
    
    async def navigate_to_next_page(self) -> bool:
        """Navigate to next page of results using ScoutBook pagination"""
        try:
            print("➡️ Navigating to next page...")
            
            # Get current page number and increment it
            page_input = await self.page.query_selector('input[name="PageNumber2"], input[name="pageNumber2"]')
            if not page_input:
                print("❌ Could not find page number input")
                return False
                
            current_page = await page_input.get_attribute('value')
            next_page = int(current_page) + 1
            print(f"📄 Going from page {current_page} to page {next_page}")
            
            # Set the new page number
            await page_input.fill(str(next_page))
            
            # Try direct JavaScript navigation (ScoutBook uses $.mobile.changePage)
            base_url = "https://scoutbook.scouting.org/mobile/dashboard/admin/counselorresults.asp"
            params = f"?UnitID=82190&MeritBadgeID=&formfname=&formlname=&zip=01720&formCouncilID=181&formDistrictID=430&Proximity=25&Availability=Available&Page={next_page}"
            new_url = base_url + params
            
            print(f"🔗 Navigating directly to: {new_url}")
            await self.page.goto(new_url, wait_until='networkidle', timeout=45000)
            await self.human_delay()
            
            print(f"✅ Successfully navigated to page {next_page}")
            return True
            
        except Exception as e:
            print(f"❌ Next page navigation failed: {e}")
            return False
    
    async def scrape_all_counselors(self, username: str = None, password: str = None, unit_id: str = "82190", 
                                   zip_code: str = "01720", council_id: str = "181", district_id: str = "430") -> List[Dict[str, Any]]:
        """Complete scraping workflow for all Merit Badge Counselors"""
        all_counselors = []
        
        # Generate single timestamp for entire run
        from datetime import datetime
        import os
        self.run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.scraped_dir = f"data/scraped/{self.run_timestamp}"
        os.makedirs(self.scraped_dir, exist_ok=True)
        print(f"📁 Created run directory: {self.scraped_dir}")
        
        try:
            # Setup browser
            if not await self.setup_browser():
                return []
            
            # Login if credentials provided, otherwise expect manual login
            if username and password:
                if not await self.login_to_scoutbook(username, password):
                    return []
            else:
                print("🔐 Please log in manually in the browser window...")
                await self.page.goto('https://scoutbook.scouting.org', wait_until='networkidle', timeout=60000)
                print("⏱️ Waiting 60 seconds for manual login...")
                await self.page.wait_for_timeout(60000)  # Wait 60 seconds for manual login
            
            # Navigate directly to search results
            if not await self.navigate_to_counselor_search(unit_id, zip_code, council_id, district_id):
                return []
            
            # Extract data from all pages (detect total pages dynamically)
            page_number = 1
            max_pages = None  # Will be detected from page
            
            while True:
                print(f"📄 Processing page {page_number}...")
                
                page_counselors = await self.extract_counselor_data(page_number)
                all_counselors.extend(page_counselors)
                
                # Detect total pages on first run
                if max_pages is None:
                    page_count_input = await self.page.query_selector('input[name="pageCount"], #pageCount')
                    if page_count_input:
                        total_pages_str = await page_count_input.get_attribute('value')
                        max_pages = int(total_pages_str)
                        print(f"📚 Detected {max_pages} total pages")
                    else:
                        max_pages = 999  # Fallback: rely on pagination detection
                        print("⚠️ Could not detect total pages, will rely on pagination detection")

                # Check for more pages
                if await self.check_for_pagination():
                    if page_number >= max_pages:
                        print(f"✅ Reached final page ({page_number} of {max_pages})")
                        break
                    if await self.navigate_to_next_page():
                        page_number += 1
                        await self.human_delay(1, 2)  # Reduced delay for urgent report generation
                        continue
                    else:
                        print("❌ Failed to navigate to next page, stopping")
                        break
                else:
                    print("✅ No more pages to process")
                    break
            
            print(f"🎉 Scraping complete! Total counselors extracted: {len(all_counselors)}")
            return all_counselors
            
        except Exception as e:
            print(f"❌ Scraping workflow failed: {e}")
            return []
        
        finally:
            await self.cleanup()
    
    def _parse_counselor_div_legacy(self, div, counselor_num: int) -> Optional[Dict[str, Any]]:
        """Parse counselor data from HTML div using legacy enhanced scraper patterns"""
        import re
        
        try:
            counselor = {
                'name': '',
                'first_name': '',
                'alt_first_name': '', 
                'last_name': '',
                'location': '',
                'email': '',
                'phone': '',
                'phone_home': '',
                'phone_mobile': '',
                'phone_work': '',
                'ypt_expiration': '',
                'merit_badges': '',
                'extraction_timestamp': datetime.now().isoformat()
            }
            
            # Get text content and lines
            full_text = div.get_text()
            text_content = full_text
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            
            print(f"  📋 Counselor {counselor_num} has {len(lines)} text lines")
            if len(lines) > 0:
                print(f"  🔍 Sample lines: {lines[:5]}")  # Show first 5 lines
            print(f"  📝 Full text preview: {full_text[:200]}...")  # Show first 200 chars
            
            if not lines:
                return None
            
            # Extract name from first line (legacy logic)
            name_line = lines[0]
            print(f"  👤 Name line: '{name_line}'")
            
            # Parse name with alternate name support: "Timothy (Tim) Werner"
            alt_match = re.search(r'(\w+)\s*\(([^)]+)\)\s*(.+)', name_line)
            if alt_match:
                counselor["first_name"] = alt_match.group(1)
                counselor["alt_first_name"] = alt_match.group(2) 
                counselor["last_name"] = alt_match.group(3)
                counselor["name"] = f"{alt_match.group(1)} ({alt_match.group(2)}) {alt_match.group(3)}"
            else:
                name_parts = name_line.split()
                if len(name_parts) >= 2:
                    counselor["first_name"] = name_parts[0]
                    counselor["last_name"] = " ".join(name_parts[1:])
                    counselor["name"] = name_line
            
            # Extract location - check for both div.address and direct text pattern
            address_div = div.find('div', class_='address')
            if address_div:
                address_text = address_div.get_text().strip()
                # Clean up address - extract Town/State/Zip portion
                address_lines = [line.strip() for line in address_text.split('\n') if line.strip()]
                # Filter out phone/email lines, keep geographic location
                location_lines = []
                for line in address_lines:
                    if not any(keyword in line.lower() for keyword in ['home', 'mobile', 'work', '@', 'expires']):
                        if re.search(r'\b[A-Z]{2}\b|\d{5}', line):  # Contains state or zip
                            location_lines.append(line)
                counselor["location"] = ", ".join(location_lines)
            else:
                # Look for location pattern in lines - based on debug output, it's in lines[1]
                # Format: "Acton, MA 01720Home (978) 263-4038Mobile (508) 782-8502"
                if len(lines) > 1:
                    location_line = lines[1]
                    print(f"  🗺️ Location line: '{location_line}'")
                    # Extract location part before phone numbers
                    # Pattern: "Acton, MA 01720Home (978) 263-4038Mobile..."
                    location_match = re.search(r'([A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5})(?=Home|Mobile|Work|\(|$)', location_line)
                    if location_match:
                        counselor["location"] = location_match.group(1)
                        print(f"  ✅ Extracted location: '{counselor['location']}'")
                    else:
                        print(f"  ❌ Location regex failed on: '{location_line}'")
                        # Try broader pattern in full text
                        location_match = re.search(r'([A-Za-z\s]+),\s*([A-Z]{2})\s*(\d{5})', full_text)
                        if location_match:
                            counselor["location"] = f"{location_match.group(1)}, {location_match.group(2)} {location_match.group(3)}"
                            print(f"  ✅ Fallback location: '{counselor['location']}'")
            
            # Extract contact info from full text
            
            # Phone numbers (legacy patterns)
            phone_patterns = [
                (r'Home[:\s]*\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})', "phone_home"),
                (r'Mobile[:\s]*\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})', "phone_mobile"), 
                (r'Work[:\s]*\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})', "phone_work")
            ]
            
            for pattern, field in phone_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    counselor[field] = f"({match.group(1)}) {match.group(2)}-{match.group(3)}"
            
            # Set primary phone to first available
            counselor["phone"] = counselor["phone_home"] or counselor["phone_mobile"] or counselor["phone_work"]
            
            # Email (legacy pattern)
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', full_text)
            if email_match:
                counselor["email"] = email_match.group(1)
            
            # Youth Protection expiration - look for div.yptDate in current div and parent containers
            ypt_div = div.find('div', class_='yptDate')
            if not ypt_div:
                # Look in parent containers (yptDate might be a sibling)
                parent = div.parent
                while parent and parent.name == 'div' and not ypt_div:
                    ypt_div = parent.find('div', class_='yptDate')
                    parent = parent.parent
            
            if ypt_div:
                ypt_text = ypt_div.get_text().strip()
                print(f"  📅 Found yptDate div: '{ypt_text}'")
                # Extract date from text like "Expires: 12/5/2026"
                date_match = re.search(r'Expires:\s*(\d{1,2}/\d{1,2}/\d{4})', ypt_text, re.IGNORECASE)
                if date_match:
                    counselor["ypt_expiration"] = date_match.group(1)
                    print(f"  ✅ Extracted YPT expiration: {counselor['ypt_expiration']}")
            else:
                # Fallback: Look for "Expires:" pattern in the full text
                yp_match = re.search(r'Expires:\s*(\d{1,2}/\d{1,2}/\d{4})', full_text, re.IGNORECASE)
                if yp_match:
                    counselor["ypt_expiration"] = yp_match.group(1)
                    print(f"  ✅ Found YPT in full text: {counselor['ypt_expiration']}")
                else:
                    print(f"  ❌ No YPT expiration found for {counselor['name']}")
            
            # Merit badges from div.mbContainer as per requirements
            mb_container = div.find('div', class_='mbContainer')
            badge_list = []
            
            if mb_container:
                # Look for specific structure: div.mb.ui-corner-all.ui-shadow
                badge_divs = mb_container.find_all('div', class_='mb ui-corner-all ui-shadow')
                if not badge_divs:
                    # Fallback: look for any div with 'mb' class
                    badge_divs = mb_container.find_all('div', class_=lambda x: x and 'mb' in x.lower())
                
                for badge_div in badge_divs:
                    badge_text = badge_div.get_text().strip()
                    # Filter out checkmark images and council info
                    if badge_text and not any(phrase in badge_text.lower() for phrase in ['council', 'heart', 'england', 'approved', 'checkbox']):
                        badge_list.append(badge_text)
            else:
                # Fallback: look for common merit badge names in text
                badge_keywords = ['Coin Collecting', 'Cooking', 'Golf', 'Painting', 'Skating', 
                                 'Citizenship in Society', 'Citizenship in the Community', 'Citizenship in the Nation', 'Citizenship in the World',
                                 'Communication', 'Family Life', 'Genealogy', 'Personal Management', 
                                 'Camping', 'Cycling', 'Hiking', 'Personal Fitness']
                found_badges = [badge for badge in badge_keywords if badge in full_text]
                badge_list = found_badges[:3]  # Limit to avoid duplicates
            
            counselor["merit_badges"] = ", ".join(badge_list)
            
            print(f"  ✅ Parsed: {counselor['name']} | {counselor['location']} | {counselor['email']}")
            
            # Return if we have basic info
            if counselor["name"] and (counselor["email"] or counselor["phone"]):
                return counselor
            else:
                print(f"  ❌ Insufficient data for counselor {counselor_num}")
                return None
                
        except Exception as e:
            print(f"  ⚠️ Error parsing counselor {counselor_num}: {e}")
            return None

    def _parse_counselor_section(self, section_text: str) -> Optional[Dict[str, Any]]:
        """Parse individual counselor section text to extract structured data"""
        import re
        
        lines = section_text.strip().split('\n')
        if len(lines) < 3:
            return None
        
        counselor = {
            'name': '',
            'location': '',
            'email': '',
            'phone': '',
            'ypt_expiration': '',
            'merit_badges': '',
            'extraction_timestamp': datetime.now().isoformat()
        }
        
        # First line should be name
        counselor['name'] = lines[0].strip()
        
        # Look for location (town, state, zip)
        location_pattern = r'([A-Za-z\s,]+\d{5})'
        location_match = re.search(location_pattern, section_text)
        if location_match:
            counselor['location'] = location_match.group(1).strip()
        
        # Extract email
        email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        email_match = re.search(email_pattern, section_text)
        if email_match:
            counselor['email'] = email_match.group(1)
        
        # Extract phone
        phone_pattern = r'\((\d{3})\)\s(\d{3})-(\d{4})'
        phone_match = re.search(phone_pattern, section_text)
        if phone_match:
            counselor['phone'] = f"({phone_match.group(1)}) {phone_match.group(2)}-{phone_match.group(3)}"
        
        # Extract expiration date
        expiry_pattern = r'Expires:\s*(\d{1,2}/\d{1,2}/\d{4})'
        expiry_match = re.search(expiry_pattern, section_text)
        if expiry_match:
            counselor['ypt_expiration'] = expiry_match.group(1)
        
        # Extract merit badges (this will need refinement based on actual structure)
        badge_keywords = ['Coin Collecting', 'Cooking', 'Golf', 'Painting', 'Skating', 'Citizenship', 
                         'Communication', 'Family Life', 'Genealogy', 'Personal Management', 
                         'Camping', 'Cycling', 'Hiking', 'Personal Fitness']
        found_badges = [badge for badge in badge_keywords if badge in section_text]
        counselor['merit_badges'] = ', '.join(found_badges)
        
        return counselor if counselor['name'] else None

    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            print("🧹 Browser cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")


def save_counselor_data(counselors: List[Dict[str, Any]], output_file: str):
    """Save counselor data to JSON file"""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            'extraction_metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_counselors': len(counselors),
                'source': 'ScoutBook Merit Badge Counselor List'
            },
            'counselors': counselors
        }, f, indent=2)
    
    print(f"💾 Data saved to {output_path}")


async def main():
    """Main CLI interface for ScoutBook MBC scraper"""
    parser = argparse.ArgumentParser(description='ScoutBook Merit Badge Counselor Scraper V2.0')
    parser.add_argument('--unit-id', default='82190', help='ScoutBook Unit ID')
    parser.add_argument('--zip-code', help='ZIP code for proximity search')
    parser.add_argument('--output', default='data/processed/mbc_counselors.json', help='Output file path')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--username', help='ScoutBook username (optional - will use manual login if not provided)')
    parser.add_argument('--password', help='ScoutBook password (optional - will use manual login if not provided)')
    parser.add_argument('--council-id', default='181', help='Council ID (default: 181)')
    parser.add_argument('--district-id', default='430', help='District ID (default: 430)')
    
    args = parser.parse_args()
    
    # Get credentials (optional now)
    username = args.username
    password = args.password
    
    if username and not password:
        password = getpass.getpass("ScoutBook Password: ")
    
    # Initialize scraper
    scraper = ScoutBookMBCScraper(headless=args.headless)
    
    # Run scraping
    counselors = await scraper.scrape_all_counselors(
        username=username,
        password=password, 
        unit_id=args.unit_id,
        zip_code=args.zip_code or "01720",
        council_id=args.council_id,
        district_id=args.district_id
    )
    
    # Save results
    if counselors:
        save_counselor_data(counselors, args.output)
        print(f"✅ Successfully scraped {len(counselors)} Merit Badge Counselors")
    else:
        print("❌ No counselor data extracted")


if __name__ == "__main__":
    asyncio.run(main())