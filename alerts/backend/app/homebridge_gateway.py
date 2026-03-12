"""
Homebridge Tuya Web integration for device discovery and status.

Homebridge runs as a separate Node.js service exposing devices via HTTP API.
This module communicates with Homebridge to fetch device information.
"""

from __future__ import annotations

import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)


class HomebergeTuyaGateway:
    """Client for Homebridge Tuya Web plugin."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8581,
        pin: str = "",
        username: str = "",
        password: str = "",
        access_token: str = "",
    ) -> None:
        """
        Initialize Homebridge Tuya Web gateway.

        Args:
            host: Homebridge API host (default: localhost)
            port: Homebridge API port (default: 8581)
            pin: HomeKit accessory PIN if required (optional)
        """
        self.host = host
        self.port = port
        self.pin = pin
        self.base_url = f"http://{host}:{port}"
        self._last_error: str | None = None
        self._connected = False
        self._username = username
        self._password = password
        self._access_token = access_token
        self._client = httpx.Client(timeout=10.0)

    def _auth_headers(self) -> dict[str, str]:
        if self._access_token:
            return {"Authorization": f"Bearer {self._access_token}"}
        return {}

    def _authenticate(self) -> bool:
        if not self._username or not self._password:
            self._last_error = "Homebridge authentication required: set HOMEBRIDGE_USERNAME and HOMEBRIDGE_PASSWORD."
            return False

        try:
            response = self._client.post(
                f"{self.base_url}/api/auth/login",
                json={"username": self._username, "password": self._password},
            )
            if response.status_code != 201:
                self._last_error = f"Homebridge login failed: status {response.status_code}"
                return False

            payload: Any = response.json()
            if not isinstance(payload, dict):
                self._last_error = "Homebridge login failed: invalid response payload."
                return False

            token = payload.get("access_token")
            if not isinstance(token, str) or not token:
                self._last_error = "Homebridge login failed: access token missing in response."
                return False

            self._access_token = token
            self._last_error = None
            return True
        except Exception as error:
            self._last_error = f"Homebridge login failed: {str(error)}"
            return False

    def _request(self, method: str, path: str, json: Any = None, retry_on_401: bool = True) -> httpx.Response:
        response = self._client.request(
            method,
            f"{self.base_url}{path}",
            headers=self._auth_headers(),
            json=json,
        )

        if response.status_code == 401 and retry_on_401:
            if self._authenticate():
                return self._request(method, path, json=json, retry_on_401=False)

        return response

    @property
    def connected(self) -> bool:
        """Check if successfully connected to Homebridge."""
        return self._connected

    @property
    def last_error(self) -> str | None:
        """Get the last connection error if any."""
        return self._last_error

    def check_connection(self) -> bool:
        """
        Test connection to Homebridge API.

        Returns:
            True if Homebridge is reachable, False otherwise
        """
        try:
            response = self._request("GET", "/api/accessories")
            if response.status_code == 200:
                self._connected = True
                self._last_error = None
                logger.info("Connected to Homebridge at %s:%d", self.host, self.port)
                return True
            else:
                self._last_error = f"Homebridge API returned status {response.status_code}"
                self._connected = False
                return False
        except Exception as error:
            self._last_error = f"Failed to connect to Homebridge: {str(error)}"
            self._connected = False
            logger.warning(self._last_error)
            return False

    def get_accessories(self) -> list[dict[str, Any]]:
        """
        Fetch all accessories (devices) from Homebridge.

        Returns:
            List of accessory dictionaries with device info
        """
        if not self._connected:
            if not self.check_connection():
                return []

        try:
            response = self._request("GET", "/api/accessories")
            if response.status_code == 200:
                data: Any = response.json()
                if isinstance(data, dict):
                    accessories: list[dict[str, Any]] = data.get("accessories", [])
                else:
                    accessories = data if isinstance(data, list) else []
                logger.info("Fetched %d accessories from Homebridge", len(accessories))
                return accessories
            else:
                self._last_error = f"Failed to fetch accessories: {response.status_code}"
                return []
        except Exception as error:
            self._last_error = f"Error fetching accessories: {str(error)}"
            logger.warning(self._last_error)
            return []

    def get_characteristic(
        self, aid: int, iid: int
    ) -> dict[str, Any]:
        """
        Get a specific characteristic (property) of an accessory.

        Args:
            aid: Accessory ID
            iid: Instance ID

        Returns:
            Characteristic data
        """
        try:
            response = self._request("GET", f"/characteristics?id={aid}.{iid}")
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as error:
            logger.warning("Error fetching characteristic %d.%d: %s", aid, iid, error)
            return {}

    def set_characteristic(self, aid: int, iid: int, value: Any) -> bool:
        """
        Set a characteristic value (control a device).

        Args:
            aid: Accessory ID
            iid: Instance ID
            value: Value to set

        Returns:
            True if successful
        """
        try:
            response = self._request(
                "PUT",
                "/characteristics",
                json={"characteristics": [{"aid": aid, "iid": iid, "value": value}]},
            )
            return response.status_code == 200
        except Exception as error:
            logger.warning("Error setting characteristic %d.%d: %s", aid, iid, error)
            return False

    def get_homebridge_info(self) -> dict[str, Any]:
        """Get Homebridge instance information."""
        try:
            response = self._request("GET", "/api/accessories")
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as error:
            logger.warning("Error fetching Homebridge info: %s", error)
            return {}

    def convert_accessories_to_devices(
        self, accessories: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Convert Homebridge accessories format to Tuya device format for compatibility.

        Args:
            accessories: List of Homebridge accessory objects

        Returns:
            List of device dictionaries in Tuya format
        """
        devices = []

        for acc in accessories:
            if not isinstance(acc, dict):
                continue

            # Extract device info from Homebridge accessory
            device = {
                "id": acc.get("aid") or acc.get("UUID", ""),
                "name": acc.get("displayName", f"Device {acc.get('aid', '?')}"),
                "category": acc.get("category", "unknown"),
                "online": True,  # Homebridge reports online accessories
                "uuid": acc.get("UUID"),
                "services": acc.get("services", []),
            }

            if device["id"]:
                devices.append(device)

        return devices

    def close(self) -> None:
        """Close HTTP client connection."""
        self._client.close()
