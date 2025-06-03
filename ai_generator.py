import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

class MessageGenerator:
    def __init__(self):
        # Configure Gemini AI
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def generate_interview_message(self, candidate_data):
        """Generate personalized WhatsApp message based on candidate data"""
        name = candidate_data.get('Name', 'Candidate')
        current_round = candidate_data.get('Current_Round', 'Interview')
        status = candidate_data.get('Status', 'Scheduled')
        interview_date = candidate_data.get('Interview_Date', 'TBD')
        next_round = candidate_data.get('Next_Round', '')
        
        # Create context-specific prompts
        if status.lower() == 'scheduled':
            prompt = self._create_scheduled_prompt(name, current_round, interview_date)
        elif status.lower() == 'cleared':
            prompt = self._create_cleared_prompt(name, current_round, next_round)
        elif status.lower() == 'rejected':
            prompt = self._create_rejection_prompt(name, current_round)
        else:
            prompt = self._create_general_prompt(name, current_round, status)
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error generating AI message: {e}")
            return self._get_fallback_message(candidate_data)
    
    def _create_scheduled_prompt(self, name, round_type, date):
        return f"""
        Create a professional and encouraging WhatsApp message for {name} about their {round_type} interview scheduled for {date}.
        
        Requirements:
        - Keep it under 150 words
        - Use a friendly, professional tone
        - Include congratulations for reaching this stage
        - Mention the interview details
        - Add encouragement
        - Use 1-2 appropriate emojis
        - End with a positive note
        
        Make it sound personal and engaging.
        """
    
    def _create_cleared_prompt(self, name, completed_round, next_round):
        return f"""
        Create a congratulatory WhatsApp message for {name} who has successfully cleared their {completed_round}.
        
        Requirements:
        - Congratulate them enthusiastically
        - Mention they cleared the {completed_round}
        - If next round exists: {next_round}, mention it
        - Keep it under 150 words
        - Use celebratory emojis (2-3)
        - Sound excited and encouraging
        - Professional but warm tone
        """
    
    def _create_rejection_prompt(self, name, round_type):
        return f"""
        Create a respectful and encouraging WhatsApp message for {name} regarding their {round_type} interview result.
        
        Requirements:
        - Be respectful and professional
        - Thank them for their time and effort
        - Keep it positive and encouraging
        - Mention they can apply for future opportunities
        - Keep it under 100 words
        - Use supportive tone
        - No negative emojis
        """
    
    def _create_general_prompt(self, name, round_type, status):
        return f"""
        Create a professional WhatsApp update message for {name} about their {round_type} with status: {status}.
        
        Requirements:
        - Keep it professional and clear
        - Under 120 words
        - Appropriate tone for the status
        - Include relevant next steps if applicable
        """
    
    def _get_fallback_message(self, candidate_data):
        """Fallback message if AI generation fails"""
        name = candidate_data.get('Name', 'Candidate')
        status = candidate_data.get('Status', 'update')
        round_type = candidate_data.get('Current_Round', 'interview')
        
        fallback_messages = {
            'scheduled': f"Hi {name}! Your {round_type} interview has been scheduled. Please check your email for details. Best of luck! 🍀",
            'cleared': f"Congratulations {name}! You've successfully cleared the {round_type}. We'll update you about next steps soon. 🎉",
            'rejected': f"Hi {name}, thank you for your time with the {round_type}. We'll keep your profile for future opportunities."
        }
        
        return fallback_messages.get(status.lower(), 
                                   f"Hi {name}, there's an update regarding your {round_type}. Please check your email for details.")
