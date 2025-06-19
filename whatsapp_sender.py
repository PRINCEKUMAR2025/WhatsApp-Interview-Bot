from twilio.rest import Client
import os
from dotenv import load_dotenv
import re
import json

load_dotenv()

class WhatsAppSender:
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER')

        if not all([self.account_sid, self.auth_token, self.whatsapp_number]):
            raise ValueError("Missing Twilio configuration. Check your .env file.")

        self.client = Client(self.account_sid, self.auth_token)

    def send_message(self, to_number, message_data):
        """Send WhatsApp message - supports both templates and regular messages"""
        try:
            formatted_number = self._format_phone_number(to_number)
            if not formatted_number:
                return False, "Invalid phone number format"

            # Check if it's template data or regular message
            if isinstance(message_data, dict) and message_data.get('use_template'):
                return self._send_template_message(formatted_number, message_data)
            else:
                # Regular message (for webhook responses)
                return self._send_regular_message(formatted_number, message_data)

        except Exception as e:
            error_msg = f"Failed to send message to {to_number}: {str(e)}"
            print(f"Error: {error_msg}")
            return False, error_msg

    def _send_template_message(self, to_number, template_data):
        """Send WhatsApp template message"""
        try:
            message = self.client.messages.create(
                content_sid=template_data['template_sid'],
                content_variables=json.dumps(template_data['variables']),
                from_=self.whatsapp_number,
                to=to_number
            )
            
            print(f"Template message sent successfully to {to_number}")
            print(f"Message SID: {message.sid}")
            return True, message.sid

        except Exception as e:
            print(f"Template message error: {e}")
            # Fallback to regular message if template fails
            fallback_message = self._create_fallback_message(template_data['variables'])
            return self._send_regular_message(to_number, fallback_message)

    def _send_regular_message(self, to_number, message_body):
        """Send regular WhatsApp message"""
        try:
            message = self.client.messages.create(
                body=message_body,
                from_=self.whatsapp_number,
                to=to_number
            )

            print(f"Regular message sent successfully to {to_number}")
            print(f"Message SID: {message.sid}")
            return True, message.sid

        except Exception as e:
            error_msg = f"Failed to send regular message: {str(e)}"
            print(f"Error: {error_msg}")
            return False, error_msg

    def _create_fallback_message(self, variables):
        """Create fallback message from template variables"""
        name = variables.get('1', 'there')
        company = variables.get('3', 'the company')
        role = variables.get('7', 'the position')
        
        message = f"Hi {name}! 👋\n\n"
        message += f"Update regarding your application at {company} for {role}.\n\n"
        message += f"We'll keep you updated on your progress.\n\n"
        message += "Feel free to reach out if you have any questions! 😊"
        
        return message

    def _format_phone_number(self, phone):
        """Format phone number for WhatsApp"""
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
        """Validate phone number format"""
        formatted = self._format_phone_number(phone)
        if formatted:
            return True, formatted.replace('whatsapp:', '')
        else:
            return False, "Phone number must include country code (e.g., +1234567890)"

    def send_test_message(self, phone):
        """Send test message"""
        test_message = "Test message from your Interview Notification Bot! Setup is working correctly."
        return self._send_regular_message(self._format_phone_number(phone), test_message)
