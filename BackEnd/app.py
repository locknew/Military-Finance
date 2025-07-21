from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
from datetime import datetime

from pdf_splitter import split_and_upload
from drive_utils import get_or_create_folder

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
            creds = flow.run_local_server(port=8080)

        # Save token
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

# Initialize drive client once
drive_service = get_drive_service()

@app.route('/api/upload-slip', methods=['POST'])
def upload_slip():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400

        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'กรุณาอัปโหลดไฟล์ PDF เท่านั้น'}), 400

        # Create uploads directory if it doesn't exist
        uploads_dir = "uploads"
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Save file temporarily
        temp_path = os.path.join(uploads_dir, file.filename)
        file.save(temp_path)

        try:
            # Process the PDF and upload to Google Drive
            result, year, month = split_and_upload(temp_path, drive_service, ROOT_FOLDER_ID)
            
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # Generate URL if result contains file info
            url = ''
            if result and isinstance(result, dict) and 'file_id' in result:
                url = f"https://drive.google.com/file/d/{result['file_id']}/view"
            elif result and isinstance(result, list) and len(result) > 0:
                # If result is a list of files, use the first one
                if isinstance(result[0], dict) and 'file_id' in result[0]:
                    url = f"https://drive.google.com/file/d/{result[0]['file_id']}/view"
            
            return jsonify({
                'success': True,
                'message': 'Upload success',
                'url': url,
                'files': result,
                'year': year,
                'month': month
            })
            
        except Exception as e:
            # Clean up temporary file on error
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

@app.route('/api/get-slip', methods=['POST'])
def get_slip():
    try:
        data = request.get_json()
        account = data.get('account')
        year = data.get('year')
        month = data.get('month')
        
        if not account or not year or not month:
            return jsonify({'success': False, 'error': 'กรุณาระบุข้อมูลให้ครบถ้วน'}), 400
            
        filename = f"{account}.pdf"

        # Get or create folder structure
        year_folder_id = get_or_create_folder(drive_service, year, parent_id=ROOT_FOLDER_ID)
        month_folder_id = get_or_create_folder(drive_service, month, parent_id=year_folder_id)

        # Search for the file
        query = (
            f"name = '{filename}' and "
            f"'{month_folder_id}' in parents and "
            f"mimeType = 'application/pdf'"
        )
        results = drive_service.files().list(q=query, fields="files(id)").execute()
        items = results.get('files', [])

        if not items:
            return jsonify({'success': False, 'error': '❌ ไม่พบสลิป'}), 404

        file_id = items[0]['id']
        preview_url = f"https://drive.google.com/file/d/{file_id}/preview"

        return jsonify({'success': True, 'url': preview_url})

    except Exception as e:
        return jsonify({'success': False, 'error': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

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

        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/list', methods=['GET'])
def list_files():
    try:
        # Get files from Google Drive (recent uploads)
        files = []
        
        # Search for PDF files in the root folder and subfolders
        query = f"mimeType = 'application/pdf' and '{ROOT_FOLDER_ID}' in parents"
        results = drive_service.files().list(
            q=query,
            fields="files(id, name, size, createdTime, modifiedTime)",
            orderBy="modifiedTime desc"
        ).execute()
        
        drive_files = results.get('files', [])
        
        for file in drive_files:
            files.append({
                'id': file['id'],
                'name': file['name'],
                'size': int(file.get('size', 0)),
                'uploadedAt': file.get('createdTime', file.get('modifiedTime', '')),
                'url': f"https://drive.google.com/file/d/{file['id']}/view"
            })
        
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/delete', methods=['DELETE'])
def delete_file():
    try:
        filename = request.args.get('filename')
        file_id = request.args.get('file_id')
        
        if not filename and not file_id:
            return jsonify({'success': False, 'error': 'Filename or file_id is required'}), 400
        
        # If we have file_id, use it directly
        if file_id:
            drive_service.files().delete(fileId=file_id).execute()
            return jsonify({'success': True, 'message': 'File deleted successfully'})
        
        # Otherwise, search for the file by name
        if filename:
            # Search for the file in Google Drive
            query = f"name = '{filename}' and mimeType = 'application/pdf'"
            results = drive_service.files().list(q=query, fields="files(id)").execute()
            items = results.get('files', [])
            
            if not items:
                return jsonify({'success': False, 'error': 'File not found'}), 404
            
            # Delete the file
            file_id = items[0]['id']
            drive_service.files().delete(fileId=file_id).execute()
            
            return jsonify({'success': True, 'message': 'File deleted successfully'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'API is running'})

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

# Run app
port = int(os.environ.get('PORT', 8000))
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=False)