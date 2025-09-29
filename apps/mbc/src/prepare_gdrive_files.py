#!/usr/bin/env python3
"""
Prepare MBC Report Files for Manual Google Drive Upload

Creates copies of the latest PDF reports with standardized filenames
in a "ready-to-upload" directory for easy drag-and-drop to Google Drive.

Usage:
    python src/prepare_gdrive_files.py

Output:
    data/gdrive/ - Directory with standardized filenames
"""

import shutil
import re
from datetime import datetime
from pathlib import Path


class GDriveFilePrep:
    """Prepare MBC reports for manual Google Drive upload"""

    def __init__(self, reports_dir: str = "data/reports"):
        """
        Initialize file preparation

        Inputs:
        - reports_dir: Directory containing MBC report folders

        Outputs:
        - Configured GDriveFilePrep instance
        """
        self.reports_dir = Path(reports_dir)
        self.output_dir = Path("data/gdrive")

        if not self.reports_dir.exists():
            raise FileNotFoundError(f"Reports directory not found: {self.reports_dir}")

    def find_latest_report_directory(self) -> Path:
        """
        Find the most recent MBC report directory

        Inputs:
        - None (scans self.reports_dir)

        Outputs:
        - Path to latest report directory

        Raises:
        - FileNotFoundError: If no report directories found
        """
        # Look for directories matching pattern: *_MBC_Reports_YYYYMMDD_HHMMSS
        pattern = re.compile(r'.*_MBC_Reports_(\d{8}_\d{6})$')

        latest_dir = None
        latest_timestamp = None

        print("🔍 Scanning for report directories...")
        for item in self.reports_dir.iterdir():
            if item.is_dir():
                match = pattern.match(item.name)
                if match:
                    timestamp_str = match.group(1)
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                        print(f"  Found: {item.name} ({timestamp})")
                        if latest_timestamp is None or timestamp > latest_timestamp:
                            latest_timestamp = timestamp
                            latest_dir = item
                    except ValueError:
                        continue

        if not latest_dir:
            raise FileNotFoundError("❌ No MBC report directories found")

        print(f"📁 Latest report directory: {latest_dir.name}")
        return latest_dir

    def get_pdf_files_with_mapping(self, report_dir: Path) -> list:
        """
        Get PDF files from report directory with their standardized names

        Inputs:
        - report_dir: Path to MBC report directory

        Outputs:
        - List of tuples: (source_file_path, standardized_filename)
        """
        pdf_files = []

        # Expected PDF files and their standardized names
        file_mappings = {
            'Troop_Counselors': 'T32_T7012_MBC_Troop_Counselors.pdf',
            'Non_Counselors': 'T32_T7012_MBC_Non_Counselors.pdf',
            'Coverage_Report': 'T32_T7012_MBC_Coverage_Report.pdf',
            'Priority_Report': 'T32_T7012_MBC_Priority_Report.pdf'
        }

        print("📄 Scanning for PDF files...")
        for pdf_file in report_dir.glob('*.pdf'):
            # Determine the standardized name based on file content type
            standardized_name = None

            for pattern, std_name in file_mappings.items():
                if pattern in pdf_file.name:
                    standardized_name = std_name
                    break

            if standardized_name:
                pdf_files.append((pdf_file, standardized_name))
                print(f"  ✓ {pdf_file.name} → {standardized_name}")
            else:
                print(f"  ⚠️ Unrecognized PDF file: {pdf_file.name}")

        return pdf_files

    def prepare_files(self) -> bool:
        """
        Main preparation function - copy files with standardized names

        Inputs:
        - None

        Outputs:
        - True if successful, False otherwise
        """
        print("📋 MBC Reports - Google Drive File Preparation")
        print("=" * 50)

        try:
            # Find latest report directory
            latest_dir = self.find_latest_report_directory()

            # Get PDF files to copy
            pdf_files = self.get_pdf_files_with_mapping(latest_dir)
            if not pdf_files:
                print("❌ No PDF files found to prepare")
                return False

            # Create output directory
            print(f"\n📁 Creating output directory: {self.output_dir}")
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Clear any existing files
            for existing_file in self.output_dir.glob('*'):
                if existing_file.is_file():
                    existing_file.unlink()
                    print(f"  🗑️ Removed old file: {existing_file.name}")

            # Copy files with standardized names
            print(f"\n📋 Copying {len(pdf_files)} files...")
            success_count = 0

            for source_file, standardized_name in pdf_files:
                try:
                    dest_file = self.output_dir / standardized_name
                    shutil.copy2(source_file, dest_file)

                    # Get file size for confirmation
                    size_mb = dest_file.stat().st_size / (1024 * 1024)
                    print(f"  ✅ {source_file.name} → {standardized_name} ({size_mb:.1f} MB)")
                    success_count += 1

                except Exception as e:
                    print(f"  ❌ Failed to copy {source_file.name}: {e}")

            # Report results
            print(f"\n🎉 Preparation complete!")
            print(f"📊 Successfully prepared {success_count}/{len(pdf_files)} files")
            print(f"📁 Files ready for upload at: {self.output_dir.absolute()}")

            print(f"\n📋 Manual Upload Instructions:")
            print(f"1. Open the folder: {self.output_dir.absolute()}")
            print(f"2. Select all 4 PDF files")
            print(f"3. Drag and drop to Google Drive folder:")
            print(f"   https://drive.google.com/drive/folders/1bC3_71dlmp0CvoDFisRpb-Y3WoKHvpiD")
            print(f"4. Files will have consistent names for unit website links")

            return success_count == len(pdf_files)

        except Exception as e:
            print(f"❌ Preparation failed: {e}")
            return False


def main():
    """Main entry point for the script"""
    try:
        prep = GDriveFilePrep()
        success = prep.prepare_files()

        if success:
            print("\n✅ File preparation completed successfully!")
            exit(0)
        else:
            print("\n❌ File preparation completed with errors")
            exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ Preparation cancelled by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Preparation failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()