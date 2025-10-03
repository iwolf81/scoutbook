#!/usr/bin/env python3
"""
Coverage Gap Analyzer for Merit Badge Priority Identification

Analyzes Scout demand data against MBC coverage to identify priority gaps
and recruitment opportunities for unit leaders.

Usage:
    python coverage_gap_analyzer.py
    python coverage_gap_analyzer.py --demand-file scout_demand.json --mbc-file roster_mbc_join.json
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class CoverageGapAnalyzer:
    """Analyze merit badge coverage gaps using Scout demand and MBC data"""

    def __init__(self, processed_dir: str = "data/processed", exclusion_file: str = "data/input/exclusion_list.txt"):
        self.processed_dir = Path(processed_dir)
        self.exclusion_file = Path(exclusion_file)
        self.fully_excluded, self.selective_inclusion = self.load_exclusion_list()

        # Badge name mapping to handle discrepancies between Scout signup and MBC data
        self.badge_name_mapping = {
            # Scout signup name -> MBC data name
            'Citizenship in Community': 'Citizenship in the Community',
            # Add more mappings as needed
        }

    def load_exclusion_list(self) -> tuple[set, dict]:
        """
        Load exclusion and selective inclusion rules from file

        Returns:
            Tuple of (fully_excluded_names, selective_inclusion_map)
            - fully_excluded_names: Set of normalized names to fully exclude
            - selective_inclusion_map: Dict mapping normalized_name -> allowed_badge
        """
        fully_excluded = set()
        selective_inclusion = {}

        if not self.exclusion_file.exists():
            return fully_excluded, selective_inclusion

        with open(self.exclusion_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Check if line has comma (selective inclusion format)
                    if ',' in line:
                        parts = [p.strip() for p in line.split(',', 1)]
                        name = parts[0]
                        badge = parts[1] if len(parts) > 1 else None

                        if name and badge:
                            # Normalize name for matching
                            normalized_name = name.lower().replace(' ', '')
                            selective_inclusion[normalized_name] = badge
                    else:
                        # Full exclusion (name only)
                        normalized = line.lower().replace(' ', '')
                        fully_excluded.add(normalized)

        total_rules = len(fully_excluded) + len(selective_inclusion)
        if total_rules > 0:
            print(f"🚫 Loaded {len(fully_excluded)} full exclusions and {len(selective_inclusion)} selective inclusions")

        return fully_excluded, selective_inclusion

    def get_exclusion_rule(self, name: str) -> tuple[str, str]:
        """
        Get exclusion rule for a counselor name using smart matching

        Matches work even with middle names/initials:
        - "Jon Campbell" matches "Jon A Campbell"
        - "Tori Campbell" matches "Tori J Campbell"

        Returns:
            Tuple of (rule_type, allowed_badge)
            - rule_type: 'none' (not excluded), 'full' (fully excluded), or 'selective' (selective inclusion)
            - allowed_badge: Merit badge name if selective, None otherwise
        """
        if not name:
            return ('none', None)

        # Normalize the full name
        name_lower = name.lower()
        name_parts = name_lower.split()

        # Helper function to check if normalized name matches
        def matches_normalized(excluded_name):
            # Exact match after normalization
            if excluded_name == name_lower.replace(' ', ''):
                return True
            # First + last name match (ignoring middle names/initials)
            if len(name_parts) >= 2:
                first_last = f"{name_parts[0]}{name_parts[-1]}"
                if excluded_name == first_last:
                    return True
            return False

        # Check fully excluded names
        for excluded in self.fully_excluded:
            if matches_normalized(excluded):
                return ('full', None)

        # Check selective inclusion names
        for excluded_name, allowed_badge in self.selective_inclusion.items():
            if matches_normalized(excluded_name):
                return ('selective', allowed_badge)

        return ('none', None)

    def auto_detect_latest_files(self) -> Tuple[Optional[Path], Optional[Path]]:
        """
        Auto-detect latest demand analysis and MBC data files

        Returns:
            Tuple of (demand_file, mbc_file) paths, or None for missing files
        """
        print(f"🔍 Auto-detecting analysis files in {self.processed_dir}...")

        # Find latest scout demand analysis file
        demand_files = list(self.processed_dir.glob("scout_demand_analysis_*.json"))
        demand_file = None
        if demand_files:
            demand_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            demand_file = demand_files[0]
            print(f"📊 Found demand analysis: {demand_file.name}")

        # Find MBC data file
        mbc_file = self.processed_dir / "roster_mbc_join.json"
        if mbc_file.exists():
            print(f"🎯 Found MBC data: {mbc_file.name}")
        else:
            mbc_file = None
            print("❌ MBC data file not found: roster_mbc_join.json")

        return demand_file, mbc_file

    def load_demand_data(self, demand_file: Path) -> Dict:
        """Load Scout demand analysis data"""
        with open(demand_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_mbc_data(self, mbc_file: Path) -> Dict:
        """Load MBC coverage data"""
        with open(mbc_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def extract_mbc_coverage(self, mbc_data: Dict) -> Dict[str, List[Dict]]:
        """
        Extract merit badge coverage from MBC data

        Args:
            mbc_data: Loaded MBC join data

        Returns:
            Dict mapping badge_name -> list of counselor info
        """
        badge_coverage = {}

        # Process both troop counselors and supplemental counselors
        all_counselors = (
            mbc_data.get('troop_counselors', []) +
            mbc_data.get('supplemental_counselors', [])
        )

        excluded_count = 0
        selective_count = 0

        for counselor in all_counselors:
            counselor_name = counselor.get('name', '')

            # Check exclusion rule for this counselor
            rule_type, allowed_badge = self.get_exclusion_rule(counselor_name)

            # Handle full exclusion
            if rule_type == 'full':
                excluded_count += 1
                continue

            counselor_info = {
                'name': counselor_name,
                'troops': counselor.get('troops', []),
                'troop_display': counselor.get('troop_display', ''),
                'email': counselor.get('email', ''),
                'phone': counselor.get('phone', ''),
                'source': counselor.get('source', 'roster')
            }

            # Parse merit badges list
            merit_badges_str = counselor.get('merit_badges', '')
            if merit_badges_str:
                badges = [badge.strip() for badge in merit_badges_str.split(',')]

                # Handle selective inclusion
                if rule_type == 'selective':
                    # Only include the allowed badge
                    if allowed_badge in badges:
                        if allowed_badge not in badge_coverage:
                            badge_coverage[allowed_badge] = []
                        badge_coverage[allowed_badge].append(counselor_info)
                        selective_count += 1
                else:
                    # Include all badges (no exclusion)
                    for badge in badges:
                        if badge:
                            if badge not in badge_coverage:
                                badge_coverage[badge] = []
                            badge_coverage[badge].append(counselor_info)

        if excluded_count > 0:
            print(f"🚫 Excluded {excluded_count} counselors from coverage analysis")
        if selective_count > 0:
            print(f"🎯 Applied {selective_count} selective inclusions (counselors limited to specific badges)")
        print(f"📋 Extracted coverage for {len(badge_coverage)} merit badges")
        return badge_coverage

    def _is_eagle_required_badge(self, badge_name: str) -> bool:
        """Check if a badge is Eagle-required based on known Eagle badge list"""
        # Standard 13 Eagle-required merit badges (as of 2023)
        eagle_required_badges = {
            'Camping', 'Citizenship in Community', 'Citizenship in the Nation',
            'Citizenship in the World', 'Communication', 'Cooking',
            'Emergency Preparedness', 'Environmental Science', 'Family Life',
            'First Aid', 'Hiking', 'Personal Fitness', 'Personal Management',
            'Sustainability'  # Added as alternate to Environmental Science
        }

        # Apply name mapping and check
        mapped_name = self.badge_name_mapping.get(badge_name, badge_name)
        return badge_name in eagle_required_badges or mapped_name in eagle_required_badges

    def calculate_priority_scores(self, demand_data: Dict, coverage_data: Dict) -> List[Dict]:
        """
        Calculate priority scores for merit badges

        Priority Score = (Scout Demand × Eagle Multiplier) / (Counselor Count + 1)
        - Higher score = Higher recruitment priority

        Args:
            demand_data: Scout demand analysis data
            coverage_data: MBC coverage data

        Returns:
            List of priority analysis records
        """
        badge_priorities = []
        badge_demand = demand_data.get('badge_demand', {})

        # Get all Eagle-required badges from demand data for Pass 4 Critical Priority logic
        eagle_badges_in_demand = {name: info for name, info in badge_demand.items()
                                 if info.get('is_eagle_required', False)}

        # Process ALL coverage data to find Eagle badges with 0-1 MBC (Pass 4 requirement)
        all_eagle_badges_with_limited_coverage = {}
        for badge_name, counselors in coverage_data.items():
            counselor_count = len(counselors)
            if counselor_count <= 1:  # 0 or 1 MBC
                # Check if this is an Eagle-required badge by looking it up in demand data or Eagle badge list
                eagle_info = eagle_badges_in_demand.get(badge_name)
                if eagle_info or self._is_eagle_required_badge(badge_name):
                    all_eagle_badges_with_limited_coverage[badge_name] = {
                        'counselors': counselors,
                        'counselor_count': counselor_count,
                        'is_eagle_required': True,
                        'scout_demand': eagle_info.get('scout_count', 0) if eagle_info else 0,
                        'interested_scouts': eagle_info.get('interested_scouts', []) if eagle_info else [],
                        'priority_weight': 1.5
                    }

        # First add ALL Eagle badges with 0-1 MBC to priorities (Pass 4 requirement)
        for badge_name, eagle_info in all_eagle_badges_with_limited_coverage.items():
            counselors = eagle_info['counselors']
            counselor_count = eagle_info['counselor_count']
            scout_count = eagle_info['scout_demand']

            # Calculate priority score
            eagle_multiplier = eagle_info['priority_weight']
            priority_score = (scout_count * eagle_multiplier) / (counselor_count + 1)

            # Pass 4: ALL Eagle badges with 0-1 MBC are Critical Priority
            gap_level = "CRITICAL"
            if counselor_count == 0:
                gap_description = "Eagle-required Merit Badge with no Merit Badge Counselor (MBC) coverage"
            else:
                gap_description = "Only 1 MBC for Eagle-required Merit Badge (busy Troop Committee Chair needs help)"

            # Create priority record
            priority_record = {
                'badge_name': badge_name,
                'scout_demand': scout_count,
                'interested_scouts': eagle_info['interested_scouts'],
                'counselor_count': counselor_count,
                'counselors': counselors,
                'is_eagle_required': True,
                'priority_score': round(priority_score, 2),
                'gap_level': gap_level,
                'gap_description': gap_description
            }
            badge_priorities.append(priority_record)

        # Then process Scout-requested badges
        for badge_name, demand_info in badge_demand.items():
            scout_count = demand_info.get('scout_count', 0)
            if scout_count == 0:  # Skip badges with no Scout interest
                continue

            # Skip Eagle badges already processed in Pass 4 Critical Priority logic
            if badge_name in all_eagle_badges_with_limited_coverage:
                continue

            # Apply name mapping to handle discrepancies
            mbc_badge_name = self.badge_name_mapping.get(badge_name, badge_name)
            if mbc_badge_name != badge_name:
                print(f"🔄 Name mapping: '{badge_name}' → '{mbc_badge_name}'")

            # Get coverage info using mapped name
            counselors = coverage_data.get(mbc_badge_name, [])
            counselor_count = len(counselors)

            # Calculate priority score
            eagle_multiplier = demand_info.get('priority_weight', 1.0)
            priority_score = (scout_count * eagle_multiplier) / (counselor_count + 1)

            # Determine gap classification based on Pass 3 feedback definitions
            is_eagle = demand_info.get('is_eagle_required', False)

            # Merit badges with 3+ MBCs are considered adequately covered and not priority
            if counselor_count >= 3:
                gap_level = "ADEQUATE"
                gap_description = f"Adequate coverage ({counselor_count} Merit Badge Counselors)"
            elif (counselor_count == 0 and is_eagle) or (counselor_count == 1 and is_eagle):
                gap_level = "CRITICAL"
                if counselor_count == 0:
                    gap_description = "Eagle-required Merit Badge with no Merit Badge Counselor (MBC) coverage"
                else:
                    gap_description = "Only 1 MBC for Eagle-required Merit Badge (busy Troop Committee Chair needs help)"
            elif (scout_count >= 3 and not is_eagle and counselor_count == 0):
                gap_level = "HIGH"
                gap_description = f"{scout_count} or more Scouts requesting non-Eagle Merit Badge with no MBC coverage"
            elif (scout_count >= 1 and scout_count <= 2 and not is_eagle and counselor_count == 0):
                gap_level = "MEDIUM"
                gap_description = f"{scout_count} Scout(s) requesting non-Eagle Merit Badge with no MBC coverage"
            elif counselor_count == 0 and not is_eagle and scout_count == 0:
                gap_level = "LOW"
                gap_description = "Non-requested, non-Eagle Merit Badge with no MBC coverage"
            else:
                gap_level = "ADEQUATE"
                gap_description = f"Adequate coverage ({counselor_count} Merit Badge Counselors)"

            # Create priority record
            priority_record = {
                'badge_name': badge_name,
                'scout_demand': scout_count,
                'interested_scouts': demand_info.get('interested_scouts', []),
                'counselor_count': counselor_count,
                'counselors': counselors,
                'is_eagle_required': demand_info.get('is_eagle_required', False),
                'priority_score': round(priority_score, 2),
                'gap_level': gap_level,
                'gap_description': gap_description
            }

            badge_priorities.append(priority_record)

        # Sort by Eagle status first (Eagle badges supersede non-Eagle), then priority score
        badge_priorities.sort(key=lambda x: (
            not x['is_eagle_required'],  # Eagle badges first (False sorts before True)
            -x['priority_score'],         # Higher priority score first within same Eagle status
            x['badge_name']               # Alphabetical as tiebreaker
        ))

        print(f"🎯 Analyzed {len(badge_priorities)} badges with Scout demand")
        return badge_priorities


    def generate_coverage_analysis(self, priority_data: List[Dict]) -> Dict:
        """Generate summary analysis of coverage gaps"""

        # Categorize by gap level
        critical_gaps = [p for p in priority_data if p['gap_level'] == 'CRITICAL']
        high_gaps = [p for p in priority_data if p['gap_level'] == 'HIGH']
        medium_gaps = [p for p in priority_data if p['gap_level'] == 'MEDIUM']
        low_gaps = [p for p in priority_data if p['gap_level'] == 'LOW']
        adequate_gaps = [p for p in priority_data if p['gap_level'] == 'ADEQUATE']

        # Eagle vs Non-Eagle breakdown
        eagle_critical = [p for p in critical_gaps if p['is_eagle_required']]
        eagle_high = [p for p in high_gaps if p['is_eagle_required']]

        # Top recruitment targets - only include badges that need recruitment (exclude ADEQUATE)
        recruitment_candidates = [p for p in priority_data if p['gap_level'] != 'ADEQUATE']
        top_priorities = recruitment_candidates[:10]  # Top 10 by score

        # Calculate total Scout impact (critical, high, and medium priority gaps only)
        total_badge_requests_affected = sum(p['scout_demand'] for p in critical_gaps + high_gaps + medium_gaps)

        # Calculate unique Scouts affected by priority gaps
        unique_scouts_affected = set()
        for gap in critical_gaps + high_gaps + medium_gaps:
            unique_scouts_affected.update(gap['interested_scouts'])
        unique_scouts_count = len(unique_scouts_affected)

        analysis_summary = {
            'analysis_timestamp': datetime.now().isoformat(),
            'total_badges_analyzed': len(priority_data),
            'gap_summary': {
                'critical_gaps': len(critical_gaps),
                'high_priority_gaps': len(high_gaps),
                'medium_priority_gaps': len(medium_gaps),
                'low_priority_gaps': len(low_gaps),
                'adequate_coverage': len(adequate_gaps)
            },
            'eagle_badge_gaps': {
                'critical_eagle_gaps': len(eagle_critical),
                'high_priority_eagle_gaps': len(eagle_high)
            },
            'scout_impact': {
                'badge_requests_affected_by_critical_gaps': sum(p['scout_demand'] for p in critical_gaps),
                'badge_requests_affected_by_high_gaps': sum(p['scout_demand'] for p in high_gaps),
                'badge_requests_affected_by_medium_gaps': sum(p['scout_demand'] for p in medium_gaps),
                'total_badge_requests_affected': total_badge_requests_affected,
                'unique_scouts_affected': unique_scouts_count
            },
            'top_recruitment_priorities': [
                {
                    'badge_name': p['badge_name'],
                    'priority_score': p['priority_score'],
                    'scout_demand': p['scout_demand'],
                    'gap_level': p['gap_level'],
                    'is_eagle': p['is_eagle_required']
                }
                for p in top_priorities
            ],
            'critical_gaps_detail': [
                {
                    'badge_name': p['badge_name'],
                    'scout_demand': p['scout_demand'],
                    'interested_scouts': p['interested_scouts'],
                    'is_eagle': p['is_eagle_required']
                }
                for p in critical_gaps
            ]
        }

        return analysis_summary

    def save_priority_analysis(self, priority_data: List[Dict], analysis_summary: Dict) -> Path:
        """Save complete priority analysis to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.processed_dir / f"coverage_priority_analysis_{timestamp}.json"

        complete_analysis = {
            'priority_analysis': priority_data,
            'analysis_summary': analysis_summary
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(complete_analysis, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved priority analysis: {output_file}")
        return output_file

    def analyze_coverage_gaps(self, demand_file: Optional[Path] = None, mbc_file: Optional[Path] = None) -> Dict:
        """
        Main analysis function - complete gap analysis pipeline

        Args:
            demand_file: Scout demand data file (optional, auto-detects if None)
            mbc_file: MBC coverage data file (optional, auto-detects if None)

        Returns:
            Complete priority analysis data
        """
        print("🚀 Starting Coverage Gap Analysis...")

        # Auto-detect files if not specified
        if demand_file is None or mbc_file is None:
            auto_demand, auto_mbc = self.auto_detect_latest_files()
            demand_file = demand_file or auto_demand
            mbc_file = mbc_file or auto_mbc

        if not demand_file or not demand_file.exists():
            raise FileNotFoundError("Scout demand analysis file not found")
        if not mbc_file or not mbc_file.exists():
            raise FileNotFoundError("MBC coverage data file not found")

        # Load data
        print(f"📊 Loading demand data: {demand_file.name}")
        demand_data = self.load_demand_data(demand_file)

        print(f"🎯 Loading MBC data: {mbc_file.name}")
        mbc_data = self.load_mbc_data(mbc_file)

        # Extract coverage information
        coverage_data = self.extract_mbc_coverage(mbc_data)

        # Calculate priority scores
        priority_data = self.calculate_priority_scores(demand_data, coverage_data)

        # Generate analysis summary
        analysis_summary = self.generate_coverage_analysis(priority_data)

        # Save results
        self.save_priority_analysis(priority_data, analysis_summary)

        # Print key findings
        summary = analysis_summary
        print(f"\n🎯 Coverage Gap Analysis Results:")
        print(f"   ❌ {summary['gap_summary']['critical_gaps']} critical gaps (no coverage)")
        print(f"   ⚠️  {summary['gap_summary']['high_priority_gaps']} high-priority gaps (limited coverage)")
        print(f"   🦅 {summary['eagle_badge_gaps']['critical_eagle_gaps']} Eagle badge critical gaps")
        print(f"   👥 {summary['scout_impact']['unique_scouts_affected']} unique Scouts affected by gaps")

        return {
            'priority_analysis': priority_data,
            'analysis_summary': analysis_summary
        }


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Analyze merit badge coverage gaps using Scout demand data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python coverage_gap_analyzer.py                                    # Auto-detect latest files
  python coverage_gap_analyzer.py --demand-file demand.json         # Specific demand file
  python coverage_gap_analyzer.py --mbc-file roster_join.json       # Specific MBC file
        """
    )

    parser.add_argument(
        '--demand-file',
        help='Path to Scout demand analysis file',
        type=str
    )

    parser.add_argument(
        '--mbc-file',
        help='Path to MBC coverage data file',
        type=str
    )

    parser.add_argument(
        '--processed-dir',
        help='Directory containing processed files',
        default='data/processed',
        type=str
    )

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()

    try:
        # Initialize analyzer
        analyzer = CoverageGapAnalyzer(processed_dir=args.processed_dir)

        # Run analysis
        demand_path = Path(args.demand_file) if args.demand_file else None
        mbc_path = Path(args.mbc_file) if args.mbc_file else None

        results = analyzer.analyze_coverage_gaps(demand_path, mbc_path)

        # Show top priorities
        top_priorities = results['analysis_summary']['top_recruitment_priorities'][:5]
        print(f"\n🏆 Top 5 Recruitment Priorities:")
        for i, badge in enumerate(top_priorities, 1):
            eagle_indicator = "🦅" if badge['is_eagle'] else ""
            print(f"   {i}. {badge['badge_name']} {eagle_indicator}")
            print(f"      Score: {badge['priority_score']} | Demand: {badge['scout_demand']} Scouts | Gap: {badge['gap_level']}")

        return 0

    except KeyboardInterrupt:
        print("\n⚠️ Analysis cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Analysis failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())