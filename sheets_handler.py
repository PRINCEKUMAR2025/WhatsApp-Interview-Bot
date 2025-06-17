import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class SheetsHandler:
    def __init__(self):
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE'),
            scope
        )
        self.client = gspread.authorize(creds)
        self.sheet_id = os.getenv('GOOGLE_SHEETS_ID')
        self.worksheet = self.client.open_by_key(self.sheet_id).sheet1

    def get_all_data(self):
        """Get data with duplicate header handling and correct column names."""
        try:
            raw_data = self.worksheet.get_all_values()
            # Clean headers: remove spaces, lowercase, replace with underscores
            headers = []
            seen_headers = {}
            for h in raw_data[0]:
                clean_h = h.strip().replace(' ', '_')
                if clean_h in seen_headers:
                    seen_headers[clean_h] += 1
                    headers.append(f"{clean_h}_{seen_headers[clean_h]}")
                else:
                    seen_headers[clean_h] = 0
                    headers.append(clean_h)
            df = pd.DataFrame(raw_data[1:], columns=headers)
            return df
        except Exception as e:
            print(f"Error reading Google Sheets: {e}")
            return None

    def get_pending_notifications(self):
        df = self.get_all_data()
        if df is None or df.empty:
            return []
        pending = df[
            (df['Notification_Sent'].isin(['', 'No', 'FALSE', 'no', 'false'])) &
            (df['Interview_Status'].str.strip() != '') &
            ((df['Interview_Outcome'].str.lower() == 'pending') | (df['Interview_Outcome'].str.strip() == ''))
        ]
        return pending.to_dict('records')

    def mark_notification_sent(self, candidate_id):
        try:
            cell = self.worksheet.find(str(candidate_id))
            if cell:
                # Notification_Sent is column P (16th column)
                self.worksheet.update_cell(cell.row, 16, 'Yes')
        except Exception as e:
            print(f"Error updating notification status: {e}")