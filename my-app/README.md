# Tuya Safety Monitor App

This project includes:

- An Expo mobile app that displays safety alerts.
- A Python `tinytuya` monitor service that polls Tuya Cloud and exposes alert data.

The app alerts for:

- Low or dead battery.
- Circuit breaker tripped.
- Panic/SOS button activated.
- Fire/smoke alarm activated.

## Architecture

- `backend/main.py`: Polls Tuya Cloud, evaluates alert conditions, and exposes `/health` + `/alerts`.
- `app/(tabs)/index.tsx`: Polls backend API every 10 seconds and shows alert cards.

## 1) Mobile App Setup

1. Install Node dependencies:

   ```bash
   npm install
   ```

2. Create app env file:

   ```bash
   copy .env.example .env
   ```

3. Set API URL in `.env`:

   - Emulator/simulator: `http://127.0.0.1:8000`
   - Physical phone: `http://<your-computer-lan-ip>:8000`

4. Start Expo:

   ```bash
   npx expo start
   ```

## 2) Backend Setup (tinytuya)

1. Open a second terminal.

2. Create Python venv and install dependencies:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```

3. Create backend env file:

   ```bash
   copy backend\.env.example backend\.env
   ```

4. Fill in Tuya credentials in `backend/.env`:

   - `TUYA_API_REGION`
   - `TUYA_API_KEY`
   - `TUYA_API_SECRET`
   - `TUYA_API_DEVICE_ID`
   - Optional: `TUYA_DEVICE_IDS` (comma-separated, only used when `TUYA_ONLY_SELECTED_DEVICES=true`)

   Default behavior is to monitor all devices in your Tuya project.

5. Start API:

   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

## 3) Optional Device Rule Tuning

If your devices use different Tuya status codes:

1. Copy `backend/device_rules.example.json` to `backend/device_rules.json`.
2. Edit code/value mappings per device type.
3. Set `TUYA_RULES_FILE=backend/device_rules.json` in `backend/.env`.

## API Endpoints

- `GET /health`: Monitor connectivity and last error.
- `GET /alerts`: Recent deduplicated alert events.

## Notes

- The monitor uses polling (`TUYA_POLL_INTERVAL_SECONDS`) for real-time updates; default is now 5 seconds.
- App polls backend every 3 seconds for near-real-time alert visibility.
- Device monitoring shows all Tuya devices being checked.
- Alert matching is code/value based and may require rule tuning for your specific devices.
