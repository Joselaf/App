#!/usr/bin/env python3
"""
Test script to verify Firebase Realtime Database connectivity
"""
import os
import firebase_admin
from firebase_admin import credentials, db
import json

def test_firebase():
    try:
        # Initialize Firebase (same as in tuya_server.py)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        firebase_key_path = os.path.join(base_dir, 'firebase-key.json')
        cred = credentials.Certificate(firebase_key_path)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://alarmes-7adaa-default-rtdb.europe-west1.firebasedatabase.app/'  # UPDATE THIS!
        })
        print("✅ Firebase initialized successfully")

        # Test writing to database
        ref = db.reference('test')
        test_data = {
            'timestamp': 'test',
            'message': 'Firebase connection test'
        }
        ref.set(test_data)
        print("✅ Test data written to Firebase")

        # Test reading from database
        snapshot = ref.get()
        if snapshot:
            print(f"✅ Test data read from Firebase: {snapshot}")
        else:
            print("❌ No data read from Firebase")

        # Clean up test data
        ref.delete()
        print("✅ Test data cleaned up")

        print("\n🎉 Firebase connectivity test PASSED!")
        print("You can now run the main server: python tuya_server.py")

    except Exception as e:
        print(f"❌ Firebase test FAILED: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure 'firebase-key.json' exists in this directory")
        print("2. Update the databaseURL with your actual Firebase project URL")
        print("3. Check that your Firebase project has Realtime Database enabled")

if __name__ == '__main__':
    test_firebase()