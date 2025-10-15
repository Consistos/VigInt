#!/usr/bin/env python3
"""
Test script to verify the local video server works correctly
"""

import time
import requests
import subprocess
import threading
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_video_server():
    """Test that the video server starts and can serve videos"""
    
    logger.info("🧪 Testing Local Video Server")
    logger.info("=" * 50)
    
    # Start the video server in background
    logger.info("🚀 Starting video server...")
    
    def start_server():
        try:
            subprocess.run(['python', 'local_video_server.py'], check=True)
        except Exception as e:
            logger.error(f"Server startup error: {e}")
    
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    logger.info("⏳ Waiting for server to start...")
    time.sleep(5)
    
    # Test server health
    try:
        response = requests.get('http://127.0.0.1:8888/health', timeout=5)
        if response.status_code == 200:
            logger.info("✅ Video server is running!")
            logger.info(f"📊 Health check: {response.json()}")
        else:
            logger.error(f"❌ Server health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Cannot connect to video server: {e}")
        return False
    
    # Test video listing
    try:
        response = requests.get('http://127.0.0.1:8888/videos', timeout=5)
        if response.status_code == 200:
            videos = response.json()
            logger.info(f"📹 Found {len(videos)} videos available")
            
            # Test accessing a video if available
            if videos:
                video = videos[0]
                video_url = f"http://127.0.0.1:8888/video/{video['video_id']}?token={video.get('token', 'test')}"
                logger.info(f"🔗 Testing video link: {video_url}")
                
                # Just test if the endpoint responds (don't download the whole video)
                response = requests.head(video_url, timeout=5)
                if response.status_code == 200:
                    logger.info("✅ Video link is accessible!")
                else:
                    logger.warning(f"⚠️ Video link returned: {response.status_code}")
            else:
                logger.info("📝 No videos available for testing")
        else:
            logger.warning(f"⚠️ Video listing failed: {response.status_code}")
    
    except requests.exceptions.RequestException as e:
        logger.warning(f"⚠️ Video listing test failed: {e}")
    
    logger.info("\n" + "=" * 50)
    logger.info("🎉 Video server test completed!")
    logger.info("💡 If the server is running, video links should work in emails")
    
    return True

if __name__ == '__main__':
    test_video_server()