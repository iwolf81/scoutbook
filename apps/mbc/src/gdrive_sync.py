#!/usr/bin/env python3
"""
Google Drive Sync for Merit Badge Counselor Reports

Uploads the latest MBC report PDFs to Google Drive with standardized filenames
for consistent unit website linking.

Usage:
    python gdrive_sync.py

Requirements:
    - Google Drive API credentials (service account)
    - Latest MBC reports generated in data/reports/
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
from datetime import datetime

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.service_account import Credentials
except ImportError:
    print("❌ Google Drive API libraries not installed.")
    print("   Run: pip install google-api-python-client google-auth")
    sys.exit(1)


class GDriveSync:
    """Sync MBC report PDFs to Google Drive with standardized filenames"""

    # Google Drive folder ID from the URL
    GDRIVE_FOLDER_ID = "1bC3_71dlmp0CvoDFisRpb-Y3WoKHvpiD"

    # If modifying these scopes, delete the token file
    SCOPES = ['https://www.googleapis.com/auth/drive.file']

    def __init__(self, reports_dir: str = "data/reports"):
        """
        Initialize Google Drive sync

        Inputs:
        - reports_dir: Directory containing MBC report folders

        Outputs:
        - Configured GDriveSync instance
        """
        self.reports_dir = Path(reports_dir)
        self.service = None

        if not self.reports_dir.exists():
            raise FileNotFoundError(f"Reports directory not found: {self.reports_dir}")

    def authenticate(self) -> None:
        """
        Authenticate with Google Drive API using service account

        Inputs:
        - None (looks for credentials.json file)

        Outputs:
        - Sets self.service to authenticated Drive API service

        Raises:
        - Exception: If authentication fails
        """
        creds = None

        # Service account authentication
        service_account_file = 'credentials.json'
        if os.path.exists(service_account_file):
            try:
                creds = Credentials.from_service_account_file(
                    service_account_file, scopes=self.SCOPES)
                print(f"✅ Using service account authentication: {service_account_file}")
            except Exception as e:
                print(f"❌ Service account auth failed: {e}")
                raise Exception(f"Authentication failed: {e}")
        else:
            raise Exception("❌ credentials.json not found. Please download service account credentials from Google Cloud Console.")

        self.service = build('drive', 'v3', credentials=creds)
        print("✅ Google Drive API authenticated successfully")


    def find_latest_report_directory(self) -> Optional[Path]:
        """
        Find the most recent MBC report directory

        Inputs:
        - None (scans self.reports_dir)

        Outputs:
        - Path to latest report directory or None if not found
        """
        # Look for directories matching pattern: *_MBC_Reports_YYYYMMDD_HHMMSS
        pattern = re.compile(r'.*_MBC_Reports_(\d{8}_\d{6})$')

        latest_dir = None
        latest_timestamp = None

        for item in self.reports_dir.iterdir():
            if item.is_dir():
                match = pattern.match(item.name)
                if match:
                    timestamp_str = match.group(1)
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                        if latest_timestamp is None or timestamp > latest_timestamp:
                            latest_timestamp = timestamp
                            latest_dir = item
                    except ValueError:
                        continue

        if latest_dir:
            print(f"📁 Found latest report directory: {latest_dir.name}")
        else:
            print("❌ No MBC report directories found")

        return latest_dir

    def get_pdf_files(self, report_dir: Path) -> List[Tuple[Path, str]]:
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
            'Coverage_Report': 'T32_T7012_MBC_Coverage_Report.pdf'
        }

        for pdf_file in report_dir.glob('*.pdf'):
            # Determine the standardized name based on file content type
            standardized_name = None

            for pattern, std_name in file_mappings.items():
                if pattern in pdf_file.name:
                    standardized_name = std_name
                    break

            if standardized_name:
                pdf_files.append((pdf_file, standardized_name))
                print(f"📄 Found: {pdf_file.name} → {standardized_name}")
            else:
                print(f"⚠️ Unrecognized PDF file: {pdf_file.name}")

        return pdf_files

    def upload_file_to_gdrive(self, local_file: Path, gdrive_filename: str) -> bool:
        """
        Upload a file to Google Drive folder

        Inputs:
        - local_file: Path to local file to upload
        - gdrive_filename: Filename to use in Google Drive

        Outputs:
        - True if upload successful, False otherwise

        Raises:
        - Exception: If upload fails
        """
        try:
            # Check if file already exists in the folder
            existing_file_id = self._find_file_in_folder(gdrive_filename)

            # Prepare file metadata
            file_metadata = {
                'name': gdrive_filename,
                'parents': [self.GDRIVE_FOLDER_ID]
            }

            # Upload the file
            media = MediaFileUpload(str(local_file), resumable=True)

            if existing_file_id:
                # Update existing file
                print(f"🔄 Updating existing file: {gdrive_filename}")
                file = self.service.files().update(
                    fileId=existing_file_id,
                    media_body=media
                ).execute()
            else:
                # Create new file
                print(f"📤 Uploading new file: {gdrive_filename}")
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()

            print(f"✅ Successfully uploaded: {gdrive_filename} (ID: {file.get('id')})")
            return True

        except Exception as e:
            print(f"❌ Failed to upload {gdrive_filename}: {str(e)}")
            return False

    def _find_file_in_folder(self, filename: str) -> Optional[str]:
        """
        Find a file by name in the Google Drive folder

        Inputs:
        - filename: Name of file to search for

        Outputs:
        - File ID if found, None otherwise
        """
        try:
            query = f"name='{filename}' and parents in '{self.GDRIVE_FOLDER_ID}' and trashed=false"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])

            if files:
                return files[0]['id']
            return None

        except Exception as e:
            print(f"⚠️ Error searching for file {filename}: {str(e)}")
            return None

    def sync_reports(self) -> bool:
        """
        Main sync function - upload latest reports to Google Drive

        Inputs:
        - None

        Outputs:
        - True if all uploads successful, False otherwise
        """
        print("🚀 Starting Google Drive sync...")

        # Authenticate
        try:
            self.authenticate()
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False

        # Find latest report directory
        latest_dir = self.find_latest_report_directory()
        if not latest_dir:
            return False

        # Get PDF files to upload
        pdf_files = self.get_pdf_files(latest_dir)
        if not pdf_files:
            print("❌ No PDF files found to upload")
            return False

        # Upload each file
        success_count = 0
        for local_file, gdrive_name in pdf_files:
            if self.upload_file_to_gdrive(local_file, gdrive_name):
                success_count += 1

        # Report results
        total_files = len(pdf_files)
        if success_count == total_files:
            print(f"🎉 Successfully uploaded all {total_files} files to Google Drive!")
            print(f"📁 Google Drive folder: https://drive.google.com/drive/folders/{self.GDRIVE_FOLDER_ID}")
            return True
        else:
            print(f"⚠️ Uploaded {success_count}/{total_files} files")
            return False


def main():
    """Main entry point for the script"""
    print("📋 Merit Badge Counselor Report - Google Drive Sync")
    print("=" * 50)

    try:
        # Initialize and run sync
        sync = GDriveSync()
        success = sync.sync_reports()

        if success:
            print("\n✅ Google Drive sync completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Google Drive sync completed with errors")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ Sync cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Sync failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()