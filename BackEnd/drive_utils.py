from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service_account.json'

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

def get_or_create_folder(name, parent_id=None):
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = drive_service.files().list(q=query, spaces='drive').execute()
    items = results.get('files', [])
    if items:
        return items[0]['id']

    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id] if parent_id else []
    }
    folder = drive_service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def upload_pdf(filepath, year, month, root_folder_id=None):
    year_folder_id = get_or_create_folder(year, root_folder_id)
    month_folder_id = get_or_create_folder(month, year_folder_id)

    file_metadata = {
        'name': os.path.basename(filepath),
        'parents': [month_folder_id]
    }
    media = MediaFileUpload(filepath, mimetype='application/pdf')
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    return file.get('id')
