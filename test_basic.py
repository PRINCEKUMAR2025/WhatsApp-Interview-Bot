from ai_generator import MessageGenerator
from whatsapp_sender import WhatsAppSender
import os
from dotenv import load_dotenv

load_dotenv()

def test_basic_functionality():
    """Test basic functionality without Google Sheets"""
    print("Testing basic functionality...")
    
    # Test AI Generation
    try:
        print("1. Testing AI message generation...")
        message_gen = MessageGenerator()
        
        test_data = {
            'Name': 'John Doe',
            'Current_Round': 'Technical',
            'Status': 'Scheduled',
            'Interview_Date': '2025-06-04 10:00 AM'
        }
        
        message = message_gen.generate_interview_message(test_data)
        print(f"   Generated message: {message[:100]}...")
        print("   AI Generation: SUCCESS")
        
    except Exception as e:
        print(f"   AI Generation failed: {e}")
        return False
    
    # Test WhatsApp validation
    try:
        print("\n2. Testing WhatsApp validation...")
        whatsapp = WhatsAppSender()
        
        is_valid, result = whatsapp.validate_phone_number('+919263222643')
        print(f"   Validation result: {is_valid}, {result}")
        print("   WhatsApp validation: SUCCESS")
        
    except Exception as e:
        print(f"   WhatsApp validation failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if test_basic_functionality():
        print("\nBasic functionality test: PASSED")
        
        # Optional: Send test message
        send_test = input("\nSend test WhatsApp message? (y/n): ")
        if send_test.lower() == 'y':
            phone = input("Enter your phone number (+country_code_number): ")
            whatsapp = WhatsAppSender()
            success, result = whatsapp.send_test_message(phone)
            if success:
                print("Test message sent successfully!")
            else:
                print(f"Test message failed: {result}")
    else:
        print("\nBasic functionality test: FAILED")
