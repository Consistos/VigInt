#!/usr/bin/env python3
"""Check what Sparse AI base URL is configured"""

import os
from config import config

print("=" * 70)
print("SPARSE AI CONFIGURATION CHECK")
print("=" * 70)

# Check environment variable
env_url = os.getenv('SPARSE_AI_BASE_URL')
print(f"\nEnvironment Variable (SPARSE_AI_BASE_URL):")
print(f"  Value: {env_url or 'NOT SET'}")

# Check config.ini
config_url = config.get('SparseAI', 'base_url', 'NOT FOUND')
print(f"\nConfig File (config.ini [SparseAI] base_url):")
print(f"  Value: {config_url}")

# Show what will be used
final_url = env_url or config_url
print(f"\nFinal URL that will be used:")
print(f"  {final_url}")

# Check if it's the correct production URL
print(f"\n✅ Status:")
if 'vigint.onrender.com' in final_url:
    print("  ✓ Correctly configured for Render.com production")
elif '127.0.0.1' in final_url or 'localhost' in final_url:
    print("  ✗ ISSUE: Still using localhost!")
    print("\n  To fix: Update config.ini [SparseAI] section:")
    print("  base_url = https://vigint.onrender.com")
else:
    print(f"  ? Unknown URL: {final_url}")

print("=" * 70)
