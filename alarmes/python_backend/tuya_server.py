import flet as ft
import tinytuya
import paho.mqtt.client as mqtt
import threading
import time
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, messaging

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
mqtt_connected = False
mqtt_config = {}
mqtt_client = None  # Store MQTT config for API
device_tokens = set()  # Store FCM device tokens

app = Flask(__name__)
CORS(app)

# Initialize Firebase Admin SDK
# Note: You need to download your Firebase service account key and place it as 'firebase-key.json'
try:
    cred = credentials.Certificate('firebase-key.json')
    firebase_admin.initialize_app(cred)
    print("Firebase initialized successfully")
except Exception as e:
    print(f"Firebase initialization failed: {e}")
    print("Make sure to add your Firebase service account key as 'firebase-key.json'")

def publish_alerts():
    global mqtt_client, active_alerts, last_update
    if mqtt_client and mqtt_connected:
        payload = json.dumps({
            "alerts": list(active_alerts.values()),
            "last_update": last_update
        })
        mqtt_client.publish(f"tuya/alerts/{API_KEY}", payload, qos=1)
        print(f"Published alerts: {len(active_alerts)} alerts")

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

def on_mqtt_message(client, userdata, msg):
    global last_update, active_alerts
    try:
        payload = json.loads(msg.payload.decode())
        device_id = payload.get("devId") or payload.get("data", {}).get("devId")
        status    = payload.get("status") or payload.get("data", {}).get("properties", [])
        
        if not device_id or not status:
            return
        
        dps = {item["code"]: item["value"] for item in status if "code" in item}
        alerts = check_alerts(device_id, dps)
        
        device_name = device_names.get(device_id, device_id)
        had_alerts_before = device_id in active_alerts
        
        if alerts:
            active_alerts[device_id] = {
                "device_id": device_id,
                "device_name": device_name,
                "alerts": alerts
            }
            # Send push notification for new alerts
            if not had_alerts_before:
                send_push_notifications(
                    "🚨 Alerta de Dispositivo",
                    f"{device_name}: {alerts[0]}"  # Send first alert as notification
                )
        else:
            active_alerts.pop(device_id, None)
        
        last_update = time.strftime('%H:%M:%S')
        publish_alerts()
    except Exception as e:
        print(f"Error processing message: {e}")

def connect_mqtt(config):
    """Connect to Tuya MQTT using the exact configuration returned by tinytuya.

    `config` should be the dictionary returned by `cloud.getmqttconfig()` (or
    equivalent).  This avoids rebuilding the credentials manually and ensures
    we use the values Tuya expects.
    """
    global mqtt_connected, mqtt_config, mqtt_client
    mqtt_config = config  # keep a copy for the HTTP API

    print("connect_mqtt called with config:", config)

    client_id = config.get("client_id")
    host = config.get("host")
    port = config.get("port", 1883)
    username = config.get("username")
    password = config.get("password")

    mqtt_client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    mqtt_client.username_pw_set(username, password)
    # only enable TLS if port is 8883
    if port == 8883:
        mqtt_client.tls_set()
    mqtt_client.on_message = on_mqtt_message

    def on_connect(client, userdata, flags, rc):
        global mqtt_connected
        mqtt_connected = (rc == 0)
        if mqtt_connected:
            print("MQTT Connected")
        else:
            print(f"Failed to connect, rc={rc}")

    mqtt_client.on_connect = on_connect

    mqtt_client.connect(host, port, keepalive=60)

    topic = config.get("subscribe_topic", f"tygateway/{API_KEY}/#")
    mqtt_client.subscribe(topic)
    mqtt_client.loop_forever()

def start_cloud():
    global last_update
    try:
        cloud = tinytuya.Cloud(
            apiRegion=API_REGION,
            apiKey=API_KEY,
            apiSecret=API_SECRET,
        )
        
        print("Connecting to Tuya Cloud...")
        
        # Load initial device names
        devices = cloud.getdevices()
        print(f"Found {len(devices)} devices")
        
        for dev in devices:
            device_names[dev["id"]] = dev.get("name", dev["id"])
            print(f"Device: {dev.get('name', dev['id'])} (ID: {dev['id']})")
        
        # Load initial statuses
        for dev in devices:
            try:
                status = cloud.getstatus(dev["id"])
                print(f"\nDevice {dev.get('name', dev['id'])} status:")
                print(f"  Raw status: {status}")
                
                dps = {item["code"]: item["value"] for item in status.get("result", [])}
                print(f"  Parsed DPS: {dps}")
                
                alerts = check_alerts(dev["id"], dps)
                if alerts:
                    print(f"  ALERTS: {alerts}")
                    active_alerts[dev["id"]] = {
                        "device_id": dev["id"],
                        "device_name": device_names.get(dev["id"], dev["id"]),
                        "alerts": alerts
                    }
                else:
                    print(f"  No alerts")
            except Exception as e:
                print(f"Error loading status for {dev['id']}: {e}")
        
        last_update = time.strftime('%H:%M:%S')
        publish_alerts()
        
        # Try to get MQTT credentials/config from the cloud API
        try:
            if hasattr(cloud, 'getmqttconfig'):
                mqtt_cfg = cloud.getmqttconfig()
                print("\nMQTT configuration from Tuya:", mqtt_cfg)
            else:
                # Fallback: build a minimal config using the cloud token
                mqtt_cfg = {
                    "host": MQTT_HOSTS.get(API_REGION, "m1.tuyaeu.com"),
                    "port": 8883,
                    "client_id": f"tuyapy_{API_KEY}",
                    "username": cloud.token,
                    "password": cloud.token,
                    "api_key": API_KEY,
                }
                print("\nUsing fallback MQTT config (no getmqttconfig available)")

            # write config to file for inspection
            try:
                with open("mqtt_debug.json", "w") as f:
                    json.dump(mqtt_cfg, f)
                print("Wrote mqtt_config to mqtt_debug.json")
            except Exception as e:
                print("Failed to write mqtt_debug.json:", e)

            # Start MQTT listener using the config dictionary
            print("Invoking connect_mqtt directly for debug – program will block here.")
            # call synchronously so we can see the connection log immediately
            connect_mqtt(mqtt_cfg)
            # after connect_mqtt returns (unlikely), exit to avoid fetching devices
            import sys
            sys.exit(0)
        except Exception as e:
            print(f"MQTT setup error: {e}")
            print("Continuing without MQTT (will only show initial status)")
        
    except Exception as e:
        print(f"Error starting cloud: {e}")
        import traceback
        traceback.print_exc()
        active_alerts["__error__"] = {
            "device_id": "__error__",
            "device_name": "Erro",
            "alerts": [f"Erro: {str(e)}"]
        }

@app.route('/api/mqtt_config', methods=['GET'])
def get_mqtt_config():
    return jsonify(mqtt_config)

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    return jsonify({
        "alerts": list(active_alerts.values()),
        "last_update": last_update,
        "mqtt_connected": mqtt_connected
    })

@app.route('/api/register_token', methods=['POST'])
def register_token():
    global device_tokens
    try:
        data = request.get_json()
        token = data.get('token')
        if token:
            device_tokens.add(token)
            print(f"Registered device token: {token[:20]}...")
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "No token provided"}), 400
    except Exception as e:
        print(f"Error registering token: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Start Tuya Cloud connection in background
    threading.Thread(target=start_cloud, daemon=True).start()
    
    # Give it a moment to initialize
    time.sleep(2)
    
    # Start Flask server
    print("Starting Flask server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
