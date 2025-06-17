import google.generativeai as genai
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class MessageGenerator:
    def __init__(self):
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_interview_message(self, candidate_data):
        name = candidate_data.get('Candidate_Name', 'Candidate')
        company = candidate_data.get('Company_Name', '')
        role = candidate_data.get('Applied_Role', '')
        current_round = candidate_data.get('Current_Round', '')
        status = candidate_data.get('Interview_Status', '')
        interview_date = candidate_data.get('Interview_Date', '')
        start_time = candidate_data.get('Start_Time', '')
        end_time = candidate_data.get('End_Time', '')
        jd_link = candidate_data.get('JD_Link', '')
        resources = candidate_data.get('Resources_To_Prepare', '')
        comments = candidate_data.get('Additional_Comments', '')
        outcome = candidate_data.get('Interview_Outcome', '')

        # Create base message with date/time if available
        base_info = self._create_datetime_header(interview_date, start_time, end_time)
        
        if status.lower() == 'reschedule':
            prompt = f"""
            Create a WhatsApp message for {name} about rescheduling their {current_round} at {company}.
            
            CRITICAL REQUIREMENT: You MUST include the following date and time information at the beginning of the message:
            {base_info}
            
            Additional details to include:
            - Role: {role}
            - JD Link: {jd_link if jd_link else 'Will be shared separately'}
            - Resources: {resources if resources else 'Will be provided'}
            - Additional Comments: {comments}

            Format: Start with the date/time, then explain the rescheduling in a polite and clear tone.
            """

        elif status.lower() == 'not responding':
            prompt = f"""
            Create a WhatsApp message to update {name} about their interview status at {company}.
            
            {base_info}
            
            Details to include:
            - Company: {company}
            - Role: {role}
            - Round: {current_round}
            - Outcome: {outcome}
            - Feedback: {comments}

            Mention that the recruiter is not responding and we are following up. Use a professional yet empathetic tone.
            """
            
        elif status.lower() == 'confirmed':
            prompt = f"""
            Create a congratulatory WhatsApp message for {name} who cleared the {current_round} at {company}.
            
            MANDATORY: Start the message with this exact date/time information:
            {base_info}
            
            Then include:
            - Role: {role}
            - Outcome: {outcome}
            - Feedback: {comments}

            Use a warm, celebratory, and professional tone. Make the date and time prominent.
            """
            
        elif status.lower() == 'dropped':
            prompt = f"""
            Create a respectful WhatsApp message to inform {name} about their interview result at {company}.
            
            {base_info}
            
            Include these details sensitively:
            - Role: {role}
            - Round: {current_round}
            - Outcome: {outcome}
            - Feedback: {comments}

            Use a respectful, empathetic, and professional tone. Keep it concise but supportive.
            """
            
        else:
            prompt = f"""
            Create a WhatsApp message to update {name} about their interview process at {company}.
            
            {base_info}
            
            Details to include:
            - Role: {role}
            - Interview Round: {current_round}
            - Current Status: {status}
            - Outcome: {outcome}
            - Comments/Feedback: {comments}

            Ensure the message is polite, clear, and informative with a professional tone.
            """

        try:
            response = self.model.generate_content(prompt)
            generated_message = response.text.strip()
            
            # Validate and enhance the message if needed
            validated_message = self._validate_and_enhance_message(
                generated_message, candidate_data
            )
            
            return validated_message
            
        except Exception as e:
            return self._get_fallback_message(candidate_data)

    def _create_datetime_header(self, interview_date, start_time, end_time):
        """Create a formatted date/time header for messages"""
        if not interview_date and not start_time:
            return "Interview details:"
            
        header_parts = []
        
        if interview_date:
            header_parts.append(f"📅 Date: {interview_date}")
            
        if start_time:
            if end_time:
                header_parts.append(f"⏰ Time: {start_time} to {end_time}")
            else:
                header_parts.append(f"⏰ Time: {start_time}")
                
        if header_parts:
            return "\n".join(header_parts) + "\n"
        else:
            return ""

    def _validate_and_enhance_message(self, message, candidate_data):
        """Validate that the message contains date/time and enhance if missing"""
        interview_date = candidate_data.get('Interview_Date', '')
        start_time = candidate_data.get('Start_Time', '')
        end_time = candidate_data.get('End_Time', '')
        
        # Check if date/time information is missing from the generated message
        missing_info = []
        
        if interview_date and interview_date not in message:
            missing_info.append(f"📅 Date: {interview_date}")
            
        if start_time and start_time not in message:
            if end_time:
                missing_info.append(f"⏰ Time: {start_time} to {end_time}")
            else:
                missing_info.append(f"⏰ Time: {start_time}")
        
        # If critical info is missing, prepend it to the message
        if missing_info:
            enhanced_header = "\n".join(missing_info) + "\n\n"
            return enhanced_header + message
            
        return message

    def _get_fallback_message(self, candidate_data):
        """Enhanced fallback messages with date/time"""
        name = candidate_data.get('Candidate_Name', 'Candidate')
        status = candidate_data.get('Interview_Status', 'update')
        round_type = candidate_data.get('Current_Round', 'interview')
        interview_date = candidate_data.get('Interview_Date', '')
        start_time = candidate_data.get('Start_Time', '')
        end_time = candidate_data.get('End_Time', '')
        
        # Create date/time header for fallback
        datetime_info = self._create_datetime_header(interview_date, start_time, end_time)
        
        fallback_messages = {
            'scheduled': f"Hi {name}!\n\n{datetime_info}Your {round_type} interview has been scheduled. Please check your email for details. Best of luck!",
            'confirmed': f"Congratulations {name}!\n\n{datetime_info}You've successfully cleared the {round_type}. We'll update you about next steps soon.",
            'dropped': f"Hi {name},\n\n{datetime_info}Thank you for your time with the {round_type}. We'll keep your profile for future opportunities.",
            'reschedule': f"Hi {name},\n\n{datetime_info}Your {round_type} interview has been rescheduled. Please check the new timing above."
        }
        
        default_message = f"Hi {name},\n\n{datetime_info}There's an update regarding your {round_type}. Please check your email for details."
        
        return fallback_messages.get(status.lower(), default_message)
