from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import tinytuya
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

load_dotenv()


class AlertEvent(BaseModel):
    id: str
    kind: str
    severity: str
    device_id: str
    device_name: str
    message: str
    code: str
    value: Any
    timestamp: str


class MonitorState:
    def __init__(self) -> None:
        self.alerts: list[AlertEvent] = []
        self.last_poll: str | None = None
        self.last_error: str | None = None
        self.connected: bool = False
        self._seen_alerts: set[str] = set()
        self.devices: list[dict[str, Any]] = []
        self._lock = threading.Lock()


state = MonitorState()
app = FastAPI(title="Tuya Monitor API", version="1.0.0")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def env_bool(name: str, fallback: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return fallback
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_rules() -> dict[str, Any]:
    rules_file = os.getenv("TUYA_RULES_FILE", "backend/device_rules.json")
    rules_path = Path(rules_file)
    if rules_path.exists():
        with rules_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    # Fall back to built-in defaults matching device_rules.example.json.
    return {
        "battery": {
            "percentage_threshold": 20,
            "dead_percentage_threshold": 5,
            "code_candidates": [
                "battery_percentage",
                "battery",
                "va_battery",
                "residual_electricity",
                "battery_value",
            ],
            "state_candidates": ["battery_state", "battery_status"],
            "low_values": ["low", "warning"],
            "dead_values": ["dead", "critical", "empty"],
        },
        "breaker": {
            "code_candidates": ["trip", "breaker", "relay_status", "alarm_state"],
            "tripped_values": ["trip", "tripped", "open", False, 1],
        },
        "panic": {
            "code_candidates": ["sos", "panic", "emergency_alarm"],
            "active_values": [True, "1", 1, "on", "alarm"],
        },
        "fire": {
            "code_candidates": ["smoke_sensor_state", "smoke_alarm", "fire_alarm", "smoke_state"],
            "active_values": [True, "1", 1, "alarm", "detected", "warning"],
        },
    }


def stringify(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    return str(value).strip().lower()


def parse_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def find_status(statuses: list[dict[str, Any]], code_candidates: list[str]) -> tuple[str, Any] | None:
    wanted = {c.lower() for c in code_candidates}
    for item in statuses:
        code = str(item.get("code", "")).lower()
        if code in wanted:
            return code, item.get("value")
    return None


def build_alert(
    kind: str,
    severity: str,
    device_id: str,
    device_name: str,
    code: str,
    value: Any,
    message: str,
) -> AlertEvent:
    timestamp = utc_now_iso()
    fingerprint = f"{kind}:{severity}:{device_id}:{code}:{stringify(value)}"
    return AlertEvent(
        id=f"{fingerprint}:{timestamp}",
        kind=kind,
        severity=severity,
        device_id=device_id,
        device_name=device_name,
        message=message,
        code=code,
        value=value,
        timestamp=timestamp,
    )


def evaluate_device(device: dict[str, Any], statuses: list[dict[str, Any]], rules: dict[str, Any]) -> list[AlertEvent]:
    device_id = str(device.get("id", "unknown"))
    device_name = str(device.get("name", device_id))
    alerts: list[AlertEvent] = []

    battery_rules = rules.get("battery", {})
    percentage = find_status(statuses, battery_rules.get("code_candidates", []))
    battery_state = find_status(statuses, battery_rules.get("state_candidates", []))

    if percentage:
        code, value = percentage
        number = parse_number(value)
        if number is not None:
            dead_threshold = float(battery_rules.get("dead_percentage_threshold", 5))
            low_threshold = float(battery_rules.get("percentage_threshold", 20))
            if number <= dead_threshold:
                alerts.append(
                    build_alert(
                        kind="battery",
                        severity="critical",
                        device_id=device_id,
                        device_name=device_name,
                        code=code,
                        value=value,
                        message=f"Bateria sem carga — {device_name} ({number:.0f}%)",
                    )
                )
            elif number <= low_threshold:
                alerts.append(
                    build_alert(
                        kind="battery",
                        severity="warning",
                        device_id=device_id,
                        device_name=device_name,
                        code=code,
                        value=value,
                        message=f"Bateria fraca — {device_name} ({number:.0f}%)",
                    )
                )

    if battery_state:
        code, value = battery_state
        low_values = {stringify(v) for v in battery_rules.get("low_values", [])}
        dead_values = {stringify(v) for v in battery_rules.get("dead_values", [])}
        normalized = stringify(value)
        if normalized in dead_values:
            alerts.append(
                build_alert(
                    kind="battery",
                    severity="critical",
                    device_id=device_id,
                    device_name=device_name,
                    code=code,
                    value=value,
                    message=f"Bateria sem carga — {device_name}",
                )
            )
        elif normalized in low_values:
            alerts.append(
                build_alert(
                    kind="battery",
                    severity="warning",
                    device_id=device_id,
                    device_name=device_name,
                    code=code,
                    value=value,
                    message=f"Bateria fraca — {device_name}",
                )
            )

    breaker_rules = rules.get("breaker", {})
    breaker = find_status(statuses, breaker_rules.get("code_candidates", []))
    if breaker:
        code, value = breaker
        tripped = {stringify(v) for v in breaker_rules.get("tripped_values", [])}
        if stringify(value) in tripped:
            alerts.append(
                build_alert(
                    kind="breaker",
                    severity="critical",
                    device_id=device_id,
                    device_name=device_name,
                    code=code,
                    value=value,
                    message=f"Disjuntor disparado — {device_name}",
                )
            )

    panic_rules = rules.get("panic", {})
    panic = find_status(statuses, panic_rules.get("code_candidates", []))
    if panic:
        code, value = panic
        active = {stringify(v) for v in panic_rules.get("active_values", [])}
        if stringify(value) in active:
            alerts.append(
                build_alert(
                    kind="panic",
                    severity="critical",
                    device_id=device_id,
                    device_name=device_name,
                    code=code,
                    value=value,
                    message=f"Botão de pânico acionado — {device_name}",
                )
            )

    fire_rules = rules.get("fire", {})
    fire = find_status(statuses, fire_rules.get("code_candidates", []))
    if fire:
        code, value = fire
        active = {stringify(v) for v in fire_rules.get("active_values", [])}
        if stringify(value) in active:
            alerts.append(
                build_alert(
                    kind="fire",
                    severity="critical",
                    device_id=device_id,
                    device_name=device_name,
                    code=code,
                    value=value,
                    message=f"Alarme de incêndio — {device_name}",
                )
            )

    return alerts


def build_cloud() -> tinytuya.Cloud:
    api_region = os.getenv("TUYA_API_REGION", "us")
    api_key = os.getenv("TUYA_API_KEY", "")
    api_secret = os.getenv("TUYA_API_SECRET", "")
    api_device_id = os.getenv("TUYA_API_DEVICE_ID", "")

    if not api_key or not api_secret or not api_device_id:
        raise RuntimeError(
            "Missing Tuya credentials. Set TUYA_API_KEY, TUYA_API_SECRET, and TUYA_API_DEVICE_ID."
        )

    return tinytuya.Cloud(
        apiRegion=api_region,
        apiKey=api_key,
        apiSecret=api_secret,
        apiDeviceID=api_device_id,
    )


def list_devices(cloud: tinytuya.Cloud) -> list[dict[str, Any]]:
    response = cloud.getdevices(verbose=False)

    if isinstance(response, list):
        devices = response
    elif isinstance(response, dict):
        if not response.get("success"):
            raise RuntimeError(f"Tuya getdevices API error: {response.get('msg', response)}")
        devices = response.get("result") or []
    else:
        raise RuntimeError(f"Unexpected getdevices response type: {type(response)}")

    if not isinstance(devices, list):
        return []

    # Default behavior is to monitor every device in the Tuya project.
    only_selected = env_bool("TUYA_ONLY_SELECTED_DEVICES", False)
    selected_ids = {
        item.strip()
        for item in os.getenv("TUYA_DEVICE_IDS", "").split(",")
        if item.strip()
    }

    if only_selected and selected_ids:
        return [d for d in devices if str(d.get("id", "")) in selected_ids]

    return devices


def poll_once(cloud: tinytuya.Cloud, rules: dict[str, Any]) -> None:
    devices = list_devices(cloud)
    new_events: list[AlertEvent] = []

    for device in devices:
        device_id = str(device.get("id", ""))
        if not device_id:
            continue

        response = cloud.getstatus(device_id)
        if not isinstance(response, dict) or not response.get("success"):
            continue

        statuses = response.get("result") or []
        if not isinstance(statuses, list):
            continue

        events = evaluate_device(device, statuses, rules)
        new_events.extend(events)

    with state._lock:
        for event in new_events:
            dedupe_key = f"{event.kind}:{event.device_id}:{event.code}:{stringify(event.value)}"
            if dedupe_key in state._seen_alerts:
                continue
            state._seen_alerts.add(dedupe_key)
            state.alerts.insert(0, event)

        # Keep memory bounded.
        state.alerts = state.alerts[:300]
        state.devices = [{"id": str(d.get("id", "")), "name": str(d.get("name", d.get("id", "")))} for d in devices]
        state.connected = True
        state.last_error = None
        state.last_poll = utc_now_iso()


def poll_loop() -> None:
    interval = max(3, int(os.getenv("TUYA_POLL_INTERVAL_SECONDS", "5")))
    rules = load_rules()

    while True:
        try:
            cloud = build_cloud()
            poll_once(cloud, rules)
        except Exception as exc:  # noqa: BLE001
            with state._lock:
                state.connected = False
                state.last_error = str(exc)
                state.last_poll = utc_now_iso()

        time.sleep(interval)


@app.on_event("startup")
def start_background_poll() -> None:
    thread = threading.Thread(target=poll_loop, daemon=True)
    thread.start()


@app.get("/health")
def health() -> dict[str, Any]:
    with state._lock:
        return {
            "ok": state.connected,
            "last_poll": state.last_poll,
            "last_error": state.last_error,
        }


@app.get("/alerts")
def alerts(limit: int = 100) -> dict[str, Any]:
    capped = max(1, min(limit, 300))
    with state._lock:
        return {
            "connected": state.connected,
            "last_poll": state.last_poll,
            "last_error": state.last_error,
            "count": min(len(state.alerts), capped),
            "alerts": [event.model_dump() for event in state.alerts[:capped]],
        }


@app.get("/devices")
def devices() -> dict[str, Any]:
    with state._lock:
        return {
            "connected": state.connected,
            "last_poll": state.last_poll,
            "device_count": len(state.devices),
            "devices": state.devices,
        }
