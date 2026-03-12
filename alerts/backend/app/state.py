from __future__ import annotations

import json
from pathlib import Path

from .models import AlertEvent, MonitoredDevice, SubscriptionRecord


class PersistentState:
    def __init__(self, path: Path, history_limit: int) -> None:
        self.path = path
        self.history_limit = history_limit
        self.subscriptions: dict[str, SubscriptionRecord] = {}
        self.recent_alerts: list[AlertEvent] = []
        self.active_fingerprints: set[str] = set()
        self.last_sent_by_fingerprint: dict[str, str] = {}
        self.devices: list[MonitoredDevice] = []
        self.last_poll_at: str | None = None

    def load(self) -> None:
        if not self.path.exists():
            return

        payload = json.loads(self.path.read_text())
        self.subscriptions = {
            token: SubscriptionRecord.model_validate(record)
            for token, record in payload.get("subscriptions", {}).items()
        }
        self.recent_alerts = [AlertEvent.model_validate(item) for item in payload.get("recent_alerts", [])]
        self.active_fingerprints = set(payload.get("active_fingerprints", []))
        self.last_sent_by_fingerprint = {
            str(fingerprint): str(timestamp)
            for fingerprint, timestamp in payload.get("last_sent_by_fingerprint", {}).items()
        }
        self.devices = [MonitoredDevice.model_validate(item) for item in payload.get("devices", [])]
        self.last_poll_at = payload.get("last_poll_at")

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "subscriptions": {
                token: record.model_dump(mode="json", by_alias=True)
                for token, record in self.subscriptions.items()
            },
            "recent_alerts": [item.model_dump(mode="json", by_alias=True) for item in self.recent_alerts[-self.history_limit :]],
            "active_fingerprints": sorted(self.active_fingerprints),
            "last_sent_by_fingerprint": self.last_sent_by_fingerprint,
            "devices": [device.model_dump(mode="json", by_alias=True) for device in self.devices],
            "last_poll_at": self.last_poll_at,
        }
        self.path.write_text(json.dumps(payload, indent=2))

    def add_alert(self, event: AlertEvent) -> None:
        self.recent_alerts.insert(0, event)
        self.recent_alerts = self.recent_alerts[: self.history_limit]