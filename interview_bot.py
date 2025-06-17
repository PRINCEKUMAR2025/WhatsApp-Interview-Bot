import time
import schedule
from datetime import datetime, timedelta
import hashlib
import json
from sheets_handler import SheetsHandler
from ai_generator import MessageGenerator
from whatsapp_sender import WhatsAppSender
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('interview_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class InterviewNotificationBot:
    def __init__(self):
        try:
            self.sheets_handler = SheetsHandler()
            self.message_generator = MessageGenerator()
            self.whatsapp_sender = WhatsAppSender()
            self.processed_notifications = {}
            self.notification_cooldown = 1800
            self.daily_limit_per_candidate = 100
            self.hourly_limit_per_candidate = 10
            self.daily_counts = {}
            self.hourly_counts = {}
            self.last_reset_date = datetime.now().date()
            self.last_reset_hour = datetime.now().hour
            self.last_sheet_hash = None
            self.row_hashes = {}
            self.last_check_time = datetime.now()
            logging.info("Interview Notification Bot initialized with enhanced change detection")
        except Exception as e:
            logging.error(f"Failed to initialize bot: {e}")
            raise

    def monitor_sheet_changes(self):
        try:
            current_data = self.sheets_handler.get_all_data()
            if current_data is None:
                logging.warning("Could not fetch sheet data")
                return
            sheet_content = current_data.to_json()
            current_sheet_hash = hashlib.md5(sheet_content.encode()).hexdigest()
            if self.last_sheet_hash is None:
                self.last_sheet_hash = current_sheet_hash
                self._initialize_row_hashes(current_data)
                logging.info("Initialized sheet monitoring")
                return
            if current_sheet_hash != self.last_sheet_hash:
                logging.info("Sheet changes detected! Analyzing specific changes...")
                changed_rows = self._detect_row_changes(current_data)
                if changed_rows:
                    logging.info(f"Found {len(changed_rows)} changed rows")
                    self._process_changed_rows(changed_rows)
                self.last_sheet_hash = current_sheet_hash
                self._update_row_hashes(current_data)
            else:
                logging.info("No changes detected in sheet")
        except Exception as e:
            logging.error(f"Error monitoring sheet changes: {e}")

    def _initialize_row_hashes(self, data):
        self.row_hashes = {}
        for index, row in data.iterrows():
            row_key = str(row.get('Candidate_Email', index))
            row_content = row.to_json()
            self.row_hashes[row_key] = hashlib.md5(row_content.encode()).hexdigest()

    def _update_row_hashes(self, data):
        for index, row in data.iterrows():
            row_key = str(row.get('Candidate_Email', index))
            row_content = row.to_json()
            self.row_hashes[row_key] = hashlib.md5(row_content.encode()).hexdigest()

    def _detect_row_changes(self, current_data):
        changed_rows = []
        for index, row in current_data.iterrows():
            row_key = str(row.get('Candidate_Email', index))
            row_content = row.to_json()
            current_row_hash = hashlib.md5(row_content.encode()).hexdigest()
            if row_key not in self.row_hashes or self.row_hashes[row_key] != current_row_hash:
                if row.get('Notification_Sent', '').lower() in ['no', '', 'false']:
                    changed_rows.append(row.to_dict())
                    logging.info(f"Detected change in row for {row.get('Candidate_Name', 'Unknown')}")
        return changed_rows

    def _process_changed_rows(self, changed_rows):
        for row_data in changed_rows:
            self._process_single_candidate_with_flood_protection(row_data)
            time.sleep(3)

    def _reset_counters_if_needed(self):
        current_time = datetime.now()
        current_date = current_time.date()
        current_hour = current_time.hour
        if current_date > self.last_reset_date:
            self.daily_counts = {}
            self.last_reset_date = current_date
            logging.info("Daily notification counts reset")
        if current_hour != self.last_reset_hour:
            self.hourly_counts = {}
            self.last_reset_hour = current_hour
            logging.info("Hourly notification counts reset")

    def _process_single_candidate_with_flood_protection(self, candidate_data):
        try:
            candidate_id = candidate_data.get('Candidate_Email', '')  # Use email as unique ID
            name = candidate_data.get('Candidate_Name', 'Unknown')
            phone = candidate_data.get('Candidate_Phone', '')
            outcome = candidate_data.get('Interview_Outcome', '')
            status = candidate_data.get('Interview_Status', '')
            if outcome.lower() == 'rejected':
                logging.info(f"{name} was rejected, skipping notification.")
                return
            message = self.message_generator.generate_interview_message(candidate_data)
            success, result = self.whatsapp_sender.send_message(phone, message)
            if success:
                self.sheets_handler.mark_notification_sent(candidate_id)
                logging.info(f"Notification sent to {name} ({phone})")
            else:
                logging.error(f"Failed to notify {name}: {result}")
        except Exception as e:
            logging.error(f"Error processing {candidate_data.get('Candidate_Name', 'Unknown')}: {e}")

    def run_continuous_monitoring(self):
        logging.info("Starting continuous Google Sheets monitoring...")
        logging.info("Bot will check for changes every 60 seconds")
        schedule.every(1).minutes.do(self.monitor_sheet_changes)
        schedule.every().hour.do(self._cleanup_old_entries)
        self.monitor_sheet_changes()
        while True:
            try:
                schedule.run_pending()
                time.sleep(30)
            except KeyboardInterrupt:
                logging.info("Bot stopped by user")
                break
            except Exception as e:
                logging.error(f"Error in continuous monitoring: {e}")
                time.sleep(60)

    def _cleanup_old_entries(self):
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=24)
        keys_to_remove = [
            key for key, timestamp in self.processed_notifications.items()
            if timestamp < cutoff_time
        ]
        for key in keys_to_remove:
            del self.processed_notifications[key]
        if keys_to_remove:
            logging.info(f"Cleaned up {len(keys_to_remove)} old notification entries")