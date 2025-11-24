#!/usr/bin/env python3
"""Check what API key the video analyzer would actually use"""

import os
import sys
from config import config
from api_client import APIClient

print("=" * 60)
print("API KEY DEBUGGING")
print("=" * 60)

print(f"\n1. Environment variable VIGINT_API_KEY: {os.getenv('VIGINT_API_KEY')}")
print(f"2. Config secret_key: {config.secret_key}")
print(f"3. Config secret_key length: {len(config.secret_key)}")
print(f"4. Config secret_key repr: {repr(config.secret_key)}")

print("\n--- Creating APIClient ---")
client = APIClient()
print(f"5. APIClient.api_key: {client.api_key}")
print(f"6. APIClient.api_key length: {len(client.api_key)}")
print(f"7. APIClient.api_key repr: {repr(client.api_key)}")

print("\n--- Testing with server ---")
import hashlib
key_hash = hashlib.sha256(client.api_key.encode()).hexdigest()
print(f"8. Hash of API key being sent: {key_hash}")

try:
    result = client.health_check()
    print(f"9. Health check result: {result}")
except Exception as e:
    print(f"9. Health check FAILED: {e}")

print("=" * 60)
