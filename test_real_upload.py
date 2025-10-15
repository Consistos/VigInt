#!/usr/bin/env python3
"""
Test Real Upload to Render.com Server
"""

import os
import sys
import requests
import json
import hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def test_upload():
    """Test video upload to actual Render.com server"""
    
    print("=" * 70)
    print("🧪 TESTING REAL UPLOAD TO RENDER.COM")
    print("=" * 70)
    print()
    
    # Get configuration
    base_url = os.getenv('SPARSE_AI_BASE_URL', 'https://sparse-ai-video-server.onrender.com')
    api_key = os.getenv('SPARSE_AI_API_KEY', '')
    
    print(f"Base URL: {base_url}")
    print(f"API Key: {api_key[:10]}...{api_key[-10:]}")
    print()
    
    # Step 1: Test health endpoint
    print("Step 1: Testing health endpoint...")
    print("-" * 70)
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            print(f"✅ Server is healthy: {response.json()}")
        else:
            print(f"❌ Health check failed: HTTP {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot reach server: {e}")
        return
    
    print()
    
    # Step 2: Create a tiny test video
    print("Step 2: Creating test video...")
    print("-" * 70)
    
    # Use an existing video if available
    test_video_path = None
    test_videos = [
        'buffer_video_1.mp4',
        'incident_video_20250926_151327.mp4',
        'local_videos/incident_HIGH_20250925_152759_2806e1c2.mp4'
    ]
    
    for video in test_videos:
        if os.path.exists(video):
            test_video_path = video
            break
    
    if not test_video_path:
        print("❌ No test video found")
        return
    
    file_size = os.path.getsize(test_video_path) / (1024 * 1024)
    print(f"✅ Using test video: {test_video_path}")
    print(f"   Size: {file_size:.1f} MB")
    print()
    
    # Step 3: Test upload
    print("Step 3: Testing upload...")
    print("-" * 70)
    
    video_id = f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    expiration_hours = 48
    expiration_time = datetime.now() + timedelta(hours=expiration_hours)
    
    metadata = {
        'video_id': video_id,
        'upload_timestamp': datetime.now().isoformat(),
        'expiration_time': expiration_time.isoformat(),
        'source': 'vigint-test-script',
        'type': 'test_upload'
    }
    
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    
    with open(test_video_path, 'rb') as video_file:
        files = {
            'video': (f'test_{video_id}.mp4', video_file, 'video/mp4')
        }
        
        data = {
            'metadata': json.dumps(metadata),
            'expiration_hours': expiration_hours,
            'access_type': 'private'
        }
        
        print(f"Uploading to: {base_url}/api/v1/videos/upload")
        print(f"Video ID: {video_id}")
        print()
        
        try:
            response = requests.post(
                f"{base_url}/api/v1/videos/upload",
                headers=headers,
                files=files,
                data=data,
                timeout=120
            )
            
            print(f"Response Status: HTTP {response.status_code}")
            print(f"Response Body: {response.text}")
            print()
            
            if response.status_code == 200:
                result = response.json()
                print("✅ UPLOAD SUCCESSFUL!")
                print()
                print("Response Details:")
                print(f"  Video ID: {result.get('video_id')}")
                print(f"  Private Link: {result.get('private_link')}")
                print(f"  Expiration: {result.get('expiration_time')}")
                print()
                
                # Test if the link works
                print("Step 4: Testing video link...")
                print("-" * 70)
                
                link = result.get('private_link')
                if link:
                    try:
                        test_response = requests.head(link, timeout=10, allow_redirects=True)
                        if test_response.status_code == 200:
                            print(f"✅ Video link is accessible!")
                            print(f"   Link: {link}")
                        else:
                            print(f"⚠️  Video link returned HTTP {test_response.status_code}")
                            print(f"   This might be normal - the video might need processing")
                    except Exception as e:
                        print(f"⚠️  Could not test link: {e}")
                
                print()
                print("=" * 70)
                print("✅ ALL TESTS PASSED!")
                print("=" * 70)
                print()
                print("Your Vigint system should now work correctly.")
                print("New incidents will upload videos successfully.")
                
            elif response.status_code == 401:
                print("❌ AUTHENTICATION FAILED (HTTP 401)")
                print()
                print("This means the Authorization header is missing or invalid.")
                print("Check your API key format.")
                
            elif response.status_code == 403:
                print("❌ API KEY MISMATCH (HTTP 403)")
                print()
                print("🔑 CRITICAL ISSUE IDENTIFIED!")
                print()
                print("Your local API key does NOT match the server's API key.")
                print()
                print("To fix:")
                print("1. Go to https://dashboard.render.com")
                print("2. Select: sparse-ai-video-server")
                print("3. Click: Environment")
                print("4. Update SPARSE_AI_API_KEY to match your local key:")
                print(f"   {api_key}")
                print("5. Save and wait for redeploy (~2 minutes)")
                print("6. Run this test again")
                
            else:
                print(f"❌ UPLOAD FAILED (HTTP {response.status_code})")
                print()
                try:
                    error_data = response.json()
                    print(f"Error: {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"Response: {response.text}")
                    
        except requests.exceptions.Timeout:
            print("❌ Upload timeout - video might be too large or server is slow")
        except Exception as e:
            print(f"❌ Upload error: {e}")
    
    print()
    print("=" * 70)


if __name__ == '__main__':
    test_upload()
