from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from .config import Settings
from .models import AlertEvent


def _normalize_whatsapp_address(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return normalized
    if normalized.startswith("whatsapp:"):
        return normalized
    return f"whatsapp:{normalized}"


def _normalize_evolution_number(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith("whatsapp:"):
        normalized = normalized.removeprefix("whatsapp:")
    return normalized.lstrip("+")


def _format_alert_body(event: AlertEvent) -> str:
    return (
        "Alert from Tuya monitor\n"
        f"Type: {event.event_type}\n"
        f"Severity: {event.severity}\n"
        f"Status: {event.status}\n"
        f"Device: {event.device_name} ({event.device_id})\n"
        f"Title: {event.title}\n"
        f"Message: {event.message}\n"
        f"Time: {event.timestamp}"
    )


async def send_whatsapp_notifications(recipients: Iterable[str], event: AlertEvent, settings: Settings) -> None:
    provider = settings.whatsapp_provider.strip().lower()
    if provider in {"", "webhook"}:
        await _send_via_webhook(recipients, event, settings)
        return
    if provider == "twilio":
        await _send_via_twilio(recipients, event, settings)
        return
    raise RuntimeError(
        f"Unsupported WHATSAPP_PROVIDER '{settings.whatsapp_provider}'. Use 'webhook' or 'twilio'."
    )


async def _send_via_webhook(recipients: Iterable[str], event: AlertEvent, settings: Settings) -> None:
    webhook_url = settings.whatsapp_webhook_url.strip()
    if not webhook_url:
        raise RuntimeError(
            "WhatsApp webhook mode is enabled, but WHATSAPP_WEBHOOK_URL is missing."
        )

    normalized_recipients = [address.strip() for address in recipients if address.strip()]
    if not normalized_recipients:
        raise RuntimeError(
            "WHATSAPP_TO_NUMBERS is empty. Add at least one destination number."
        )

    headers: dict[str, str] = {"Content-Type": "application/json"}
    auth_token = settings.whatsapp_webhook_auth_token.strip()
    if auth_token:
        auth_header = settings.whatsapp_webhook_auth_header.strip() or "Authorization"
        headers[auth_header] = auth_token

    async with httpx.AsyncClient(timeout=20.0) as client:
        if "/message/sendText/" in webhook_url:
            text = _format_alert_body(event)
            for recipient in normalized_recipients:
                response = await client.post(
                    webhook_url,
                    json={
                        "number": _normalize_evolution_number(recipient),
                        "text": text,
                    },
                    headers=headers,
                )
                response.raise_for_status()
            return

        payload: dict[str, Any] = {
            "channel": "whatsapp",
            "to": normalized_recipients,
            "title": event.title,
            "message": _format_alert_body(event),
            "event": {
                "id": event.id,
                "eventType": event.event_type,
                "severity": event.severity,
                "status": event.status,
                "deviceId": event.device_id,
                "deviceName": event.device_name,
                "timestamp": event.timestamp,
                "metadata": event.metadata,
            },
        }
        response = await client.post(webhook_url, json=payload, headers=headers)
        response.raise_for_status()


async def _send_via_twilio(recipients: Iterable[str], event: AlertEvent, settings: Settings) -> None:
    from_address = _normalize_whatsapp_address(settings.twilio_whatsapp_from)
    account_sid = settings.twilio_account_sid.strip()
    auth_token = settings.twilio_auth_token.strip()

    if not from_address or not account_sid or not auth_token:
        raise RuntimeError(
            "WhatsApp delivery is enabled, but Twilio credentials are incomplete. "
            "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM."
        )

    normalized_recipients = [_normalize_whatsapp_address(address) for address in recipients if address.strip()]
    if not normalized_recipients:
        return

    body = _format_alert_body(event)
    api_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

    async with httpx.AsyncClient(timeout=20.0) as client:
        for to_address in normalized_recipients:
            response = await client.post(
                api_url,
                data={
                    "From": from_address,
                    "To": to_address,
                    "Body": body,
                },
                auth=(account_sid, auth_token),
            )
            response.raise_for_status()
