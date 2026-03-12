"""
Automatic TinyTuya setup initialization.

Handles first-time setup of devices.json when using local device scanning.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEVICES_FILE = Path("devices.json")
SNAPSHOT_FILE = Path("snapshot.json")


def ensure_devices_json_exists() -> bool:
    """
    Check if devices.json exists. If not, provide instructions for setup.

    Returns:
        True if devices.json exists or setup is ready, False if setup is needed
    """
    if DEVICES_FILE.exists():
        logger.info("✓ devices.json found (size: %s bytes)", DEVICES_FILE.stat().st_size)
        return True

    logger.warning("devices.json not found. Run: python -m tinytuya wizard")
    return False


def create_sample_devices_json() -> None:
    """
    Create a sample devices.json for testing/demo purposes.
    
    This is useful for development when you don't have actual Tuya devices.
    For production, use: python -m tinytuya wizard
    """
    sample: list[dict[str, Any]] = [
        {
            "name": "Demo Device 1",
            "id": "bfa29c6177b6bec67f9mnv",
            "key": "0000000000000000",
            "devtype": "switch",
            "dps": {"1": True},
            "active": True,
            "category": "switch",
        }
    ]

    DEVICES_FILE.write_text(json.dumps(sample, indent=2))
    logger.info("Created sample devices.json - replace with real devices from wizard")


def get_setup_status() -> dict[str, Any]:
    """
    Get the current setup status and what's needed.

    Returns:
        Dictionary with status and setup instructions
    """
    devices_exists = DEVICES_FILE.exists()
    snapshot_exists = SNAPSHOT_FILE.exists()

    status: dict[str, Any] = {
        "devices_json_exists": devices_exists,
        "snapshot_json_exists": snapshot_exists,
        "setup_complete": devices_exists,
        "next_steps": [],
    }

    if not devices_exists:
        status["next_steps"] = [
            "Run interactive setup: python -m tinytuya wizard",
            "This will authenticate with Tuya Cloud and discover your devices",
            "It will create devices.json in the backend directory",
            "Restart the backend to start local device scanning",
        ]
    else:
        status["next_steps"] = ["Setup complete! Local device scanning is active"]

    return status


def print_setup_instructions() -> None:
    """Print setup instructions to console."""
    print("\n" + "=" * 70)
    print("TinyTuya Local Device Scanning Setup")
    print("=" * 70)

    status = get_setup_status()

    if status["setup_complete"]:
        print("\n✅ Setup complete! devices.json found.")
        print("\nLocal device scanning will run automatically in the background.")
        print("Check /api/dashboard for discovered devices.")
    else:
        print("\n⚠️  Setup needed: devices.json not found\n")
        for step in status["next_steps"]:
            print(f"  → {step}\n")
        print("\nFor more info: python -m tinytuya wizard -h")

    print("=" * 70 + "\n")
