import google.generativeai as genai
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class TemplateMessageGenerator:
    def __init__(self):
        # Initialize Gemini for webhook responses (keep existing functionality)
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Template SIDs - Update these after WhatsApp approval
        self.templates = {
            'scheduled': 'HX96b3883278a0d57d68e5b55b7a034164',
            'reschedule': 'HXebb5a65730b86f83721812509fd5623d', 
            'confirmed': 'HXe7a33ede591a314f3662e3225978e3f7',
            'dropped': 'HXa68767df5df37091e5ad1bfc0389cc45',
            'not responding': 'HXf849e9b1349a64106572a0b33866d2d3'
        }

    def generate_interview_message(self, candidate_data):
        """Generate template data for WhatsApp templates"""
        name = candidate_data.get('Candidate_Name', 'Candidate')
        company = candidate_data.get('Company_Name', '')
        role = candidate_data.get('Applied_Role', '')
        current_round = candidate_data.get('Current_Round', '')
        status = candidate_data.get('Interview_Status', '').lower()
        interview_date = candidate_data.get('Interview_Date', '')
        start_time = candidate_data.get('Start_Time', '')
        end_time = candidate_data.get('End_Time', '')
        comments = candidate_data.get('Additional_Comments', '')
        outcome = candidate_data.get('Interview_Outcome', '')
        resources = candidate_data.get('Resources_To_Prepare', '')
        jd_link = candidate_data.get('JD_Link', '')

        # Return template data based on status
        if status in ['scheduled', 'reschedule']:
            return {
                'use_template': True,
                'template_sid': self.templates.get('reschedule' if status == 'reschedule' else 'scheduled'),
                'variables': {
                    '1': name,
                    '2': current_round,
                    '3': company,
                    '4': interview_date or 'TBD',
                    '5': start_time or 'TBD',
                    '6': end_time or 'TBD',
                    '7': role,
                    '8': comments or 'Good luck with your interview!'
                }
            }
        
        elif status == 'confirmed':
            return {
                'use_template': True,
                'template_sid': self.templates.get('confirmed'),
                'variables': {
                    '1': name,
                    '2': current_round,
                    '3': company,
                    '4': interview_date or 'Recently',
                    '5': start_time or '',
                    '6': role,
                    '7': outcome or 'Cleared',
                    '8': comments or 'Congratulations on your success!'
                }
            }
        
        elif status == 'dropped':
            return {
                'use_template': True,
                'template_sid': self.templates.get('dropped'),
                'variables': {
                    '1': name,
                    '2': current_round,
                    '3': company,
                    '4': role,
                    '5': outcome or 'Not selected',
                    '6': comments or 'Thank you for your time and interest.'
                }
            }
        
        elif status == 'not responding':
            return {
                'use_template': True,
                'template_sid': self.templates.get('not responding'),
                'variables': {
                    '1': name,
                    '2': current_round,
                    '3': company,
                    '4': role,
                    '5': interview_date or 'Recently',
                    '6': 'Following up with recruiter',
                    '7': comments or 'We are actively following up on your behalf.'
                }
            }
        
        else:
            # Fallback to scheduled template
            return {
                'use_template': True,
                'template_sid': self.templates.get('scheduled'),
                'variables': {
                    '1': name,
                    '2': current_round or 'interview',
                    '3': company,
                    '4': interview_date or 'TBD',
                    '5': start_time or 'TBD',
                    '6': end_time or 'TBD',
                    '7': role,
                    '8': comments or 'We will update you soon.'
                }
            }

    # Keep existing Gemini functionality for webhook responses
    def generate_webhook_response(self, candidate_data):
        """Generate AI response for webhook (keep existing functionality)"""
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
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return self._create_fallback_response(candidate_data)

    def _create_fallback_response(self, candidate_data):
        """Fallback response for webhook"""
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

# Keep backward compatibility
MessageGenerator = TemplateMessageGenerator
