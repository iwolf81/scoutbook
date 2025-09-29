#!/usr/bin/env python3
"""
Roster Processing Script for ScoutBook Integration

Extracts adult members from troop rosters and creates unified list with troop affiliations
for joining with Merit Badge Counselor data.

Key matching logic:
- MBC key: ((first_name) or (alt_first_name)) + (last_name)
- Roster key: (first_name + last_name)

Usage:
    python roster_processor.py                     # Auto-detect latest rosters
    python roster_processor.py --units T32,T7012  # Specify units
    python roster_processor.py --config config.json # Use config file
"""

import re
import json
import argparse
from typing import Dict, List, Set, Tuple, Optional
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime

class RosterProcessor:
    def __init__(self, roster_dir: str = "data/input/rosters", supplemental_file: str = "data/input/unit_associated_mbcs.txt"):
        self.roster_dir = Path(roster_dir)
        self.supplemental_file = Path(supplemental_file)
        self.adults = {}  # name -> {troops: set, member_data: dict}

    def auto_detect_rosters(self) -> Dict[str, str]:
        """
        Auto-detect roster files by scanning directory for latest files per unit

        Returns:
            Dict mapping unit_id -> filename for latest roster per unit
        """
        print(f"🔍 Auto-detecting rosters in {self.roster_dir}...")

        if not self.roster_dir.exists():
            print(f"❌ Roster directory not found: {self.roster_dir}")
            return {}

        # Pattern to match: {UNIT} Roster {DATE}.html
        roster_pattern = re.compile(r'^([A-Z0-9]+)\s+Roster\s+(.+)\.html$')

        # Group files by unit
        unit_files = {}

        for roster_file in self.roster_dir.glob('*.html'):
            match = roster_pattern.match(roster_file.name)
            if match:
                unit_id = match.group(1)
                date_str = match.group(2)

                # Parse date for comparison
                parsed_date = self._parse_roster_date(date_str)

                if unit_id not in unit_files or parsed_date > unit_files[unit_id][1]:
                    unit_files[unit_id] = (roster_file.name, parsed_date)

                print(f"   Found: {unit_id} → {roster_file.name} ({date_str})")

        # Extract just the filenames for latest files
        roster_files = {unit_id: filename for unit_id, (filename, _) in unit_files.items()}

        if roster_files:
            print(f"✅ Auto-detected {len(roster_files)} units: {', '.join(roster_files.keys())}")
            for unit_id, filename in roster_files.items():
                print(f"   {unit_id}: {filename}")
        else:
            print("❌ No roster files found matching pattern '{UNIT} Roster {DATE}.html'")

        return roster_files

    def _parse_roster_date(self, date_str: str) -> datetime:
        """
        Parse various date formats found in roster filenames

        Inputs:
            date_str: Date string from filename (e.g., "16Sep2025", "21Sep2025")

        Returns:
            datetime object for comparison
        """
        # Try common date formats
        date_formats = [
            '%d%b%Y',      # 16Sep2025
            '%Y-%m-%d',    # 2025-09-16
            '%m-%d-%Y',    # 09-16-2025
            '%Y%m%d',      # 20250916
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Fallback: use file modification time if parsing fails
        print(f"⚠️ Could not parse date '{date_str}', using fallback")
        return datetime.now()

    def load_config(self, config_file: str = "config.json") -> Dict:
        """
        Load configuration from JSON file

        Inputs:
            config_file: Path to configuration file

        Returns:
            Configuration dictionary with defaults
        """
        config_path = Path(config_file)
        default_config = {
            "units": ["T32", "T7012"],
            "roster_pattern": "{unit} Roster *.html",
            "auto_select_latest": True,
            "roster_dir": "data/input/rosters"
        }

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                print(f"📄 Loaded configuration from {config_file}")
                return {**default_config, **config}
            except Exception as e:
                print(f"⚠️ Error loading config {config_file}: {e}")
                print("   Using default configuration")

        return default_config
        
    def extract_adults_from_roster(self, roster_file: Path, troop_id: str) -> List[Dict]:
        """Extract adult members from a single roster HTML file"""
        print(f"📋 Processing {roster_file.name} for {troop_id}...")
        
        with open(roster_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the Adult Members section
        adult_section_start = content.find("Adult Members")
        if adult_section_start == -1:
            print(f"❌ No 'Adult Members' section found in {roster_file.name}")
            return []
        
        # Extract text after Adult Members section
        adult_content = content[adult_section_start:]
        
        # Parse with BeautifulSoup for better structure
        soup = BeautifulSoup(content, 'html.parser')
        
        adults = []
        
        # Pattern to match adult member lines:
        # Number \t Name \t\t Address \t Gender \t Position
        # MemberID \t YPT Status \t Full Address \t Phone \t Expiration
        
        # Look for lines with names (pattern: number followed by name)
        name_pattern = r'(\d+)\s+([A-Za-z]+(?:\s+[A-Z])?(?:\s+[A-Za-z-]+)+)\s+\t'
        
        lines = adult_content.split('\n')
        current_adult = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Check if this is a name line (starts with number and has name)
            name_match = re.match(r'(\d+)\s+(.+?)\s+\t', line)
            if name_match:
                seq_num = name_match.group(1)
                full_name = name_match.group(2).strip()
                
                # Skip if it's just header text
                if 'Name' in full_name or 'MemberID' in full_name:
                    continue
                
                # Extract position from the line (it's at the end after gender)
                # Format: Number \t Name \t\t Address \t Gender \t Position
                parts = line.split('\t')
                position = parts[-1].strip() if len(parts) >= 5 else ""
                
                # Check if the next line contains a position continuation
                # (some positions span multiple lines in the HTML)
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # If next line doesn't start with a number (new member) and has text,
                    # it might be a position continuation
                    if next_line and not re.match(r'^\d+\s+', next_line) and not re.match(r'^\d{8}\s+', next_line):
                        # Check if it looks like a position continuation (not member ID line)
                        if not ('No' in next_line and len(next_line.split()) > 3):
                            position += " " + next_line
                
                # Skip Unit Participants (18+ members still active as Scouts, not Adult Leaders)
                if position == "Unit Participant":
                    print(f"   Skipping Unit Participant: {full_name}")
                    continue
                
                # Parse the name - extract only first and last names, ignore middle names/initials
                name_parts = full_name.split()
                if len(name_parts) >= 2:
                    # Always use just the first word as first_name
                    first_name = name_parts[0]
                    # Always use the last word as last_name
                    last_name = name_parts[-1]
                    
                    current_adult = {
                        'sequence': seq_num,
                        'full_name': full_name,
                        'first_name': first_name,
                        'last_name': last_name,
                        'name_key': f"{first_name} {last_name}",
                        'position': position,
                        'troop': troop_id,
                        'raw_line': line
                    }
                    adults.append(current_adult)
                    
        print(f"✅ Extracted {len(adults)} adults from {troop_id}")
        return adults
    
    def process_all_rosters(self, roster_files: Optional[Dict[str, str]] = None) -> Dict[str, Dict]:
        """
        Process roster files and create unified adult list

        Inputs:
            roster_files: Optional dict mapping unit_id -> filename.
                         If None, uses auto-detection.

        Returns:
            Dict mapping name_key -> adult_data with troop affiliations
        """
        if roster_files is None:
            roster_files = self.auto_detect_rosters()

        if not roster_files:
            print("❌ No roster files to process")
            return {}

        unified_adults = {}

        for troop_id, filename in roster_files.items():
            roster_path = self.roster_dir / filename
            if not roster_path.exists():
                print(f"⚠️ Roster file not found: {roster_path}")
                continue

            adults = self.extract_adults_from_roster(roster_path, troop_id)

            # Add to unified list with troop tracking
            for adult in adults:
                name_key = adult['name_key']

                if name_key in unified_adults:
                    # Adult is in multiple troops
                    unified_adults[name_key]['troops'].add(troop_id)
                    unified_adults[name_key]['troop_list'] = sorted(unified_adults[name_key]['troops'])
                else:
                    # New adult
                    unified_adults[name_key] = {
                        'first_name': adult['first_name'],
                        'last_name': adult['last_name'],
                        'full_name': adult['full_name'],
                        'name_key': name_key,
                        'troops': {troop_id},
                        'troop_list': [troop_id],
                        'member_data': {troop_id: adult}
                    }

        print(f"📊 Unified adult list: {len(unified_adults)} unique adults")
        return unified_adults
    
    def create_mbc_join_keys(self, mbc_data: Dict) -> Dict[str, Dict]:
        """Create join keys for Merit Badge Counselor data"""
        mbc_keys = {}
        
        for counselor in mbc_data.get('counselors', []):
            # MBC key: ((first_name) or (alt_first_name)) + (last_name)
            first_name = counselor.get('first_name', '').strip()
            alt_first_name = counselor.get('alt_first_name', '').strip()
            last_name = counselor.get('last_name', '').strip()
            
            # Use alt_first_name if available and different from first_name
            if alt_first_name and alt_first_name != first_name:
                key_name = alt_first_name
            else:
                key_name = first_name
            
            mbc_key = f"{key_name} {last_name}".strip()
            
            if mbc_key:
                mbc_keys[mbc_key] = counselor
                # Also add the full name variant for matching
                full_key = f"{first_name} {last_name}".strip()
                if full_key != mbc_key:
                    mbc_keys[full_key] = counselor
        
        print(f"🎯 Created {len(mbc_keys)} MBC join keys")
        return mbc_keys

    def load_supplemental_mbcs(self) -> Dict[str, str]:
        """
        Load unit-associated MBCs from supplemental input file

        Returns:
            Dict mapping name_key -> unit_id for supplemental MBCs
        """
        supplemental_mbcs = {}

        if not self.supplemental_file.exists():
            print(f"ℹ️ No supplemental MBC file found: {self.supplemental_file}")
            return supplemental_mbcs

        try:
            with open(self.supplemental_file, 'r') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Parse CSV: "FirstName LastName, UnitID"
                if ',' not in line:
                    print(f"⚠️ Skipping malformed line {line_num}: {line}")
                    continue

                name_part, unit_part = line.split(',', 1)
                name = name_part.strip()
                unit_id = unit_part.strip()

                if name and unit_id:
                    supplemental_mbcs[name] = unit_id

            print(f"📋 Loaded {len(supplemental_mbcs)} supplemental MBC associations")
            return supplemental_mbcs

        except Exception as e:
            print(f"❌ Error loading supplemental MBC file: {e}")
            return supplemental_mbcs

    def join_adults_with_mbcs(self, unified_adults: Dict, mbc_data: Dict) -> Dict:
        """Join adult roster data with Merit Badge Counselor data, including supplemental MBCs"""
        mbc_keys = self.create_mbc_join_keys(mbc_data)
        supplemental_mbcs = self.load_supplemental_mbcs()

        troop_counselors = []
        non_counselor_leaders = []
        supplemental_counselors = []

        # Process roster adults
        for name_key, adult in unified_adults.items():
            if name_key in mbc_keys:
                # This adult is also a Merit Badge Counselor
                mbc_info = mbc_keys[name_key]
                troop_counselor = {
                    'name': adult['full_name'],
                    'first_name': adult['first_name'],
                    'last_name': adult['last_name'],
                    'troops': adult['troop_list'],
                    'troop_display': ', '.join([f"T{t}" if not t.startswith('T') else t for t in adult['troop_list']]),
                    'merit_badges': mbc_info.get('merit_badges', ''),
                    'email': mbc_info.get('email', ''),
                    'phone': mbc_info.get('phone', ''),
                    'ypt_expiration': mbc_info.get('ypt_expiration', ''),
                    'mbc_data': mbc_info,
                    'roster_data': adult,
                    'source': 'roster'
                }
                troop_counselors.append(troop_counselor)
            else:
                # This adult is not a Merit Badge Counselor
                non_counselor = {
                    'name': adult['full_name'],
                    'first_name': adult['first_name'],
                    'last_name': adult['last_name'],
                    'troops': adult['troop_list'],
                    'troop_display': ', '.join([f"T{t}" if not t.startswith('T') else t for t in adult['troop_list']]),
                    'roster_data': adult
                }
                non_counselor_leaders.append(non_counselor)

        # Process supplemental MBCs (MBC-only registrations)
        processed_mbc_names = {adult['name'] for adult in troop_counselors}

        for supplemental_name, unit_id in supplemental_mbcs.items():
            if supplemental_name in mbc_keys and supplemental_name not in processed_mbc_names:
                mbc_info = mbc_keys[supplemental_name]

                # Normalize unit ID for display
                unit_display = unit_id
                if unit_id.lower().startswith('troop '):
                    unit_num = unit_id.split(' ', 1)[1]
                    unit_display = f"T{unit_num}"
                elif not unit_id.startswith('T'):
                    unit_display = f"T{unit_id}"

                supplemental_counselor = {
                    'name': supplemental_name,
                    'first_name': mbc_info.get('first_name', ''),
                    'last_name': mbc_info.get('last_name', ''),
                    'troops': [unit_display],
                    'troop_display': unit_display,
                    'merit_badges': mbc_info.get('merit_badges', ''),
                    'email': mbc_info.get('email', ''),
                    'phone': mbc_info.get('phone', ''),
                    'ypt_expiration': mbc_info.get('ypt_expiration', ''),
                    'mbc_data': mbc_info,
                    'roster_data': None,
                    'source': 'supplemental'
                }
                supplemental_counselors.append(supplemental_counselor)

        print(f"🏆 Found {len(troop_counselors)} troop members who are MBCs")
        print(f"📋 Found {len(supplemental_counselors)} supplemental MBCs (MBC-only registrations)")
        print(f"👥 Found {len(non_counselor_leaders)} troop members who are not MBCs")

        return {
            'troop_counselors': troop_counselors,
            'supplemental_counselors': supplemental_counselors,
            'non_counselor_leaders': non_counselor_leaders,
            'total_adults': len(unified_adults),
            'mbc_matches': len(troop_counselors),
            'supplemental_matches': len(supplemental_counselors)
        }

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Process Scout unit rosters and join with Merit Badge Counselor data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python roster_processor.py                          # Auto-detect latest rosters
  python roster_processor.py --units T32,T7012       # Specify units
  python roster_processor.py --config myconfig.json  # Use custom config
  python roster_processor.py --roster-dir /path/to/rosters  # Custom directory
        """
    )

    parser.add_argument(
        '--units',
        help='Comma-separated list of unit IDs (e.g., T32,T7012)',
        type=str
    )

    parser.add_argument(
        '--roster-dir',
        help='Directory containing roster files',
        default='data/input/rosters',
        type=str
    )

    parser.add_argument(
        '--config',
        help='Configuration file path',
        type=str
    )

    parser.add_argument(
        '--auto-detect',
        help='Force auto-detection of rosters (default behavior)',
        action='store_true'
    )

    parser.add_argument(
        '--mbc-data',
        help='Path to MBC counselors data file',
        default='data/processed/mbc_counselors.json',
        type=str
    )

    parser.add_argument(
        '--supplemental-file',
        help='Path to supplemental MBC associations file',
        default='data/input/unit_associated_mbcs.txt',
        type=str
    )

    return parser.parse_args()

def main():
    """Main processing function with command line argument support"""
    args = parse_arguments()

    # Initialize processor
    processor = RosterProcessor(roster_dir=args.roster_dir, supplemental_file=args.supplemental_file)

    # Determine roster files to process
    roster_files = None

    if args.config:
        # Load configuration file
        config = processor.load_config(args.config)
        if not args.units:  # Only use config units if not overridden
            roster_files = {unit: f"{unit} Roster *.html" for unit in config['units']}
            # Auto-detect actual files for these units
            roster_files = None  # Let auto_detect handle it

    if args.units:
        # Use specified units
        unit_list = [unit.strip() for unit in args.units.split(',')]
        print(f"🎯 Using specified units: {', '.join(unit_list)}")
        # Let auto-detection find the latest files for these units
        all_detected = processor.auto_detect_rosters()
        roster_files = {unit: all_detected[unit] for unit in unit_list if unit in all_detected}

        if len(roster_files) != len(unit_list):
            missing = set(unit_list) - set(roster_files.keys())
            print(f"⚠️ Could not find rosters for units: {', '.join(missing)}")

    # Process rosters
    print("🚀 Starting roster processing...")
    unified_adults = processor.process_all_rosters(roster_files)

    if not unified_adults:
        print("❌ No adults found in rosters")
        return

    # Load cleaned MBC data using specified file
    mbc_file = Path(args.mbc_data)
    if not mbc_file.exists():
        print(f"❌ MBC data file not found: {mbc_file}")
        return

    with open(mbc_file, 'r') as f:
        mbc_data = json.load(f)

    print(f"📖 Loaded {len(mbc_data.get('counselors', []))} Merit Badge Counselors from {mbc_file}")

    # Join data
    joined_data = processor.join_adults_with_mbcs(unified_adults, mbc_data)

    # Convert sets to lists for JSON serialization
    def convert_sets_to_lists(obj):
        if isinstance(obj, dict):
            return {k: convert_sets_to_lists(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_sets_to_lists(item) for item in obj]
        elif isinstance(obj, set):
            return sorted(list(obj))
        else:
            return obj

    joined_data_serializable = convert_sets_to_lists(joined_data)

    # Save results
    output_file = Path("data/processed/roster_mbc_join.json")
    with open(output_file, 'w') as f:
        json.dump(joined_data_serializable, f, indent=2)

    print(f"💾 Results saved to {output_file}")
    print("\n📊 Summary:")
    print(f"   Total adults in rosters: {joined_data['total_adults']}")
    print(f"   Adults who are MBCs: {joined_data['mbc_matches']}")
    print(f"   Adults who are not MBCs: {len(joined_data['non_counselor_leaders'])}")

if __name__ == "__main__":
    main()