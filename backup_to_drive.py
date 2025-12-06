# backup_to_drive.py
# Weekly backup of qr_scans.csv from Render to Google Drive (only if changed)

import os
import io
import csv
import datetime
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import json

# Constants
QR_CSV_URL = "https://qr-tracker-kx3q.onrender.com/logs/qr_scans.csv"

def get_drive_service():
    # Service account JSON is passed via env var GDRIVE_SERVICE_ACCOUNT_JSON
    sa_info_str = os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON")
    if not sa_info_str:
        raise RuntimeError("GDRIVE_SERVICE_ACCOUNT_JSON not set")

    sa_info = json.loads(sa_info_str)
    creds = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    service = build("drive", "v3", credentials=creds)
    return service

def download_current_csv():
    resp = requests.get(QR_CSV_URL, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError("Failed to download CSV, status code " + str(resp.status_code))
    return resp.content

def list_existing_backups(service, folder_id):
    # List files in the backup folder whose name starts with qr_scans_
    query = "mimeType='text/csv' and '" + folder_id + "' in parents and name contains 'qr_scans_'"
    results = service.files().list(
        q=query,
        orderBy="createdTime desc",
        pageSize=10,
        fields="files(id, name, createdTime)"
    ).execute()
    files = results.get("files", [])
    return files

def download_drive_file_content(service, file_id):
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    buf.seek(0)
    return buf.read()

def csv_contents_equal(a_bytes, b_bytes):
    # Simple byte-for-byte comparison is enough here
    return a_bytes == b_bytes

def generate_weekly_filename():
    today = datetime.date.today()
    iso_year, iso_week, _ = today.isocalendar()
    return "qr_scans_" + str(iso_year) + "-W" + str(iso_week).zfill(2) + ".csv"

def upload_new_backup(service, folder_id, filename, content_bytes):
    media = MediaIoBaseUpload(
        io.BytesIO(content_bytes),
        mimetype="text/csv",
        resumable=False
    )
    file_metadata = {
        "name": filename,
        "parents": [folder_id]
    }
    created = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name"
    ).execute()
    return created

def main():
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")
    if not folder_id:
        raise RuntimeError("GDRIVE_FOLDER_ID not set")

    # 1. Download current CSV from Render
    current_csv = download_current_csv()

    # 2. Connect to Drive
    service = get_drive_service()

    # 3. Find latest backup in the folder
    backups = list_existing_backups(service, folder_id)
    if backups:
        latest = backups[0]
        latest_content = download_drive_file_content(service, latest["id"])
        # 4. Compare; if identical, skip
        if csv_contents_equal(current_csv, latest_content):
            print("No change since latest backup; skipping upload.")
            return
        else:
            print("CSV has changed; creating new weekly backup.")
    else:
        print("No existing backups found; creating first backup.")

    # 5. Generate filename with year-week
    filename = generate_weekly_filename()

    # 6. Upload new backup
    created = upload_new_backup(service, folder_id, filename, current_csv)
    print("Uploaded new backup:", created.get("name"), "with id:", created.get("id"))

if __name__ == "__main__":
    main()
