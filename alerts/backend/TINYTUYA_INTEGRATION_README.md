# TinyTuya Wizard Integration - Implementation Summary

## What's New

The app now has a complete TinyTuya wizard integration to fetch devices and status. This enables device discovery through the TinyTuya command-line wizard, especially useful when Tuya Cloud API quota is exhausted.

## New Modules

### `backend/app/tinytuya_integration.py`
Provides programmatic access to TinyTuya CLI commands:
- `run_wizard()` - Launch interactive setup wizard
- `scan_local_devices()` - Scan local network using `python -m tinytuya devices`
- `get_devices_status_json()` - Read cached device status from snapshot file
- `fetch_devices_json()` - Combined scan + JSON output (main entry point)

## New API Endpoints

### `GET /api/wizard/setup`
Returns setup instructions and wizard command.

**Response:**
```json
{
  "status": "ready",
  "instructions": "Run the TinyTuya wizard interactively...",
  "command": "python -m tinytuya wizard",
  "next_step": "After running the wizard, call /api/wizard/scan..."
}
```

### `POST /api/wizard/scan`
Triggers a local network device scan using TinyTuya.
Returns device list and status as JSON.

**Response:**
```json
{
  "devices": [
    {
      "id": "device_id_1",
      "name": "Device Name",
      "status": {...}
    }
  ],
  "timestamp": "2026-03-12T10:30:00.000000"
}
```

## Usage Flow

### Step 1: Initialize with Wizard (One-time)
```bash
cd backend
python -m tinytuya wizard
# Follow prompts to authenticate and discover devices
# Creates: devices.json
```

### Step 2: Scan Devices via API
```bash
curl -X POST http://localhost:8000/api/wizard/scan
```

Or from the app:
```python
import requests
response = requests.post('http://backend:8000/api/wizard/scan')
devices = response.json()
```

### Step 3: Use Results in App
The backend can use `devices.json` and `snapshot.json` to:
- Display discovered devices
- Monitor local device status
- Cache device info without cloud quota

## Key Features

✓ **No Cloud Quota Needed** - Local network discovery works independently  
✓ **Unified Interface** - Same TinyTuya commands via API or CLI  
✓ **Fallback Support** - Can be used alongside or instead of cloud API  
✓ **Device Caching** - Snapshot files persist device status locally  
✓ **Easy Setup** - Interactive wizard handles authentication and discovery  

## Files Modified

- `backend/app/tinytuya_integration.py` - NEW: TinyTuya integration module
- `backend/app/main.py` - Added `/api/wizard/*` endpoints
- `backend/TINYTUYA_WIZARD.md` - NEW: Detailed guide with troubleshooting

## Current Status

| Feature | Status |
|---------|--------|
| Module imports | ✅ Working |
| setup endpoint | ✅ Working |
| scan endpoint | ✅ Working (requires devices.json) |
| Local device discovery | ✅ Ready |
| Cloud API fallback | ⏸️ Current (quota exhausted) |

## Next Steps (Optional)

To automate local device monitoring:

1. Update `TuyaCloudGateway` to try cloud first, fall back to local scan
2. Add periodic scan scheduling to refresh device status
3. Integrate `snapshot.json` results into dashboard
4. Create local device control endpoint using device local keys from wizard

See `TINYTUYA_WIZARD.md` for full integration guide.
