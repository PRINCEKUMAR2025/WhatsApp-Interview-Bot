from interview_bot import InterviewNotificationBot
import pandas as pd
from datetime import datetime

def create_test_data():
    """Create sample data in Google Sheets for testing"""
    print("📝 Creating test data...")
    
    # Sample test data
    test_data = [
        {
            'Candidate_ID': '001',
            'Name': 'John Doe',
            'Phone': '+1234567890',  # Replace with your test number
            'Email': 'john@test.com',
            'Current_Round': 'Technical',
            'Status': 'Scheduled',
            'Interview_Date': '2025-06-04 10:00 AM',
            'Next_Round': 'HR Round',
            'Last_Updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Notification_Sent': 'No'
        },
        {
            'Candidate_ID': '002',
            'Name': 'Jane Smith',
            'Phone': '+0987654321',  # Replace with your test number
            'Email': 'jane@test.com',
            'Current_Round': 'Screening',
            'Status': 'Cleared',
            'Interview_Date': '2025-06-03 02:00 PM',
            'Next_Round': 'Technical Round',
            'Last_Updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Notification_Sent': 'No'
        }
    ]
    
    print("✅ Test data created. Manually add this to your Google Sheet:")
    for i, candidate in enumerate(test_data, 1):
        print(f"\nCandidate {i}:")
        for key, value in candidate.items():
            print(f"  {key}: {value}")

def test_individual_components():
    """Test each component separately"""
    print("🧪 Testing individual components...\n")
    
    try:
        bot = InterviewNotificationBot()
        
        # Test Google Sheets
        print("1. Testing Google Sheets connection...")
        data = bot.sheets_handler.get_all_data()
        if data is not None:
            print(f"   ✅ Connected! Found {len(data)} rows")
        else:
            print("   ❌ Failed to connect")
        
        # Test AI Generation
        print("\n2. Testing AI message generation...")
        test_candidate = {
            'Name': 'Test User',
            'Current_Round': 'Technical',
            'Status': 'Scheduled',
            'Interview_Date': '2025-06-04 10:00 AM'
        }
        message = bot.message_generator.generate_interview_message(test_candidate)
        print(f"   ✅ Generated message: {message[:100]}...")
        
        # Test WhatsApp validation
        print("\n3. Testing WhatsApp phone validation...")
        is_valid, result = bot.whatsapp_sender.validate_phone_number('+1234567890')
        print(f"   ✅ Validation result: {is_valid}, {result}")
        
        print("\n🎉 All individual tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

def send_test_message():
    """Send a test message to verify WhatsApp integration"""
    phone = input("Enter your WhatsApp number (with country code, e.g., +1234567890): ")
    
    try:
        bot = InterviewNotificationBot()
        success, result = bot.whatsapp_sender.send_test_message(phone)
        
        if success:
            print("✅ Test message sent successfully!")
        else:
            print(f"❌ Failed to send test message: {result}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🤖 Interview Bot Test Suite")
    print("=" * 40)
    
    choice = input("""
Choose a test option:
1. Create test data template
2. Test individual components
3. Send test WhatsApp message
4. Run full bot test
Enter choice (1-4): """)
    
    if choice == '1':
        create_test_data()
    elif choice == '2':
        test_individual_components()
    elif choice == '3':
        send_test_message()
    elif choice == '4':
        bot = InterviewNotificationBot()
        bot.test_setup()
        bot.run_once()
    else:
        print("Invalid choice!")
