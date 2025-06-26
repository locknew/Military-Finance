from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os

from googleapiclient.http import MediaFileUpload
import os

def get_or_create_folder(service, name, parent_id=None):
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    if items:
        return items[0]['id']

    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id] if parent_id else []
    }
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def upload_pdf(service, filepath, year, month, root_folder_id=None):
    year_folder_id = get_or_create_folder(service, year, root_folder_id)
    month_folder_id = get_or_create_folder(service, month, year_folder_id)

    file_metadata = {
        'name': os.path.basename(filepath),
        'parents': [month_folder_id]
    }
    media = MediaFileUpload(filepath, mimetype='application/pdf')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    return file.get('id')
