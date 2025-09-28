#!/usr/bin/env python3
"""
Test video link like a browser would access it
"""
import json
import hashlib
import requests
from pathlib import Path

def generate_token(video_id, expiration_time):
    """Generate token like the server does"""
    return hashlib.sha256(
        f"{video_id}:{expiration_time}:mock-key".encode()
    ).hexdigest()[:32]

def test_browser_access():
    """Test video access like a browser would"""
    
    # Get the most recent video
    storage_dir = Path("mock_sparse_ai_cloud")
    metadata_files = sorted(storage_dir.glob("*.json"), key=lambda x: x.stat().st_mtime)
    
    if not metadata_files:
        print("❌ No video metadata files found")
        return
    
    metadata_file = metadata_files[-1]
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    video_id = metadata['video_id']
    expiration_time = metadata['expiration_time']
    token = generate_token(video_id, expiration_time)
    
    video_url = f"http://127.0.0.1:9999/video/{video_id}?token={token}"
    
    print(f"🔗 Testing video link: {video_url}")
    print(f"🎬 Video ID: {video_id}")
    print(f"⏰ Expires: {expiration_time}")
    
    try:
        # Test with HEAD request first (like browsers do)
        print("\n📋 Testing HEAD request...")
        response = requests.head(video_url, timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 501:
            print("ℹ️ HEAD not supported (expected)")
        
        # Test with GET request (partial)
        print("\n📋 Testing GET request (first 1KB)...")
        headers = {'Range': 'bytes=0-1023'}
        response = requests.get(video_url, headers=headers, timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"Content-Length: {response.headers.get('Content-Length')}")
        
        if response.status_code == 200:
            print("✅ Video link works perfectly!")
            print(f"📦 Received {len(response.content)} bytes")
            print(f"🎬 Video data starts with: {response.content[:20]}")
            
            # Create a clickable link for testing
            print(f"\n🌐 **CLICKABLE LINK FOR BROWSER TESTING:**")
            print(f"{video_url}")
            print("\n💡 Copy this link and paste it in your browser to test!")
            
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_browser_access()