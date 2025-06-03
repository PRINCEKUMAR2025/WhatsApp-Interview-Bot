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

# Fixed logging configuration
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
        """Initialize the bot with enhanced change detection and flood protection"""
        try:
            self.sheets_handler = SheetsHandler()
            self.message_generator = MessageGenerator()
            self.whatsapp_sender = WhatsAppSender()
            
            # Enhanced flood protection
            self.processed_notifications = {}  # Store processed notifications with timestamps
            self.notification_cooldown = 1800  # 30 minutes cooldown between same notifications
            self.daily_limit_per_candidate = 100  # Max 100 notifications per candidate per day
            self.hourly_limit_per_candidate = 10  # Max 10 notifications per candidate per hour
            self.daily_counts = {}
            self.hourly_counts = {}
            self.last_reset_date = datetime.now().date()
            self.last_reset_hour = datetime.now().hour
            
            # Change detection
            self.last_sheet_hash = None
            self.row_hashes = {}  # Track individual row changes
            self.last_check_time = datetime.now()
            
            logging.info("Interview Notification Bot initialized with enhanced change detection")
        except Exception as e:
            logging.error(f"Failed to initialize bot: {e}")
            raise
    
    def monitor_sheet_changes(self):
        """Enhanced method to detect specific changes in Google Sheets"""
        try:
            current_data = self.sheets_handler.get_all_data()
            if current_data is None:
                logging.warning("Could not fetch sheet data")
                return
            
            # Create hash of entire sheet for quick change detection
            sheet_content = current_data.to_json()
            current_sheet_hash = hashlib.md5(sheet_content.encode()).hexdigest()
            
            # If no previous hash, initialize and return
            if self.last_sheet_hash is None:
                self.last_sheet_hash = current_sheet_hash
                self._initialize_row_hashes(current_data)
                logging.info("Initialized sheet monitoring")
                return
            
            # Check if sheet has changed
            if current_sheet_hash != self.last_sheet_hash:
                logging.info("Sheet changes detected! Analyzing specific changes...")
                changed_rows = self._detect_row_changes(current_data)
                
                if changed_rows:
                    logging.info(f"Found {len(changed_rows)} changed rows")
                    self._process_changed_rows(changed_rows)
                
                # Update hashes
                self.last_sheet_hash = current_sheet_hash
                self._update_row_hashes(current_data)
            else:
                logging.info("No changes detected in sheet")
                
        except Exception as e:
            logging.error(f"Error monitoring sheet changes: {e}")
    
    def _initialize_row_hashes(self, data):
        """Initialize row hashes for change tracking"""
        self.row_hashes = {}
        for index, row in data.iterrows():
            row_key = str(row.get('Candidate_ID', index))
            row_content = row.to_json()
            self.row_hashes[row_key] = hashlib.md5(row_content.encode()).hexdigest()
    
    def _update_row_hashes(self, data):
        """Update row hashes after processing changes"""
        for index, row in data.iterrows():
            row_key = str(row.get('Candidate_ID', index))
            row_content = row.to_json()
            self.row_hashes[row_key] = hashlib.md5(row_content.encode()).hexdigest()
    
    def _detect_row_changes(self, current_data):
        """Detect which specific rows have changed"""
        changed_rows = []
        
        for index, row in current_data.iterrows():
            row_key = str(row.get('Candidate_ID', index))
            row_content = row.to_json()
            current_row_hash = hashlib.md5(row_content.encode()).hexdigest()
            
            # Check if this row has changed
            if row_key not in self.row_hashes or self.row_hashes[row_key] != current_row_hash:
                # Only process if notification is needed
                if row.get('Notification_Sent', '').lower() in ['no', '', 'false']:
                    changed_rows.append(row.to_dict())
                    logging.info(f"Detected change in row for {row.get('Name', 'Unknown')}")
        
        return changed_rows
    
    def _process_changed_rows(self, changed_rows):
        """Process only the rows that have actually changed"""
        for row_data in changed_rows:
            self._process_single_candidate_with_flood_protection(row_data)
            time.sleep(3)  # Delay between messages
    
    def _reset_counters_if_needed(self):
        """Reset daily and hourly counters when needed"""
        current_time = datetime.now()
        current_date = current_time.date()
        current_hour = current_time.hour
        
        # Reset daily counts
        if current_date > self.last_reset_date:
            self.daily_counts = {}
            self.last_reset_date = current_date
            logging.info("Daily notification counts reset")
        
        # Reset hourly counts
        if current_hour != self.last_reset_hour:
            self.hourly_counts = {}
            self.last_reset_hour = current_hour
            logging.info("Hourly notification counts reset")
    
    def _process_single_candidate_with_flood_protection(self, candidate_data):
        """Process notification with comprehensive flood protection"""
        try:
            candidate_id = str(candidate_data.get('Candidate_ID', ''))
            name = candidate_data.get('Name', 'Unknown')
            phone = candidate_data.get('Phone')
            status = candidate_data.get('Status', '')
            current_round = candidate_data.get('Current_Round', '')
            last_updated = candidate_data.get('Last_Updated', '')
            
            logging.info(f"Processing candidate: {name}")
            
            # Reset counters if needed
            self._reset_counters_if_needed()
            
            # Create unique notification key
            notification_key = f"{candidate_id}_{status}_{current_round}_{last_updated}"
            
            # Comprehensive flood protection checks
            if self._is_notification_recently_sent(notification_key):
                logging.info(f"Skipping {name} - same notification sent recently (cooldown: {self.notification_cooldown/60} minutes)")
                return
            
            if self._has_exceeded_daily_limit(candidate_id):
                logging.info(f"Skipping {name} - daily limit exceeded ({self.daily_limit_per_candidate}/day)")
                return
            
            if self._has_exceeded_hourly_limit(candidate_id):
                logging.info(f"Skipping {name} - hourly limit exceeded ({self.hourly_limit_per_candidate}/hour)")
                return
            
            # Validate phone number
            is_valid, phone_result = self.whatsapp_sender.validate_phone_number(phone)
            if not is_valid:
                logging.error(f"Invalid phone number for {name}: {phone_result}")
                return
            
            # Generate and send message
            logging.info(f"Generating AI message for {name}...")
            message = self.message_generator.generate_interview_message(candidate_data)
            
            logging.info(f"Sending WhatsApp message to {name} ({phone})...")
            success, result = self.whatsapp_sender.send_message(phone, message)
            
            if success:
                # Mark as sent and update tracking
                self.sheets_handler.mark_notification_sent(candidate_id)
                self._record_notification_sent(notification_key, candidate_id)
                
                logging.info(f"Successfully notified {name}")
                logging.info(f"Message preview: {message[:100]}...")
            else:
                logging.error(f"Failed to notify {name}: {result}")
                
        except Exception as e:
            logging.error(f"Error processing candidate {candidate_data.get('Name', 'Unknown')}: {e}")
    
    def _is_notification_recently_sent(self, notification_key):
        """Check if notification was sent within cooldown period"""
        if notification_key in self.processed_notifications:
            last_sent_time = self.processed_notifications[notification_key]
            time_since_last = (datetime.now() - last_sent_time).total_seconds()
            return time_since_last < self.notification_cooldown
        return False
    
    def _has_exceeded_daily_limit(self, candidate_id):
        """Check daily notification limit"""
        today = datetime.now().date()
        daily_key = f"{candidate_id}_{today}"
        current_count = self.daily_counts.get(daily_key, 0)
        return current_count >= self.daily_limit_per_candidate
    
    def _has_exceeded_hourly_limit(self, candidate_id):
        """Check hourly notification limit"""
        current_hour = datetime.now().hour
        hourly_key = f"{candidate_id}_{current_hour}"
        current_count = self.hourly_counts.get(hourly_key, 0)
        return current_count >= self.hourly_limit_per_candidate
    
    def _record_notification_sent(self, notification_key, candidate_id):
        """Record notification for flood protection tracking"""
        current_time = datetime.now()
        
        # Record the specific notification
        self.processed_notifications[notification_key] = current_time
        
        # Update daily count
        today = current_time.date()
        daily_key = f"{candidate_id}_{today}"
        self.daily_counts[daily_key] = self.daily_counts.get(daily_key, 0) + 1
        
        # Update hourly count
        current_hour = current_time.hour
        hourly_key = f"{candidate_id}_{current_hour}"
        self.hourly_counts[hourly_key] = self.hourly_counts.get(hourly_key, 0) + 1
        
        # Clean up old entries
        self._cleanup_old_entries()
    
    def _cleanup_old_entries(self):
        """Clean up old cache entries to prevent memory bloat"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=24)
        
        # Clean up old processed notifications
        keys_to_remove = [
            key for key, timestamp in self.processed_notifications.items()
            if timestamp < cutoff_time
        ]
        for key in keys_to_remove:
            del self.processed_notifications[key]
        
        if keys_to_remove:
            logging.info(f"Cleaned up {len(keys_to_remove)} old notification entries")
    
    def run_continuous_monitoring(self):
        """Run continuous monitoring with real-time change detection"""
        logging.info("Starting continuous Google Sheets monitoring...")
        logging.info("Bot will check for changes every 60 seconds")
        
        # Schedule monitoring every minute for responsive updates
        schedule.every(1).minutes.do(self.monitor_sheet_changes)
        
        # Clean up cache every hour
        schedule.every().hour.do(self._cleanup_old_entries)
        
        # Initial check
        self.monitor_sheet_changes()
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
            except KeyboardInterrupt:
                logging.info("Bot stopped by user")
                break
            except Exception as e:
                logging.error(f"Error in continuous monitoring: {e}")
                time.sleep(60)
    
    def get_monitoring_stats(self):
        """Get current monitoring and cache statistics"""
        stats = {
            'processed_notifications_count': len(self.processed_notifications),
            'daily_counts': dict(self.daily_counts),
            'hourly_counts': dict(self.hourly_counts),
            'last_check_time': str(self.last_check_time),
            'cooldown_minutes': self.notification_cooldown / 60,
            'daily_limit': self.daily_limit_per_candidate,
            'hourly_limit': self.hourly_limit_per_candidate
        }
        logging.info(f"Monitoring stats: {stats}")
        return stats

if __name__ == "__main__":
    bot = InterviewNotificationBot()
    
    choice = input("""
Choose monitoring mode:
1. Continuous monitoring (real-time change detection)
2. Show monitoring stats
3. Test single check
4. Exit
Enter choice (1-4): """)
    
    if choice == '1':
        bot.run_continuous_monitoring()
    elif choice == '2':
        bot.get_monitoring_stats()
    elif choice == '3':
        bot.monitor_sheet_changes()
    else:
        print("Goodbye!")
