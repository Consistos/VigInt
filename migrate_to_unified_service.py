#!/usr/bin/env python3
"""
Migration script for moving from separate sparse-ai-video-server to unified API server
This script helps migrate videos from the old server to the new unified service
"""

import requests
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Configuration
OLD_SERVER = os.environ.get('OLD_SERVER_URL', 'https://sparse-ai-video-server.onrender.com')
NEW_SERVER = os.environ.get('NEW_SERVER_URL', 'https://vigint-api-server.onrender.com')
OLD_API_KEY = os.environ.get('OLD_API_KEY', '')
NEW_API_KEY = os.environ.get('NEW_API_KEY', '')

def test_old_server():
    """Test connectivity to old sparse-ai-video-server"""
    print(f"\n🔍 Testing old server: {OLD_SERVER}")
    try:
        response = requests.get(f"{OLD_SERVER}/health", timeout=10)
        if response.status_code == 200:
            print(f"   ✅ Old server is accessible")
            return True
        else:
            print(f"   ⚠️  Old server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot reach old server: {e}")
        return False

def test_new_server():
    """Test connectivity to new unified API server"""
    print(f"\n🔍 Testing new server: {NEW_SERVER}")
    try:
        response = requests.get(f"{NEW_SERVER}/api/health", timeout=10)
        if response.status_code == 200:
            print(f"   ✅ New server is accessible")
            data = response.json()
            print(f"   Status: {data.get('status')}")
            return True
        else:
            print(f"   ⚠️  New server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot reach new server: {e}")
        return False

def test_upload_endpoint():
    """Test that new server has video upload endpoint"""
    print(f"\n🔍 Testing video upload endpoint on new server")
    
    # Create a tiny test video (1 frame)
    import tempfile
    import cv2
    import numpy as np
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # Create 1-second test video
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(tmp_path, fourcc, 1, (320, 240))
        
        for i in range(1):
            frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
            out.write(frame)
        
        out.release()
        
        # Test upload
        test_video_id = f"test_{int(datetime.now().timestamp())}"
        
        with open(tmp_path, 'rb') as f:
            files = {'video': ('test.mp4', f, 'video/mp4')}
            data = {
                'metadata': json.dumps({'video_id': test_video_id}),
                'expiration_hours': 1  # Expire in 1 hour
            }
            
            headers = {'Authorization': f'Bearer {NEW_API_KEY}'}
            
            response = requests.post(
                f"{NEW_SERVER}/api/v1/videos/upload",
                files=files,
                data=data,
                headers=headers,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Upload endpoint works!")
            print(f"   Video ID: {result.get('video_id')}")
            print(f"   Private link: {result.get('private_link')[:80]}...")
            return True, result.get('private_link')
        else:
            print(f"   ❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"   ❌ Upload test failed: {e}")
        return False, None
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def test_video_serving(video_link):
    """Test that video serving works on new server"""
    print(f"\n🔍 Testing video serving on new server")
    
    if not video_link:
        print("   ⚠️  No video link to test")
        return False
    
    try:
        response = requests.get(video_link, timeout=10)
        if response.status_code == 200:
            print(f"   ✅ Video serving works!")
            print(f"   Video size: {len(response.content)} bytes")
            return True
        else:
            print(f"   ❌ Video serving failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Video serving test failed: {e}")
        return False

def list_videos_to_migrate():
    """
    List videos that need to be migrated
    Note: This requires manual input as the old server doesn't have a list endpoint
    """
    print(f"\n📋 Videos to migrate")
    print("=" * 60)
    print("The old sparse-ai-video-server doesn't have an API to list videos.")
    print("You need to manually identify videos to migrate.")
    print("\nOptions:")
    print("1. Check your local mock_sparse_ai_cloud/ directory")
    print("2. Check email alerts for video links")
    print("3. Check your database for video_id records")
    print("\nVideo links look like:")
    print("https://sparse-ai-video-server.onrender.com/video/VIDEO_ID?token=TOKEN")
    
    return []

def migrate_video(video_id, token, metadata=None):
    """
    Migrate a single video from old server to new server
    
    Args:
        video_id: Video ID to migrate
        token: Access token for the video
        metadata: Optional metadata dict
    
    Returns:
        tuple: (success, new_link)
    """
    print(f"\n🔄 Migrating video: {video_id}")
    
    # Step 1: Download from old server
    old_url = f"{OLD_SERVER}/video/{video_id}?token={token}"
    print(f"   📥 Downloading from old server...")
    
    try:
        response = requests.get(old_url, timeout=60)
        if response.status_code != 200:
            print(f"   ❌ Failed to download: {response.status_code}")
            return False, None
        
        video_data = response.content
        print(f"   ✅ Downloaded {len(video_data)} bytes")
        
    except Exception as e:
        print(f"   ❌ Download failed: {e}")
        return False, None
    
    # Step 2: Upload to new server
    print(f"   📤 Uploading to new server...")
    
    try:
        if not metadata:
            metadata = {
                'video_id': video_id,
                'migrated': True,
                'original_server': OLD_SERVER,
                'migration_date': datetime.now().isoformat()
            }
        
        files = {'video': (f'{video_id}.mp4', video_data, 'video/mp4')}
        data = {
            'metadata': json.dumps(metadata),
            'expiration_hours': 720  # 30 days
        }
        
        headers = {'Authorization': f'Bearer {NEW_API_KEY}'}
        
        response = requests.post(
            f"{NEW_SERVER}/api/v1/videos/upload",
            files=files,
            data=data,
            headers=headers,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            new_link = result.get('private_link')
            print(f"   ✅ Upload successful!")
            print(f"   New link: {new_link}")
            return True, new_link
        else:
            print(f"   ❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"   ❌ Upload failed: {e}")
        return False, None

def save_migration_log(video_id, old_link, new_link, success):
    """Save migration results to a log file"""
    log_file = 'video_migration_log.json'
    
    # Load existing log
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            log = json.load(f)
    else:
        log = []
    
    # Add entry
    log.append({
        'video_id': video_id,
        'old_link': old_link,
        'new_link': new_link,
        'success': success,
        'timestamp': datetime.now().isoformat()
    })
    
    # Save log
    with open(log_file, 'w') as f:
        json.dump(log, f, indent=2)
    
    print(f"   📝 Migration logged to {log_file}")

def interactive_migration():
    """Interactive migration mode"""
    print("\n🎯 Interactive Video Migration")
    print("=" * 60)
    
    while True:
        print("\nEnter video details to migrate (or 'done' to finish):")
        
        video_id = input("Video ID: ").strip()
        if video_id.lower() == 'done':
            break
        
        if not video_id:
            print("❌ Video ID is required")
            continue
        
        token = input("Access token: ").strip()
        if not token:
            print("❌ Token is required")
            continue
        
        # Optional metadata
        print("Optional metadata (press Enter to skip):")
        description = input("  Description: ").strip()
        
        metadata = {
            'video_id': video_id,
            'migrated': True,
            'original_server': OLD_SERVER,
            'migration_date': datetime.now().isoformat()
        }
        
        if description:
            metadata['description'] = description
        
        # Migrate
        old_link = f"{OLD_SERVER}/video/{video_id}?token={token}"
        success, new_link = migrate_video(video_id, token, metadata)
        
        # Log
        save_migration_log(video_id, old_link, new_link, success)
        
        if success:
            print("\n✅ Migration successful!")
            print(f"Old link: {old_link}")
            print(f"New link: {new_link}")
        else:
            print("\n❌ Migration failed")

def main():
    """Main migration workflow"""
    print("=" * 60)
    print("📦 Vigint Video Migration Tool")
    print("=" * 60)
    print(f"Old server: {OLD_SERVER}")
    print(f"New server: {NEW_SERVER}")
    
    # Check if API keys are set
    if not OLD_API_KEY:
        print("\n⚠️  Warning: OLD_API_KEY not set (may not be needed for download)")
    
    if not NEW_API_KEY:
        print("\n❌ Error: NEW_API_KEY environment variable is required")
        print("Set it with: export NEW_API_KEY=your-api-key")
        sys.exit(1)
    
    # Test connectivity
    old_ok = test_old_server()
    new_ok = test_new_server()
    
    if not old_ok or not new_ok:
        print("\n❌ Cannot proceed - server connectivity issues")
        sys.exit(1)
    
    # Test upload endpoint
    print("\n" + "=" * 60)
    print("🧪 Testing upload functionality")
    print("=" * 60)
    
    upload_ok, test_link = test_upload_endpoint()
    
    if not upload_ok:
        print("\n❌ Upload endpoint not working - cannot migrate")
        sys.exit(1)
    
    # Test video serving
    serve_ok = test_video_serving(test_link)
    
    if not serve_ok:
        print("\n⚠️  Warning: Video serving test failed")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ All tests passed - ready to migrate")
    print("=" * 60)
    
    # Show migration options
    print("\nMigration options:")
    print("1. Interactive mode (enter videos manually)")
    print("2. Batch mode (provide CSV file)")
    print("3. Exit")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == '1':
        interactive_migration()
    elif choice == '2':
        print("\n📋 Batch mode requires a CSV file with columns:")
        print("   video_id,token,description")
        csv_file = input("CSV file path: ").strip()
        
        if os.path.exists(csv_file):
            import csv
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    video_id = row.get('video_id')
                    token = row.get('token')
                    description = row.get('description', '')
                    
                    metadata = {
                        'video_id': video_id,
                        'description': description,
                        'migrated': True
                    }
                    
                    old_link = f"{OLD_SERVER}/video/{video_id}?token={token}"
                    success, new_link = migrate_video(video_id, token, metadata)
                    save_migration_log(video_id, old_link, new_link, success)
        else:
            print(f"❌ File not found: {csv_file}")
    else:
        print("\n👋 Exiting")
        return
    
    print("\n" + "=" * 60)
    print("✅ Migration complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Verify videos work on new server")
    print("2. Update config.ini to point to new server")
    print("3. Test your Vigint system")
    print("4. Once confirmed, delete old sparse-ai-video-server")
    print("\nMigration log saved to: video_migration_log.json")

if __name__ == '__main__':
    main()
