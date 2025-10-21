import requests
import os

class LINEMessagingService:
    """Service for sending LINE messages via Messaging API"""
    
    # Short month names in Thai
    THAI_MONTHS_SHORT = {
        "01": "ม.ค.", "02": "ก.พ.", "03": "มี.ค.",
        "04": "เม.ย.", "05": "พ.ค.", "06": "มิ.ย.",
        "07": "ก.ค.", "08": "ส.ค.", "09": "ก.ย.",
        "10": "ต.ค.", "11": "พ.ย.", "12": "ธ.ค."
    }
    
    def __init__(self):
        self.channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        self.api_base = "https://api.line.me/v2/bot"
        self.liff_url = os.getenv("LIFF_URL", "https://financepj.netlify.app")
        
        if not self.channel_access_token:
            print("⚠️ Warning: LINE_CHANNEL_ACCESS_TOKEN not set")
    
    def send_broadcast(self, messages):
        """
        Send broadcast message to all users
        
        Args:
            messages: List of message objects (max 5 messages)
            
        Returns:
            dict: Response from LINE API
        """
        if not self.channel_access_token:
            return {"success": False, "error": "LINE_CHANNEL_ACCESS_TOKEN not configured"}
        
        url = f"{self.api_base}/message/broadcast"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.channel_access_token}"
        }
        
        payload = {
            "messages": messages
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Broadcast sent successfully",
                    "response": response.json() if response.text else {}
                }
            else:
                return {
                    "success": False,
                    "error": f"LINE API error: {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to send broadcast: {str(e)}"
            }
    
    def create_simple_slip_notification(self, month, year):
        """
        Create a simple notification message
        Example: "ตรวจสอบสลิปเงินเดือน ต.ค. 68 ได้ที่ https://..."
        
        Args:
            month: Month number (01-12)
            year: Buddhist year (e.g., "2568")
            
        Returns:
            list: List of LINE message objects
        """
        # Get short month name (e.g., "ต.ค.")
        month_short = self.THAI_MONTHS_SHORT.get(month, month)
        
        # Get last 2 digits of year (e.g., "2568" -> "68")
        year_short = str(year)[-2:]
        
        # Create simple message
        text_message = f"ตรวจสอบสลิปเงินเดือน {month_short} {year_short} ได้ที่ {self.liff_url}"
        
        messages = [
            {
                "type": "text",
                "text": text_message
            }
        ]
        
        return messages