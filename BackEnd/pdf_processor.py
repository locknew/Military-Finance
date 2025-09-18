import fitz  # PyMuPDF
import re
import io
from typing import List, Dict, Any,Optional

class PDFProcessor:
    """Process Thai military payslips PDF files"""
    
    THAI_MONTH_MAP = {
        "มกราคม": "01", "กุมภาพันธ์": "02", "มีนาคม": "03", "เมษายน": "04",
        "พฤษภาคม": "05", "มิถุนายน": "06", "กรกฎาคม": "07", "สิงหาคม": "08",
        "กันยายน": "09", "ตุลาคม": "10", "พฤศจิกายน": "11", "ธันวาคม": "12"
    }
    
    RANKS = [
        "พ.ต.", "พ.ท.", "พ.อ.", "พ.ต.ต.", "พ.ต.ท.", "พ.ต.อ.",
        "ร.ต.", "ร.ท.", "ร.อ.", "จ.ส.ต.", "จ.ส.ท.", "จ.ส.อ.",
        "ส.ต.", "ส.ท.", "ส.อ.", "พลฯ", "ส.ต.ต.", "ส.ต.ท.", "ส.ต.อ.",
        "พันตรี", "พันโท", "พันเอก", "ร้อยตรี", "ร้อยโท", "ร้อยเอก",
        "จ่าสิบตรี", "จ่าสิบโท", "จ่าสิบเอก", "สิบตรี", "สิบโท", "สิบเอก"
    ]
    
    def __init__(self):
        self.rank_pattern = '|'.join(re.escape(rank) for rank in self.RANKS)
    
    def process_pdf(self, pdf_content: bytes) -> List[Dict[str, Any]]:
        """
        Process a PDF file containing multiple payslips
        Returns a list of dictionaries, each containing slip data
        """
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        # First, extract month and year from the document
        year, month = self.extract_month_year_from_document(doc)
        
        slips = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Split page into two halves (top and bottom)
            page_slips = self.split_page_to_slips(doc, page, page_num, year, month)
            slips.extend(page_slips)
        
        doc.close()
        return slips
    
    def extract_month_year_from_document(self, doc) -> tuple:
        """Extract month and year from the first few pages of the document"""
        text_sample = ""
        for i in range(min(3, len(doc))):
            text_sample += doc[i].get_text()
        
        # Look for month and year pattern
        pattern = r"(" + "|".join(self.THAI_MONTH_MAP.keys()) + r")\s*(?:ปี\s*พ\.ศ\.)?\s*(\d{4})"
        match = re.search(pattern, text_sample)
        
        if match:
            thai_month = match.group(1)
            year_be = match.group(2)
            month_number = self.THAI_MONTH_MAP[thai_month]
            return year_be, month_number
        
        raise ValueError("ไม่พบข้อมูลเดือนและปีในเอกสาร")
    
    def split_page_to_slips(self, doc, page, page_num: int, year: str, month: str) -> List[Dict[str, Any]]:
        """Split a single page into individual payslips"""
        rect = page.rect
        mid_y = rect.y0 + rect.height / 2
        
        slips = []
        
        # Process top and bottom halves
        halves = [
            fitz.Rect(rect.x0, rect.y0, rect.x1, mid_y),  # Top half
            fitz.Rect(rect.x0, mid_y, rect.x1, rect.y1)    # Bottom half
        ]
        
        for i, clip_rect in enumerate(halves):
            # Create new document for this slip
            new_doc = fitz.open()
            new_page = new_doc.new_page(width=clip_rect.width, height=clip_rect.height)
            new_page.show_pdf_page(
                fitz.Rect(0, 0, clip_rect.width, clip_rect.height),
                doc,
                page.number,
                clip=clip_rect
            )
            
            # Extract text from the slip
            text = new_page.get_text()
            
            # Extract account number and other data
            account_number = self.extract_account_number(text)
            if not account_number:
                new_doc.close()
                continue  # Skip if no account number found
            
            # Extract additional information
            rank = self.extract_rank(text)
            name = self.extract_name(text)
            
            # Save PDF as bytes
            pdf_bytes = new_doc.write()
            new_doc.close()
            
            # Create slip data
            slip_data = {
                'accountNumber': account_number,
                'year': year,
                'month': month,
                'rank': rank,
                'name': name,
                'pdfData': pdf_bytes,
                'fileName': f"{account_number}_{year}_{month}.pdf"
            }
            
            slips.append(slip_data)
        
        return slips
    
    def extract_account_number(self, text: str) -> str:
        """Extract account number from text"""
        # Look for 10-13 digit numbers
        patterns = [
            r'\b\d{10}\b',           # 10 digits
            r'\b\d{3}-\d-\d{5}-\d\b', # Format: xxx-x-xxxxx-x
            r'\b\d{12,13}\b'          # 12-13 digits
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                # Remove hyphens if present
                return match.group(0).replace('-', '')
        
        return None
    
    def extract_rank(self, text: str) -> str:
        """Extract military rank from text"""
        match = re.search(self.rank_pattern, text)
        return match.group(0) if match else ""
    
    def extract_name(self, text: str) -> Optional[str]:
        """
        Extract name from text. Priority:
        1. Find the first occurrence of a rank from self.rank_pattern and extract the Thai name immediately after it.
        2. If strict pattern fails, iterate occurrences of ranks and heuristically extract the nearest Thai sequence.
        3. Fall back to other common patterns (e.g., after 'ชื่อ', typical name+surname forms).
        Returns the name (string) or None if nothing found.
        """
        if not text:
            return None

        # Normalize whitespace (helps matching across newlines)
        norm = re.sub(r'\s+', ' ', text)

        stop_keywords = r"(?:เลข|กอง|กรม|ตำแหน่ง|เงินเดือน|บัญชี|ยศ|ชื่อ|หมายเลข|\d|พ\.ต\.|พ\.ท\.|พ\.อ\.|ร\.ต\.|ร\.ท\.|ร\.อ\.)"

        # 1) Strict: rank followed by Thai name and then a stop keyword
        if getattr(self, "rank_pattern", None):
            # Use non-capturing wrapper for the rank pattern in case it contains groups
            rank_group = rf"(?:{self.rank_pattern})"
            strict_pat = re.compile(rf"{rank_group}\s+([ก-๙]+(?:\s+[ก-๙]+)*?)(?=\s+{stop_keywords})", flags=re.UNICODE)
            m = strict_pat.search(norm)
            if m:
                name = m.group(1).strip()
                name = " ".join(name.split())
                if len(name) >= 2 and re.match(r'^[ก-๙\s]+$', name):
                    return name

            # 2) Heuristic: iterate through each rank occurrence and try to take the first Thai sequence after it
            rank_iter = re.finditer(rank_group, norm)
            for r in rank_iter:
                tail = norm[r.end(): r.end() + 200]  # look a bit ahead
                # cut at the first stop keyword if present
                stop_m = re.search(stop_keywords, tail)
                candidate_raw = tail[: stop_m.start()] if stop_m else tail.split('\n')[0]
                # take the first Thai-letter chunk from candidate_raw
                name_m = re.search(r"([ก-๙]+(?:\s+[ก-๙]+)*)", candidate_raw)
                if name_m:
                    name = name_m.group(1).strip()
                    name = " ".join(name.split())
                    if len(name) >= 2 and re.match(r'^[ก-๙\s]+$', name):
                        return name

        # 3) Fallback patterns (keeps original patterns but checked only after rank-driven attempts)
        patterns = [
            # After 'ชื่อ'
            r"ชื่อ[:\-\s]*([ก-๙]+(?:\s+[ก-๙]+)*?)(?:\s+(?:เลข|กอง|กรม|ตำแหน่ง|ยศ|\d))",
            # Between rank and account number (if rank_pattern exists, include it)
            (f"({self.rank_pattern})\\s+([ก-๙]+\\s+[ก-๙]+)\\s+\\d{{10}}") if getattr(self, "rank_pattern", None) else None,
            # Typical name + surname
            r"([ก-๙]{2,}\s+[ก-๙]{2,})(?:\s+(?:เลข|บัญชี|\d))"
        ]

        for pat in (p for p in patterns if p):
            m = re.search(pat, norm)
            if m:
                # choose appropriate group (if pattern contains rank)
                if getattr(self, "rank_pattern", None) and self.rank_pattern in pat:
                    name = m.group(2).strip() if len(m.groups()) >= 2 else m.group(1).strip()
                else:
                    name = m.group(1).strip()
                name = " ".join(name.split())
                if len(name) >= 2 and re.match(r'^[ก-๙\s]+$', name):
                    return name

        return None
        

    
    def extract_single_slip(self, pdf_content: bytes, account_number: str, 
                           year: str, month: str) -> Dict[str, Any]:
        """
        Process a single slip PDF (for manual uploads)
        """
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        # Extract all text
        text = ""
        for page in doc:
            text += page.get_text()
        
        # If account number not provided, try to extract it
        if not account_number:
            account_number = self.extract_account_number(text)
        
        
        return {
            'accountNumber': account_number or 'unknown',
            'year': year,
            'month': month,
            'rank': rank,
            'name': name,
            'pdfData': pdf_content,
            'fileName': f"{account_number}_{year}_{month}.pdf"
        }