from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from typing import Any
from fastapi import FastAPI, HTTPException

from .config import get_settings
from .detection import detect_events, load_detection_profile
from .expo_push import send_push_notifications
from .tinytuya_integration import get_devices_status_json
from .models import (
    AlertEvent,
    AlertSeverity,
    AlertStatus,
    AlertEventType,
    DashboardResponse,
    HealthResponse,
    MonitoredDevice,
    SubscriptionRecord,
    SubscriptionRequest,
    SubscriptionResponse,
    TestNotificationRequest,
    TestWhatsAppRequest,
    utc_now_iso,
)
from .state import PersistentState
from .homebridge_gateway import HomebergeTuyaGateway
from .whatsapp import send_whatsapp_notifications

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
state = PersistentState(settings.state_file, settings.alert_history_limit)
state.load()
homebridge = None
if settings.homebridge_enabled:
    homebridge = HomebergeTuyaGateway(
        host=settings.homebridge_host,
        port=settings.homebridge_port,
        pin=settings.homebridge_pin,
        username=settings.homebridge_username,
        password=settings.homebridge_password,
        access_token=settings.homebridge_access_token,
    )
    homebridge.check_connection()
poll_lock = asyncio.Lock()
monitor_task: asyncio.Task[None] | None = None
detection_profile_rules = load_detection_profile(settings.detection_profile_file)

def _ensure_homebridge_checked() -> None:
    if homebridge:
        homebridge.check_connection()


def _extract_homebridge_status_map(device: dict[str, Any]) -> dict[str, Any]:
    status_map: dict[str, Any] = {}
    services = device.get("services")
    if not isinstance(services, list):
        return status_map

    for service in services:
        if not isinstance(service, dict):
            continue
        characteristics = service.get("characteristics")
        if not isinstance(characteristics, list):
            continue

        for characteristic in characteristics:
            if not isinstance(characteristic, dict):
                continue

            value = characteristic.get("value")
            name = str(
                characteristic.get("description")
                or characteristic.get("type")
                or ""
            ).strip().lower()

            if "battery level" in name:
                status_map["battery_percentage"] = value
            elif "battery" in name:
                status_map["battery_state"] = value
            elif "motion" in name:
                status_map["motion_detected"] = value
            elif "contact" in name:
                status_map["contact"] = value
            elif "smoke" in name:
                status_map["smoke_sensor_state"] = value
            elif "carbon monoxide" in name or "co detected" in name:
                status_map["co_alarm"] = value
            elif "leak" in name or "water" in name:
                status_map["water_leak"] = value
            elif name == "on":
                status_map["switch_1"] = value

    return status_map


def _get_devices_list() -> list[dict[str, Any]]:
    """Get devices from Homebridge, fallback to local TinyTuya if none found."""
    if not homebridge:
        return []

    try:
        accessories = homebridge.get_accessories()
        if accessories:
            devices = homebridge.convert_accessories_to_devices(accessories)
            logger.info("Using Homebridge device list (found %d devices)", len(devices))
            return devices
    except Exception as error:
        logger.warning("Homebridge device fetch failed: %s", error)

    # Fallback to local device scan if Homebridge has no accessories
    try:
        local_devices = get_devices_status_json()
        if local_devices:
            logger.info("Homebridge returned 0 devices, falling back to local TinyTuya scan (found %d devices)", len(local_devices))
            return [
                {
                    "id": device.get("id") or device.get("dev_id", ""),
                    "name": device.get("name", "Unknown"),
                    "category": device.get("category"),
                    "online": device.get("online", True),
                }
                for device in local_devices
                if isinstance(device, dict)
            ]
    except Exception as error:
        logger.warning("Local device scan fallback failed: %s", error)

    return []


def _fingerprint(event: AlertEvent) -> str:
    return f"{event.device_id}:{event.event_type}"


def _parse_iso_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _cooldown_seconds_for_event(event: AlertEvent) -> int:
    return settings.alert_cooldown_by_type_seconds.get(
        event.event_type.value,
        settings.alert_cooldown_seconds,
    )


def _is_event_in_cooldown(event: AlertEvent, now: datetime) -> bool:
    if event.status == AlertStatus.CLEARED and not settings.alert_cooldown_apply_to_cleared:
        return False

    fingerprint = _fingerprint(event)
    last_sent_at = _parse_iso_utc(state.last_sent_by_fingerprint.get(fingerprint))
    if not last_sent_at:
        return False

    cooldown_seconds = _cooldown_seconds_for_event(event)
    if cooldown_seconds <= 0:
        return False

    return (now - last_sent_at).total_seconds() < cooldown_seconds


async def poll_once() -> None:
    async with poll_lock:
        devices = _get_devices_list()
        if not devices and homebridge and homebridge.last_error:
            logger.warning("No devices available from Homebridge: %s", homebridge.last_error)
            return

        current_fingerprints: set[str] = set()
        device_snapshots: list[MonitoredDevice] = []
        new_events: list[AlertEvent] = []

        for device in devices:
            device_id = str(device.get("id") or device.get("dev_id") or "")
            if not device_id:
                continue

            status_map = _extract_homebridge_status_map(device)
            if settings.log_device_status:
                logger.info("Device %s status map: %s", device_id, status_map)
            detected = detect_events(device, status_map, detection_profile_rules)

            for event in detected:
                fingerprint = _fingerprint(event)
                current_fingerprints.add(fingerprint)
                if fingerprint not in state.active_fingerprints:
                    new_events.append(event)

            battery_level = next(
                (
                    int(value)
                    for key, value in status_map.items()
                    if key in {"battery_percentage", "battery_level", "battery", "va_battery"}
                    and isinstance(value, (int, float))
                ),
                None,
            )

            device_snapshots.append(
                MonitoredDevice(
                    id=device_id,
                    name=str(device.get("name") or device_id),
                    category=device.get("category"),
                    online=bool(device.get("online", True)),
                    batteryLevel=battery_level,
                    lastSeenAt=utc_now_iso(),
                    activeEvents=[event.event_type for event in detected],
                )
            )

        if settings.alert_send_clear_notifications:
            for fingerprint in state.active_fingerprints - current_fingerprints:
                device_id, event_type_value = fingerprint.split(":", 1)
                matching_device = next((device for device in device_snapshots if device.id == device_id), None)
                cleared_event = AlertEvent(
                    eventType=AlertEventType(event_type_value),
                    severity=AlertSeverity.INFO,
                    status=AlertStatus.CLEARED,
                    title="Alert cleared",
                    message=f"{matching_device.name if matching_device else device_id} returned to normal.",
                    deviceId=device_id,
                    deviceName=matching_device.name if matching_device else device_id,
                )
                new_events.append(cleared_event)

        now = datetime.now(timezone.utc)
        filtered_events: list[AlertEvent] = []
        for event in new_events:
            if _is_event_in_cooldown(event, now):
                logger.info("Suppressed event in cooldown: %s", _fingerprint(event))
                continue
            filtered_events.append(event)
            state.last_sent_by_fingerprint[_fingerprint(event)] = now.isoformat()

        state.devices = device_snapshots
        state.active_fingerprints = current_fingerprints
        state.last_poll_at = utc_now_iso()

        for event in filtered_events:
            state.add_alert(event)

        state.save()

    if settings.whatsapp_enabled and filtered_events:
        for event in filtered_events:
            try:
                await send_whatsapp_notifications(settings.whatsapp_to_numbers, event, settings)
            except Exception as error:
                logger.exception("Failed to send WhatsApp notification: %s", error)
    elif settings.expo_push_enabled and filtered_events:
        tokens = list(state.subscriptions.keys())
        for event in filtered_events:
            try:
                await send_push_notifications(tokens, event)
            except Exception as error:
                logger.exception("Failed to send Expo push notification: %s", error)


async def monitor_loop() -> None:
    while True:
        try:
            if homebridge:
                homebridge.check_connection()
            await poll_once()
        except Exception as error:
            logger.exception("Monitor loop failed: %s", error)
        await asyncio.sleep(settings.poll_interval_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global monitor_task

    if detection_profile_rules:
        logger.info("Loaded %s detection profile rules from %s", len(detection_profile_rules), settings.detection_profile_file)
    else:
        logger.info("No detection profile rules loaded from %s, using heuristics only", settings.detection_profile_file)

    if homebridge:
        logger.info(
            "Device source: Homebridge (%s:%s)",
            settings.homebridge_host,
            settings.homebridge_port,
        )
        logger.info("Starting device monitoring loop")
        monitor_task = asyncio.create_task(monitor_loop())
    else:
        logger.warning("Device monitoring disabled: Homebridge is not enabled")

    yield
    if monitor_task:
        monitor_task.cancel()


app = FastAPI(title="Tuya alerts backend", version="0.1.0", lifespan=lifespan)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    _ensure_homebridge_checked()
    connected = bool(homebridge and homebridge.connected)
    return HealthResponse(
        status="ok",
        monitorHealthy=connected,
        tuyaConfigured=settings.homebridge_enabled,
        tuyaConnected=connected,
        connectionError=homebridge.last_error if homebridge else "Homebridge is disabled.",
        lastPollAt=state.last_poll_at,
        subscriberCount=len(state.subscriptions),
    )


@app.get("/api/dashboard", response_model=DashboardResponse)
async def dashboard() -> DashboardResponse:
    _ensure_homebridge_checked()
    connected = bool(homebridge and homebridge.connected)
    return DashboardResponse(
        monitorHealthy=connected,
        tuyaConnected=connected,
        connectionError=homebridge.last_error if homebridge else "Homebridge is disabled.",
        lastPollAt=state.last_poll_at,
        devices=state.devices,
        recentAlerts=state.recent_alerts,
    )


@app.get("/api/homebridge/debug")
async def homebridge_debug() -> dict[str, Any]:
    if not settings.homebridge_enabled or not homebridge:
        return {
            "enabled": False,
            "connected": False,
            "error": "Homebridge is disabled.",
            "host": settings.homebridge_host,
            "port": settings.homebridge_port,
            "accessoryCount": 0,
            "accessories": [],
        }

    homebridge.check_connection()
    accessories = homebridge.get_accessories() if homebridge.connected else []

    return {
        "enabled": True,
        "connected": homebridge.connected,
        "error": homebridge.last_error,
        "host": settings.homebridge_host,
        "port": settings.homebridge_port,
        "accessoryCount": len(accessories),
        "accessories": accessories,
    }


@app.post("/api/subscriptions/register", response_model=SubscriptionResponse)
async def register_subscription(payload: SubscriptionRequest) -> SubscriptionResponse:
    record = SubscriptionRecord(
        expoPushToken=payload.expo_push_token,
        platform=payload.platform,
        appVersion=payload.app_version,
    )
    state.subscriptions[payload.expo_push_token] = record
    state.save()
    return SubscriptionResponse(registeredAt=record.registered_at)


@app.post("/api/notifications/test")
async def test_notification(payload: TestNotificationRequest) -> dict[str, bool]:
    if not settings.expo_push_enabled:
        raise HTTPException(status_code=400, detail="Expo push delivery is disabled.")

    event = AlertEvent(
        eventType=AlertEventType.PANIC_BUTTON,
        severity=AlertSeverity.CRITICAL,
        title="Test notification",
        message="This is a backend-generated test notification.",
        deviceId="test-device",
        deviceName="Test device",
    )
    await send_push_notifications([payload.expo_push_token], event)

    record = state.subscriptions.get(payload.expo_push_token)
    if record:
        record.last_test_at = utc_now_iso()
        state.save()

    return {"ok": True}


@app.post("/api/notifications/test-whatsapp")
async def test_whatsapp_notification(payload: TestWhatsAppRequest) -> dict[str, bool]:
    if not settings.whatsapp_enabled:
        raise HTTPException(status_code=400, detail="WhatsApp delivery is disabled.")

    event = AlertEvent(
        eventType=AlertEventType.PANIC_BUTTON,
        severity=AlertSeverity.CRITICAL,
        title="Test WhatsApp notification",
        message=payload.message or "This is a backend-generated WhatsApp test notification.",
        deviceId="test-device",
        deviceName="Test device",
    )
    try:
        await send_whatsapp_notifications(settings.whatsapp_to_numbers, event, settings)
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"ok": True}


@app.get("/api/wizard/setup")
async def wizard_setup() -> dict[str, str]:
    """Wizard endpoints are disabled when running in Homebridge-only mode."""
    return {
        "status": "disabled",
        "instructions": "TinyTuya wizard is disabled. This backend is configured to rely on Homebridge only.",
        "command": "",
        "next_step": "Configure and start Homebridge, then query /api/dashboard.",
    }


@app.post("/api/wizard/scan")
async def wizard_scan() -> dict[str, str]:
    """Wizard endpoints are disabled when running in Homebridge-only mode."""
    raise HTTPException(
        status_code=410,
        detail="TinyTuya local scanning is disabled. This backend relies on Homebridge only.",
    )