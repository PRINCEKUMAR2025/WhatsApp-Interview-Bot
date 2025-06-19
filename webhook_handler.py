from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from sheets_handler import SheetsHandler
from ai_generator import MessageGenerator
from conversational_handler import ConversationalBot
import logging
import re
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

class WhatsAppWebhookHandler:
    def __init__(self):
        self.sheets_handler = SheetsHandler()
        self.message_generator = MessageGenerator()
        self.conversational_bot = ConversationalBot()

    def process_incoming_message(self, from_number, message_body):
        """Single method to handle all incoming messages"""
        try:
            clean_number = from_number.replace('whatsapp:', '').strip()
            
            # Handle opt-out requests
            if message_body.lower().strip() in ['stop', 'unsubscribe', 'opt out']:
                return self._handle_opt_out(clean_number)
            
            # Get candidate data
            all_data = self.sheets_handler.get_all_data()
            candidate_data = None
            
            if all_data is not None and not all_data.empty:
                candidate_data = self._find_candidate_by_phone(all_data, clean_number)
            
            # Handle "hi" message with basic response
            if message_body.lower().strip() == 'hi':
                if candidate_data:
                    return self._generate_detailed_response(candidate_data)
                else:
                    return "Hello! I couldn't find your number in our records. Please contact HR if this is an error."
            
            # Process conversational messages
            if candidate_data:
                response = self.conversational_bot.process_conversation(
                    from_number, message_body, candidate_data
                )
                return response
            else:
                return "Hello! I couldn't find your information in our system. Please contact HR for assistance, or send 'hi' to check your status."
            
        except Exception as e:
            logging.error(f"Error processing conversation: {e}")
            return "I'm experiencing technical difficulties. Please try again or contact HR directly."

    def _handle_opt_out(self, phone_number):
        """Handle user opt-out requests"""
        # You can implement opt-out logic here
        return "You have been unsubscribed from WhatsApp notifications. You can still receive updates via email."

    def _find_candidate_by_phone(self, data, phone_number):
        """Find candidate by phone number"""
        search_patterns = [
            phone_number,
            phone_number.replace('+', ''),
            phone_number.replace('+91', ''),
            phone_number.replace('+1', ''),
            phone_number[-10:] if len(phone_number) >= 10 else phone_number
        ]
        
        for pattern in search_patterns:
            matches = data[data['Candidate_Phone'].astype(str).str.contains(pattern, na=False, regex=False)]
            if not matches.empty:
                return matches.iloc[0].to_dict()
        
        return None

    def _generate_detailed_response(self, candidate_data):
        """Generate detailed response for 'hi' messages"""
        try:
            response = self.message_generator.generate_webhook_response(candidate_data)
            return response
        except Exception as e:
            logging.error(f"Error generating AI response: {e}")
            return self._create_fallback_response(candidate_data)

    def _create_fallback_response(self, candidate_data):
        """Create fallback response if AI fails"""
        name = candidate_data.get('Candidate_Name', 'there')
        message = f"Hi {name}! 👋\n\n"
        message += f"🏢 Company: {candidate_data.get('Company_Name', 'N/A')}\n"
        message += f"💼 Role: {candidate_data.get('Applied_Role', 'N/A')}\n"
        message += f"📋 Status: {candidate_data.get('Interview_Status', 'N/A')}\n"
        
        if candidate_data.get('Interview_Date'):
            message += f"📅 Date: {candidate_data.get('Interview_Date')}\n"
        
        if candidate_data.get('Start_Time'):
            message += f"⏰ Time: {candidate_data.get('Start_Time')}"
            if candidate_data.get('End_Time'):
                message += f" to {candidate_data.get('End_Time')}"
            message += "\n"
        
        message += "\n💬 You can ask me questions about your interview or request changes!"
        return message

# Initialize webhook handler
webhook_handler = WhatsAppWebhookHandler()

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming WhatsApp messages"""
    try:
        from_number = request.form.get('From', '')
        message_body = request.form.get('Body', '')
        
        logging.info(f"Received message from {from_number}: {message_body}")
        
        response_text = webhook_handler.process_incoming_message(from_number, message_body)
        
        twiml_response = MessagingResponse()
        twiml_response.message(response_text)
        
        return str(twiml_response), 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        twiml_response = MessagingResponse()
        twiml_response.message("Sorry, I'm experiencing technical difficulties.")
        return str(twiml_response), 200, {'Content-Type': 'text/xml'}

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "WhatsApp Webhook Handler"}), 200

if __name__ == '__main__':
    print("Starting WhatsApp Webhook Handler...")
    app.run(debug=True, host='0.0.0.0', port=5000)
