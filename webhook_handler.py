from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from sheets_handler import SheetsHandler
from ai_generator import MessageGenerator
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

    def process_incoming_message(self, from_number, message_body):
        try:
            clean_number = from_number.replace('whatsapp:', '').strip()
            
            if message_body.lower().strip() == 'hi':
                return self._handle_hi_message(clean_number)
            else:
                return "Hello! 👋 Send 'hi' to get your latest interview status and details. 📋"
                
        except Exception as e:
            logging.error(f"Error processing message: {e}")
            return "Sorry, I encountered an error. Please try again later."

    def _handle_hi_message(self, phone_number):
        try:
            all_data = self.sheets_handler.get_all_data()
            
            if all_data is None or all_data.empty:
                return "Sorry, I couldn't access the database. Please try again later."
            
            candidate_data = self._find_candidate_by_phone(all_data, phone_number)
            
            if candidate_data is not None:
                response_message = self._generate_detailed_response(candidate_data)
                return response_message
            else:
                return f"Hello! I couldn't find your number in our records. Please contact HR if this is an error."
                
        except Exception as e:
            logging.error(f"Error handling hi message: {e}")
            return "Sorry, I encountered an error while looking up your information."

    def _find_candidate_by_phone(self, data, phone_number):
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
        prompt = f"""
        Create a comprehensive WhatsApp message for a candidate who messaged "hi".
        
        Candidate Details:
        - Name: {candidate_data.get('Candidate_Name', 'N/A')}
        - Company: {candidate_data.get('Company_Name', 'N/A')}
        - Role: {candidate_data.get('Applied_Role', 'N/A')}
        - Status: {candidate_data.get('Interview_Status', 'N/A')}
        - Interview Date: {candidate_data.get('Interview_Date', 'N/A')}
        - Time: {candidate_data.get('Start_Time', 'N/A')} to {candidate_data.get('End_Time', 'N/A')}
        - Outcome: {candidate_data.get('Interview_Outcome', 'N/A')}
        - Comments: {candidate_data.get('Additional_Comments', 'N/A')}
        
        Create a warm, professional message with all details clearly formatted with emojis.
        """
        
        try:
            response = self.message_generator.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return self._create_fallback_response(candidate_data)

    def _create_fallback_response(self, candidate_data):
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
        
        message += "\nFeel free to ask if you need any clarification! 😊"
        return message

webhook_handler = WhatsAppWebhookHandler()

@app.route('/webhook', methods=['POST'])
def webhook():
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
