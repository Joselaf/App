from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AlertEventType(StrEnum):
    LOW_BATTERY = "low_battery"
    DEAD_BATTERY = "dead_battery"
    BREAKER_TRIPPED = "breaker_tripped"
    FIRE_ALARM = "fire_alarm"
    PANIC_BUTTON = "panic_button"


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(StrEnum):
    ACTIVE = "active"
    CLEARED = "cleared"


class AlertEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=lambda: uuid4().hex)
    event_type: AlertEventType = Field(alias="eventType")
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.ACTIVE
    title: str
    message: str
    timestamp: str = Field(default_factory=utc_now_iso)
    device_id: str = Field(alias="deviceId")
    device_name: str = Field(alias="deviceName")
    metadata: dict[str, Any] = Field(default_factory=dict)


class MonitoredDevice(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    category: str | None = None
    online: bool = False
    battery_level: int | None = Field(default=None, alias="batteryLevel")
    last_seen_at: str | None = Field(default=None, alias="lastSeenAt")
    active_events: list[AlertEventType] = Field(default_factory=list, alias="activeEvents")


class DashboardResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    monitor_healthy: bool = Field(alias="monitorHealthy")
    tuya_connected: bool = Field(alias="tuyaConnected")
    connection_error: str | None = Field(default=None, alias="connectionError")
    last_poll_at: str | None = Field(default=None, alias="lastPollAt")
    devices: list[MonitoredDevice] = Field(default_factory=list)
    recent_alerts: list[AlertEvent] = Field(default_factory=list, alias="recentAlerts")


class SubscriptionRequest(BaseModel):
    expo_push_token: str = Field(alias="expoPushToken")
    platform: str = "expo"
    app_version: str | None = Field(default=None, alias="appVersion")


class SubscriptionRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    expo_push_token: str = Field(alias="expoPushToken")
    platform: str = "expo"
    app_version: str | None = Field(default=None, alias="appVersion")
    registered_at: str = Field(default_factory=utc_now_iso, alias="registeredAt")
    last_test_at: str | None = Field(default=None, alias="lastTestAt")


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ok: bool = True
    registered_at: str = Field(alias="registeredAt")


class TestNotificationRequest(BaseModel):
    expo_push_token: str = Field(alias="expoPushToken")


class TestWhatsAppRequest(BaseModel):
    message: str | None = None


class HealthResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    monitor_healthy: bool = Field(alias="monitorHealthy")
    tuya_configured: bool = Field(alias="tuyaConfigured")
    tuya_connected: bool = Field(alias="tuyaConnected")
    connection_error: str | None = Field(default=None, alias="connectionError")
    last_poll_at: str | None = Field(default=None, alias="lastPollAt")
    subscriber_count: int = Field(default=0, alias="subscriberCount")