#!/usr/bin/env python3
"""
Verify API Key Configuration
Helps ensure local and server API keys match
"""

import os
import hashlib
from dotenv import load_dotenv

load_dotenv()

print("=" * 70)
print("🔑 API KEY VERIFICATION")
print("=" * 70)
print()

# Get local API key
local_key = os.getenv('SPARSE_AI_API_KEY', '')

print("Local Configuration (.env):")
print("-" * 70)
print(f"  API Key (first 10 chars): {local_key[:10]}...")
print(f"  API Key (last 10 chars):  ...{local_key[-10:]}")
print(f"  API Key length: {len(local_key)} characters")
print(f"  API Key SHA256 hash: {hashlib.sha256(local_key.encode()).hexdigest()[:16]}...")
print()

print("Server Configuration (Render.com):")
print("-" * 70)
print("  1. Go to: https://dashboard.render.com")
print("  2. Select: sparse-ai-video-server")
print("  3. Click: Environment tab")
print("  4. Find: SPARSE_AI_API_KEY")
print()
print("  The server's API key MUST match your local key exactly!")
print()

print("Verification Checklist:")
print("-" * 70)
print("  [ ] Server API key first 10 chars match:", local_key[:10])
print("  [ ] Server API key last 10 chars match:", local_key[-10:])
print("  [ ] Server API key length is:", len(local_key), "characters")
print()

print("If they don't match:")
print("-" * 70)
print("  Option A: Update local .env to match server")
print("  Option B: Update server environment variable to match local")
print("  Then restart both Vigint and the server")
print()

print("=" * 70)
