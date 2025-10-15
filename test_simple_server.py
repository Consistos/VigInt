#!/usr/bin/env python3
"""
Quick test of the simple video server
"""

import subprocess
import time
import requests
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_simple_server():
    """Test the simple video server"""
    
    logger.info("🧪 Testing Simple Video Server")
    
    # Start server in background
    def start_server():
        subprocess.run(['python', 'simple_video_server.py'])
    
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Wait for startup
    time.sleep(3)
    
    # Test health endpoint
    try:
        response = requests.get('http://127.0.0.1:8888/health', timeout=5)
        if response.status_code == 200:
            logger.info("✅ Simple server health check passed!")
            logger.info(f"Response: {response.json()}")
        else:
            logger.error(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Cannot connect to simple server: {e}")
        return False
    
    # Test video listing
    try:
        response = requests.get('http://127.0.0.1:8888/videos', timeout=5)
        if response.status_code == 200:
            videos = response.json()
            logger.info(f"✅ Video listing works! Found {len(videos)} videos")
        else:
            logger.warning(f"⚠️ Video listing returned: {response.status_code}")
    except Exception as e:
        logger.warning(f"⚠️ Video listing failed: {e}")
    
    logger.info("🎉 Simple server test completed!")
    return True

if __name__ == '__main__':
    test_simple_server()