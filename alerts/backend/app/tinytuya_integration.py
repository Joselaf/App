"""
TinyTuya integration module for device discovery and status fetching.

Provides programmatic access to TinyTuya device scanning and status polling.
The wizard must be run once interactively to set up devices.json.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)


def _normalize_device_items(raw_items: list[Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw in raw_items:
        if isinstance(raw, dict):
            items.append(cast(dict[str, Any], raw))
    return items


def run_wizard(devices_file: Path | str = "devices.json") -> bool:
    """
    Run the TinyTuya wizard interactively to discover and configure devices.
    This must be run once to generate the devices.json configuration file.

    Usage:
        python -m alerts.app.tinytuya_integration --wizard

    Or in the shell:
        python -m tinytuya wizard -device-file devices.json

    Args:
        devices_file: Path where wizard will save device configuration

    Returns:
        True if wizard completed successfully, False otherwise
    """
    try:
        import sys
        cmd = [sys.executable, "-m", "tinytuya", "wizard", "-device-file", str(devices_file)]
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except Exception as error:
        logger.error("Failed to run TinyTuya wizard: %s", error)
        return False


def scan_local_devices(
    max_time: int = 18,
    devices_file: Path | str = "devices.json",
    snapshot_file: Path | str = "snapshot.json",
) -> dict[str, Any]:
    """
    Scan the local network for Tuya devices and save their status to snapshot file.

    Uses 'python -m tinytuya devices' command which:
    - Scans the local network for devices
    - Looks up devices in devices.json
    - Polls their status and saves it to snapshot.json

    Args:
        max_time: Maximum time in seconds to scan (default 18)
        devices_file: Path to devices.json (must exist from wizard)
        snapshot_file: Path where device status snapshot will be saved

    Returns:
        Dictionary with scan results, or empty dict if scan fails
    """
    try:
        import sys
        cmd = [
            sys.executable,
            "-m",
            "tinytuya",
            "devices",
            str(max_time),
            "-device-file",
            str(devices_file),
            "-snapshot-file",
            str(snapshot_file),
            "-yes",
            "-no-poll",  # Don't attempt to poll cloud, only local scan
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            logger.info("Local device scan completed")
            return {"status": "ok", "scanned": True}
        else:
            logger.warning("Local device scan failed: %s", result.stderr)
            return {"status": "error", "message": result.stderr, "scanned": False}
    except Exception as error:
        logger.error("Failed to run local device scan: %s", error)
        return {"status": "error", "message": str(error), "scanned": False}


def get_devices_status_json(
    devices_file: Path | str = "devices.json",
    snapshot_file: Path | str = "snapshot.json",
) -> list[dict[str, Any]]:
    """
    Get the current device status from snapshot file in JSON format.

    Prerequisites:
    1. Run the wizard once: python -m tinytuya wizard
    2. Run scan to populate snapshot: python -m tinytuya devices

    Args:
        devices_file: Path to devices.json from wizard
        snapshot_file: Path to snapshot.json from scan

    Returns:
        List of device status dictionaries, or empty list if unavailable
    """
    snapshot_path = Path(snapshot_file)
    if not snapshot_path.exists():
        logger.warning("Snapshot file not found: %s", snapshot_file)
        return []

    try:
        content = snapshot_path.read_text()
        data: Any = json.loads(content)
        if isinstance(data, list):
            return _normalize_device_items(cast(list[Any], data))
        if isinstance(data, dict):
            data_dict = cast(dict[str, Any], data)
            devices_raw: Any = data_dict.get("devices")
            if isinstance(devices_raw, list):
                return _normalize_device_items(cast(list[Any], devices_raw))
        return []
    except Exception as error:
        logger.error("Failed to read snapshot file: %s", error)
        return []


def fetch_devices_json(
    max_time: int = 18,
    devices_file: Path | str = "devices.json",
    snapshot_file: Path | str = "snapshot.json",
) -> dict[str, Any]:
    """
    Scan local network and fetch device status as JSON in one call.

    This is the main entry point for backend integration.
    Runs 'python -m tinytuya json' which outputs device status directly.

    Args:
        max_time: Maximum scan time (used for context, not passed to json command)
        devices_file: Path to devices.json
        snapshot_file: Path to snapshot.json

    Returns:
        Dictionary with device list and status, or error information
    """
    try:
        # First run devices scan to populate snapshot
        scan_result = scan_local_devices(max_time, devices_file, snapshot_file)
        if not scan_result.get("scanned"):
            return {"devices": [], "error": scan_result.get("message")}

        # Then fetch the JSON output
        status_list = get_devices_status_json(devices_file, snapshot_file)
        return {"devices": status_list, "timestamp": __import__("datetime").datetime.now().isoformat()}
    except Exception as error:
        logger.error("Failed to fetch devices JSON: %s", error)
        return {"devices": [], "error": str(error)}


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--wizard":
        success = run_wizard()
        sys.exit(0 if success else 1)
    else:
        # Default: fetch and print devices
        result = fetch_devices_json()
        print(json.dumps(result, indent=2))
