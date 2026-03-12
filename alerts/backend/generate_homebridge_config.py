#!/usr/bin/env python3
"""
Generate Homebridge config.json from environment variables.
This allows credentials to be updated without editing JSON directly.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

def generate_homebridge_config(output_path: str = ".homebridge/config.json") -> None:
    """Generate Homebridge config from environment variables."""
    
    # Read env values with defaults
    tuya_username = os.getenv("TUYA_USERNAME", "luis.faria@aup.pt").strip()
    tuya_password = os.getenv("TUYA_PASSWORD", "TBeMaBrMi_0").strip()
    tuya_country_code = os.getenv("TUYA_COUNTRY_CODE", "351").strip()
    tuya_platform = os.getenv("TUYA_PLATFORM", "tuya").strip()
    
    config: dict[str, Any] = {
        "bridge": {
            "name": "Alerts Tuya Local",
            "username": "CC:22:3D:E3:CE:31",
            "port": 53826,
            "pin": "031-45-154"
        },
        "accessories": [],
        "platforms": [
            {
                "platform": "config",
                "name": "Config",
                "port": 8582,
                "auth": "none"
            },
            {
                "platform": "@milo526/homebridge-tuya-web.TuyaWebPlatform",
                "name": "TuyaWebPlatform",
                "options": {
                    "username": tuya_username,
                    "password": tuya_password,
                    "countryCode": tuya_country_code,
                    "platform": tuya_platform,
                    "pollingInterval": 60
                }
            }
        ]
    }
    
    # Ensure .homebridge directory exists
    Path(".homebridge").mkdir(exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"Generated {output_path}")
    print(f"  username: {tuya_username}")
    print(f"  password: {'*' * (len(tuya_password) - 2) + tuya_password[-2:]}")
    print(f"  countryCode: {tuya_country_code}")
    print(f"  platform: {tuya_platform}")

if __name__ == "__main__":
    generate_homebridge_config()
