import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class SheetsHandler:
    def __init__(self):
        # Set up Google Sheets authentication
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Load credentials from service account file
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE'), 
            scope
        )
        
        self.client = gspread.authorize(creds)
        self.sheet_id = os.getenv('GOOGLE_SHEETS_ID')
        self.worksheet = self.client.open_by_key(self.sheet_id).sheet1
    
    def get_all_data(self):
        """Get all data from Google Sheets as DataFrame"""
        try:
            # Get all records as list of dictionaries
            records = self.worksheet.get_all_records()
            df = pd.DataFrame(records)
            return df
        except Exception as e:
            print(f"Error reading Google Sheets: {e}")
            return None
    
    def get_pending_notifications(self):
        """Get rows that need notifications (where Notification_Sent is empty or 'No')"""
        df = self.get_all_data()
        if df is None or df.empty:
            return []
        
        # Filter rows that need notifications
        pending = df[
            (df['Notification_Sent'].isin(['', 'No', 'FALSE'])) & 
            (df['Last_Updated'] != '') &
            (df['Status'] != '')
        ]
        
        return pending.to_dict('records')
    
    def mark_notification_sent(self, candidate_id):
        """Mark notification as sent for a specific candidate"""
        try:
            # Find the row with matching Candidate_ID
            cell = self.worksheet.find(str(candidate_id))
            if cell:
                # Update Notification_Sent column (column J = 10)
                self.worksheet.update_cell(cell.row, 10, 'Yes')
                return True
            return False
        except Exception as e:
            print(f"Error updating notification status: {e}")
            return False
    
    def add_timestamp(self, candidate_id):
        """Add current timestamp to Last_Updated column"""
        try:
            cell = self.worksheet.find(str(candidate_id))
            if cell:
                # Update Last_Updated column (column I = 9)
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.worksheet.update_cell(cell.row, 9, current_time)
                return True
            return False
        except Exception as e:
            print(f"Error adding timestamp: {e}")
            return False
