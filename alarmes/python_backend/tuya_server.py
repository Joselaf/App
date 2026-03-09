import flet as ft
import tinytuya
import threading
import time
import json
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, messaging, db

# --- Tuya Cloud Credentials ---
API_KEY    = "c8uhx3vs89grhea8mg7p"
API_SECRET = "7221603a3b754d8b89b30c8dc9114b0d"
API_REGION = "eu"

# --- Alert Conditions ---
ALERT_CONDITIONS = {
    "battery_state":       (["low", "dead"],                              "🔋 Bateria Fraca/Morta"),
    "battery_percentage":  (lambda v: isinstance(v, int) and v <= 20,    "🔋 Bateria Baixa"),
    "tripping":            ([True],                                        "⚡ Disjuntor Disparado"),
    "fault":               (lambda v: v != 0,                              "⚠️ Falha no Dispositivo"),
    "panic_button":        ([True],                                        "� Botão de Pânico"),
    "fire_alarm":          ([True],                                        "�🔥 Alarme de Incêndio"),
    "smoke_sensor_state":  (["alarm"],                                     "🔥 Sensor de Fumaça"),
    "alarm_state":         (["alarm"],                                     "🚨 Alarme Ativo"),
    "alarm_lock":          (["pry", "key", "hijack"],                      "🚨 Tentativa de Arrombamento"),
    "hijack":              ([True],                                        "🚨 Sequestro Detectado"),
}

MQTT_HOSTS = {
    "eu": "m1.tuyaeu.com",
    "us": "m1.tuyaus.com",
    "cn": "m1.tuyacn.com",
    "in": "m1.tuyain.com",
}

# --- Global State ---
active_alerts = {}
device_names  = {}
last_update   = "Iniciando..."
device_tokens = set()  # Store FCM device tokens

app = Flask(__name__)
CORS(app)

# Initialize Firebase Admin SDK (optional)
firebase_initialized = False
try:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    firebase_key_path = os.path.join(base_dir, 'firebase-key.json')
    cred = credentials.Certificate(firebase_key_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://alarmes-7adaa-default-rtdb.europe-west1.firebasedatabase.app/'
    })
    firebase_initialized = True
    print("✅ Firebase initialized successfully")
except Exception as e:
    print(f"⚠️ Firebase initialization failed: {e}")
    print("Server will continue without Firebase - update firebase-key.json and databaseURL")
    firebase_initialized = False

def publish_alerts():
    """Publish alerts to Firebase Realtime Database (if available)"""
    if not firebase_initialized:
        print(f"📊 Local alerts updated: {len(active_alerts)} alerts (Firebase not configured)")
        return

    try:
        ref = db.reference('alerts')
        # Always send an object with timestamp, never empty dict (Firebase treats {} as null)
        if active_alerts:
            ref.set(active_alerts)
        else:
            # Send a special marker when no alerts
            ref.set({"_timestamp": time.strftime('%H:%M:%S'), "_no_alerts": True})
        print(f"📤 Published {len(active_alerts)} alerts to Firebase")
    except Exception as e:
        print(f"❌ Error publishing to Firebase: {e}")

def send_push_notifications(title, body):
    """Send push notifications to all registered devices"""
    if not device_tokens:
        print("No device tokens registered for push notifications")
        return

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        tokens=list(device_tokens),
    )

    try:
        response = messaging.send_multicast(message)
        print(f"Sent push notifications: {response.success_count} successful, {response.failure_count} failed")
        if response.failure_count > 0:
            print("Failures:", response.responses)
    except Exception as e:
        print(f"Error sending push notifications: {e}")

def check_alerts(device_id, dps):
    alerts = []
    name = device_names.get(device_id, device_id)
    
    # Check for battery_percentage first
    if "battery_percentage" in dps:
        battery_pct = dps["battery_percentage"]
        print(f"  Battery percentage found: {battery_pct}%")
        if isinstance(battery_pct, int) and battery_pct <= 20:
            alerts.append(f"🔋 Bateria Baixa ({battery_pct}%) — {name}")
    
    # Check all other conditions (skip battery_state and battery_percentage)
    for dp_key, (condition, label) in ALERT_CONDITIONS.items():
        # Skip battery checks - we only use battery_percentage now
        if dp_key in ["battery_state", "battery_percentage"]:
            continue
            
        if dp_key in dps:
            value = dps[dp_key]
            triggered = condition(value) if callable(condition) else value in condition
            if triggered:
                print(f"  ⚠️ ALERT TRIGGERED: {dp_key} = {value} -> {label}")
                alerts.append(f"{label} — {name}")
    
    return alerts

def start_cloud():
    global last_update
    try:
        print("🔗 Connecting to Tuya Cloud...")
        cloud = tinytuya.Cloud(
            apiRegion=API_REGION,
            apiKey=API_KEY,
            apiSecret=API_SECRET,
        )

        # Test authentication
        print("🔑 Testing Tuya authentication...")
        token = cloud.token
        if not token:
            raise Exception("No authentication token received - check API credentials")

        print("📋 Getting device list...")
        devices = cloud.getdevices()
        print(f"✅ Found {len(devices)} devices")

        if not devices:
            print("⚠️ No devices found in Tuya Cloud")
            print("Make sure devices are added to your Tuya Cloud project")
            return

        # Store device names
        for device in devices:
            device_names[device['id']] = device.get('name', device['id'])
            print(f"📱 Device: {device['name']} ({device['id']})")

        # Publish empty alerts to Firebase immediately so app can connect
        publish_alerts()
        global last_update
        last_update = time.strftime('%H:%M:%S')

        # Initial status check
        print("🔍 Performing initial device status check...")
        update_device_status(cloud, devices)

        # Poll devices for status
        print("🔄 Starting device polling every 30 seconds...")
        poll_count = 0
        while True:
            poll_count += 1
            print(f"\n📊 Poll #{poll_count} - {time.strftime('%H:%M:%S')}")
            try:
                update_device_status(cloud, devices)
            except Exception as e:
                print(f"❌ Error in polling cycle: {e}")

            time.sleep(5)  # Poll every 30 seconds

    except Exception as e:
        error_msg = f"Tuya Cloud connection failed: {str(e)}"
        print(f"❌ {error_msg}")
        active_alerts["__error__"] = {
            "device_id": "__error__",
            "device_name": "Erro de Conexão",
            "alerts": [error_msg]
        }
        publish_alerts()

def update_device_status(cloud, devices):
    """Poll all devices for their current status"""
    global last_update, active_alerts

    updated_count = 0
    error_count = 0

    for device in devices:
        try:
            device_id = device['id']
            device_name = device_names.get(device_id, device_id)

            # Get device status with timeout
            status = cloud.getstatus(device_id)
            if not status or 'result' not in status:
                print(f"⚠️ No status data for {device_name}")
                continue

            dps = {item["code"]: item["value"] for item in status["result"] if "code" in item}
            alerts = check_alerts(device_id, dps)

            had_alerts_before = device_id in active_alerts

            if alerts:
                active_alerts[device_id] = {
                    "device_id": device_id,
                    "device_name": device_name,
                    "alerts": alerts
                }
                if not had_alerts_before:
                    print(f"🚨 NEW ALERT: {device_name} - {alerts[0]}")
                    send_push_notifications(
                        "🚨 Alerta de Dispositivo",
                        f"{device_name}: {alerts[0]}"
                    )
                updated_count += 1
            else:
                if device_id in active_alerts:
                    print(f"✅ Alert cleared: {device_name}")
                active_alerts.pop(device_id, None)
                updated_count += 1

        except Exception as e:
            error_count += 1
            print(f"❌ Error updating device {device['id']}: {e}")

    last_update = time.strftime('%H:%M:%S')
    print(f"📈 Updated {updated_count} devices, {error_count} errors, {len(active_alerts)} active alerts")
    publish_alerts()

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    return jsonify({
        "alerts": list(active_alerts.values()),
        "last_update": last_update
    })

@app.route('/api/register_token', methods=['POST'])
def register_token():
    # This endpoint is kept for compatibility but tokens are handled by Firebase directly
    return jsonify({"status": "success", "message": "Tokens handled by Firebase"})

if __name__ == '__main__':
    # Start Tuya Cloud connection in background
    threading.Thread(target=start_cloud, daemon=True).start()
    
    # Give it a moment to initialize
    time.sleep(2)
    
    # Start Flask server
    print("Starting Flask server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
