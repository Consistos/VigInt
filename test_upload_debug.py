#!/usr/bin/env python3
"""Debug script to test video upload with detailed logging"""

import requests
import base64
from config import config

# Print config
print(f"Config API URL: {config.api_server_url}")
print(f"Config Secret Key: {config.secret_key}")
print(f"")

# Create a minimal video data
video_data = base64.b64encode(b"test video content").decode('utf-8')

# Make request
url = f"{config.api_server_url}/api/video/upload"
headers = {
    'X-API-Key': config.secret_key,
    'Content-Type': 'application/json'
}
data = {
    'video_data': video_data,
    'video_filename': 'test.mp4'
}

print(f"URL: {url}")
print(f"Headers: {headers}")
print(f"")

response = requests.post(url, json=data, headers=headers)

print(f"Status Code: {response.status_code}")
print(f"Response Headers: {dict(response.headers)}")
print(f"Response Body: {response.text}")
