#!/usr/bin/env python3
"""
Test script for LiveKit Voice Agent API
"""

import requests
import json
import time
import sys

def test_health_check(base_url):
    """Test the health check endpoint"""
    print("Testing health check...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['message']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_make_call(base_url, phone_number="+1234567890"):
    """Test making a call"""
    print(f"Testing make call to {phone_number}...")
    try:
        payload = {
            "phone_number": phone_number,
            "customer_name": "Test User",
            "appointment_date": "2024-01-15",
            "appointment_time": "2:00 PM",
            "custom_instructions": "This is a test call from the API"
        }
        
        response = requests.post(f"{base_url}/call", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Call initiated successfully")
            print(f"   Call ID: {data['call_id']}")
            print(f"   Status: {data['status']}")
            print(f"   Message: {data['message']}")
            return data['call_id']
        else:
            print(f"❌ Call initiation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Call initiation error: {e}")
        return None

def test_get_call_status(base_url, call_id):
    """Test getting call status"""
    print(f"Testing get call status for {call_id}...")
    try:
        response = requests.get(f"{base_url}/call/{call_id}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Call status retrieved successfully")
            print(f"   Status: {data['status']}")
            print(f"   Phone: {data['phone_number']}")
            return True
        else:
            print(f"❌ Get call status failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Get call status error: {e}")
        return False

def test_list_calls(base_url):
    """Test listing all calls"""
    print("Testing list calls...")
    try:
        response = requests.get(f"{base_url}/calls")
        if response.status_code == 200:
            data = response.json()
            call_count = len(data['calls'])
            print(f"✅ List calls successful: {call_count} calls found")
            return True
        else:
            print(f"❌ List calls failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ List calls error: {e}")
        return False

def main():
    """Main test function"""
    if len(sys.argv) < 2:
        print("Usage: python test_api.py <base_url> [phone_number]")
        print("Example: python test_api.py http://localhost:8000 +1234567890")
        sys.exit(1)
    
    base_url = sys.argv[1]
    phone_number = sys.argv[2] if len(sys.argv) > 2 else "+1234567890"
    
    print(f"Testing LiveKit Voice Agent API at: {base_url}")
    print("=" * 50)
    
    # Test health check
    if not test_health_check(base_url):
        print("❌ Health check failed, stopping tests")
        sys.exit(1)
    
    print()
    
    # Test making a call
    call_id = test_make_call(base_url, phone_number)
    if not call_id:
        print("❌ Call initiation failed, stopping tests")
        sys.exit(1)
    
    print()
    
    # Wait a moment for the call to process
    print("Waiting 2 seconds for call to process...")
    time.sleep(2)
    
    # Test getting call status
    test_get_call_status(base_url, call_id)
    
    print()
    
    # Test listing calls
    test_list_calls(base_url)
    
    print()
    print("=" * 50)
    print("✅ All tests completed!")

if __name__ == "__main__":
    main()
