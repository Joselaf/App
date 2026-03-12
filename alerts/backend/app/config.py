from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class Settings:
    tuya_api_key: str
    tuya_api_secret: str
    tuya_api_region: str
    tuya_api_device_id: str
    poll_interval_seconds: int
    state_file: Path
    detection_profile_file: Path
    alert_history_limit: int
    alert_send_clear_notifications: bool
    alert_cooldown_seconds: int
    alert_cooldown_by_type_seconds: dict[str, int]
    alert_cooldown_apply_to_cleared: bool
    expo_push_enabled: bool
    whatsapp_enabled: bool
    whatsapp_provider: str
    whatsapp_to_numbers: list[str]
    whatsapp_webhook_url: str
    whatsapp_webhook_auth_header: str
    whatsapp_webhook_auth_token: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_whatsapp_from: str
    log_device_status: bool
    homebridge_enabled: bool
    homebridge_host: str
    homebridge_port: int
    homebridge_pin: str
    homebridge_username: str
    homebridge_password: str
    homebridge_access_token: str

    @property
    def tuya_configured(self) -> bool:
        return all(
            [
                self.tuya_api_key,
                self.tuya_api_secret,
                self.tuya_api_region,
                self.tuya_api_device_id,
            ]
        )


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int, minimum: int = 0) -> int:
    if value is None:
        return default
    try:
        return max(minimum, int(value))
    except ValueError:
        return default


def _as_event_cooldowns(value: str | None) -> dict[str, int]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}

    cooldowns: dict[str, int] = {}
    parsed_dict = cast(dict[str, Any], parsed)
    for key, raw_seconds in parsed_dict.items():
        try:
            seconds = max(0, int(raw_seconds))
        except (TypeError, ValueError):
            continue
        cooldowns[key] = seconds
    return cooldowns


def _as_csv_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def get_settings() -> Settings:
    state_file = Path(os.getenv("STATE_FILE", "./data/state.json")).expanduser()
    detection_profile_file = Path(os.getenv("DETECTION_PROFILE_FILE", "./data/detection_profile.json")).expanduser()

    return Settings(
        tuya_api_key=os.getenv("TUYA_API_KEY", "").strip(),
        tuya_api_secret=os.getenv("TUYA_API_SECRET", "").strip(),
        tuya_api_region=os.getenv("TUYA_API_REGION", "eu").strip(),
        tuya_api_device_id=os.getenv("TUYA_API_DEVICE_ID", "").strip(),
        poll_interval_seconds=_as_int(os.getenv("POLL_INTERVAL_SECONDS"), 10, minimum=5),
        state_file=state_file,
        detection_profile_file=detection_profile_file,
        alert_history_limit=_as_int(os.getenv("ALERT_HISTORY_LIMIT"), 200, minimum=10),
        alert_send_clear_notifications=_as_bool(
            os.getenv("ALERT_SEND_CLEAR_NOTIFICATIONS"),
            False,
        ),
        alert_cooldown_seconds=_as_int(os.getenv("ALERT_COOLDOWN_SECONDS"), 300, minimum=0),
        alert_cooldown_by_type_seconds=_as_event_cooldowns(os.getenv("ALERT_COOLDOWN_BY_TYPE_SECONDS")),
        alert_cooldown_apply_to_cleared=_as_bool(os.getenv("ALERT_COOLDOWN_APPLY_TO_CLEARED"), False),
        expo_push_enabled=_as_bool(os.getenv("EXPO_PUSH_ENABLED"), True),
        whatsapp_enabled=_as_bool(os.getenv("WHATSAPP_ENABLED"), False),
        whatsapp_provider=os.getenv("WHATSAPP_PROVIDER", "webhook").strip().lower(),
        whatsapp_to_numbers=_as_csv_list(os.getenv("WHATSAPP_TO_NUMBERS")),
        whatsapp_webhook_url=os.getenv("WHATSAPP_WEBHOOK_URL", "").strip(),
        whatsapp_webhook_auth_header=os.getenv("WHATSAPP_WEBHOOK_AUTH_HEADER", "Authorization").strip(),
        whatsapp_webhook_auth_token=os.getenv("WHATSAPP_WEBHOOK_AUTH_TOKEN", "").strip(),
        twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", "").strip(),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", "").strip(),
        twilio_whatsapp_from=os.getenv("TWILIO_WHATSAPP_FROM", "").strip(),
        log_device_status=_as_bool(os.getenv("LOG_DEVICE_STATUS"), False),
        homebridge_enabled=_as_bool(os.getenv("HOMEBRIDGE_ENABLED"), True),
        homebridge_host=os.getenv("HOMEBRIDGE_HOST", "localhost").strip(),
        homebridge_port=_as_int(os.getenv("HOMEBRIDGE_PORT"), 8581, minimum=1),
        homebridge_pin=os.getenv("HOMEBRIDGE_PIN", "").strip(),
        homebridge_username=os.getenv("HOMEBRIDGE_USERNAME", "").strip(),
        homebridge_password=os.getenv("HOMEBRIDGE_PASSWORD", "").strip(),
        homebridge_access_token=os.getenv("HOMEBRIDGE_ACCESS_TOKEN", "").strip(),
    )