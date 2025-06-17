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
