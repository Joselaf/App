#!/usr/bin/env python3
"""
Test script to verify Tuya Cloud connectivity
"""
import tinytuya
import time

# --- Tuya Cloud Credentials ---
API_KEY    = "c8uhx3vs89grhea8mg7p"
API_SECRET = "7221603a3b754d8b89b30c8dc9114b0d"
API_REGION = "eu"

def test_tuya_connection():
    """Test Tuya Cloud connection and device discovery"""
    print("🔍 Testing Tuya Cloud connection...")

    try:
        print("📡 Creating Tuya Cloud client...")
        cloud = tinytuya.Cloud(
            apiRegion=API_REGION,
            apiKey=API_KEY,
            apiSecret=API_SECRET,
        )

        print("🔑 Testing authentication...")
        # Try to get token (this will fail if credentials are wrong)
        token = cloud.token
        if not token:
            print("❌ No token received - credentials might be invalid")
            return False

        print(f"✅ Authentication successful, token: {token[:20]}...")

        print("📋 Getting device list...")
        start_time = time.time()
        devices = cloud.getdevices()
        elapsed = time.time() - start_time

        print(f"✅ Found {len(devices)} devices in {elapsed:.1f}s")

        for i, device in enumerate(devices[:5]):  # Show first 5 devices
            print(f"  {i+1}. {device.get('name', 'Unknown')} (ID: {device['id']})")

        if len(devices) > 5:
            print(f"  ... and {len(devices) - 5} more devices")

        # Test getting status of first device (if any)
        if devices:
            print(f"\n🧪 Testing device status for {devices[0].get('name', devices[0]['id'])}...")
            try:
                status = cloud.getstatus(devices[0]['id'])
                if status and 'result' in status:
                    dps = {item["code"]: item["value"] for item in status["result"] if "code" in item}
                    print(f"✅ Device status retrieved: {len(dps)} properties")
                    print(f"   Sample DPS: {dict(list(dps.items())[:3])}")
                else:
                    print("⚠️ Device status empty or invalid")
            except Exception as e:
                print(f"❌ Error getting device status: {e}")

        print("\n🎉 Tuya Cloud connection test PASSED!")
        return True

    except Exception as e:
        print(f"❌ Tuya Cloud test FAILED: {e}")
        print("\nTroubleshooting:")
        print("1. Check your API_KEY and API_SECRET are correct")
        print("2. Verify API_REGION is correct (eu, us, cn, in)")
        print("3. Make sure your Tuya Cloud project is active")
        print("4. Check your internet connection")
        return False

if __name__ == '__main__':
    test_tuya_connection()