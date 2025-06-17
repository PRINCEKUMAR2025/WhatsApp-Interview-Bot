from twilio.rest import Client
import os
from dotenv import load_dotenv
import re

load_dotenv()

class WhatsAppSender:
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER')
        if not all([self.account_sid, self.auth_token, self.whatsapp_number]):
            raise ValueError("Missing Twilio configuration. Check your .env file.")
        self.client = Client(self.account_sid, self.auth_token)

    def send_message(self, to_number, message_body):
        try:
            formatted_number = self._format_phone_number(to_number)
            if not formatted_number:
                return False, "Invalid phone number format"
            message = self.client.messages.create(
                body=message_body,
                from_=self.whatsapp_number,
                to=formatted_number
            )
            print(f"Message sent successfully to {to_number}")
            print(f"Message SID: {message.sid}")
            return True, message.sid
        except Exception as e:
            error_msg = f"Failed to send message to {to_number}: {str(e)}"
            print(f"Error: {error_msg}")
            return False, error_msg

    def _format_phone_number(self, phone):
        if not phone:
            return None
        phone = str(phone).strip()
        phone = re.sub(r'[^\d+]', '', phone)
        if not phone.startswith('+'):
            if phone.startswith(('91', '1', '44')):
                phone = '+' + phone
            else:
                return None
        if not re.match(r'^\+\d{10,15}$', phone):
            return None
        return f'whatsapp:{phone}'

    def validate_phone_number(self, phone):
        formatted = self._format_phone_number(phone)
        if formatted:
            return True, formatted.replace('whatsapp:', '')
        else:
            return False, "Phone number must include country code (e.g., +1234567890)"

    def send_test_message(self, phone):
        test_message = "Test message from your Interview Notification Bot! Setup is working correctly."
        return self.send_message(phone, test_message)
