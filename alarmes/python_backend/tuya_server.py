import flet as ft
import tinytuya
import paho.mqtt.client as mqtt
import threading
import time
import json
from flask import Flask, jsonify
from flask_cors import CORS

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

app = Flask(__name__)
CORS(app)

def publish_alerts():
    global mqtt_client, active_alerts, last_update
    if mqtt_client and mqtt_connected:
        payload = json.dumps({
            "alerts": list(active_alerts.values()),
            "last_update": last_update
        })
        mqtt_client.publish(f"tuya/alerts/{API_KEY}", payload, qos=1)
        print(f"Published alerts: {len(active_alerts)} alerts")
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
        
        if alerts:
            active_alerts[device_id] = {
                "device_id": device_id,
                "device_name": device_names.get(device_id, device_id),
                "alerts": alerts
            }
        else:
            active_alerts.pop(device_id, None)
        
        last_update = time.strftime('%H:%M:%S')
        publish_alerts()
    except Exception as e:
        print(f"Error processing message: {e}")

def connect_mqtt(access_token):
    global mqtt_connected, mqtt_config, mqtt_client
    client_id = f"tuyapy_{API_KEY}"
    username   = access_token
    password   = ""
    
    # Store config for API
    mqtt_config = {
        "host": MQTT_HOSTS.get(API_REGION, "m1.tuyaeu.com"),
        "port": 8883,
        "client_id": client_id,
        "username": username,
        "password": password,
        "api_key": API_KEY
    }
    
    mqtt_client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    mqtt_client.username_pw_set(username, password)
    mqtt_client.tls_set()
    mqtt_client.on_message = on_mqtt_message
    
    def on_connect(client, userdata, flags, rc):
        global mqtt_connected
        mqtt_connected = (rc == 0)
        if mqtt_connected:
            print("MQTT Connected")
    
    mqtt_client.on_connect = on_connect
    
    host = mqtt_config["host"]
    mqtt_client.connect(host, 8883, keepalive=60)
    
    topic = f"tygateway/{API_KEY}/#"
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
        
        # Try to get MQTT credentials - use token if method doesn't exist
        try:
            if hasattr(cloud, 'getmqttconfig'):
                mqtt_config = cloud.getmqttconfig()
                access_token = mqtt_config.get("access_token", cloud.token)
            else:
                # Use the cloud token directly
                access_token = cloud.token
            
            print(f"\nStarting MQTT with token: {access_token[:20]}...")
            # Start MQTT listener
            threading.Thread(target=connect_mqtt, args=(access_token,), daemon=True).start()
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

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "mqtt_connected": mqtt_connected,
        "device_count": len(device_names),
        "alert_count": len(active_alerts)
    })

if __name__ == '__main__':
    # Start Tuya Cloud connection in background
    threading.Thread(target=start_cloud, daemon=True).start()
    
    # Give it a moment to initialize
    time.sleep(2)
    
    # Start Flask server
    print("Starting Flask server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
