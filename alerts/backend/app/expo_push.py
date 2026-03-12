from __future__ import annotations

from collections.abc import Iterable

import httpx

from .models import AlertEvent

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


async def send_push_notifications(tokens: Iterable[str], event: AlertEvent) -> None:
    messages = [
        {
            "to": token,
            "title": event.title,
            "body": event.message,
            "priority": "high",
            "sound": "default",
            "data": {
                "href": "/(tabs)/alerts",
                "eventType": event.event_type,
                "deviceId": event.device_id,
            },
        }
        for token in tokens
    ]

    if not messages:
        return

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(EXPO_PUSH_URL, json=messages)
        response.raise_for_status()