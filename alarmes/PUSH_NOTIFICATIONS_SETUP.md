# Push Notifications Setup Guide

This guide will help you set up Firebase Cloud Messaging (FCM) for push notifications in your Flutter app.

## 1. Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Create a project" or select an existing one
3. Enable Google Analytics if prompted
4. Choose your Google Analytics account

## 2. Add Firebase to Your Flutter App

### Android Setup
1. In Firebase Console, click the Android icon to add an Android app
2. Enter your package name: `com.example.alarmes`
3. Download the `google-services.json` file
4. Place it in `android/app/google-services.json`

### iOS Setup (Optional)
1. In Firebase Console, click the iOS icon to add an iOS app
2. Enter your bundle ID (check `ios/Runner.xcodeproj/project.pbxproj` for PRODUCT_BUNDLE_IDENTIFIER)
3. Download the `GoogleService-Info.plist` file
4. Place it in `ios/Runner/GoogleService-Info.plist`

## 3. Set Up Firebase Admin SDK for Python Backend

1. In Firebase Console, go to Project Settings > Service Accounts
2. Click "Generate new private key"
3. Download the JSON file
4. Rename it to `firebase-key.json` and place it in the `python_backend/` directory

## 4. Install Python Dependencies

Run this in the `python_backend/` directory:
```bash
pip install -r requirements.txt
```

## 5. Test the Setup

1. Start your Python backend: `python tuya_server.py`
2. Run your Flutter app: `flutter run`
3. The app should automatically register for push notifications
4. Trigger an alert on a Tuya device to test notifications

## Troubleshooting

- Make sure `firebase-key.json` is in the `python_backend/` directory
- Check that your device has internet connection for FCM
- For Android, ensure Google Play Services is up to date
- Check the console logs for any Firebase initialization errors