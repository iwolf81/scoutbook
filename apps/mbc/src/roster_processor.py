#!/usr/bin/env python3
"""
Roster Processing Script for ScoutBook Integration

Extracts adult members from troop rosters and creates unified list with troop affiliations
for joining with Merit Badge Counselor data.

Key matching logic:
- MBC key: ((first_name) or (alt_first_name)) + (last_name)
- Roster key: (first_name + last_name)
"""

import re
import json
from typing import Dict, List, Set
from bs4 import BeautifulSoup
from pathlib import Path

class RosterProcessor:
    def __init__(self, roster_dir: str = "data/input/rosters"):
        self.roster_dir = Path(roster_dir)
        self.adults = {}  # name -> {troops: set, member_data: dict}
        
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
    
    def process_all_rosters(self) -> Dict[str, Dict]:
        """Process all roster files and create unified adult list"""
        roster_files = {
            'T32': 'T32 Roster 16Sep2025.html',
            'T7012': 'T7012 Roster 16Sep2025.html'
        }
        
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
    
    def join_adults_with_mbcs(self, unified_adults: Dict, mbc_data: Dict) -> Dict:
        """Join adult roster data with Merit Badge Counselor data"""
        mbc_keys = self.create_mbc_join_keys(mbc_data)
        
        troop_counselors = []
        non_counselor_leaders = []
        
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
                    'roster_data': adult
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
        
        print(f"🏆 Found {len(troop_counselors)} troop members who are MBCs")
        print(f"👥 Found {len(non_counselor_leaders)} troop members who are not MBCs")
        
        return {
            'troop_counselors': troop_counselors,
            'non_counselor_leaders': non_counselor_leaders,
            'total_adults': len(unified_adults),
            'mbc_matches': len(troop_counselors)
        }

def main():
    """Main processing function"""
    processor = RosterProcessor()
    
    # Process rosters
    print("🚀 Starting roster processing...")
    unified_adults = processor.process_all_rosters()
    
    # Load cleaned MBC data
    mbc_file = Path("data/processed/mbc_counselors_cleaned.json")
    if not mbc_file.exists():
        print(f"❌ MBC data file not found: {mbc_file}")
        return
    
    with open(mbc_file, 'r') as f:
        mbc_data = json.load(f)
    
    print(f"📖 Loaded {len(mbc_data.get('counselors', []))} Merit Badge Counselors")
    
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