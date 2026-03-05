import flet as ft
import tinytuya
import paho.mqtt.client as mqtt
import threading
import time
import json

# --- Tuya Cloud Credentials ---
API_KEY    = "c8uhx3vs89grhea8mg7p"
API_SECRET = "7221603a3b754d8b89b30c8dc9114b0d"
API_REGION = "eu"  # us, eu, cn, in

# --- Alert Conditions ---
ALERT_CONDITIONS = {
    "battery_state":       (["low", "dead"],                              "🔋 Bateria Fraca/Morta"),
    "battery_percentage":  (lambda v: isinstance(v, int) and v <= 20,    "🔋 Bateria Baixa"),
    "tripping":            ([True],                                        "⚡ Disjuntor Disparado"),
    "panic_button":        ([True],                                        "🚨 Botão de Pânico"),
    "fire_alarm":          ([True],                                        "🔥 Alarme de Incêndio"),
    "smoke_sensor_state":  (["alarm"],                                     "🔥 Sensor de Fumaça"),
    "alarm_state":         (["alarm"],                                     "🚨 Alarme Ativo"),
}

MQTT_ENDPOINTS = {
    "eu": "mqtts://m1.tuyaeu.com:8883",
    "us": "mqtts://m1.tuyaus.com:8883",
    "cn": "mqtts://m1.tuyacn.com:8883",
    "in": "mqtts://m1.tuyain.com:8883",
}

MQTT_HOSTS = {
    "eu": "m1.tuyaeu.com",
    "us": "m1.tuyaus.com",
    "cn": "m1.tuyacn.com",
    "in": "m1.tuyain.com",
}

# --- Global State ---
active_alerts = {}   # device_id -> list of alert strings
device_names  = {}   # device_id -> name
page_ref      = None
alert_list_ref = None
empty_msg_ref  = None
last_update_ref = None

def check_alerts(device_id, dps):
    alerts = []
    name = device_names.get(device_id, device_id)
    for dp_key, (condition, label) in ALERT_CONDITIONS.items():
        if dp_key in dps:
            value = dps[dp_key]
            triggered = condition(value) if callable(condition) else value in condition
            if triggered:
                alerts.append(f"{label} — {name}")
    return alerts

def build_alert_card(device_id):
    alerts = active_alerts.get(device_id, [])
    name   = device_names.get(device_id, device_id)
    return ft.Container(
        key=device_id,
        content=ft.Column([
            ft.Text(f"🔴 {name}", size=15, weight=ft.FontWeight.BOLD, color="white"),
            *[ft.Text(f"  ⚠️ {a}", size=13, color="#FF6B6B") for a in alerts],
        ], spacing=4),
        bgcolor="#2a0000",
        border=ft.border.all(2, "#FF6B6B"),
        border_radius=10,
        padding=15,
        animate_opacity=300,
    )

def update_ui():
    if not page_ref or not alert_list_ref:
        return

    alert_list_ref.controls.clear()

    if not active_alerts:
        empty_msg_ref.visible = True
    else:
        empty_msg_ref.visible = False
        for device_id in active_alerts:
            alert_list_ref.controls.append(build_alert_card(device_id))

    last_update_ref.value = f"Última atualização: {time.strftime('%H:%M:%S')}"
    page_ref.update()

def on_mqtt_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        device_id = payload.get("devId") or payload.get("data", {}).get("devId")
        status    = payload.get("status") or payload.get("data", {}).get("properties", [])

        if not device_id or not status:
            return

        dps = {item["code"]: item["value"] for item in status if "code" in item}
        alerts = check_alerts(device_id, dps)

        if alerts:
            active_alerts[device_id] = alerts
        else:
            active_alerts.pop(device_id, None)

        update_ui()
    except Exception:
        pass

def connect_mqtt(access_token):
    client_id = f"tuyapy_{API_KEY}"
    username   = access_token
    password   = ""

    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    client.username_pw_set(username, password)
    client.tls_set()
    client.on_message = on_mqtt_message

    host = MQTT_HOSTS.get(API_REGION, "m1.tuyaeu.com")
    client.connect(host, 8883, keepalive=60)

    topic = f"tygateway/{API_KEY}/#"
    client.subscribe(topic)
    client.loop_forever()

def start_cloud():
    try:
        cloud = tinytuya.Cloud(
            apiRegion=API_REGION,
            apiKey=API_KEY,
            apiSecret=API_SECRET,
        )

        # Load initial device names
        devices = cloud.getdevices()
        for dev in devices:
            device_names[dev["id"]] = dev.get("name", dev["id"])

        # Load initial statuses
        for dev in devices:
            try:
                status = cloud.getstatus(dev["id"])
                dps = {item["code"]: item["value"] for item in status.get("result", [])}
                alerts = check_alerts(dev["id"], dps)
                if alerts:
                    active_alerts[dev["id"]] = alerts
            except Exception:
                pass

        update_ui()

        # Get MQTT credentials
        mqtt_config = cloud.getmqttconfig()
        access_token = mqtt_config.get("access_token", API_KEY)

        # Start MQTT listener
        threading.Thread(
            target=connect_mqtt,
            args=(access_token,),
            daemon=True
        ).start()

    except Exception as e:
        if active_alerts is not None:
            active_alerts["__error__"] = [f"Erro: {str(e)}"]
            update_ui()

def main(page: ft.Page):
    global page_ref, alert_list_ref, empty_msg_ref, last_update_ref

    page.title   = "Tuya Real-Time Monitor"
    page.bgcolor = "#1a1a2e"
    page.scroll  = ft.ScrollMode.AUTO
    page.padding = 20

    page_ref = page

    title = ft.Text(
        "🏠 Tuya Monitor — Tempo Real",
        size=24,
        weight=ft.FontWeight.BOLD,
        color="white"
    )

    last_update_ref = ft.Text(
        "A conectar ao Tuya Cloud...",
        size=12,
        color=ft.Colors.GREY_400
    )

    mqtt_badge = ft.Container(
        content=ft.Row([
            ft.Container(width=8, height=8, bgcolor="#2ecc71", border_radius=4),
            ft.Text("MQTT Ativo", size=11, color="#2ecc71"),
        ], spacing=5),
        bgcolor="#0a2a0a",
        border_radius=10,
        padding=ft.Padding(left=10, right=10, top=4, bottom=4),
    )

    empty_msg_ref = ft.Container(
        content=ft.Column([
            ft.Text("✅", size=48),
            ft.Text("Sem alertas ativos", size=18, weight=ft.FontWeight.BOLD, color="white"),
            ft.Text("Todos os dispositivos estão normais.", size=13, color=ft.Colors.GREY_400),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        padding=ft.Padding(left=0, right=0, top=80, bottom=0),
        visible=True,
    )

    alert_list_ref = ft.Column(spacing=10)

    page.add(
        title,
        ft.Row(
            [last_update_ref, mqtt_badge],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        ),
        ft.Divider(color=ft.Colors.GREY_800),
        ft.Text(
            "ALERTAS ATIVOS",
            size=13,
            color=ft.Colors.GREY_500,
            weight=ft.FontWeight.BOLD
        ),
        empty_msg_ref,
        alert_list_ref,
    )

    threading.Thread(target=start_cloud, daemon=True).start()

ft.run(main)