import os
import google.generativeai as genai
import re
from datetime import datetime, timedelta
from sheets_handler import SheetsHandler
from dotenv import load_dotenv
import json

load_dotenv()

class ConversationalBot:
    def __init__(self):
        self.sheets_handler = SheetsHandler()
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Track conversation context
        self.user_sessions = {}
        
    def process_conversation(self, from_number, message_body, candidate_data=None):
        """Enhanced conversation processing with multi-step flows"""
        clean_number = from_number.replace('whatsapp:', '').strip()
        
        # Initialize session if new user
        if clean_number not in self.user_sessions:
            self.user_sessions[clean_number] = {
                'context': [],
                'pending_action': None,
                'candidate_data': candidate_data,
                'last_interaction': datetime.now()
            }
        
        session = self.user_sessions[clean_number]
        session['context'].append(f"User: {message_body}")
        session['last_interaction'] = datetime.now()
        
        # Handle pending actions first (multi-step conversations)
        if session.get('pending_action'):
            return self._handle_pending_action(message_body, session, candidate_data)
        
        # Analyze user intent
        intent = self._analyze_intent(message_body, candidate_data)
        
        # Route to appropriate handler
        if intent['action'] == 'query_data':
            return self._handle_data_query(message_body, candidate_data, session)
        elif intent['action'] == 'reschedule':
            return self._handle_reschedule(message_body, candidate_data, session, intent)
        elif intent['action'] == 'update_info':
            return self._handle_update_request(message_body, candidate_data, session, intent)
        elif intent['action'] == 'general_chat':
            return self._handle_general_chat(message_body, candidate_data, session)
        else:
            return self._handle_unknown_intent(message_body, candidate_data)

    def _analyze_intent(self, message, candidate_data):
        """Enhanced intent analysis with more categories"""
        try:
            message_lower = message.lower()
            
            # Query data intents
            if any(word in message_lower for word in ['when', 'what', 'status', 'interview', 'tell me', 'show me', 'my']):
                return {"action": "query_data", "confidence": 0.8, "details": {}}
            
            # Reschedule intents
            elif any(word in message_lower for word in ['reschedule', 'change date', 'change time', 'move', 'postpone', 'shift']):
                # Extract date/time if mentioned
                date_mentioned = self._extract_date_from_message(message)
                time_mentioned = self._extract_time_from_message(message)
                return {
                    "action": "reschedule", 
                    "confidence": 0.9, 
                    "details": {
                        "new_date": date_mentioned,
                        "new_time": time_mentioned
                    }
                }
            
            # Update info intents
            elif any(word in message_lower for word in ['update', 'change my', 'modify', 'edit', 'phone', 'email', 'address']):
                field_to_update = self._identify_update_field(message_lower)
                return {
                    "action": "update_info", 
                    "confidence": 0.8, 
                    "details": {
                        "field": field_to_update,
                        "new_value": self._extract_new_value(message, field_to_update)
                    }
                }
            
            # General chat
            else:
                return {"action": "general_chat", "confidence": 0.6, "details": {}}
                
        except Exception as e:
            print(f"Intent analysis error: {e}")
            return {"action": "unknown", "confidence": 0.0, "details": {}}

    def _handle_pending_action(self, message, session, candidate_data):
        """Handle multi-step conversations"""
        pending = session['pending_action']
        
        if pending['type'] == 'reschedule':
            return self._handle_reschedule_flow(message, session, candidate_data, pending)
        elif pending['type'] == 'update':
            return self._handle_update_flow(message, session, candidate_data, pending)
        else:
            # Clear unknown pending action
            session['pending_action'] = None
            return "Let's start over. What can I help you with?"

    def _handle_reschedule_flow(self, message, session, candidate_data, pending):
        """Handle step-by-step rescheduling"""
        if pending['step'] == 'awaiting_date':
            new_date = self._extract_date_from_message(message)
            if new_date:
                session['pending_action']['step'] = 'awaiting_time'
                session['pending_action']['new_date'] = new_date
                return f"""Perfect! I've noted **{new_date}** as your preferred date. 📅

What time would work best for you? You can say:
• "Morning" (9-12 AM)
• "Afternoon" (1-5 PM) 
• "2 PM" or "14:00"
• "Any time after 3 PM"

What time suits you?"""
            else:
                return """I couldn't understand that date format. Please try:
• "Tomorrow"
• "Next Monday"
• "June 25" or "25-06-2025"
• "25th June"

What date would you prefer?"""
        
        elif pending['step'] == 'awaiting_time':
            new_time = self._extract_time_from_message(message)
            if new_time:
                # Confirm before updating
                session['pending_action']['step'] = 'confirming'
                session['pending_action']['new_time'] = new_time
                
                current_date = candidate_data.get('Interview_Date', 'Not set')
                current_time = candidate_data.get('Start_Time', 'Not set')
                
                return f"""Let me confirm your reschedule request:

**Current Schedule:**
📅 {current_date} at {current_time}

**New Schedule:**
📅 {pending['new_date']} at {new_time}

Reply **"YES"** to confirm or **"NO"** to cancel."""
            else:
                return """I couldn't understand that time. Please try:
• "2 PM" or "14:00"
• "Morning" (9-12 AM)
• "Afternoon" (1-5 PM)
• "Evening" (5-8 PM)

What time works for you?"""
        
        elif pending['step'] == 'confirming':
            if message.lower().strip() in ['yes', 'y', 'confirm', 'ok', 'okay']:
                # Process the reschedule
                result = self._process_reschedule_update(
                    candidate_data, 
                    pending['new_date'], 
                    pending['new_time']
                )
                session['pending_action'] = None  # Clear pending action
                return result
            elif message.lower().strip() in ['no', 'n', 'cancel']:
                session['pending_action'] = None
                return "Reschedule cancelled. Your original interview time remains unchanged. Is there anything else I can help with?"
            else:
                return "Please reply **YES** to confirm the reschedule or **NO** to cancel."
        
        return "Something went wrong with the rescheduling. Let's start over."

    def _handle_update_flow(self, message, session, candidate_data, pending):
        """Handle step-by-step information updates"""
        if pending['step'] == 'awaiting_value':
            field = pending['field']
            new_value = message.strip()
            
            # Validate the new value
            if self._validate_update_value(field, new_value):
                session['pending_action']['step'] = 'confirming'
                session['pending_action']['new_value'] = new_value
                
                current_value = candidate_data.get(field, 'Not set')
                field_display = field.replace('_', ' ').title()
                
                return f"""Let me confirm your update:

**{field_display}:**
Current: {current_value}
New: {new_value}

Reply **"YES"** to confirm or **"NO"** to cancel."""
            else:
                return f"That doesn't look like a valid {field.replace('_', ' ')}. Please try again."
        
        elif pending['step'] == 'confirming':
            if message.lower().strip() in ['yes', 'y', 'confirm', 'ok', 'okay']:
                result = self._process_info_update(
                    candidate_data,
                    pending['field'],
                    pending['new_value']
                )
                session['pending_action'] = None
                return result
            elif message.lower().strip() in ['no', 'n', 'cancel']:
                session['pending_action'] = None
                return "Update cancelled. Your information remains unchanged."
            else:
                return "Please reply **YES** to confirm the update or **NO** to cancel."
        
        return "Something went wrong with the update. Let's start over."

    def _handle_data_query(self, message, candidate_data, session):
        """Enhanced data query handling with specific responses"""
        if not candidate_data:
            return "I couldn't find your information in our system. Please contact HR for assistance."
        
        # Use AI to generate contextual response
        prompt = f"""
        The candidate is asking: "{message}"
        
        Provide a helpful response based on their data:
        Name: {candidate_data.get('Candidate_Name', 'N/A')}
        Company: {candidate_data.get('Company_Name', 'N/A')}
        Role: {candidate_data.get('Applied_Role', 'N/A')}
        Status: {candidate_data.get('Interview_Status', 'N/A')}
        Date: {candidate_data.get('Interview_Date', 'N/A')}
        Time: {candidate_data.get('Start_Time', 'N/A')} to {candidate_data.get('End_Time', 'N/A')}
        Outcome: {candidate_data.get('Interview_Outcome', 'N/A')}
        Comments: {candidate_data.get('Additional_Comments', 'N/A')}
        
        Be conversational, friendly, and answer their specific question. Use emojis appropriately.
        End with asking if they need anything else or want to make changes.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except:
            return self._create_fallback_query_response(candidate_data)

    def _handle_reschedule(self, message, candidate_data, session, intent):
        """Handle rescheduling requests"""
        if not candidate_data:
            return "I couldn't find your interview information. Please contact HR for rescheduling."
        
        details = intent.get('details', {})
        new_date = details.get('new_date')
        new_time = details.get('new_time')
        
        # If both date and time provided, process directly
        if new_date and new_time:
            return self._process_reschedule_update(candidate_data, new_date, new_time)
        
        # If only date provided, ask for time
        elif new_date:
            session['pending_action'] = {
                'type': 'reschedule',
                'step': 'awaiting_time',
                'new_date': new_date
            }
            return f"Great! I've noted **{new_date}**. What time would work best for you?"
        
        # If only time provided, ask for date
        elif new_time:
            session['pending_action'] = {
                'type': 'reschedule',
                'step': 'awaiting_date',
                'new_time': new_time
            }
            return f"I've noted **{new_time}** as your preferred time. What date would you like?"
        
        # Start interactive rescheduling
        else:
            session['pending_action'] = {
                'type': 'reschedule',
                'step': 'awaiting_date'
            }
            
            current_date = candidate_data.get('Interview_Date', 'Not scheduled')
            current_time = candidate_data.get('Start_Time', 'Not scheduled')
            
            return f"""I can help you reschedule! 📅

**Current Schedule:**
📅 Date: {current_date}
⏰ Time: {current_time}

What new date would you prefer? You can say:
• "Tomorrow"
• "Next Monday"
• "June 25" or "25-06-2025"
• "Next week"

What date works for you?"""

    def _handle_update_request(self, message, candidate_data, session, intent):
        """Handle information update requests"""
        if not candidate_data:
            return "I couldn't find your information to update. Please contact HR."
        
        details = intent.get('details', {})
        field = details.get('field')
        new_value = details.get('new_value')
        
        # If both field and value provided, process directly
        if field and new_value:
            return self._process_info_update(candidate_data, field, new_value)
        
        # If only field provided, ask for new value
        elif field:
            session['pending_action'] = {
                'type': 'update',
                'step': 'awaiting_value',
                'field': field
            }
            field_display = field.replace('_', ' ').title()
            current_value = candidate_data.get(field, 'Not set')
            return f"Current {field_display}: **{current_value}**\n\nWhat would you like to change it to?"
        
        # Ask what they want to update
        else:
            return """What information would you like to update? I can help you change:

📱 **Phone number** - "Update my phone"
📧 **Email address** - "Change my email"  
🏠 **Address** - "Update my address"
👤 **Name** - "Change my name"

What would you like to update?"""

    def _handle_general_chat(self, message, candidate_data, session):
        """Handle general conversation with AI"""
        name = candidate_data.get('Candidate_Name', 'there') if candidate_data else 'there'
        company = candidate_data.get('Company_Name', 'the company') if candidate_data else 'your target company'
        role = candidate_data.get('Applied_Role', 'the position') if candidate_data else 'your desired role'
        
        prompt = f"""
        You are a helpful recruitment assistant. The candidate {name} is asking: "{message}"
        
        They are applying for {role} at {company}.
        
        Provide a helpful, encouraging, and professional response. Keep it conversational and friendly.
        If you don't know specific details, suggest they contact HR or ask me about their specific interview details.
        
        End with offering to help with their interview status or any changes they might need.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except:
            return f"Hi {name}! I'm here to help with your interview process. Feel free to ask about your status, schedule, or any other questions!"

    def _extract_date_from_message(self, message):
        """Extract and parse dates from user messages"""
        message_lower = message.lower().strip()
        today = datetime.now()
        
        # Handle relative dates
        if 'tomorrow' in message_lower:
            return (today + timedelta(days=1)).strftime('%d-%m-%Y')
        elif 'day after tomorrow' in message_lower:
            return (today + timedelta(days=2)).strftime('%d-%m-%Y')
        elif 'next week' in message_lower:
            return (today + timedelta(days=7)).strftime('%d-%m-%Y')
        elif 'next monday' in message_lower:
            days_ahead = 0 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime('%d-%m-%Y')
        elif 'next tuesday' in message_lower:
            days_ahead = 1 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime('%d-%m-%Y')
        # Add more weekdays as needed
        
        # Handle specific date patterns
        date_patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # DD/MM/YYYY or DD-MM-YYYY
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # YYYY/MM/DD or YYYY-MM-DD
            r'(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',  # DD Month
            r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2})',  # Month DD
        ]
        
        month_map = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        
        for pattern in date_patterns:
            match = re.search(pattern, message_lower)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3 and groups[0].isdigit() and len(groups[0]) == 4:
                        # YYYY-MM-DD format
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    elif len(groups) == 3:
                        # DD-MM-YYYY format
                        day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                    elif len(groups) == 2:
                        # Handle month name formats
                        if groups[0] in month_map:
                            month, day = month_map[groups[0]], int(groups[1])
                        else:
                            day, month = int(groups[0]), month_map[groups[1]]
                        year = today.year
                        
                    parsed_date = datetime(year, month, day)
                    return parsed_date.strftime('%d-%m-%Y')
                except (ValueError, KeyError):
                    continue
        
        return None

    def _extract_time_from_message(self, message):
        """Extract and parse times from user messages"""
        message_lower = message.lower().strip()
        
        # Handle relative times
        if 'morning' in message_lower:
            return '10:00'
        elif 'afternoon' in message_lower:
            return '14:00'
        elif 'evening' in message_lower:
            return '17:00'
        
        # Handle specific time patterns
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)?',
            r'(\d{1,2})\s*(am|pm)',
            r'(\d{1,2})\.(\d{2})',  # 14.30 format
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, message_lower)
            if match:
                try:
                    groups = match.groups()
                    hour = int(groups[0])
                    minute = int(groups[1]) if len(groups) > 1 and groups[1] and groups[1].isdigit() else 0
                    period = groups[2] if len(groups) > 2 else None
                    
                    if period == 'pm' and hour != 12:
                        hour += 12
                    elif period == 'am' and hour == 12:
                        hour = 0
                    
                    return f"{hour:02d}:{minute:02d}"
                except (ValueError, IndexError):
                    continue
        
        return None

    def _identify_update_field(self, message):
        """Identify which field the user wants to update"""
        if any(word in message for word in ['phone', 'number', 'mobile']):
            return 'Candidate_Phone'
        elif any(word in message for word in ['email', 'mail']):
            return 'Candidate_Email'
        elif any(word in message for word in ['address', 'location']):
            return 'Candidate_Address'
        elif any(word in message for word in ['name']):
            return 'Candidate_Name'
        return None

    def _extract_new_value(self, message, field):
        """Extract new value from update message"""
        # Simple extraction - can be enhanced
        if field and 'to' in message.lower():
            parts = message.lower().split('to')
            if len(parts) > 1:
                return parts[1].strip()
        return None

    def _validate_update_value(self, field, value):
        """Validate the new value for the field"""
        if field == 'Candidate_Phone':
            return bool(re.match(r'^[\+]?[\d\s\-\(\)]{10,15}$', value))
        elif field == 'Candidate_Email':
            return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value))
        elif field in ['Candidate_Name', 'Candidate_Address']:
            return len(value.strip()) > 0
        return True

    def _process_reschedule_update(self, candidate_data, new_date, new_time):
        """Process the actual reschedule update"""
        try:
            phone = candidate_data.get('Candidate_Phone')
            updates = {}
            
            if new_date:
                updates['Interview_Date'] = new_date
            if new_time:
                updates['Start_Time'] = new_time
            
            success = self.sheets_handler.update_candidate_data(phone, updates)
            
            if success:
                return f"""✅ **Interview rescheduled successfully!**

📅 **New Date:** {new_date or candidate_data.get('Interview_Date')}
⏰ **New Time:** {new_time or candidate_data.get('Start_Time')}

You'll receive a confirmation message shortly. Is there anything else I can help you with? 😊"""
            else:
                return "❌ Sorry, I couldn't update your schedule in the system. Please contact HR directly for assistance."
                
        except Exception as e:
            print(f"Reschedule error: {e}")
            return "❌ There was an error processing your reschedule request. Please contact HR for assistance."

    def _process_info_update(self, candidate_data, field, new_value):
        """Process information updates"""
        try:
            phone = candidate_data.get('Candidate_Phone')
            updates = {field: new_value}
            
            success = self.sheets_handler.update_candidate_data(phone, updates)
            
            if success:
                field_display = field.replace('_', ' ').title()
                return f"""✅ **{field_display} updated successfully!**

**New {field_display}:** {new_value}

Your information has been saved. Is there anything else you'd like to update? 😊"""
            else:
                return "❌ Sorry, I couldn't update your information. Please contact HR directly."
                
        except Exception as e:
            print(f"Update error: {e}")
            return "❌ There was an error updating your information. Please contact HR for assistance."

    def _create_fallback_query_response(self, candidate_data):
        """Fallback response for data queries"""
        name = candidate_data.get('Candidate_Name', 'there')
        company = candidate_data.get('Company_Name', 'the company')
        role = candidate_data.get('Applied_Role', 'the position')
        status = candidate_data.get('Interview_Status', 'your application')
        
        response = f"Hi {name}! 👋\n\n"
        response += f"Here's your current information:\n"
        response += f"🏢 **Company:** {company}\n"
        response += f"💼 **Role:** {role}\n"
        response += f"📋 **Status:** {status}\n"
        
        if candidate_data.get('Interview_Date'):
            response += f"📅 **Date:** {candidate_data.get('Interview_Date')}\n"
        
        if candidate_data.get('Start_Time'):
            response += f"⏰ **Time:** {candidate_data.get('Start_Time')}"
            if candidate_data.get('End_Time'):
                response += f" to {candidate_data.get('End_Time')}"
            response += "\n"
        
        response += "\n💬 Ask me anything about your interview or let me know if you want to make changes!"
        return response

    def _handle_unknown_intent(self, message, candidate_data):
        """Handle unknown intents with helpful suggestions"""
        name = candidate_data.get('Candidate_Name', 'there') if candidate_data else 'there'
        
        return f"""Hi {name}! I'm not sure how to help with that specific request. 

Here's what I can help you with:

📋 **Check Status** - "What's my interview status?"
📅 **Reschedule** - "Can I reschedule to tomorrow?"
📝 **Update Info** - "Update my phone number"
❓ **General Questions** - Ask me anything about your interview

What would you like to know or do?"""

    def cleanup_old_sessions(self):
        """Clean up old user sessions to free memory"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        to_remove = []
        
        for phone, session in self.user_sessions.items():
            if session.get('last_interaction', datetime.now()) < cutoff_time:
                to_remove.append(phone)
        
        for phone in to_remove:
            del self.user_sessions[phone]
