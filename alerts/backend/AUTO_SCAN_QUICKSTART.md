# Automatic TinyTuya Device Scanning - Quick Start

The backend now **automatically scans for TinyTuya devices** without manual intervention after you run the wizard once.

## One-time Setup

### Step 1: Run the TinyTuya Wizard
```bash
cd /home/luisj/App/alerts/backend
python -m tinytuya wizard
```

This interactive wizard will:
- Ask for Tuya Cloud credentials
- Discover all your devices
- Save device configuration to `devices.json`

### Step 2: Restart the Backend
```bash
# Backend will now automatically:
# 1. Print setup status on startup
# 2. Start a monitoring loop
# 3. Scan for local devices every ~50 seconds (5 × 10s poll interval)
# 4. Fall back to local scanning when cloud API quota is exhausted
```

## What Happens Automatically

✅ **On Backend Startup:**
```
TinyTuya Local Device Scanning Setup
======================================================================
Setup complete! Local device scanning is active
======================================================================
```

✅ **Every ~50 Seconds:**
- Automatically scans the local network for devices
- Updates device status cache
- Detects battery, breaker, fire, and panic events

✅ **When Cloud API Fails:**
- Automatically falls back to local device scanning
- No manual intervention needed
- Shows connection errors in `/api/dashboard`

## Testing the Setup

### Check Setup Status
```bash
curl http://localhost:8000/api/wizard/setup
```

### View Discovered Devices
```bash
curl http://localhost:8000/api/dashboard
```

### View Connection Status
```bash
curl http://localhost:8000/api/health
```

## File Structure After Setup

```
backend/
├── devices.json          # ← Created by wizard (one-time)
├── snapshot.json         # ← Auto-updated by scanner
└── app/
    ├── main.py          # Auto-starts monitoring loop
    ├── setup.py         # Prints setup instructions
    └── tinytuya_integration.py  # Handles scanning
```

## Troubleshooting

### "devices.json not found"
→ Run the wizard: `python -m tinytuya wizard`

### "No devices found"
- Ensure devices are powered on & connected to network
- Check firewall allows UDP broadcasts
- Verify devices were created in Tuya wizard

### Backend errors with Tuya Cloud
→ Expected when trial quota exhausted (error 28841004)
→ Local scanning will still work automatically

## Features Enabled

| Feature | Status |
|---------|--------|
| Cloud API (Tuya Cloud) | ⏸️ Disabled (quota exhausted) |
| Local Device Scanning | ✅ Automatic |
| Event Detection | ✅ Automatic |
| Background Monitoring | ✅ Automatic |
| Setup Instructions | ✅ Auto-printed |

## Next Steps

1. **Run the wizard** (one-time): `python -m tinytuya wizard`
2. **Restart the backend** - it will auto-start scanning
3. **Check the dashboard** - http://backend:8000/api/dashboard
4. Monitor logs for device discovery

No more manual commands needed after wizard completes!
