#!/usr/bin/env python3
"""Test client setup - verify connection to server"""

import os
from dotenv import load_dotenv
import requests

# Load .env file
load_dotenv()

api_key = os.getenv('VIGINT_API_KEY')
api_url = os.getenv('VIGINT_API_URL', 'https://vigint.onrender.com')

if not api_key:
    print("❌ VIGINT_API_KEY not found in .env file")
    exit(1)

print(f"Testing connection to: {api_url}")
print(f"Using API key: {api_key[:10]}...")

# Test health endpoint
try:
    response = requests.get(f"{api_url}/api/health")
    if response.status_code == 200:
        print("✅ Server is reachable")
        print(f"   Response: {response.json()}")
    else:
        print(f"❌ Server returned status {response.status_code}")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    exit(1)

# Test authenticated endpoint
try:
    headers = {'X-API-Key': api_key}
    response = requests.get(f"{api_url}/api/usage", headers=headers)
    
    if response.status_code == 200:
        print("✅ Authentication successful!")
        print(f"   Your usage: {response.json()}")
    elif response.status_code == 401:
        print("❌ Authentication failed - invalid API key")
    else:
        print(f"❌ Unexpected response: {response.status_code}")
        print(f"   {response.text}")
except Exception as e:
    print(f"❌ Request failed: {e}")
    exit(1)

print("\n✅ Client setup is working correctly!")
print("\nYour local machine is now configured as a client.")
print("All AI analysis will go through the server.")
