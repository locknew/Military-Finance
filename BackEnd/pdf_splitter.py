import fitz
import os
import re
from drive_utils import upload_pdf

RANKS = [
    "พันโท", "พันเอก", "พันตรี", "ร้อยตรี", "ร้อยโท", "ร้อยเอก",
    "จ่าสิบตรี", "จ่าสิบโท", "จ่าสิบเอก", "สิบเอก", "สิบโท", "สิบตรี"
]
THAI_MONTH_MAP = {
    "มกราคม": "01", "กุมภาพันธ์": "02", "มีนาคม": "03", "เมษายน": "04",
    "พฤษภาคม": "05", "มิถุนายน": "06", "กรกฎาคม": "07", "สิงหาคม": "08",
    "กันยายน": "09", "ตุลาคม": "10", "พฤศจิกายน": "11", "ธันวาคม": "12"
}
RANK_PATTERN = '|'.join(RANKS)

def extract_month_year_from_text(text):
    pattern = r"(" + "|".join(THAI_MONTH_MAP.keys()) + r")\s*(\d{4})"
    match = re.search(pattern, text)
    if match:
        month_th = match.group(1)
        year_be = match.group(2)
        return year_be, THAI_MONTH_MAP[month_th]
    raise ValueError("ไม่พบเดือนหรือปีในไฟล์ PDF")

def extract_account(page):
    text = page.get_text()
    match = re.search(r"\d{10,}", text)
    return match.group(0) if match else None

def split_and_upload(pdf_path):
    doc = fitz.open(pdf_path)
    text_sample = "".join([doc[i].get_text() for i in range(min(3, len(doc)))])
    year, month = extract_month_year_from_text(text_sample)

    tmp_dir = "tmp_slips"
    os.makedirs(tmp_dir, exist_ok=True)

    uploaded_files = {}

    for i, page in enumerate(doc):
        rect = page.rect
        mid_y = rect.y0 + rect.height / 2
        halves = [
            fitz.Rect(rect.x0, rect.y0, rect.x1, mid_y),
            fitz.Rect(rect.x0, mid_y, rect.x1, rect.y1)
        ]

        for j, clip in enumerate(halves):
            new_doc = fitz.open()
            new_page = new_doc.new_page(width=clip.width, height=clip.height)
            new_page.show_pdf_page(fitz.Rect(0, 0, clip.width, clip.height), doc, i, clip=clip)

            acc = extract_account(new_page)
            if not acc:
                continue

            file_path = os.path.join(tmp_dir, f"{acc}.pdf")
            new_doc.save(file_path)
            new_doc.close()

            file_id = upload_pdf(file_path, year, month)
            uploaded_files[acc] = file_id

    return uploaded_files, year, month
