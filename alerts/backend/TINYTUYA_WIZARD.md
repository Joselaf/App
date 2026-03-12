# TinyTuya Wizard Integration Guide

This backend can use the TinyTuya wizard to discover and configure Tuya devices. This is especially useful when:
- Your Tuya Cloud API quota is exhausted (like the current trial edition limit)
- You want to use local device discovery instead of cloud polling
- You need to set up device local keys for offline control

## Quick Start

### 1. Run the TinyTuya Wizard (Interactive)

This must be done once to create `devices.json`:

```bash
cd backend
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
python -m tinytuya wizard
```

The wizard will:
- Ask for your Tuya Cloud credentials (API key/secret)
- Discover devices in your account
- Obtain local device keys
- Save everything to `devices.json`

### 2. Trigger Device Scan from Backend

Once `devices.json` exists, you can scan for devices on the local network:

```bash
# Via API endpoint
curl -X POST http://localhost:8000/api/wizard/scan

# Or from Python
from app.tinytuya_integration import fetch_devices_json
result = fetch_devices_json()
print(result)
```

The scan will:
- Discover Tuya devices on your local network
- Poll their status
- Return device info as JSON
- Save the snapshot to `snapshot.json`

### 3. View Wizard Setup Instructions

Check the backend setup endpoint:

```bash
curl http://localhost:8000/api/wizard/setup
```

## File Structure

After running the wizard:

```
backend/
├── devices.json          # Device configuration (from wizard)
├── snapshot.json         # Current device status (from scan)
└── data/
    ├── state.json        # Alert history and subscriptions
    └── detection_profile.json  # Detection rules
```

## Advantages Over Cloud API

Local device discovery (via wizard) offers:
- **No quota limits** - Works even when trial edition is exhausted
- **Faster responses** - Direct local network communication
- **Privacy** - Devices discovered locally, not via cloud relay
- **Reliability** - Works even if Tuya Cloud is slow/down

## Integration with Backend

### Current Cloud API (Tuya Cloud)
- Uses `tinytuya.Cloud()` client
- Requires valid cloud credentials and quota
- Currently fails with code 28841004 (quota exhausted)
- Endpoint: `/api/dashboard`

### New Local Discovery (Wizard + Scan)
- Uses `python -m tinytuya devices` command
- No cloud quota required
- Works with `devices.json` from wizard
- Endpoints: `/api/wizard/setup`, `/api/wizard/scan`

## Next Steps

To fully integrate local discovery into device monitoring:

1. Run the wizard to generate `devices.json`
2. Update `TuyaCloudGateway` to fall back to local scan when cloud fails
3. Or create a separate `TuyaLocalGateway` for local-only monitoring
4. Store the local device keys and use them for direct device control

## Troubleshooting

### "devices.json not found"
Run the wizard first: `python -m tinytuya wizard`

### "No devices found in scan"
- Ensure devices are powered on and connected to your network
- Check firewall rules allow UDP broadcast
- Run with verbose: `python -m tinytuya devices -debug`

### "Error from Tuya Cloud: Code 28841004"
This means your Tuya Cloud trial quota is exhausted. Use local device scan instead:
```bash
python -m tinytuya devices -yes -no-poll  # Local scan only, no cloud access
```

The `-no-poll` flag disables cloud polling and only uses local discovery.
