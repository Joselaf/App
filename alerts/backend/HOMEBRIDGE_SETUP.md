# Homebridge Tuya Web Integration Guide

The app backend now supports **Homebridge Tuya Web** as a device source. This is an alternative to direct Tuya Cloud API or local TinyTuya scanning.

## Quick Start

### 1. Install Homebridge (One-time)

**Linux/macOS:**
```bash
npm install -g homebridge homebridge-config-ui-x @milo526/homebridge-tuya-web
```

**Docker (Recommended):**
```bash
docker run -d \
  --name homebridge \
  -p 8581:8581 \
  -p 51826:51826 \
  -v homebridge-data:/homebridge \
  homebridge/homebridge:latest
```

### 2. Configure Homebridge Tuya Web

Extract and edit the Homebridge config:

```bash
# Copy the sample config
cp homebridge-config.json ~/.homebridge/config.json
# Or for Docker: cp homebridge-config.json /var/lib/docker/volumes/homebridge-data/_data/config.json
```

Edit with your Tuya Cloud credentials:
```json
{
  "platforms": [
    {
      "platform": "config",
      "name": "Config",
      "port": 8582,
      "auth": "none"
    },
    {
      "platform": "@milo526/homebridge-tuya-web.TuyaWebPlatform",
      "name": "TuyaWebPlatform",
      "options": {
        "username": "your-tuya-account",
        "password": "your-tuya-password",
        "countryCode": "351",
        "platform": "tuya",
        "pollingInterval": 60
      }
    }80
  ]
}
```

### 3. Configure Backend to Use Homebridge

Add environment variables to `.env`:
```bash
HOMEBRIDGE_ENABLED=true
HOMEBRIDGE_HOST=127.0.0.1
HOMEBRIDGE_PORT=8582
HOMEBRIDGE_PIN=031-45-154
```

### 4. Start Backend

The backend will automatically:
- ✅ Detect Homebridge connection
- ✅ Fetch devices from Homebridge
- ✅ Fall back to local TinyTuya if Homebridge unavailable
- ✅ Monitor and report device status

## Architecture

```
Tuya Cloud
    ↓
Homebridge (HTTP API)
    ↓
Python Backend
    ↓
Mobile App
```

## Device Source Priority

The backend tries to fetch devices in this order:

1. **Homebridge** (if enabled and connected)
2. **Tuya Cloud API** (if credentials configured)
3. **Local TinyTuya scan** (devices.json from wizard)

## Environment Variables

```env
# Enable Homebridge integration
HOMEBRIDGE_ENABLED=true

# Homebridge host (default: localhost)
HOMEBRIDGE_HOST=192.168.1.100

# Homebridge port (default: 8582)
HOMEBRIDGE_PORT=8582

# HomeKit PIN (optional)
HOMEBRIDGE_PIN=031-45-154
```

## Advantages of Homebridge

✅ **No API quota** - Unlimited device fetches  
✅ **HomeKit integration** - Control devices via Apple Home  
✅ **Web interface** - Built-in Homebridge UI  
✅ **Plugins** - Support for many smart home platforms  
✅ **Local first** - Devices on same network  
✅ **Private** - No cloud relay needed  

## Troubleshooting

### "Homebridge not found"
- Check if Homebridge is running: `curl http://127.0.0.1:8582/api/auth/settings`
- Check firewall allows port 8582
- Verify Homebridge is installed: `homebridge --version`

### "Connection refused"
- Ensure Homebridge is running
- Check HOMEBRIDGE_HOST and HOMEBRIDGE_PORT in .env

### "No devices found"
- Verify Tuya credentials in Homebridge config
- Check Homebridge logs for authentication errors
- Restart Homebridge after config changes

### Devices not updating
- Check pollingInterval in Homebridge config (set to 60+ seconds)
- Backend automatically checks Homebridge every 30 seconds
- Verify network connectivity between backend and Homebridge

## API Testing

```bash
# Check Homebridge auth settings
curl http://127.0.0.1:8582/api/auth/settings

# Get accessories (devices)
curl http://127.0.0.1:8582/api/accessories

# Backend will log device sources on startup
```

## Configuration Files

- `homebridge-config.json` - Sample Homebridge configuration
- `.env` - Backend environment variables with Homebridge settings

## Next Steps

1. Install Homebridge: `npm install -g homebridge`
2. Configure Tuya credentials in Homebridge config
3. Enable in backend: `HOMEBRIDGE_ENABLED=true`
4. Restart backend - it will auto-connect

See [README.md](README.md) in backend folder for full backend setup.
