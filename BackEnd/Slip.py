import fitz  # PyMuPDF
import re
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

THAI_MONTH_MAP = {
    "มกราคม": "01", "กุมภาพันธ์": "02", "มีนาคม": "03", "เมษายน": "04",
    "พฤษภาคม": "05", "มิถุนายน": "06", "กรกฎาคม": "07", "สิงหาคม": "08",
    "กันยายน": "09", "ตุลาคม": "10", "พฤศจิกายน": "11", "ธันวาคม": "12"
}

def extract_month_year_from_text(text):
    pattern = r"(" + "|".join(THAI_MONTH_MAP.keys()) + r")\s*(?:ปี\s*พ\.ศ\.)?\s*(\d{4})"
    match = re.search(pattern, text)
    if not match:
        raise ValueError("❌ ไม่พบเดือนหรือปีในเนื้อหา PDF")
    
    thai_month = match.group(1)
    year_be = int(match.group(2))
    month_number = THAI_MONTH_MAP[thai_month]
    
    return str(year_be), month_number

def extract_account_number_from_page(page):
    text = page.get_text()
    
    # Example patterns for account numbers (adjust based on your PDF format)
    # 1. Match digits with hyphens (e.g. 123-4-56789-0)
    match = re.search(r'\d{3}-\d-\d{5}-\d', text)
    if match:
        return match.group(0).replace("-", "")

    # 2. Match long digit strings (e.g. 10 digits or more)
    match = re.search(r'\b\d{9,12}\b', text)
    if match:
        return match.group(0)

    return None

def split_and_save_named_pdfs(input_path, output_base_dir):
    doc = fitz.open(input_path)
    month = None
    year = None

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        rect = page.rect
        mid_y = rect.y0 + rect.height / 2

        top_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, mid_y)
        bottom_rect = fitz.Rect(rect.x0, mid_y, rect.x1, rect.y1)

        for i, clip_rect in enumerate([top_rect, bottom_rect]):
            new_doc = fitz.open()
            new_page = new_doc.new_page(width=clip_rect.width, height=clip_rect.height)
            new_page.show_pdf_page(
                fitz.Rect(0, 0, clip_rect.width, clip_rect.height),
                doc,
                page.number,
                clip=clip_rect
            )

            # Extract full text to get month and year
            text = new_page.get_text()
            if month is None or year is None:
                try:
                    year, month = extract_month_year_from_text(text)
                except ValueError as e:
                    print(f"⚠️ Skipping page {page_num+1} part {i+1}: {e}")
                    continue

            # Extract account number
            account_number = extract_account_number_from_page(new_page)
            if not account_number:
                account_number = f"page{page_num+1}_part{i+1}"

            safe_name = re.sub(r'[\\/*?:"<>|]', "", account_number.replace(" ", "_"))

            # Construct final output path: output_base_dir / year / month
            target_folder = os.path.join(output_base_dir, year, month)
            os.makedirs(target_folder, exist_ok=True)

            save_path = os.path.join(target_folder, f"{safe_name}.pdf")
            new_doc.save(save_path)
            upload_to_drive(save_path, year, month, root_folder_id='1zcL_hN8n4QyoL2Uo9bd9nWyLZJuKhbow')
            new_doc.close()

            print(f"✅ Saved: {save_path}")



SERVICE_ACCOUNT_FILE = 'finance-project-463303-239395cb7ac6.json'
SCOPES = ['https://www.googleapis.com/auth/drive']
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=credentials)


def get_or_create_folder(name, parent_id=None):
    query = f"name = '{name}' and mimeType = 'application/vnd.google-apps.folder'"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    response = drive_service.files().list(q=query, spaces='drive').execute()
    files = response.get('files', [])
    if files:
        return files[0]['id']

    # Create folder
    metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        metadata['parents'] = [parent_id]
    folder = drive_service.files().create(body=metadata, fields='id').execute()
    return folder['id']


def upload_to_drive(filepath, year, month, root_folder_id=None):
    year_folder_id = get_or_create_folder(year, root_folder_id)
    month_folder_id = get_or_create_folder(month, year_folder_id)

    file_metadata = {
        'name': os.path.basename(filepath),
        'parents': [month_folder_id]
    }
    media = MediaFileUpload(filepath, mimetype='application/pdf')
    uploaded = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    print(f"✅ Uploaded {filepath} to Drive folder {year}/{month}")




# Example usage:
input_pdf = "สลีป พ.ค.68.pdf"
output_folder = "split_named_pdfs"
split_and_save_named_pdfs(input_pdf, output_folder)

