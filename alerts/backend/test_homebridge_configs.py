#!/usr/bin/env python3
"""
Test different Tuya credential combinations for Homebridge.
Restarts Homebridge config and checks for accessory count.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from urllib import request

def test_homebridge_config(username: str, password: str, country_code: str, platform_name: str) -> int:
    """
    Test a specific Homebridge config combination and return accessory count.
    
    Returns:
        Number of accessories found, or -1 if connection failed.
    """
    # Generate config for this combination
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
                    "username": username,
                    "password": password,
                    "countryCode": country_code,
                    "platform": platform_name,
                    "pollingInterval": 60
                }
            }
        ]
    }
    
    # Ensure directory exists
    Path(".homebridge").mkdir(exist_ok=True)
    
    # Write config
    with open(".homebridge/config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"\n🔄 Testing: {username} | CC={country_code} | platform={platform_name}")
    
    # Give Homebridge time to reload config and retry connection
    time.sleep(4)
    
    # Query debug endpoint
    try:
        with request.urlopen("http://127.0.0.1:8000/api/homebridge/debug", timeout=8) as r:
            data = json.loads(r.read().decode())
            count = data.get("accessoryCount", -1)
            error = data.get("error")
            print(f"   Result: {count} accessories | error={error}")
            return count
    except Exception as e:
        print(f"   Result: Failed to query backend: {e}")
        return -1

def main():
    # Current credentials from env
    username = os.getenv("TUYA_USERNAME", "luis.faria@aup.pt")
    password = os.getenv("TUYA_PASSWORD", "TBeMaBrMi_0")
    
    # Test combinations
    combinations = [
        # (country_code, platform)
        ("351", "tuya"),         # Portugal
        ("86", "tuya"),          # China
        ("1", "tuya"),           # US
        ("44", "tuya"),          # UK
        ("55", "tuya"),          # Brazil
        ("351", "tuya_eu"),      # Portugal with EU variant
        ("86", "smartvolume"),   # China with smartvolume
        ("1", "smartliving"),    # US with smartliving
    ]
    
    best_count = -1
    best_config = None
    
    for country_code, platform_name in combinations:
        count = test_homebridge_config(username, password, country_code, platform_name)
        if count > best_count:
            best_count = count
            best_config = (country_code, platform_name)
        if count > 0:
            print(f"\n✅ Found working config! Accessories: {count}")
            break
    
    if best_config and best_count > 0:
        print(f"\n✅ Best config found with {best_count} accessories:")
        print(f"   TUYA_COUNTRY_CODE={best_config[0]}")
        print(f"   TUYA_PLATFORM={best_config[1]}")
        print("\nUpdate .env with these values and restart Homebridge:")
        print(f"   TUYA_COUNTRY_CODE={best_config[0]}")
        print(f"   TUYA_PLATFORM={best_config[1]}")
    else:
        print(f"\n⚠️  No config found accessories. Best was {best_count} accessories.")
        print("This likely means the Tuya account credentials are invalid.")
        print("Check username/password and ensure they match your Tuya app account.")

if __name__ == "__main__":
    main()
