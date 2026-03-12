from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from .models import AlertEvent, AlertEventType, AlertSeverity

ACTIVE_STRINGS = {"1", "alarm", "true", "warn", "warning", "panic", "sos", "trip", "tripped", "open"}
INACTIVE_STRINGS = {"0", "false", "normal", "ok", "clear", "idle", "closed"}

BATTERY_LEVEL_CODES = {
    "battery_percentage",
    "battery_level",
    "battery",
    "va_battery",
    "battery_value",
    "battery_capacity",
}
BATTERY_STATE_CODES = {
    "battery_state",
    "battery_status",
    "battery_alarm",
    "battery_warning",
    "low_battery",
    "battery_low",
}
LOW_BATTERY_STRINGS = {"low", "lower", "warn", "warning", "under_voltage", "needs_charge", "need_charge"}
DEAD_BATTERY_STRINGS = {"critical", "dead", "empty", "shutdown", "exhausted", "no_power"}

BREAKER_CODE_TOKENS = {
    "trip",
    "breaker",
    "circuit",
    "over_current",
    "overload",
    "overvoltage",
    "undervoltage",
    "fault",
    "leakage",
}
FIRE_CODE_TOKENS = {
    "smoke",
    "fire",
    "co_alarm",
    "combustible",
    "gas_alarm",
}
PANIC_CODE_TOKENS = {
    "panic",
    "sos",
    "emergency",
    "help",
    "alarm_key",
}


ProfileRule = dict[str, Any]


def _normalize(value: Any) -> str:
    return str(value).strip().lower()


def _is_active(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    normalized = _normalize(value)
    if normalized in INACTIVE_STRINGS:
        return False
    return normalized in ACTIVE_STRINGS


def _parse_numeric(value: Any) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _find_numeric(status_map: Mapping[str, Any], keys: set[str]) -> int | None:
    for code, value in status_map.items():
        if code in keys:
            parsed = _parse_numeric(value)
            if parsed is not None:
                return parsed
    return None


def _code_matches_any_token(code: str, tokens: set[str]) -> bool:
    normalized_code = code.lower()
    return any(token in normalized_code for token in tokens)


def load_detection_profile(profile_path: Path) -> list[ProfileRule]:
    if not profile_path.exists():
        return []

    try:
        payload_raw = json.loads(profile_path.read_text())
        payload = cast(dict[str, Any], payload_raw)
    except (OSError, json.JSONDecodeError):
        return []

    rules_raw = payload.get("event_rules", [])
    rules = cast(list[Any], rules_raw)
    
    validated: list[ProfileRule] = []
    for rule_raw in rules:
        rule = cast(dict[str, Any], rule_raw) if isinstance(rule_raw, dict) else {}
        if not rule:
            continue
        if not isinstance(rule.get("eventType"), str):
            continue
        if not isinstance(rule.get("severity"), str):
            continue
        if not isinstance(rule.get("code"), str):
            continue
        validated.append(rule)

    return validated


def _matches_profile_rule(
    rule: ProfileRule,
    category: str,
    normalized_code: str,
    normalized_value: str,
    raw_value: Any,
) -> bool:
    if rule.get("enabled", True) is False:
        return False

    categories = rule.get("categories")
    if isinstance(categories, list):
        categories_list = cast(list[Any], categories)
        normalized_categories = {str(item).strip().lower() for item in categories_list}
        if category.lower() not in normalized_categories:
            return False

    if normalized_code != str(rule.get("code")).strip().lower():
        return False

    value_in = rule.get("value_in")
    if isinstance(value_in, list):
        value_in_list = cast(list[Any], value_in)
        allowed_values = {str(item).strip().lower() for item in value_in_list}
        if normalized_value not in allowed_values:
            return False

    value_bool = rule.get("value_bool")
    if isinstance(value_bool, bool) and bool(raw_value) is not value_bool:
        return False

    value_gt = rule.get("value_gt")
    if value_gt is not None:
        numeric = _parse_numeric(raw_value)
        if numeric is None or numeric <= int(value_gt):
            return False

    return True


def _events_from_profile(
    rules: list[ProfileRule],
    device_id: str,
    device_name: str,
    category: str,
    status_map: Mapping[str, Any],
) -> list[AlertEvent]:
    events: list[AlertEvent] = []

    for code, value in status_map.items():
        normalized_code = str(code).strip().lower()
        normalized_value = _normalize(value)

        for rule in rules:
            if not _matches_profile_rule(rule, category, normalized_code, normalized_value, value):
                continue

            try:
                event_type = AlertEventType(str(rule["eventType"]))
                severity = AlertSeverity(str(rule["severity"]))
            except ValueError:
                continue

            title = str(rule.get("title") or event_type.value.replace("_", " ").title())
            message_template = str(rule.get("message") or "{device_name} triggered an alert.")
            message = message_template.format(device_name=device_name, code=code, value=value)

            events.append(
                AlertEvent(
                    eventType=event_type,
                    severity=severity,
                    title=title,
                    message=message,
                    deviceId=device_id,
                    deviceName=device_name,
                    metadata={"code": code, "value": value, "source": "profile"},
                )
            )

    return events


def detect_events(
    device: Mapping[str, Any],
    status_map: Mapping[str, Any],
    profile_rules: list[ProfileRule] | None = None,
) -> list[AlertEvent]:
    device_id = str(device.get("id") or device.get("dev_id") or "unknown-device")
    device_name = str(device.get("name") or device_id)
    category = str(device.get("category") or "")
    events: list[AlertEvent] = []

    if profile_rules:
        events.extend(_events_from_profile(profile_rules, device_id, device_name, category, status_map))

    numeric_battery = _find_numeric(status_map, BATTERY_LEVEL_CODES)

    for code, value in status_map.items():
        normalized_code = code.lower()
        normalized_value = _normalize(value)
        numeric_value = _parse_numeric(value)

        # Smart lock payloads often expose battery warnings through alarm_lock.
        if normalized_code == "alarm_lock" and normalized_value == "low_battery":
            events.append(
                AlertEvent(
                    eventType=AlertEventType.LOW_BATTERY,
                    severity=AlertSeverity.WARNING,
                    title="Low battery",
                    message=f"{device_name} battery is low.",
                    deviceId=device_id,
                    deviceName=device_name,
                    metadata={"code": code, "value": value},
                )
            )
            continue

        # Smart locks can publish emergency alarms using hijack.
        if normalized_code == "hijack" and _is_active(value):
            events.append(
                AlertEvent(
                    eventType=AlertEventType.PANIC_BUTTON,
                    severity=AlertSeverity.CRITICAL,
                    title="Panic button activated",
                    message=f"{device_name} triggered a hijack/emergency alarm.",
                    deviceId=device_id,
                    deviceName=device_name,
                    metadata={"code": code, "value": value},
                )
            )
            continue

        if normalized_code in BATTERY_STATE_CODES or normalized_code in BATTERY_LEVEL_CODES:
            if (numeric_battery is not None and numeric_battery <= 5) or normalized_value in DEAD_BATTERY_STRINGS:
                events.append(
                    AlertEvent(
                        eventType=AlertEventType.DEAD_BATTERY,
                        severity=AlertSeverity.CRITICAL,
                        title="Dead battery",
                        message=f"{device_name} reports a dead or exhausted battery.",
                        deviceId=device_id,
                        deviceName=device_name,
                        metadata={"code": code, "value": value},
                    )
                )
                continue

            if (numeric_battery is not None and numeric_battery <= 20) or normalized_value in LOW_BATTERY_STRINGS:
                events.append(
                    AlertEvent(
                        eventType=AlertEventType.LOW_BATTERY,
                        severity=AlertSeverity.WARNING,
                        title="Low battery",
                        message=f"{device_name} battery is low.",
                        deviceId=device_id,
                        deviceName=device_name,
                        metadata={"code": code, "value": value},
                    )
                )
                continue

        # DLQ breakers commonly expose trip/fault through the fault datapoint.
        if category == "dlq" and normalized_code == "fault" and numeric_value is not None and numeric_value > 0:
            events.append(
                AlertEvent(
                    eventType=AlertEventType.BREAKER_TRIPPED,
                    severity=AlertSeverity.CRITICAL,
                    title="Circuit breaker tripped",
                    message=f"{device_name} reports a breaker fault ({numeric_value}).",
                    deviceId=device_id,
                    deviceName=device_name,
                    metadata={"code": code, "value": value},
                )
            )
            continue

        if _code_matches_any_token(normalized_code, BREAKER_CODE_TOKENS) and _is_active(value):
            events.append(
                AlertEvent(
                    eventType=AlertEventType.BREAKER_TRIPPED,
                    severity=AlertSeverity.CRITICAL,
                    title="Circuit breaker tripped",
                    message=f"{device_name} indicates a breaker trip.",
                    deviceId=device_id,
                    deviceName=device_name,
                    metadata={"code": code, "value": value},
                )
            )
            continue

        if _code_matches_any_token(normalized_code, FIRE_CODE_TOKENS) and _is_active(value):
            events.append(
                AlertEvent(
                    eventType=AlertEventType.FIRE_ALARM,
                    severity=AlertSeverity.CRITICAL,
                    title="Fire alarm triggered",
                    message=f"{device_name} is reporting a fire or smoke alarm.",
                    deviceId=device_id,
                    deviceName=device_name,
                    metadata={"code": code, "value": value},
                )
            )
            continue

        if _code_matches_any_token(normalized_code, PANIC_CODE_TOKENS) and _is_active(value):
            events.append(
                AlertEvent(
                    eventType=AlertEventType.PANIC_BUTTON,
                    severity=AlertSeverity.CRITICAL,
                    title="Panic button activated",
                    message=f"{device_name} triggered an emergency or panic action.",
                    deviceId=device_id,
                    deviceName=device_name,
                    metadata={"code": code, "value": value},
                )
            )

    deduped: dict[tuple[str, str], AlertEvent] = {}
    for event in events:
        deduped[(event.device_id, event.event_type)] = event

    return list(deduped.values())