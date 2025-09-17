#!/usr/bin/env python3
"""
Report Generator for ScoutBook Merit Badge Counselor Reports

Generates HTML reports matching the legacy format from:
legacy/test_outputs/MBC_Reports_2025-06-04_14-51/

Reports generated:
1. troop_counselors.html - Troop leaders who are MBCs
2. non_counselors.html - Troop leaders who are not MBCs  
3. coverage_report.html - Merit badge coverage analysis
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import asyncio

class ReportGenerator:
    def __init__(self, data_file: str = "data/processed/roster_mbc_join.json", exclusion_file: str = "data/input/exclusion_list.txt"):
        self.data_file = Path(data_file)
        self.exclusion_file = Path(exclusion_file)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.excluded_names = self.load_exclusion_list()
        
        # Determine troop abbreviations from data
        self.troop_abbrevs = self.get_troop_abbreviations()
        troop_prefix = "_".join(self.troop_abbrevs)
        
        self.output_dir = Path(f"data/reports/{troop_prefix}_MBC_Reports_{self.timestamp}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def load_exclusion_list(self) -> List[str]:
        """Load names to exclude from all reports"""
        if not self.exclusion_file.exists():
            return []
        
        excluded_names = []
        with open(self.exclusion_file, 'r') as f:
            for line in f:
                name = line.strip()
                if name and not name.startswith('#'):  # Allow comments with #
                    excluded_names.append(name)
        
        if excluded_names:
            print(f"📝 Loaded {len(excluded_names)} names to exclude: {', '.join(excluded_names)}")
        
        return excluded_names
    
    def get_troop_abbreviations(self) -> List[str]:
        """Get troop abbreviations from the data"""
        data = self.load_data()
        troops = set()
        
        # Collect troops from both counselors and non-counselors
        for counselor in data.get('troop_counselors', []):
            troops.update(counselor.get('troops', []))
        
        for leader in data.get('non_counselor_leaders', []):
            troops.update(leader.get('troops', []))
        
        # Sort and return as list
        return sorted(list(troops))
    
    def filter_excluded_names(self, people_list: List[Dict]) -> List[Dict]:
        """Filter out excluded names from a list of people"""
        if not self.excluded_names:
            return people_list
        
        filtered = []
        excluded_count = 0
        
        for person in people_list:
            full_name = person.get('name', '')
            first_name = person.get('first_name', '')
            last_name = person.get('last_name', '')
            
            # Check if this person should be excluded
            should_exclude = False
            
            for excluded_name in self.excluded_names:
                excluded_parts = excluded_name.lower().split()
                if len(excluded_parts) >= 2:
                    # Match first and last name (ignoring middle names/initials)
                    excluded_first = excluded_parts[0]
                    excluded_last = excluded_parts[-1]
                    
                    if (excluded_first in first_name.lower() and 
                        excluded_last in last_name.lower()):
                        should_exclude = True
                        break
                else:
                    # Fallback to simple substring matching
                    if excluded_name.lower() in full_name.lower():
                        should_exclude = True
                        break
            
            if not should_exclude:
                filtered.append(person)
            else:
                excluded_count += 1
                print(f"🚫 Excluded {full_name} from reports")
        
        if excluded_count > 0:
            print(f"📊 Filtered out {excluded_count} excluded names")
        
        return filtered
    
    def get_all_merit_badges(self) -> List[str]:
        """Return comprehensive list of all current merit badges"""
        return [
            'Animal Science', 'Animation', 'Archaeology', 'Archery', 'Architecture', 'Art', 
            'Astronomy', 'Athletics', 'Automotive', 'Aviation', 'Backpacking', 'Basketry', 
            'Bird Study', 'Bugling', 'Camping', 'Canoeing', 'Chemistry', 'Chess', 
            'Citizenship in the Community', 'Citizenship in the Nation', 'Citizenship in Society', 
            'Climbing', 'Coin Collecting', 'Collections', 'Communication', 'Composite Materials', 
            'Cooking', 'Crime Prevention', 'Cycling', 'Dentistry', 'Digital Technology', 
            'Disabilities Awareness', 'Dog Care', 'Drafting', 'Electricity', 'Electronics', 
            'Emergency Preparedness', 'Energy', 'Engineering', 'Entrepreneurship', 
            'Environmental Science', 'Exploration', 'Family Life', 'Farm Mechanics', 
            'Fingerprinting', 'Fire Safety', 'First Aid', 'Fish and Wildlife Management', 
            'Fishing', 'Forestry', 'Game Design', 'Gardening', 'Genealogy', 'Geocaching', 
            'Geology', 'Golf', 'Graphic Arts', 'Hiking', 'Home Repairs', 'Horsemanship', 
            'Indian Lore', 'Insect Study', 'Inventing', 'Journalism', 'Kayaking', 
            'Landscape Architecture', 'Law', 'Leatherwork', 'Lifesaving', 'Mammal Study', 
            'Medicine', 'Metalwork', 'Model Design and Building', 'Motorboating', 'Music', 
            'Nature', 'Nuclear Science', 'Oceanography', 'Orienteering', 'Painting', 
            'Personal Fitness', 'Personal Management', 'Pets', 'Photography', 'Pioneering', 
            'Plant Science', 'Plumbing', 'Pottery', 'Programming', 'Public Health', 
            'Public Speaking', 'Pulp and Paper', 'Radio', 'Railroading', 'Reading', 
            'Reptile and Amphibian Study', 'Rifle Shooting', 'Robotics', 'Rowing', 'Safety', 
            'Salesmanship', 'Scholarship', 'Scouting Heritage', 'Scuba Diving', 'Sculpture', 
            'Search and Rescue', 'Shotgun Shooting', 'Signs, Signals, and Codes', 'Skating', 
            'Small-Boat Sailing', 'Snow Sports', 'Soil and Water Conservation', 'Space Exploration', 
            'Sports', 'Stamp Collecting', 'Sustainability', 'Swimming', 'Textile', 'Theater', 
            'Traffic Safety', 'Truck Transportation', 'Veterinary Medicine', 'Water Sports', 
            'Weather', 'Welding', 'Whitewater', 'Wilderness Survival', 'Wood Carving', 'Woodworking'
        ]
    
    def get_positions_for_leader(self, leader: Dict) -> str:
        """Extract positions from roster data for a leader across all troops"""
        positions = []
        roster_data = leader.get('roster_data', {})
        member_data = roster_data.get('member_data', {})
        
        for troop_id, troop_data in member_data.items():
            position = troop_data.get('position', '').strip()
            if position:
                # Include troop prefix if leader is in multiple troops
                if len(member_data) > 1:
                    positions.append(f"{troop_id}: {position}")
                else:
                    positions.append(position)
        
        return '; '.join(positions) if positions else 'Unknown'
    
    def load_data(self) -> Dict:
        """Load the joined roster and MBC data"""
        with open(self.data_file, 'r') as f:
            return json.load(f)
    
    def generate_html_header(self, title: str) -> str:
        """Generate common HTML header"""
        return f"""
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
        .coverage-table {{
            table-layout: fixed;
        }}
        .coverage-table th:first-child {{
            width: 30%;
        }}
        .coverage-table th:last-child {{
            width: 70%;
        }}
        .coverage-table td {{
            vertical-align: top;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <div class="timestamp">Generated on {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</div>
    </div>
"""

    def generate_troop_counselors_report(self, data: Dict) -> str:
        """Generate troop counselors HTML report"""
        troop_prefix = "/".join(self.troop_abbrevs)
        html = self.generate_html_header(f"{troop_prefix} Merit Badge Counselors")
        
        troop_filename_prefix = "_".join(self.troop_abbrevs)
        html += f"""
    <div class="controls">
        <a href="{troop_filename_prefix}_MBC_Non_Counselors_{self.timestamp}.html" class="btn">Non-Counselor Leaders</a>
        <a href="{troop_filename_prefix}_MBC_Coverage_Report_{self.timestamp}.html" class="btn">Coverage Report</a>
    </div>
    
    <div class="content">
        <div class="section">
            <h2>{troop_prefix} Leaders Who Are Merit Badge Counselors</h2>
            <p>Adult members of {" and ".join(self.troop_abbrevs)} who are also certified Merit Badge Counselors.</p>
            
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Troops</th>
                        <th>Contact</th>
                        <th>YPT Expires</th>
                        <th>Merit Badges</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # Filter out excluded names
        filtered_counselors = self.filter_excluded_names(data['troop_counselors'])
        counselor_count = len(filtered_counselors)
        
        # Update heading with count
        html = html.replace(
            f"<h2>{troop_prefix} Leaders Who Are Merit Badge Counselors</h2>",
            f"<h2>{troop_prefix} Leaders Who Are Merit Badge Counselors ({counselor_count})</h2>"
        )
        
        for counselor in filtered_counselors:
            badges_html = f'<div class="badge-list">'
            for badge in counselor['merit_badges'].split(', '):
                if badge.strip():
                    # Mark Eagle required badges
                    eagle_badges = ['Camping', 'Citizenship in Society', 'Citizenship in the Community', 
                                   'Citizenship in the Nation', 'Citizenship in the World', 'Communication',
                                   'Cooking', 'Emergency Preparedness', 'Environmental Science', 'Family Life',
                                   'First Aid', 'Hiking', 'Lifesaving', 'Personal Fitness', 'Personal Management',
                                   'Swimming', 'Cycling', 'Sustainability']
                    badge_class = 'eagle-badge' if badge.strip() in eagle_badges else 'badge'
                    badges_html += f'<span class="{badge_class}">{badge.strip()}</span>'
            badges_html += '</div>'
            
            # Build phone number display with labels
            contact_info = [counselor['email']]
            mbc_data = counselor.get('mbc_data', {})
            
            phone_types = [
                ('Home', mbc_data.get('phone_home', '')),
                ('Mobile', mbc_data.get('phone_mobile', '')), 
                ('Work', mbc_data.get('phone_work', ''))
            ]
            
            phone_lines = []
            for label, phone in phone_types:
                if phone and phone.strip():
                    phone_lines.append(f'{label}: {phone.strip()}')
            
            if phone_lines:
                contact_info.extend(phone_lines)
            elif counselor['phone']:  # Fallback to main phone field
                contact_info.append(counselor['phone'])
            
            contact_display = '<br>'.join(contact_info)
            
            html += f"""
                    <tr>
                        <td>{counselor['name']}</td>
                        <td>{counselor['troop_display']}</td>
                        <td>{contact_display}</td>
                        <td>{counselor['ypt_expiration']}</td>
                        <td>{badges_html}</td>
                    </tr>"""
        
        html += """
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def generate_non_counselors_report(self, data: Dict) -> str:
        """Generate non-counselor leaders HTML report"""
        troop_prefix = "/".join(self.troop_abbrevs)
        html = self.generate_html_header(f"{troop_prefix} Non-Counselor Leaders")
        
        troop_filename_prefix = "_".join(self.troop_abbrevs)
        html += f"""
    <div class="controls">
        <a href="{troop_filename_prefix}_MBC_Troop_Counselors_{self.timestamp}.html" class="btn">Troop Counselors</a>
        <a href="{troop_filename_prefix}_MBC_Coverage_Report_{self.timestamp}.html" class="btn">Coverage Report</a>
    </div>
    
    <div class="content">
        <div class="section">
            <h2>{troop_prefix} Leaders Who Are NOT Merit Badge Counselors</h2>
            <p>Adult members of {" and ".join(self.troop_abbrevs)} who could potentially become Merit Badge Counselors.</p>
            
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Troops</th>
                        <th>Position</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # Filter out excluded names
        filtered_leaders = self.filter_excluded_names(data['non_counselor_leaders'])
        leader_count = len(filtered_leaders)
        
        # Update heading with count
        html = html.replace(
            f"<h2>{troop_prefix} Leaders Who Are NOT Merit Badge Counselors</h2>",
            f"<h2>{troop_prefix} Leaders Who Are NOT Merit Badge Counselors ({leader_count})</h2>"
        )
        
        for leader in filtered_leaders:
            position = self.get_positions_for_leader(leader)
            html += f"""
                    <tr>
                        <td>{leader['name']}</td>
                        <td>{leader['troop_display']}</td>
                        <td>{position}</td>
                    </tr>"""
        
        html += """
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    def generate_coverage_report(self, data: Dict) -> str:
        """Generate merit badge coverage report matching legacy format"""
        troop_prefix = "/".join(self.troop_abbrevs)
        html = self.generate_html_header(f"{troop_prefix} Merit Badge Coverage Report")
        
        # Get all merit badges and Eagle-required badges
        all_merit_badges = self.get_all_merit_badges()
        eagle_badges = ['Camping', 'Citizenship in Society', 'Citizenship in the Community', 
                       'Citizenship in the Nation', 'Citizenship in the World', 'Communication',
                       'Cooking', 'Emergency Preparedness', 'Environmental Science', 'Family Life',
                       'First Aid', 'Hiking', 'Lifesaving', 'Personal Fitness', 'Personal Management',
                       'Swimming', 'Cycling', 'Sustainability']
        
        # Analyze badge coverage using filtered data
        filtered_counselors = self.filter_excluded_names(data['troop_counselors'])
        
        # Create mapping of badges to counselors
        badge_to_counselors = {}
        for counselor in filtered_counselors:
            counselor_display = f"{counselor['name']} ({counselor['troop_display']})"
            for badge in counselor['merit_badges'].split(', '):
                badge = badge.strip()
                if badge:
                    if badge not in badge_to_counselors:
                        badge_to_counselors[badge] = []
                    badge_to_counselors[badge].append(counselor_display)
        
        # Categorize badges
        eagle_with_counselors = []
        eagle_without_counselors = []
        non_eagle_with_counselors = []
        non_eagle_without_counselors = []
        
        for badge in all_merit_badges:
            is_eagle = badge in eagle_badges
            has_counselor = badge in badge_to_counselors
            
            if is_eagle:
                if has_counselor:
                    eagle_with_counselors.append(badge)
                else:
                    eagle_without_counselors.append(badge)
            else:
                if has_counselor:
                    non_eagle_with_counselors.append(badge)
                else:
                    non_eagle_without_counselors.append(badge)
        
        troop_filename_prefix = "_".join(self.troop_abbrevs)
        
        html += f"""
    <div class="controls">
        <a href="{troop_filename_prefix}_MBC_Troop_Counselors_{self.timestamp}.html" class="btn">Troop Counselors</a>
        <a href="{troop_filename_prefix}_MBC_Non_Counselors_{self.timestamp}.html" class="btn">Non-Counselor Leaders</a>
    </div>
    
    <div class="content">
        <h2>{troop_prefix} Merit Badge Coverage Report</h2>
        
        <div class="section">
            <h3>Eagle-Required Merit Badges with {troop_prefix} Counselors ({len(eagle_with_counselors)} badges)</h3>
            <table class="coverage-table">
                <tr><th>Merit Badge</th><th>Counselors</th></tr>
"""
        
        for badge in sorted(eagle_with_counselors):
            counselor_list = '<br>'.join(badge_to_counselors[badge])
            html += f"""
                <tr>
                    <td>{badge}</td>
                    <td>{counselor_list}</td>
                </tr>
"""
        
        html += f"""
            </table>
        </div>
        
        <div class="section">
            <h3>Eagle-Required Merit Badges without {troop_prefix} Counselors ({len(eagle_without_counselors)} badges)</h3>
            <div class="badge-list">
"""
        
        for badge in sorted(eagle_without_counselors):
            html += f'<span class="badge eagle-badge">{badge}</span>'
        
        html += f"""
            </div>
        </div>
        
        <div class="section">
            <h3>Non-Eagle Merit Badges with {troop_prefix} Counselors ({len(non_eagle_with_counselors)} badges)</h3>
            <table class="coverage-table">
                <tr><th>Merit Badge</th><th>Counselors</th></tr>
"""
        
        for badge in sorted(non_eagle_with_counselors):
            counselor_list = '<br>'.join(badge_to_counselors[badge])
            html += f"""
                <tr>
                    <td>{badge}</td>
                    <td>{counselor_list}</td>
                </tr>
"""
        
        html += f"""
            </table>
        </div>
        
        <div class="section">
            <h3>Non-Eagle Merit Badges without {troop_prefix} Counselors ({len(non_eagle_without_counselors)} badges)</h3>
            <div class="badge-list">
"""
        
        for badge in sorted(non_eagle_without_counselors):
            html += f'<span class="badge">{badge}</span>'
        
        html += """
            </div>
        </div>
    </div>
</body>
</html>"""
        
        return html
    
    async def generate_pdf_from_html_async(self, html_file: Path) -> Path:
        """Generate PDF from HTML file using Playwright"""
        try:
            from playwright.async_api import async_playwright
            
            pdf_file = html_file.with_suffix('.pdf')
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Load the HTML file
                await page.goto(f"file://{html_file.absolute()}")
                
                # Generate PDF with full color and good formatting
                await page.pdf(
                    path=str(pdf_file),
                    format='Letter',
                    margin={
                        'top': '0.75in',
                        'right': '0.75in', 
                        'bottom': '0.75in',
                        'left': '0.75in'
                    },
                    print_background=True,  # Include background colors and images
                    prefer_css_page_size=False
                )
                
                await browser.close()
                
            print(f"📄 Generated PDF: {pdf_file.name}")
            return pdf_file
            
        except ImportError:
            print(f"⚠️ Playwright not available. Skipping PDF generation for {html_file.name}")
            print("   Install with: pip install playwright && playwright install chromium")
            return None
        except Exception as e:
            print(f"❌ PDF generation failed for {html_file.name}: {str(e)}")
            return None
    
    def generate_pdf_from_html(self, html_file: Path) -> Path:
        """Synchronous wrapper for PDF generation"""
        return asyncio.run(self.generate_pdf_from_html_async(html_file))
    
    def generate_all_reports(self) -> str:
        """Generate all reports and return output directory"""
        print(f"📊 Generating reports in {self.output_dir}...")
        
        # Load data
        data = self.load_data()
        
        # Generate reports with new filename format
        troop_filename_prefix = "_".join(self.troop_abbrevs)
        reports = {
            f'{troop_filename_prefix}_MBC_Troop_Counselors_{self.timestamp}.html': self.generate_troop_counselors_report(data),
            f'{troop_filename_prefix}_MBC_Non_Counselors_{self.timestamp}.html': self.generate_non_counselors_report(data), 
            f'{troop_filename_prefix}_MBC_Coverage_Report_{self.timestamp}.html': self.generate_coverage_report(data)
        }
        
        # Save HTML reports and generate PDFs
        for filename, content in reports.items():
            output_file = self.output_dir / filename
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Generated {filename}")
            
            # Generate PDF version
            self.generate_pdf_from_html(output_file)
        
        # Generate summary JSON with filtered counts
        filtered_counselors = self.filter_excluded_names(data['troop_counselors'])
        filtered_leaders = self.filter_excluded_names(data['non_counselor_leaders'])
        
        summary = {
            "generation_time": datetime.now().isoformat(),
            "troops_processed": self.troop_abbrevs,
            "exclusions_applied": len(self.excluded_names) > 0,
            "excluded_names": self.excluded_names,
            "statistics": {
                "total_adults_processed": len(filtered_counselors) + len(filtered_leaders),
                "troop_counselors": len(filtered_counselors),
                "non_counselor_leaders": len(filtered_leaders),
                "merit_badge_html_processed": True,
                "web_data_retrieved": True
            }
        }
        
        summary_file = self.output_dir / 'summary_report.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"✅ Generated summary_report.json")
        
        return str(self.output_dir)

def main():
    """Main report generation function"""
    generator = ReportGenerator()
    output_dir = generator.generate_all_reports()
    
    print(f"\n🎉 Reports generated successfully!")
    print(f"📁 Location: {output_dir}")
    print(f"🌐 Open troop_counselors.html to view the main report")

if __name__ == "__main__":
    main()