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

    def update_candidate_data(self, phone_number, updates):
        """Enhanced update method with better error handling"""
        try:
            df = self.get_all_data()
            if df is None:
                print("Could not fetch sheet data")
                return False

            # Find the candidate row with flexible phone matching
            phone_matches = None
            search_patterns = [
                phone_number,
                phone_number.replace('+', ''),
                phone_number.replace('+91', ''),
                phone_number.replace('+1', ''),
                phone_number[-10:] if len(phone_number) >= 10 else phone_number
            ]
        
            for pattern in search_patterns:
                matches = df[df['Candidate_Phone'].astype(str).str.contains(pattern, na=False, regex=False)]
                if not matches.empty:
                    phone_matches = matches
                    break
        
            if phone_matches is None or phone_matches.empty:
                print(f"No candidate found with phone: {phone_number}")
                return False

            row_index = phone_matches.index[0]
        
            # Update the worksheet
            worksheet = self.client.open_by_key(self.sheet_id).sheet1
        
            for column, value in updates.items():
                if column in df.columns:
                    col_index = df.columns.get_loc(column) + 1  # +1 for 1-based indexing
                    cell_row = row_index + 2  # +2 for header and 0-based index
                    worksheet.update_cell(cell_row, col_index, value)
                    print(f"Updated {column} to {value} at row {cell_row}, col {col_index}")
        
            return True

        except Exception as e:
            print(f"Error updating candidate data: {e}")
            return False

    def log_conversation(self, phone_number, message, response):
        """Log conversations for audit trail"""
        try:
            # You can implement conversation logging here
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] {phone_number}: {message} -> {response[:50]}...")
        except Exception as e:
            print(f"Error logging conversation: {e}")
