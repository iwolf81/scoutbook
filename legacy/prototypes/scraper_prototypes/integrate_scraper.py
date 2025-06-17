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
