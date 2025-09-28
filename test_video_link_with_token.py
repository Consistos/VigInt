#!/usr/bin/env python3
"""
Test video link with proper token generation
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

def test_video_link():
    """Test a video link with proper token"""
    
    # Get a recent video metadata
    storage_dir = Path("mock_sparse_ai_cloud")
    metadata_files = list(storage_dir.glob("*.json"))
    
    if not metadata_files:
        print("❌ No video metadata files found")
        return
    
    # Use the most recent metadata file
    metadata_file = sorted(metadata_files, key=lambda x: x.stat().st_mtime)[-1]
    print(f"📁 Using metadata file: {metadata_file}")
    
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    video_id = metadata['video_id']
    expiration_time = metadata['expiration_time']
    
    print(f"🎬 Video ID: {video_id}")
    print(f"⏰ Expiration: {expiration_time}")
    
    # Generate token
    token = generate_token(video_id, expiration_time)
    print(f"🔑 Generated token: {token}")
    
    # Test the video link
    video_url = f"http://127.0.0.1:9999/video/{video_id}?token={token}"
    print(f"🔗 Testing URL: {video_url}")
    
    try:
        response = requests.get(video_url, timeout=10, stream=True)
        print(f"📊 Response status: {response.status_code}")
        print(f"📋 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ Video link works! Server is serving the video correctly.")
            
            # Read first few bytes to confirm it's video data
            content = next(response.iter_content(chunk_size=100))
            print(f"📦 First 20 bytes: {content[:20]}")
            
        else:
            print(f"❌ Video link failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_video_link()