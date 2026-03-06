# Tuya Monitor - Android App

Android app that monitors Tuya smart home devices in real-time using tinytuya Python backend.

## Architecture

- **Flutter App**: Android frontend that displays alerts
- **Python Backend**: Uses tinytuya to connect to Tuya Cloud and MQTT
- **Communication**: Flutter app polls Python backend via REST API

## Setup Instructions

### 1. Install Python Backend

```bash
cd python_backend
pip install -r requirements.txt
```

### 2. Start Python Backend

```bash
python tuya_server.py
```

The server will start on `http://0.0.0.0:5000`

### 3. Configure Flutter App

Edit `lib/services/tuya_service.dart` and set the correct backend URL:

- **Android Emulator**: `http://10.0.2.2:5000`
- **Real Android Device**: `http://YOUR_COMPUTER_IP:5000` (find your IP with `ipconfig` on Windows or `ifconfig` on Mac/Linux)
- **Local Testing**: `http://localhost:5000`

### 4. Run Flutter App

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

**"Não foi possível conectar ao servidor Python"**
- Check if Python backend is running
- Verify the backend URL is correct
- Check firewall settings
- Ensure devices are on same network (for real device)

**No alerts showing**
- Check Python backend console for errors
- Verify Tuya credentials are correct
- Check if devices are online in Tuya app
