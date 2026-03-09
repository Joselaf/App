# Tuya Monitor - Android App

Android app that monitors Tuya smart home devices in real-time using Firebase Realtime Database.

## Architecture

- **Flutter App**: Android frontend that listens to Firebase Realtime Database for alerts
- **Python Backend**: Uses tinytuya to poll Tuya Cloud devices and writes alerts to Firebase
- **Communication**: Firebase Realtime Database for real-time data synchronization

## Setup Instructions

### 1. Firebase Setup

1. Create a Firebase project at https://console.firebase.google.com/
2. Enable Realtime Database in your Firebase project
3. Generate a service account key:
   - Go to Project Settings → Service Accounts
   - Click "Generate new private key"
   - Download the JSON file and rename it to `firebase-key.json`
   - Place it in the `python_backend/` directory
4. Update the database URL in `python_backend/tuya_server.py`:
   ```python
   'databaseURL': 'https://YOUR-PROJECT-ID-default-rtdb.firebaseio.com/'
   ```
5. Add your Android app to Firebase project and download `google-services.json` to `android/app/`

### 2. Install Python Backend

```bash
cd python_backend
pip install -r requirements.txt
pip install firebase-admin
```

### 3. Test Firebase Connection

```bash
cd python_backend
python test_firebase.py
```

### 4. Start Python Backend

```bash
python tuya_server.py
```

The backend will poll Tuya devices every 30 seconds and update Firebase.

### 5. Run Flutter App

```bash
flutter pub get
flutter run
```

## Building APK

```bash
flutter build apk --release
```

The APK will be in `build/app/outputs/flutter-apk/app-release.apk`

## Network Configuration

### For Real Device Testing

1. Make sure your computer and Android device are on the same WiFi network
2. Find your computer's IP address:
   - Windows: `ipconfig` (look for IPv4 Address)
   - Mac/Linux: `ifconfig` or `ip addr`
3. Update the `backendUrl` in `lib/services/tuya_service.dart`
4. Make sure your firewall allows connections on port 5000

### For Android Emulator

The emulator uses `10.0.2.2` to access the host machine's localhost.

## Troubleshooting

**"Falha ao conectar ao Firebase"**
- Check if `firebase-key.json` exists in `python_backend/`
- Verify the database URL is correct in `tuya_server.py`
- Run `python test_firebase.py` to test connectivity
- Make sure Realtime Database is enabled in Firebase console

**No alerts showing**
- Check Python backend console for errors
- Verify Tuya credentials are correct in `tuya_server.py`
- Check if devices are online in Tuya app
- Verify Firebase database has data (check Firebase console)

**Push notifications not working**
- Make sure `google-services.json` is in `android/app/`
- Check Firebase Cloud Messaging is enabled
- Verify device permissions for notifications

**App shows "Desconectado"**
- Check Firebase Realtime Database rules allow read access
- Verify internet connection on device
- Check Firebase console for connection errors
