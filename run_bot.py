#!/usr/bin/env python3
import sys
import signal
import argparse
from interview_bot import InterviewNotificationBot

def signal_handler(sig, frame):
    print('\nBot stopped gracefully')
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description='Interview Notification Bot')
    parser.add_argument('--mode', choices=['once', 'continuous', 'test'],
                        default='once', help='Bot running mode')
    parser.add_argument('--test-phone', help='Phone number for test message')
    args = parser.parse_args()
    signal.signal(signal.SIGINT, signal_handler)
    try:
        print("Initializing Interview Notification Bot...")
        bot = InterviewNotificationBot()
        if args.mode == 'test':
            print("Running in test mode...")
            if args.test_phone:
                print(f"Sending test message to {args.test_phone}")
                success, result = bot.whatsapp_sender.send_test_message(args.test_phone)
                if success:
                    print("Test message sent successfully!")
                else:
                    print(f"Test failed: {result}")
            else:
                print("All tests passed!")
        elif args.mode == 'once':
            print("Running once...")
            bot.monitor_sheet_changes()
        elif args.mode == 'continuous':
            print("Running continuously...")
            bot.run_continuous_monitoring()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()