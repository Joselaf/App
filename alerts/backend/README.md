# Tuya monitor backend

This service polls Tuya Cloud through TinyTuya, detects battery, breaker, fire, and panic events,
and sends notifications to WhatsApp.

Default WhatsApp delivery uses an open-source/self-hosted webhook gateway (for example Evolution API).
Twilio is optional fallback mode.

## Quick start

1. Create a Python 3.11+ virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your Tuya credentials.
4. Start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /api/health`
- `GET /api/dashboard`
- `GET /api/homebridge/debug`
- `POST /api/subscriptions/register`
- `POST /api/notifications/test`
- `POST /api/notifications/test-whatsapp`

## Notes

- The detector uses generic Tuya status-code heuristics. You will likely need to tune mappings for
  your exact device categories.
- Expo push requires real devices and valid Expo push tokens from the mobile app.
- WhatsApp delivery can use an open-source/self-hosted webhook gateway or Twilio.
- Deploy behind HTTPS before exposing it outside a trusted network.

## WhatsApp notifications (Open-source gateway)

Set the following environment variables:

- `WHATSAPP_ENABLED=true`
- `WHATSAPP_PROVIDER=webhook`
- `WHATSAPP_TO_NUMBERS=+15551234567,+15557654321` (comma-separated recipients)
- `WHATSAPP_WEBHOOK_URL=http://your-gateway/send`
- `WHATSAPP_WEBHOOK_AUTH_HEADER=Authorization` (optional)
- `WHATSAPP_WEBHOOK_AUTH_TOKEN=Bearer ...` (optional)

The backend posts JSON payloads to your gateway with these fields: `channel`, `to`, `title`, `message`, and `event`.

## WhatsApp notifications (Twilio, optional)

If you prefer Twilio, set:

- `WHATSAPP_PROVIDER=twilio`
- `TWILIO_ACCOUNT_SID=...`
- `TWILIO_AUTH_TOKEN=...`
- `TWILIO_WHATSAPP_FROM=whatsapp:+14155238886`

Then call the test endpoint:

```bash
curl -X POST http://127.0.0.1:8000/api/notifications/test-whatsapp \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello from alerts backend"}'
```

## Precision and noise control

The detector now uses stricter matching rules:

- Battery alerts are based on known battery status/value codes and thresholds.
- Breaker, fire, and panic alerts are matched against focused token sets to reduce false positives.

Use these environment variables to tune behavior:

- `ALERT_COOLDOWN_SECONDS`: default cooldown (in seconds) per `deviceId:eventType`.
- `ALERT_COOLDOWN_BY_TYPE_SECONDS`: optional JSON map for per-event cooldowns.
- `ALERT_COOLDOWN_APPLY_TO_CLEARED`: apply cooldown to clear notifications.
- `LOG_DEVICE_STATUS`: set to `true` to print raw Tuya status maps for rule tuning.
- `DETECTION_PROFILE_FILE`: JSON file with explicit per-category datapoint rules.

### Detection profile (config-only rules)

Default profile path: `./data/detection_profile.json`.

Each rule supports:

- `enabled`: true/false
- `eventType`: `low_battery`, `dead_battery`, `breaker_tripped`, `fire_alarm`, `panic_button`
- `severity`: `info`, `warning`, `critical`
- `categories`: optional category filter list (for example `ms`, `jtmspro`, `dlq`)
- `code`: exact status key
- `value_in`: optional list of accepted string values
- `value_bool`: optional boolean match
- `value_gt`: optional numeric greater-than match
- `title`, `message`: notification text template (`{device_name}`, `{code}`, `{value}`)

Profile rules are evaluated first; heuristic detection remains as fallback.

Example:

```env
ALERT_COOLDOWN_SECONDS=300
ALERT_COOLDOWN_BY_TYPE_SECONDS={"low_battery":21600,"dead_battery":3600,"breaker_tripped":120,"fire_alarm":30,"panic_button":30}
ALERT_COOLDOWN_APPLY_TO_CLEARED=false
LOG_DEVICE_STATUS=false
```

## Production checklist

1. Keep secrets only in runtime environment variables (`.env` on server, never in git).
2. Run behind HTTPS (Nginx/Caddy reverse proxy to Uvicorn on localhost).
3. Use a process manager (`systemd`, `supervisor`, or container restart policy).
4. Enable logs and rotate them (`journald`/`logrotate`).
5. Restrict network exposure with firewall rules to only required ports.
6. Set a stable `STATE_FILE` location on persistent disk.
7. Monitor `/api/health` with uptime checks.
8. Validate push delivery periodically with `/api/notifications/test`.