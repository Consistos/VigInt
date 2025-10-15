#!/usr/bin/env python3
"""
Create a working video link that you can click in your email
"""

import os
import sys
import json
import hashlib
import logging
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.append('.')

from alerts import send_security_alert_with_video
from mock_sparse_ai_service import MockSparseAIService


def create_working_video_link():
    """Create a working video link and start the server"""
    logger.info("🔗 Creating Working Video Link")
    logger.info("=" * 40)
    
    # Check if we have any videos in mock storage
    storage_dir = Path('mock_sparse_ai_cloud')
    video_files = list(storage_dir.glob("*.mp4"))
    
    if not video_files:
        logger.info("📹 No videos found, creating a test video...")
        
        # Create test frames and send alert to generate video
        import cv2
        import numpy as np
        import base64
        
        frames = []
        for i in range(10):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:, :] = [50, 100, 150]
            cv2.putText(frame, f"TEST VIDEO FRAME {i+1}", (50, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            _, buffer = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            frames.append({
                'frame_data': frame_base64,
                'frame_count': i + 1,
                'timestamp': datetime.now().isoformat()
            })
        
        # Send alert to create video
        incident_data = {
            'incident_type': 'test_working_link',
            'risk_level': 'MEDIUM',
            'analysis': 'Test video for working link demonstration',
            'frame_count': 10,
            'confidence': 0.8
        }
        
        message = "🧪 TEST: Création d'un lien vidéo fonctionnel"
        
        result = send_security_alert_with_video(message, frames, incident_data)
        
        if not result['success']:
            logger.error("❌ Failed to create test video")
            return None
        
        video_info = result.get('video_link_info')
        if not video_info:
            logger.error("❌ No video info returned")
            return None
    else:
        logger.info(f"📹 Found {len(video_files)} existing videos")
        
        # Use the first video
        video_file = video_files[0]
        metadata_file = video_file.with_suffix('.mp4.json')
        
        if not metadata_file.exists():
            logger.error(f"❌ Metadata file not found: {metadata_file}")
            return None
        
        # Read metadata
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Generate working link
        video_id = metadata['video_id']
        expiration_time = metadata['expiration_time']
        
        # Generate token
        token = hashlib.sha256(f"{video_id}:{expiration_time}:mock-key".encode()).hexdigest()[:32]
        
        video_info = {
            'video_id': video_id,
            'private_link': f"http://127.0.0.1:8888/video/{video_id}?token={token}",
            'expiration_time': expiration_time,
            'local_path': str(video_file)
        }
    
    return video_info


def start_video_server_background():
    """Start video server in background"""
    logger.info("🚀 Starting video server...")
    
    # Start server as background process
    try:
        process = subprocess.Popen([
            sys.executable, 'local_video_server.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for server to start
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            logger.info("✅ Video server started successfully")
            return process
        else:
            stdout, stderr = process.communicate()
            logger.error(f"❌ Server failed to start: {stderr.decode()}")
            return None
    
    except Exception as e:
        logger.error(f"❌ Error starting server: {e}")
        return None


def main():
    """Main function"""
    logger.info("🎬 WORKING VIDEO LINK CREATOR")
    logger.info("=" * 50)
    
    # Create working video link
    video_info = create_working_video_link()
    if not video_info:
        logger.error("❌ Failed to create working video link")
        return
    
    # Start video server
    server_process = start_video_server_background()
    if not server_process:
        logger.error("❌ Failed to start video server")
        return
    
    try:
        logger.info("✅ Working video link created!")
        logger.info(f"📹 Video ID: {video_info['video_id']}")
        logger.info(f"🔗 Working Link: {video_info['private_link']}")
        logger.info(f"⏰ Expires: {video_info['expiration_time']}")
        
        logger.info("\n📧 EMAIL INSTRUCTIONS:")
        logger.info("1. Check your email for the security alert")
        logger.info("2. Look for 'PREUVES VIDÉO DISPONIBLES (CONFORME RGPD)'")
        logger.info("3. Click on 'Lien privé sécurisé'")
        logger.info("4. Video should play in your browser")
        
        logger.info("\n🌐 DIRECT ACCESS:")
        logger.info(f"You can also access the video directly at:")
        logger.info(f"{video_info['private_link']}")
        
        logger.info("\n🔄 Server is running... Press Ctrl+C to stop")
        
        # Keep server running
        while True:
            time.sleep(1)
            
            # Check if server process is still alive
            if server_process.poll() is not None:
                logger.error("❌ Video server stopped unexpectedly")
                break
    
    except KeyboardInterrupt:
        logger.info("\n👋 Stopping video server...")
        server_process.terminate()
        server_process.wait()
        logger.info("✅ Server stopped")


if __name__ == '__main__':
    main()