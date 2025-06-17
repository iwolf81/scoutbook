#!/usr/bin/env python3
"""
ScoutBook Merit Badge Counselor Scraper

Automated tool to scrape merit badge counselor data from ScoutBook
with human-like interaction patterns to avoid detection.

Usage:
    python scoutbook_scraper.py --zip-code 01720 --radius 25 --output counselors_data
"""

import json
import csv
import time
import random
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import getpass
import sys

import click
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, 
    ElementClickInterceptedException, StaleElementReferenceException
)
from bs4 import BeautifulSoup
import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

# Set up rich console and logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scoutbook_scraper.log', mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class HumanLikeInteraction:
    """Utilities for human-like web interaction patterns."""
    
    @staticmethod
    def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Random delay to simulate human timing."""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    @staticmethod
    def human_type(element, text: str, typing_delay: tuple = (0.05, 0.15)):
        """Type text with human-like delays between characters."""
        element.clear()
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(*typing_delay))
    
    @staticmethod
    def scroll_to_element(driver, element):
        """Scroll element into view naturally."""
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        HumanLikeInteraction.random_delay(0.5, 1.0)
    
    @staticmethod
    def move_to_element_and_click(driver, element):
        """Move mouse to element and click with human-like behavior."""
        actions = ActionChains(driver)
        actions.move_to_element(element)
        actions.pause(random.uniform(0.2, 0.5))
        actions.click()
        actions.perform()
        HumanLikeInteraction.random_delay(0.5, 1.0)


class CounselorData:
    """Data structure for merit badge counselor information."""
    
    def __init__(self):
        self.first_name = ""
        self.alt_first_name = ""
        self.last_name = ""
        self.address = ""
        self.email = ""
        self.phone_home = ""
        self.phone_mobile = ""
        self.phone_work = ""
        self.yp_expiration = ""
        self.merit_badges = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON/CSV export."""
        return {
            "first_name": self.first_name,
            "alt_first_name": self.alt_first_name,
            "last_name": self.last_name,
            "full_name": f"{self.first_name} {self.last_name}".strip(),
            "display_name": f"{self.first_name} ({self.alt_first_name}) {self.last_name}" if self.alt_first_name else f"{self.first_name} {self.last_name}",
            "address": self.address,
            "email": self.email,
            "phone_home": self.phone_home,
            "phone_mobile": self.phone_mobile,
            "phone_work": self.phone_work,
            "yp_expiration": self.yp_expiration,
            "yp_expiration_date": self._parse_yp_date(),
            "merit_badges": self.merit_badges,
            "merit_badge_count": len(self.merit_badges),
            "merit_badges_string": "; ".join(self.merit_badges),
            "scraped_at": datetime.now().isoformat()
        }
    
    def _parse_yp_date(self) -> str:
        """Parse YP expiration into standard date format."""
        if not self.yp_expiration:
            return ""
        
        # Extract date from "Expires: MM/DD/YYYY" format
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', self.yp_expiration)
        if date_match:
            return date_match.group(1)
        return ""


class ScoutBookScraper:
    """Main scraper class for ScoutBook merit badge counselor data."""
    
    def __init__(self, headless: bool = False, timeout: int = 20):
        self.driver = None
        self.wait = None
        self.timeout = timeout
        self.headless = headless
        self.human = HumanLikeInteraction()
        self.counselors = []
        
    def setup_driver(self):
        """Initialize Chrome WebDriver with human-like settings."""
        console.print("[blue]Setting up web driver...[/blue]")
        
        options = Options()
        if self.headless:
            options.add_argument('--headless')
        
        # Human-like browser settings
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Set user agent to look like regular Chrome
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, self.timeout)
            
            # Remove automation indicators
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("WebDriver initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            console.print(f"[red]Error: Could not start Chrome browser. Please ensure ChromeDriver is installed.[/red]")
            console.print(f"[yellow]Install ChromeDriver: https://chromedriver.chromium.org/[/yellow]")
            return False
    
    def login(self, username: str, password: str) -> bool:
        """Login to ScoutBook with human-like behavior."""
        console.print("[blue]Logging into ScoutBook...[/blue]")
        
        try:
            # Navigate to login page
            self.driver.get("https://scoutbook.scouting.org/mobile/dashboard/")
            self.human.random_delay(2, 4)
            
            # Wait for login form
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            
            # Human-like typing
            self.human.scroll_to_element(self.driver, username_field)
            self.human.human_type(username_field, username)
            self.human.random_delay(0.5, 1.0)
            
            password_field = self.driver.find_element(By.ID, "password")
            self.human.human_type(password_field, password)
            self.human.random_delay(1, 2)
            
            # Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            self.human.move_to_element_and_click(self.driver, login_button)
            
            # Wait for successful login (dashboard page)
            self.wait.until(
                EC.any_of(
                    EC.url_contains("dashboard"),
                    EC.presence_of_element_located((By.CLASS_NAME, "dashboard")),
                    EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Troop"))
                )
            )
            
            logger.info("Successfully logged into ScoutBook")
            console.print("[green]✓ Login successful[/green]")
            return True
            
        except TimeoutException:
            logger.error("Login timeout - check credentials or website availability")
            console.print("[red]Login failed: Timeout. Please check your credentials.[/red]")
            return False
        except Exception as e:
            logger.error(f"Login failed: {e}")
            console.print(f"[red]Login failed: {e}[/red]")
            return False
    
    def navigate_to_counselor_search(self) -> bool:
        """Navigate to Troop 32B MB Counselor List."""
        console.print("[blue]Navigating to Merit Badge Counselor search...[/blue]")
        
        try:
            # Look for Troop 32B link
            troop_link = self.wait.until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Troop 32"))
            )
            
            self.human.scroll_to_element(self.driver, troop_link)
            self.human.move_to_element_and_click(self.driver, troop_link)
            self.human.random_delay(2, 3)
            
            # Look for MB Counselor List
            counselor_link = self.wait.until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "MB Counselor"))
            )
            
            self.human.scroll_to_element(self.driver, counselor_link)
            self.human.move_to_element_and_click(self.driver, counselor_link)
            self.human.random_delay(2, 4)
            
            logger.info("Successfully navigated to counselor search")
            console.print("[green]✓ Reached Merit Badge Counselor search[/green]")
            return True
            
        except TimeoutException:
            logger.error("Could not find navigation elements")
            console.print("[red]Could not navigate to counselor search. Page structure may have changed.[/red]")
            return False
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            console.print(f"[red]Navigation error: {e}[/red]")
            return False
    
    def setup_search_parameters(self, zip_code: str = "01720", radius_miles: int = 25) -> bool:
        """Configure search parameters."""
        console.print(f"[blue]Setting up search: {zip_code} within {radius_miles} miles...[/blue]")
        
        try:
            # Set up search parameters
            # All Badges (should be default)
            all_badges_option = self.driver.find_element(By.XPATH, "//input[@value='all' or @value='All Badges']")
            if not all_badges_option.is_selected():
                self.human.move_to_element_and_click(self.driver, all_badges_option)
                self.human.random_delay(0.5, 1.0)
            
            # Zip code
            zip_field = self.driver.find_element(By.NAME, "zipCode")
            self.human.scroll_to_element(self.driver, zip_field)
            self.human.human_type(zip_field, zip_code)
            self.human.random_delay(0.5, 1.0)
            
            # Proximity radius
            radius_select = Select(self.driver.find_element(By.NAME, "proximity"))
            radius_select.select_by_value(str(radius_miles))
            self.human.random_delay(0.5, 1.0)
            
            # Council should default to "Heart of New England"
            # District should default to "Quinapoxet"
            # Availability: Both (should be default)
            
            logger.info(f"Search parameters set: {zip_code}, {radius_miles} miles")
            console.print("[green]✓ Search parameters configured[/green]")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set search parameters: {e}")
            console.print(f"[red]Search setup error: {e}[/red]")
            return False
    
    def execute_search_and_scrape(self) -> List[CounselorData]:
        """Execute search and scrape all paginated results."""
        console.print("[blue]Executing search and scraping results...[/blue]")
        
        try:
            # Click search button
            search_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
            self.human.move_to_element_and_click(self.driver, search_button)
            self.human.random_delay(3, 5)  # Wait for results to load
            
            page_number = 1
            total_counselors = 0
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task("Scraping counselor data...", total=None)
                
                while True:
                    console.print(f"[cyan]Processing page {page_number}...[/cyan]")
                    
                    # Scrape current page
                    page_counselors = self._scrape_current_page()
                    self.counselors.extend(page_counselors)
                    total_counselors += len(page_counselors)
                    
                    progress.update(task, description=f"Scraped {total_counselors} counselors from {page_number} pages")
                    
                    console.print(f"[green]  ✓ Page {page_number}: {len(page_counselors)} counselors[/green]")
                    
                    # Check for next page
                    if not self._navigate_to_next_page():
                        break
                    
                    page_number += 1
                    self.human.random_delay(2, 4)  # Respectful delay between pages
            
            logger.info(f"Scraping complete: {total_counselors} counselors from {page_number} pages")
            console.print(f"[bold green]✓ Scraping complete: {total_counselors} counselors found[/bold green]")
            return self.counselors
            
        except Exception as e:
            logger.error(f"Search and scrape failed: {e}")
            console.print(f"[red]Scraping error: {e}[/red]")
            return self.counselors
    
    def _scrape_current_page(self) -> List[CounselorData]:
        """Scrape counselor data from current page."""
        page_counselors = []
        
        try:
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find counselor entries (adapt this selector based on actual HTML structure)
            counselor_divs = soup.find_all('div', class_='counselor-entry') or \
                           soup.find_all('div', style=lambda value: value and 'margin-left: 65px' in value) or \
                           soup.find_all('div', class_='mb-counselor')
            
            for div in counselor_divs:
                counselor = self._parse_counselor_div(div)
                if counselor and counselor.first_name and counselor.last_name:
                    page_counselors.append(counselor)
            
        except Exception as e:
            logger.error(f"Error scraping current page: {e}")
        
        return page_counselors
    
    def _parse_counselor_div(self, counselor_div) -> Optional[CounselorData]:
        """Parse individual counselor data from HTML div."""
        try:
            counselor = CounselorData()
            
            # Extract name (adapt based on actual HTML structure)
            name_text = None
            for content in counselor_div.contents:
                if isinstance(content, str) and content.strip():
                    name_text = content.strip()
                    break
            
            if name_text:
                # Parse name - handle "Christopher (Chris) White" format
                alt_name_match = re.search(r'\(([^)]+)\)', name_text)
                counselor.alt_first_name = alt_name_match.group(1) if alt_name_match else ""
                
                clean_name = re.sub(r'\s*\([^)]+\)\s*', ' ', name_text).strip()
                name_parts = clean_name.split()
                
                if len(name_parts) >= 2:
                    counselor.first_name = name_parts[0]
                    counselor.last_name = ' '.join(name_parts[1:])
            
            # Extract contact information
            address_div = counselor_div.find('div', class_='address')
            if address_div:
                address_text = address_div.get_text()
                
                # Extract address (first lines before phone/email)
                lines = address_text.split('\n')
                address_lines = []
                for line in lines:
                    line = line.strip()
                    if line and not any(keyword in line.lower() for keyword in ['home', 'mobile', 'work', '@', 'expires']):
                        address_lines.append(line)
                counselor.address = ', '.join(address_lines)
                
                # Extract phone numbers
                home_match = re.search(r'Home[:\s]*\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})', address_text, re.IGNORECASE)
                if home_match:
                    counselor.phone_home = f"({home_match.group(1)}) {home_match.group(2)}-{home_match.group(3)}"
                
                mobile_match = re.search(r'Mobile[:\s]*\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})', address_text, re.IGNORECASE)
                if mobile_match:
                    counselor.phone_mobile = f"({mobile_match.group(1)}) {mobile_match.group(2)}-{mobile_match.group(3)}"
                
                work_match = re.search(r'Work[:\s]*\(?(\d{3})\)?[-.\s]*(\d{3})[-.\s]*(\d{4})', address_text, re.IGNORECASE)
                if work_match:
                    counselor.phone_work = f"({work_match.group(1)}) {work_match.group(2)}-{work_match.group(3)}"
                
                # Extract email
                email_link = address_div.find('a', href=lambda href: href and href.startswith('mailto:'))
                if email_link:
                    counselor.email = email_link.get_text().strip()
                
                # Extract Youth Protection expiration date
                yp_match = re.search(r'Expires:\s*(\d{1,2}/\d{1,2}/\d{4})', address_text, re.IGNORECASE)
                if yp_match:
                    counselor.yp_expiration = f"Expires: {yp_match.group(1)}"
            
            # Extract merit badges
            mb_container = counselor_div.find('div', class_='mbContainer')
            if mb_container:
                mb_divs = mb_container.find_all('div', class_='mb')
                for mb_div in mb_divs:
                    badge_text = mb_div.get_text().strip()
                    if badge_text and not any(phrase in badge_text.lower() for phrase in ['council', 'heart', 'england']):
                        counselor.merit_badges.append(badge_text)
                
                counselor.merit_badges.sort()
            
            return counselor
            
        except Exception as e:
            logger.error(f"Error parsing counselor div: {e}")
            return None
    
    def _navigate_to_next_page(self) -> bool:
        """Navigate to next page if available."""
        try:
            # Look for next page link/button
            next_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Next')] | //a[contains(@class, 'next')] | //button[contains(text(), 'Next')]")
            
            for next_link in next_links:
                if next_link.is_enabled() and next_link.is_displayed():
                    self.human.scroll_to_element(self.driver, next_link)
                    self.human.move_to_element_and_click(self.driver, next_link)
                    self.human.random_delay(2, 4)
                    return True
            
            # Try pagination numbers
            page_links = self.driver.find_elements(By.CSS_SELECTOR, ".pagination a, .pager a")
            current_page = None
            
            for link in page_links:
                if 'current' in link.get_attribute('class') or 'active' in link.get_attribute('class'):
                    current_page = int(link.text) if link.text.isdigit() else None
                    break
            
            if current_page:
                next_page_link = self.driver.find_element(By.XPATH, f"//a[text()='{current_page + 1}']")
                if next_page_link:
                    self.human.scroll_to_element(self.driver, next_page_link)
                    self.human.move_to_element_and_click(self.driver, next_page_link)
                    self.human.random_delay(2, 4)
                    return True
            
            return False
            
        except (NoSuchElementException, TimeoutException):
            return False
        except Exception as e:
            logger.error(f"Error navigating to next page: {e}")
            return False
    
    def save_data(self, output_prefix: str):
        """Save scraped data to JSON and CSV files."""
        if not self.counselors:
            console.print("[yellow]No data to save[/yellow]")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Convert to dictionaries
        data = [counselor.to_dict() for counselor in self.counselors]
        
        # Save JSON
        json_file = f"{output_prefix}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "scraped_at": datetime.now().isoformat(),
                    "total_counselors": len(self.counselors),
                    "search_radius": "25 miles",
                    "zip_code": "01720"
                },
                "counselors": data
            }, f, indent=2, ensure_ascii=False)
        
        # Save CSV
        csv_file = f"{output_prefix}_{timestamp}.csv"
        df = pd.DataFrame(data)
        df.to_csv(csv_file, index=False, encoding='utf-8')
        
        console.print(f"[green]✓ Data saved:[/green]")
        console.print(f"  📄 JSON: {json_file}")
        console.print(f"  📊 CSV: {csv_file}")
        console.print(f"  📈 Total counselors: {len(self.counselors)}")
        
        logger.info(f"Data saved: {len(self.counselors)} counselors to {json_file} and {csv_file}")
    
    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")


@click.command()
@click.option('--zip-code', default='01720', help='Zip code for search center')
@click.option('--radius', default=25, help='Search radius in miles')
@click.option('--output', default='counselors_data', help='Output file prefix')
@click.option('--headless/--no-headless', default=False, help='Run browser in headless mode')
@click.option('--timeout', default=20, help='WebDriver timeout in seconds')
def main(zip_code, radius, output, headless, timeout):
    """
    ScoutBook Merit Badge Counselor Scraper
    
    Automated tool to scrape merit badge counselor data from ScoutBook
    with human-like interaction patterns.
    
    Examples:
    
    \b
    # Basic usage with prompts
    python scoutbook_scraper.py
    
    \b
    # Specify parameters
    python scoutbook_scraper.py --zip-code 01720 --radius 25 --output my_counselors
    
    \b
    # Run in headless mode (faster, no browser window)
    python scoutbook_scraper.py --headless
    """
    
    console.print(Panel.fit(
        "[bold blue]ScoutBook Merit Badge Counselor Scraper[/bold blue]\n"
        "[dim]Automated data collection with human-like behavior[/dim]",
        border_style="blue"
    ))
    
    # Get credentials
    console.print("\n[bold]ScoutBook Login Credentials[/bold]")
    username = Prompt.ask("Username")
    password = Prompt.ask("Password", password=True)
    
    if not username or not password:
        console.print("[red]Username and password are required[/red]")
        return
    
    # Confirm parameters
    console.print(f"\n[bold]Search Parameters:[/bold]")
    console.print(f"  Zip Code: {zip_code}")
    console.print(f"  Radius: {radius} miles")
    console.print(f"  Output: {output}_TIMESTAMP.json/csv")
    console.print(f"  Headless: {headless}")
    
    if not Confirm.ask("\nProceed with scraping?"):
        console.print("[yellow]Operation cancelled[/yellow]")
        return
    
    # Initialize scraper
    scraper = ScoutBookScraper(headless=headless, timeout=timeout)
    
    try:
        # Setup and run scraping process
        if not scraper.setup_driver():
            return
        
        if not scraper.login(username, password):
            return
        
        if not scraper.navigate_to_counselor_search():
            return
        
        if not scraper.setup_search_parameters(zip_code, radius):
            return
        
        counselors = scraper.execute_search_and_scrape()
        
        if counselors:
            scraper.save_data(output)
            
            # Display summary
            console.print("\n[bold green]Scraping Summary:[/bold green]")
            console.print(f"  Total counselors: {len(counselors)}")
            
            if counselors:
                badges_with_counselors = set()
                for counselor in counselors:
                    badges_with_counselors.update(counselor.merit_badges)
                console.print(f"  Merit badges covered: {len(badges_with_counselors)}")
                
                # YP expiration warnings
                yp_expired = [c for c in counselors if c.yp_expiration and 'expires' in c.yp_expiration.lower()]
                if yp_expired:
                    console.print(f"  [yellow]Counselors with YP expiration data: {len(yp_expired)}[/yellow]")
        else:
            console.print("[yellow]No counselors found. Check search parameters.[/yellow]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        logger.exception("Unexpected error during scraping")
    finally:
        scraper.cleanup()


if __name__ == "__main__":
    main()