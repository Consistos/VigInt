#!/usr/bin/env python3
"""Initialize database on remote server"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

server_url = os.getenv('VIGINT_API_URL', 'https://vigint.onrender.com')
admin_key = os.getenv('VIGINT_ADMIN_KEY')

if not admin_key:
    print("❌ VIGINT_ADMIN_KEY not set")
    print("   Set it with: export VIGINT_ADMIN_KEY=your-secret-key")
    exit(1)

# Try to trigger database initialization by accessing an admin endpoint
# This forces the app context to initialize
url = f"{server_url}/admin/clients"
headers = {'X-Admin-Key': admin_key}

print(f"Checking database connection to: {server_url}")
print("This will trigger database initialization if needed...")

response = requests.get(url, headers=headers)

if response.status_code == 200:
    print("✅ Database is initialized")
    print(f"   Clients: {response.json()}")
else:
    print(f"❌ Error: {response.status_code}")
    print(f"   {response.text}")
