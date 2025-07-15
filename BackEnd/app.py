from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import base64
import json
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

from pdf_splitter import split_and_upload
from drive_utils import get_or_create_folder

# Setup Flask app
app = Flask(__name__)
CORS(app)
load_dotenv()
# Google Drive root folder ID
ROOT_FOLDER_ID = '1uJ9aRF5VQewAZQDqZ_nt1SOoOFHNTgpl'

def get_drive_service():
    creds = None

    # Load token if exists
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json',
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            creds = flow.run_local_server(port=8080)  # <-- must be inside else

        # Save token
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)
# Initialize drive client once
drive_service = get_drive_service()

@app.route('/api/upload-slip', methods=['POST'])
def upload_slip():
    if 'file' not in request.files:
        return jsonify({'message': 'No file uploaded'}), 400

    file = request.files['file']
    temp_path = os.path.join("uploads", file.filename)
    os.makedirs("uploads", exist_ok=True)
    file.save(temp_path)

    try:
        result, year, month = split_and_upload(temp_path, drive_service, ROOT_FOLDER_ID)
        return jsonify({
            'message': 'Upload success',
            'files': result,
            'year': year,
            'month': month
        })
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/get-slip', methods=['POST'])
def get_slip():
    data = request.get_json()
    account = data.get('account')
    year = data.get('year')
    month = data.get('month')
    filename = f"{account}.pdf"

    try:
        year_folder_id = get_or_create_folder(drive_service, year, parent_id=ROOT_FOLDER_ID)
        month_folder_id = get_or_create_folder(drive_service, month, parent_id=year_folder_id)

        query = (
            f"name = '{filename}' and "
            f"'{month_folder_id}' in parents and "
            f"mimeType = 'application/pdf'"
        )
        results = drive_service.files().list(q=query, fields="files(id)").execute()
        items = results.get('files', [])

        if not items:
            return jsonify({'message': '❌ ไม่พบสลิป'}), 404

        file_id = items[0]['id']
        preview_url = f"https://drive.google.com/file/d/{file_id}/preview"

        return jsonify({'url': preview_url})

    except Exception as e:
        return jsonify({'message': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

@app.route('/api/available-months', methods=['GET'])
def get_available_months():
    try:
        query = f"mimeType = 'application/vnd.google-apps.folder' and '{ROOT_FOLDER_ID}' in parents"
        year_folders = drive_service.files().list(q=query, fields="files(id, name)").execute().get('files', [])

        data = {}

        for year in year_folders:
            year_name = year['name']
            year_id = year['id']

            # List months inside this year folder
            month_query = f"mimeType = 'application/vnd.google-apps.folder' and '{year_id}' in parents"
            month_folders = drive_service.files().list(q=month_query, fields="files(name)").execute().get('files', [])
            months = [m['name'] for m in month_folders]

            data[year_name] = sorted(months)

        return jsonify(data)
    except Exception as e:
        return jsonify({'message': str(e)}), 500

# Run app (Render will auto use host='0.0.0.0' and the correct PORT)
port = int(os.environ.get('PORT', 8000))
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
drive_service = get_drive_service()