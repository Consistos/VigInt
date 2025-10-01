#!/usr/bin/env python3
"""
Start the local video server for GDPR-compliant video hosting
"""

import os
import sys
import time
import threading
import requests
import logging
from pathlib import Path

# Add current directory to path
sys.path.append('.')

from local_video_server import start_server, BASE_URL, VIDEO_STORAGE_DIR

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_server_health():
    """Check if the video server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def start_server_background():
    """Start the video server in a background thread"""
    try:
        logger.info("Starting local video server in background...")
        start_server()
    except Exception as e:
        logger.error(f"Error starting video server: {e}")


def test_video_server():
    """Test the video server with existing videos"""
    logger.info("🧪 Testing Local Video Server")
    logger.info("=" * 40)
    
    try:
        # Check health
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            health = response.json()
            logger.info(f"✅ Server healthy: {health['service']}")
            logger.info(f"   Storage: {health['storage_dir']}")
        else:
            logger.error("❌ Server health check failed")
            return False
        
        # List videos
        response = requests.get(f"{BASE_URL}/videos")
        if response.status_code == 200:
            videos_data = response.json()
            videos = videos_data['videos']
            logger.info(f"📹 Found {len(videos)} videos:")
            
            for video in videos[:3]:  # Show first 3
                logger.info(f"   - {video['filename']} ({video['size_mb']} MB)")
                logger.info(f"     ID: {video['video_id']}")
                logger.info(f"     Risk: {video['risk_level']}")
                logger.info(f"     Expired: {video['expired']}")
                
                # Test video access (we need the token from metadata)
                try:
                    # Read metadata to get token
                    metadata_files = list(VIDEO_STORAGE_DIR.glob("*.json"))
                    for metadata_file in metadata_files:
                        with open(metadata_file, 'r') as f:
                            import json
                            metadata = json.load(f)
                        
                        if metadata['video_id'] == video['video_id']:
                            # Extract token from the private link we would have generated
                            import hashlib
                            token = hashlib.sha256(
                                f"{video['video_id']}:{metadata['expiration_time']}:mock-key".encode()
                            ).hexdigest()[:32]
                            
                            # Test video info endpoint
                            info_url = f"{BASE_URL}/video/{video['video_id']}/info?token={token}"
                            info_response = requests.get(info_url)
                            
                            if info_response.status_code == 200:
                                logger.info(f"     ✅ Video accessible via API")
                                
                                # Generate working link
                                video_url = f"{BASE_URL}/video/{video['video_id']}?token={token}"
                                logger.info(f"     🔗 Working link: {video_url}")
                            else:
                                logger.warning(f"     ⚠️  Video API access failed: {info_response.status_code}")
                            break
                
                except Exception as e:
                    logger.warning(f"     ⚠️  Error testing video access: {e}")
            
            return True
        else:
            logger.error("❌ Failed to list videos")
            return False
    
    except Exception as e:
        logger.error(f"❌ Error testing server: {e}")
        return False


def main():
    """Main function"""
    logger.info("🎬 LOCAL VIDEO SERVER STARTUP")
    logger.info("=" * 50)
    
    # Check if server is already running
    if check_server_health():
        logger.info("✅ Video server is already running!")
        test_video_server()
        return
    
    # Start server in background thread
    server_thread = threading.Thread(target=start_server_background, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    logger.info("⏳ Waiting for server to start...")
    for i in range(10):
        time.sleep(1)
        if check_server_health():
            logger.info(f"✅ Server started successfully after {i+1} seconds!")
            break
    else:
        logger.error("❌ Server failed to start within 10 seconds")
        return
    
    # Test the server
    if test_video_server():
        logger.info("\n🎉 Local video server is working!")
        logger.info(f"📍 Server URL: {BASE_URL}")
        logger.info("📧 Video links in emails will now work properly")
        
        logger.info("\n📋 NEXT STEPS:")
        logger.info("1. Keep this server running")
        logger.info("2. Send a test security alert")
        logger.info("3. Click the video link in the email")
        logger.info("4. Video should play in your browser")
        
        # Keep server running
        try:
            logger.info("\n🔄 Server running... Press Ctrl+C to stop")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n👋 Shutting down video server...")
    else:
        logger.error("❌ Server test failed")


if __name__ == '__main__':
    main()