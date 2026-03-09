#!/usr/bin/env python3
"""
Test script to send a test push notification
"""
import firebase_admin
from firebase_admin import credentials, messaging
import json

def send_test_notification():
    try:
        # Initialize Firebase
        cred = credentials.Certificate('firebase-key.json')
        firebase_admin.initialize_app(cred)

        # Test message
        message = messaging.Message(
            notification=messaging.Notification(
                title="🧪 Test Notification",
                body="Push notifications are working!",
            ),
            topic="test_notifications",  # Send to test topic
        )

        # Send message
        response = messaging.send(message)
        print(f"✅ Test notification sent successfully!")
        print(f"Message ID: {response}")

    except Exception as e:
        print(f"❌ Error sending test notification: {e}")

if __name__ == "__main__":
    send_test_notification()