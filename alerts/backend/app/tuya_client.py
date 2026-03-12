from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import tinytuya

from .config import Settings


class TuyaCloudGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cloud = None
        self._last_error: str | None = None
        self._has_checked_connection = False
        if settings.tuya_configured:
            self._cloud = tinytuya.Cloud(
                apiRegion=settings.tuya_api_region,
                apiKey=settings.tuya_api_key,
                apiSecret=settings.tuya_api_secret,
                apiDeviceID=settings.tuya_api_device_id,
            )

    @property
    def enabled(self) -> bool:
        return self._cloud is not None

    @property
    def connected(self) -> bool:
        return self.enabled and self._has_checked_connection and self._last_error is None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def has_checked_connection(self) -> bool:
        return self._has_checked_connection

    def _get_error_message(self, response: Any) -> str | None:
        if not isinstance(response, Mapping):
            return None

        error = response.get("Error") or response.get("error")
        code = response.get("Err") or response.get("err") or response.get("code")
        payload = response.get("Payload") or response.get("payload") or response.get("msg")

        if error or payload:
            parts = [str(part).strip() for part in (error, code, payload) if part not in (None, "")]
            return ": ".join(parts) if parts else "Unknown Tuya Cloud error"

        success = response.get("success")
        if success is False:
            return str(payload or code or "Unknown Tuya Cloud error").strip()

        return None

    def _mark_result(self, response: Any) -> str | None:
        self._has_checked_connection = True
        error = self._get_error_message(response)
        self._last_error = error
        return error

    def list_devices(self) -> list[dict[str, Any]]:
        if not self._cloud:
            return []

        response = self._cloud.getdevices() or []
        if self._mark_result(response):
            return []
        if isinstance(response, list):
            return response
        if isinstance(response, Mapping) and isinstance(response.get("result"), list):
            return list(response["result"])
        return []

    def get_status_map(self, device_id: str) -> dict[str, Any]:
        if not self._cloud:
            return {}

        response = self._cloud.getstatus(device_id) or {}
        if self._mark_result(response):
            return {}
        result = response.get("result") if isinstance(response, Mapping) else None

        if isinstance(result, list):
            return {
                str(item.get("code", "")): item.get("value")
                for item in result
                if isinstance(item, Mapping) and item.get("code")
            }

        if isinstance(result, Mapping) and isinstance(result.get("status"), list):
            return {
                str(item.get("code", "")): item.get("value")
                for item in result["status"]
                if isinstance(item, Mapping) and item.get("code")
            }

        return {}