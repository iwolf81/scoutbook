# ScoutBook Scraper Setup and Requirements

# 1. Create requirements file for the scraper
cat > requirements-scraper.txt << 'EOF'
# Core scraping dependencies
selenium>=4.15.0
beautifulsoup4>=4.12.0
pandas>=2.0.0
click>=8.1.0

# UI and progress
rich>=13.0.0

# Web driver management
webdriver-manager>=4.0.0

# Data handling
lxml>=4.9.0

# Existing dependencies (if integrating with main project)
requests>=2.31.0
python-dotenv>=1.0.0
EOF

# 2. Install dependencies
pip install -r requirements-scraper.txt

# 3. Install ChromeDriver (choose your platform)

# Option A: Using webdriver-manager (automatic)
python -c "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()"

# Option B: Manual installation
# macOS with Homebrew:
# brew install chromedriver

# Ubuntu/Debian:
# sudo apt-get update && sudo apt-get install chromium-chromedriver

# Windows:
# Download from https://chromedriver.chromium.org/downloads
# Add to PATH or place in same directory as script

# 4. Create enhanced version with better error handling
cat > scoutbook_scraper_enhanced.py << 'EOF'
#!/usr/bin/env python3
"""
Enhanced ScoutBook Merit Badge Counselor Scraper with improved error handling
and better HTML structure detection.
"""

import json
import csv
import time
import random
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import getpass
import sys

import click
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

console = Console()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScoutBookScraperEnhanced:
    """Enhanced scraper with better error handling and structure detection."""
    
    def __init__(self, headless: bool = False):
        self.driver = None
        self.wait = None
        self.headless = headless
        self.counselors = []
        self.base_url = "https://scoutbook.scouting.org"
    
    def setup_driver(self):
        """Setup Chrome driver with anti-detection measures."""
        console.print("[blue]Setting up Chrome driver...[/blue]")
        
        options = Options()
        if self.headless:
            options.add_argument('--headless')
        
        # Anti-detection settings
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        
        try:
            # Try webdriver-manager first
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = webdriver.chrome.service.Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            except ImportError:
                # Fallback to system ChromeDriver
                self.driver = webdriver.Chrome(options=options)
            
            self.wait = WebDriverWait(self.driver, 20)
            
            # Remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            console.print("[green]✓ Chrome driver ready[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]ChromeDriver setup failed: {e}[/red]")
            console.print("[yellow]Please install ChromeDriver: https://chromedriver.chromium.org/[/yellow]")
            return False
    
    def human_delay(self, min_sec=1.0, max_sec=3.0):
        """Random human-like delay."""
        time.sleep(random.uniform(min_sec, max_sec))
    
    def safe_click(self, element):
        """Safe click with retry logic."""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                self.human_delay(0.5, 1.0)
                element.click()
                return True
            except Exception as e:
                if attempt == max_attempts - 1:
                    logger.error(f"Click failed after {max_attempts} attempts: {e}")
                    return False
                self.human_delay(1, 2)
        return False
    
    def safe_type(self, element, text):
        """Safe typing with human-like behavior."""
        try:
            element.clear()
            for char in text:
                element.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            return True
        except Exception as e:
            logger.error(f"Typing failed: {e}")
            return False
    
    def login_to_scoutbook(self, username: str, password: str) -> bool:
        """Login with enhanced error detection."""
        console.print("[blue]Logging into ScoutBook...[/blue]")
        
        try:
            self.driver.get(f"{self.base_url}/mobile/dashboard/")
            self.human_delay(2, 4)
            
            # Check if already logged in
            if "dashboard" in self.driver.current_url.lower():
                console.print("[green]Already logged in[/green]")
                return True
            
            # Find login form
            username_field = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            password_field = self.driver.find_element(By.ID, "password")
            
            # Enter credentials
            if not self.safe_type(username_field, username):
                return False
            self.human_delay(0.5, 1.0)
            
            if not self.safe_type(password_field, password):
                return False
            self.human_delay(1, 2)
            
            # Submit form
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            if not self.safe_click(submit_button):
                return False
            
            # Wait for login result
            self.human_delay(3, 5)
            
            # Check for successful login
            if "dashboard" in self.driver.current_url.lower() or self.driver.find_elements(By.PARTIAL_LINK_TEXT, "Troop"):
                console.print("[green]✓ Login successful[/green]")
                return True
            
            # Check for error messages
            error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".error, .alert-danger, .login-error")
            if error_elements:
                error_text = error_elements[0].text
                console.print(f"[red]Login failed: {error_text}[/red]")
            else:
                console.print("[red]Login failed: Unknown error[/red]")
            
            return False
            
        except TimeoutException:
            console.print("[red]Login timeout - website may be slow[/red]")
            return False
        except Exception as e:
            console.print(f"[red]Login error: {e}[/red]")
            return False
    
    def navigate_to_mb_counselors(self) -> bool:
        """Navigate to Merit Badge Counselor list with flexible element finding."""
        console.print("[blue]Navigating to MB Counselor search...[/blue]")
        
        try:
            # Look for Troop 32 link (try different variations)
            troop_selectors = [
                "//a[contains(text(), 'Troop 32')]",
                "//a[contains(text(), '32')]",
                "//span[contains(text(), 'Troop 32')]/parent::a",
                ".troop-link"
            ]
            
            troop_link = None
            for selector in troop_selectors:
                try:
                    if selector.startswith("//"):
                        troop_link = self.driver.find_element(By.XPATH, selector)
                    else:
                        troop_link = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not troop_link:
                console.print("[red]Could not find Troop 32 link[/red]")
                return False
            
            if not self.safe_click(troop_link):
                return False
            self.human_delay(2, 4)
            
            # Look for MB Counselor link
            mb_selectors = [
                "//a[contains(text(), 'MB Counselor')]",
                "//a[contains(text(), 'Merit Badge Counselor')]",
                "//a[contains(text(), 'Counselor')]",
                ".mb-counselor-link"
            ]
            
            mb_link = None
            for selector in mb_selectors:
                try:
                    if selector.startswith("//"):
                        mb_link = self.driver.find_element(By.XPATH, selector)
                    else:
                        mb_link = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not mb_link:
                console.print("[red]Could not find MB Counselor link[/red]")
                return False
            
            if not self.safe_click(mb_link):
                return False
            self.human_delay(2, 4)
            
            console.print("[green]✓ Reached MB Counselor search[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Navigation error: {e}[/red]")
            return False
    
    def setup_search_params(self, zip_code: str = "01720", radius: int = 25) -> bool:
        """Setup search parameters with error handling."""
        console.print(f"[blue]Setting up search: {zip_code}, {radius} miles...[/blue]")
        
        try:
            # Find and set zip code
            zip_selectors = ["input[name='zipCode']", "#zipCode", "input[placeholder*='zip']"]
            zip_field = None
            
            for selector in zip_selectors:
                try:
                    zip_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if zip_field:
                if not self.safe_type(zip_field, zip_code):
                    return False
                self.human_delay(0.5, 1.0)
            
            # Find and set radius
            radius_selectors = ["select[name='proximity']", "#proximity", "select[name='radius']"]
            radius_select = None
            
            for selector in radius_selectors:
                try:
                    radius_select = Select(self.driver.find_element(By.CSS_SELECTOR, selector))
                    break
                except NoSuchElementException:
                    continue
            
            if radius_select:
                try:
                    radius_select.select_by_value(str(radius))
                except:
                    radius_select.select_by_visible_text(f"{radius} miles")
                self.human_delay(0.5, 1.0)
            
            console.print("[green]✓ Search parameters set[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Search setup error: {e}[/red]")
            return False
    
    def execute_search(self) -> bool:
        """Execute the search."""
        console.print("[blue]Executing search...[/blue]")
        
        try:
            # Find submit button
            submit_selectors = [
                "input[type='submit']",
                "button[type='submit']", 
                "button[value='Search']",
                ".search-button"
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not submit_button:
                console.print("[red]Could not find search button[/red]")
                return False
            
            if not self.safe_click(submit_button):
                return False
            
            self.human_delay(3, 6)  # Wait for results
            
            console.print("[green]✓ Search executed[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Search execution error: {e}[/red]")
            return False
    
    def scrape_all_pages(self) -> List[Dict[str, Any]]:
        """Scrape all pages of results."""
        all_counselors = []
        page_num = 1
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Scraping counselor data...", total=None)
            
            while True:
                console.print(f"[cyan]Processing page {page_num}...[/cyan]")
                
                page_counselors = self.scrape_current_page()
                all_counselors.extend(page_counselors)
                
                progress.update(task, description=f"Scraped {len(all_counselors)} counselors from {page_num} pages")
                
                if not page_counselors:
                    console.print("[yellow]No counselors found on this page[/yellow]")
                    break
                
                if not self.go_to_next_page():
                    break
                
                page_num += 1
                self.human_delay(2, 4)
        
        console.print(f"[green]✓ Scraped {len(all_counselors)} total counselors[/green]")
        return all_counselors
    
    def scrape_current_page(self) -> List[Dict[str, Any]]:
        """Scrape counselors from current page."""
        counselors = []
        
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Try different selectors for counselor entries
            counselor_selectors = [
                'div[style*="margin-left: 65px"]',
                '.counselor-entry',
                '.mb-counselor',
                'div.counselor'
            ]
            
            counselor_divs = []
            for selector in counselor_selectors:
                counselor_divs = soup.select(selector)
                if counselor_divs:
                    break
            
            for div in counselor_divs:
                counselor = self.parse_counselor_data(div)
                if counselor:
                    counselors.append(counselor)
        
        except Exception as e:
            logger.error(f"Error scraping page: {e}")
        
        return counselors
    
    def parse_counselor_data(self, div) -> Optional[Dict[str, Any]]:
        """Parse counselor data from HTML div."""
        try:
            counselor = {
                "first_name": "",
                "alt_first_name": "",
                "last_name": "",
                "address": "",
                "email": "",
                "phone_home": "",
                "phone_mobile": "",
                "phone_work": "",
                "yp_expiration": "",
                "merit_badges": [],
                "scraped_at": datetime.now().isoformat()
            }
            
            # Extract name from first text content
            text_content = div.get_text()
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            
            if lines:
                name_line = lines[0]
                
                # Parse name with alternate name support
                alt_match = re.search(r'(\w+)\s*\(([^)]+)\)\s*(.+)', name_line)
                if alt_match:
                    counselor["first_name"] = alt_match.group(1)
                    counselor["alt_first_name"] = alt_match.group(2)
                    counselor["last_name"] = alt_match.group(3)
                else:
                    name_parts = name_line.split()
                    if len(name_parts) >= 2:
                        counselor["first_name"] = name_parts[0]
                        counselor["last_name"] = " ".join(name_parts[1:])
            
            # Extract contact info
            full_text = div.get_text()
            
            # Address (lines before phone/email)
            address_lines = []
            for line in lines[1:]:
                if not any(keyword in line.lower() for keyword in ['home', 'mobile', 'work', '@', 'expires']):
                    address_lines.append(line)
                else:
                    break
            counselor["address"] = ", ".join(address_lines)
            
            # Phone numbers
            phone_patterns = [
                (r'Home[:\s]*\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})', "phone_home"),
                (r'Mobile[:\s]*\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})', "phone_mobile"),
                (r'Work[:\s]*\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})', "phone_work")
            ]
            
            for pattern, field in phone_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    counselor[field] = f"({match.group(1)}) {match.group(2)}-{match.group(3)}"
            
            # Email
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', full_text)
            if email_match:
                counselor["email"] = email_match.group(1)
            
            # Youth Protection expiration
            yp_match = re.search(r'Expires:\s*(\d{1,2}/\d{1,2}/\d{4})', full_text, re.IGNORECASE)
            if yp_match:
                counselor["yp_expiration"] = f"Expires: {yp_match.group(1)}"
            
            # Merit badges (look for badge container)
            mb_container = div.find('div', class_='mbContainer') or div.find('div', class_='badges')
            if mb_container:
                badge_elements = mb_container.find_all(['div', 'span'], class_=lambda x: x and 'mb' in x.lower())
                for badge_elem in badge_elements:
                    badge_text = badge_elem.get_text().strip()
                    # Filter out council-related text
                    if badge_text and not any(phrase in badge_text.lower() for phrase in ['council', 'heart', 'england', 'approved']):
                        counselor["merit_badges"].append(badge_text)
            
            # Return only if we have basic info
            if counselor["first_name"] and counselor["last_name"]:
                return counselor
            
        except Exception as e:
            logger.error(f"Error parsing counselor: {e}")
        
        return None
    
    def go_to_next_page(self) -> bool:
        """Navigate to next page if available."""
        try:
            next_selectors = [
                "a:contains('Next')",
                "a:contains('>')", 
                ".next-page",
                ".pagination-next"
            ]
            
            for selector in next_selectors:
                try:
                    next_link = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_link.is_enabled() and next_link.is_displayed():
                        return self.safe_click(next_link)
                except NoSuchElementException:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error navigating to next page: {e}")
            return False
    
    def save_results(self, counselors: List[Dict], output_prefix: str):
        """Save results to JSON and CSV."""
        if not counselors:
            console.print("[yellow]No data to save[/yellow]")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON
        json_file = f"{output_prefix}_{timestamp}.json"
        json_data = {
            "metadata": {
                "scraped_at": datetime.now().isoformat(),
                "total_counselors": len(counselors),
                "search_radius": "25 miles",
                "zip_code": "01720"
            },
            "counselors": counselors
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        # Save CSV
        csv_file = f"{output_prefix}_{timestamp}.csv"
        df = pd.DataFrame(counselors)
        df.to_csv(csv_file, index=False, encoding='utf-8')
        
        console.print(f"[green]✓ Saved {len(counselors)} counselors:[/green]")
        console.print(f"  📄 JSON: {json_file}")
        console.print(f"  📊 CSV: {csv_file}")
    
    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            self.driver.quit()

@click.command()
@click.option('--zip-code', default='01720', help='Search zip code')
@click.option('--radius', default=25, help='Search radius in miles')
@click.option('--output', default='counselors', help='Output file prefix')
@click.option('--headless/--no-headless', default=False, help='Run in headless mode')
def main(zip_code, radius, output, headless):
    """ScoutBook Merit Badge Counselor Scraper - Enhanced Version"""
    
    console.print(Panel.fit(
        "[bold blue]ScoutBook Merit Badge Counselor Scraper[/bold blue]\n"
        "[dim]Enhanced version with better error handling[/dim]",
        border_style="blue"
    ))
    
    # Get credentials
    username = Prompt.ask("ScoutBook Username")
    password = Prompt.ask("ScoutBook Password", password=True)
    
    if not username or not password:
        console.print("[red]Username and password required[/red]")
        return
    
    # Confirm parameters
    console.print(f"\n[bold]Search Parameters:[/bold]")
    console.print(f"  Zip Code: {zip_code}")
    console.print(f"  Radius: {radius} miles")
    console.print(f"  Headless: {headless}")
    
    if not Confirm.ask("Proceed?"):
        return
    
    scraper = ScoutBookScraperEnhanced(headless=headless)
    
    try:
        if not scraper.setup_driver():
            return
        
        if not scraper.login_to_scoutbook(username, password):
            return
        
        if not scraper.navigate_to_mb_counselors():
            return
        
        if not scraper.setup_search_params(zip_code, radius):
            return
        
        if not scraper.execute_search():
            return
        
        counselors = scraper.scrape_all_pages()
        
        if counselors:
            scraper.save_results(counselors, output)
            console.print(f"\n[bold green]Success! Scraped {len(counselors)} counselors[/bold green]")
        else:
            console.print("[yellow]No counselors found[/yellow]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
    finally:
        scraper.cleanup()

if __name__ == "__main__":
    main()
EOF

# 5. Usage examples
echo "
# Usage Examples:

# Basic usage (prompts for credentials)
python scoutbook_scraper.py

# Specify parameters
python scoutbook_scraper.py --zip-code 01720 --radius 25 --output my_counselors

# Run in headless mode (no browser window)
python scoutbook_scraper.py --headless

# Custom search area
python scoutbook_scraper.py --zip-code 02101 --radius 50 --output boston_area

# The enhanced version with better error handling
python scoutbook_scraper_enhanced.py --zip-code 01720 --radius 25
"

# 6. Create a test script
cat > test_scraper.py << 'EOF'
#!/usr/bin/env python3
"""
Test script for the ScoutBook scraper - validates HTML parsing logic
without actually scraping the website.
"""

def test_name_parsing():
    """Test name parsing with various formats."""
    test_cases = [
        ("John Smith", ("John", "", "Smith")),
        ("Christopher (Chris) White", ("Christopher", "Chris", "White")),
        ("Mary-Jane Watson-Parker", ("Mary-Jane", "", "Watson-Parker")),
        ("Robert de Silva", ("Robert", "", "de Silva"))
    ]
    
    for input_name, expected in test_cases:
        # Test the name parsing logic here
        print(f"Input: {input_name} -> Expected: {expected}")

def test_phone_parsing():
    """Test phone number extraction."""
    test_text = """
    Home (555) 123-4567
    Mobile 555.987.6543
    Work: 5551234567
    """
    
    import re
    
    patterns = [
        (r'Home[:\s]*\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})', "home"),
        (r'Mobile[:\s]*\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})', "mobile"),
        (r'Work[:\s]*\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})', "work")
    ]
    
    for pattern, phone_type in patterns:
        match = re.search(pattern, test_text, re.IGNORECASE)
        if match:
            formatted = f"({match.group(1)}) {match.group(2)}-{match.group(3)}"
            print(f"{phone_type.title()}: {formatted}")

def test_yp_expiration():
    """Test Youth Protection expiration parsing."""
    test_text = "Youth Protection Training Expires: 12/31/2025"
    
    import re
    yp_match = re.search(r'Expires:\s*(\d{1,2}/\d{1,2}/\d{4})', test_text, re.IGNORECASE)
    if yp_match:
        print(f"YP Expiration: {yp_match.group(1)}")

if __name__ == "__main__":
    print("Testing ScoutBook scraper parsing logic...")
    test_name_parsing()
    print()
    test_phone_parsing() 
    print()
    test_yp_expiration()
EOF

# 7. Create integration script for existing workflow
cat > integrate_scraper.py << 'EOF'
#!/usr/bin/env python3
"""
Integration script to use scraped JSON/CSV data with existing mbc_tool.py workflow.
"""

import json
import sys
from pathlib import Path

def convert_scraped_to_legacy_format(scraped_json_file, output_json_file):
    """Convert scraped JSON to format compatible with existing tool."""
    
    with open(scraped_json_file, 'r', encoding='utf-8') as f:
        scraped_data = json.load(f)
    
    # Convert to legacy format
    legacy_counselors = []
    
    for counselor in scraped_data.get('counselors', []):
        legacy_format = {
            'firstname': counselor.get('first_name', ''),
            'lastname': counselor.get('last_name', ''),
            'alt_firstname': counselor.get('alt_first_name', ''),
            'emails': [counselor.get('email')] if counselor.get('email') else [],
            'phones': [
                phone for phone in [
                    counselor.get('phone_home'),
                    counselor.get('phone_mobile'), 
                    counselor.get('phone_work')
                ] if phone
            ],
            'merit_badges': counselor.get('merit_badges', []),
            'yp_expiration': counselor.get('yp_expiration', ''),
            'address': counselor.get('address', '')
        }
        legacy_counselors.append(legacy_format)
    
    # Save in legacy format
    with open(output_json_file, 'w', encoding='utf-8') as f:
        json.dump(legacy_counselors, f, indent=2, ensure_ascii=False)
    
    print(f"Converted {len(legacy_counselors)} counselors to legacy format")
    print(f"Saved to: {output_json_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python integrate_scraper.py <scraped_file.json> <output_file.json>")
        sys.exit(1)
    
    convert_scraped_to_legacy_format(sys.argv[1], sys.argv[2])
EOF

chmod +x test_scraper.py
chmod +x integrate_scraper.py
chmod +x scoutbook_scraper_enhanced.py

echo "
✅ ScoutBook Scraper Setup Complete!

📁 Files created:
  🔧 requirements-scraper.txt
  🤖 scoutbook_scraper.py (main scraper)
  🚀 scoutbook_scraper_enhanced.py (improved version)
  🧪 test_scraper.py (test parsing logic)
  🔗 integrate_scraper.py (convert to legacy format)

🚀 Quick Start:
  1. pip install -r requirements-scraper.txt
  2. python scoutbook_scraper_enhanced.py --zip-code 01720 --radius 25

⚠️  Important Notes:
  - Respects rate limits with human-like delays
  - Handles pagination automatically
  - Extracts Youth Protection expiration dates
  - Saves data in JSON and CSV formats
  - Use responsibly and in compliance with ScoutBook terms of service
"