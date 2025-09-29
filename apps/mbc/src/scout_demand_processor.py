#!/usr/bin/env python3
"""
Scout Demand Processor for Merit Badge Coverage Priority Analysis

Parses Scout merit badge signup data and calculates demand metrics to identify
coverage gaps and recruitment priorities.

Usage:
    python scout_demand_processor.py
    python scout_demand_processor.py --input-file "path/to/signup.csv"
    python scout_demand_processor.py --output-file "custom_output.json"
"""

import csv
import json
import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ScoutDemandProcessor:
    """Process Scout merit badge signup data into structured demand analysis"""

    def __init__(self, input_dir: str = "data/input", output_dir: str = "data/processed"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Eagle-required merit badges for priority weighting
        self.eagle_badges = {
            'Camping', 'Citizenship in Society', 'Citizenship in Community',
            'Citizenship in the Nation', 'Citizenship in the World', 'Communication',
            'Cooking', 'Cycling', 'Emergency Preparedness', 'Environmental Science',
            'Family Life', 'First Aid', 'Hiking', 'Lifesaving', 'Personal Fitness',
            'Personal Management', 'Swimming', 'Sustainability'
        }

    def auto_detect_signup_file(self) -> Optional[Path]:
        """
        Auto-detect the latest Scout signup CSV file

        Returns:
            Path to latest signup file or None if not found
        """
        print(f"🔍 Auto-detecting Scout signup files in {self.input_dir}...")

        # Pattern: Scout Requested Merit Badges*.csv
        signup_pattern = re.compile(r'^Scout Requested Merit Badges.*\.csv$', re.IGNORECASE)

        signup_files = []
        for file_path in self.input_dir.glob('*.csv'):
            if signup_pattern.match(file_path.name):
                signup_files.append(file_path)

        if not signup_files:
            print("❌ No Scout signup CSV files found")
            return None

        # Sort by modification time, newest first
        signup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        latest_file = signup_files[0]

        print(f"📁 Found latest signup file: {latest_file.name}")
        return latest_file

    def parse_signup_csv(self, csv_file: Path) -> Dict:
        """
        Parse Scout signup CSV into structured demand data

        Args:
            csv_file: Path to the CSV file

        Returns:
            Dict with badge demand analysis
        """
        print(f"📊 Processing Scout signup data from {csv_file.name}...")

        badge_demand = {}
        eagle_section = False
        non_eagle_section = False

        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)

                for row_num, row in enumerate(reader, 1):
                    if not row or len(row) < 2:
                        continue

                    # Check both column A and B for section headers and content
                    col_a = row[0].strip() if len(row) > 0 else ""
                    col_b = row[1].strip() if len(row) > 1 else ""

                    # Detect section headers (can be in column A or B)
                    section_text = col_a + " " + col_b
                    if 'Eagle Merit Badges' in section_text:
                        eagle_section = True
                        non_eagle_section = False
                        continue
                    elif 'Non-Eagle Merit Badges' in section_text:
                        eagle_section = False
                        non_eagle_section = True
                        continue
                    elif col_b == 'Merit Badge':  # Column headers
                        continue

                    # Process merit badge rows - merit badge name is in column B (index 1)
                    if (eagle_section or non_eagle_section) and col_b:
                        # Clean badge name (remove * for Eagle badges)
                        badge_name = col_b.rstrip('*').strip()
                        if not badge_name:
                            continue

                        # Extract Scout names from columns C onwards (index 2+)
                        scouts = []
                        for col_idx in range(2, len(row)):
                            scout_name = row[col_idx].strip()
                            if scout_name and scout_name not in scouts:
                                scouts.append(scout_name)

                        # Store demand data
                        is_eagle = badge_name in self.eagle_badges
                        badge_demand[badge_name] = {
                            'badge_name': badge_name,
                            'interested_scouts': scouts,
                            'scout_count': len(scouts),
                            'is_eagle_required': is_eagle,
                            'section': 'Eagle' if eagle_section else 'Non-Eagle',
                            'priority_weight': 1.5 if is_eagle else 1.0
                        }

        except Exception as e:
            print(f"❌ Error parsing CSV file: {e}")
            return {}

        print(f"✅ Parsed {len(badge_demand)} merit badges with Scout interest")
        return badge_demand

    def calculate_demand_metrics(self, badge_demand: Dict) -> Dict:
        """
        Calculate overall demand metrics and statistics

        Args:
            badge_demand: Raw badge demand data

        Returns:
            Enhanced data with metrics
        """
        # Calculate summary statistics
        total_badges_requested = len(badge_demand)
        total_scout_requests = sum(data['scout_count'] for data in badge_demand.values())
        eagle_badges_requested = len([b for b in badge_demand.values() if b['is_eagle_required']])
        non_eagle_badges_requested = total_badges_requested - eagle_badges_requested

        # Find high-demand badges (3+ Scouts)
        high_demand_badges = [
            badge for badge, data in badge_demand.items()
            if data['scout_count'] >= 3
        ]

        # Get unique Scouts participating
        all_scouts = set()
        for data in badge_demand.values():
            all_scouts.update(data['interested_scouts'])

        # Sort badges by demand (Scout count descending)
        sorted_badges = sorted(
            badge_demand.items(),
            key=lambda x: (-x[1]['scout_count'], x[0])  # By count desc, then name asc
        )

        summary = {
            'analysis_timestamp': datetime.now().isoformat(),
            'total_badges_requested': total_badges_requested,
            'total_scout_requests': total_scout_requests,
            'unique_scouts_participating': len(all_scouts),
            'eagle_badges_requested': eagle_badges_requested,
            'non_eagle_badges_requested': non_eagle_badges_requested,
            'high_demand_badges': high_demand_badges,
            'participating_scouts': sorted(list(all_scouts)),
            'top_requested_badges': [
                {
                    'badge_name': badge,
                    'scout_count': data['scout_count'],
                    'is_eagle': data['is_eagle_required']
                }
                for badge, data in sorted_badges[:10]  # Top 10
            ]
        }

        result = {
            'badge_demand': badge_demand,
            'demand_summary': summary
        }

        print(f"📈 Demand Metrics:")
        print(f"   • {total_badges_requested} badges requested by Scouts")
        print(f"   • {total_scout_requests} total Scout-badge combinations")
        print(f"   • {len(all_scouts)} unique Scouts participating")
        print(f"   • {len(high_demand_badges)} high-demand badges (3+ Scouts)")

        return result

    def save_demand_analysis(self, demand_data: Dict, output_file: Optional[Path] = None) -> Path:
        """
        Save demand analysis to JSON file

        Args:
            demand_data: Processed demand analysis
            output_file: Custom output file path (optional)

        Returns:
            Path to saved file
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"scout_demand_analysis_{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(demand_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved demand analysis: {output_file}")
        return output_file

    def process_scout_demands(self, input_file: Optional[Path] = None, output_file: Optional[Path] = None) -> Dict:
        """
        Main processing function - full pipeline

        Args:
            input_file: Custom input CSV file (optional)
            output_file: Custom output JSON file (optional)

        Returns:
            Processed demand analysis data
        """
        print("🚀 Starting Scout Demand Analysis...")

        # Determine input file
        if input_file is None:
            input_file = self.auto_detect_signup_file()
            if input_file is None:
                raise FileNotFoundError("No Scout signup CSV file found")

        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        # Parse CSV data
        badge_demand = self.parse_signup_csv(input_file)
        if not badge_demand:
            raise ValueError("No valid badge demand data found in CSV")

        # Calculate metrics
        demand_analysis = self.calculate_demand_metrics(badge_demand)

        # Save results
        output_path = self.save_demand_analysis(demand_analysis, output_file)

        print(f"🎉 Scout demand analysis complete!")
        return demand_analysis


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Process Scout merit badge signup data for demand analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scout_demand_processor.py                                    # Auto-detect latest CSV
  python scout_demand_processor.py --input-file "signup_29Sep.csv"   # Specific input file
  python scout_demand_processor.py --output-file "custom.json"       # Custom output file
        """
    )

    parser.add_argument(
        '--input-file',
        help='Path to Scout signup CSV file',
        type=str
    )

    parser.add_argument(
        '--output-file',
        help='Path for output JSON file',
        type=str
    )

    parser.add_argument(
        '--input-dir',
        help='Directory containing input files',
        default='data/input',
        type=str
    )

    parser.add_argument(
        '--output-dir',
        help='Directory for output files',
        default='data/processed',
        type=str
    )

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()

    try:
        # Initialize processor
        processor = ScoutDemandProcessor(
            input_dir=args.input_dir,
            output_dir=args.output_dir
        )

        # Process demand data
        input_path = Path(args.input_file) if args.input_file else None
        output_path = Path(args.output_file) if args.output_file else None

        demand_analysis = processor.process_scout_demands(input_path, output_path)

        # Print summary
        summary = demand_analysis['demand_summary']
        print(f"\n📊 Analysis Summary:")
        print(f"   📋 {summary['total_badges_requested']} badges have Scout interest")
        print(f"   👥 {summary['unique_scouts_participating']} Scouts participated")
        print(f"   🦅 {summary['eagle_badges_requested']} Eagle-required badges requested")
        print(f"   🏆 {len(summary['high_demand_badges'])} high-demand badges (3+ Scouts)")

        return 0

    except KeyboardInterrupt:
        print("\n⚠️ Processing cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Processing failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())