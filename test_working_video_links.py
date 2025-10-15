#!/usr/bin/env python3
"""
Test working video links with local video server
"""

import os
import sys
import time
import requests
import logging
import threading
import cv2
import numpy as np
import base64
from datetime import datetime

# Add current directory to path
sys.path.append('.')

from alerts import send_security_alert_with_video
from local_video_server import start_server, BASE_URL

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_server_running():
    """Check if video server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def start_server_if_needed():
    """Start video server if not already running"""
    if check_server_running():
        logger.info("✅ Video server is already running")
        return True
    
    logger.info("🚀 Starting video server...")
    
    # Start server in background
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    for i in range(10):
        time.sleep(1)
        if check_server_running():
            logger.info(f"✅ Video server started after {i+1} seconds")
            return True
    
    logger.error("❌ Failed to start video server")
    return False


def create_test_frames(count=15):
    """Create test frames for video"""
    frames = []
    
    for i in range(count):
        # Create a realistic security incident frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add store scene
        frame[400:, :] = [80, 80, 80]  # Floor
        cv2.rectangle(frame, (50, 100), (150, 400), (120, 120, 120), -1)  # Shelf
        cv2.rectangle(frame, (490, 100), (590, 400), (120, 120, 120), -1)  # Shelf 2
        
        # Add products on shelves
        for shelf_x in [50, 490]:
            for y in range(120, 380, 40):
                cv2.rectangle(frame, (shelf_x + 10, y), (shelf_x + 40, y + 30), (200, 150, 100), -1)
        
        # Add moving person (suspicious behavior)
        person_x = int(200 + 200 * (i / count))
        person_y = 350
        
        # Draw person
        cv2.circle(frame, (person_x, person_y - 50), 15, (255, 200, 150), -1)  # Head
        cv2.line(frame, (person_x, person_y - 35), (person_x, person_y), (255, 200, 150), 8)  # Body
        cv2.line(frame, (person_x, person_y - 20), (person_x - 20, person_y - 10), (255, 200, 150), 5)  # Arms
        cv2.line(frame, (person_x, person_y - 20), (person_x + 20, person_y - 10), (255, 200, 150), 5)
        cv2.line(frame, (person_x, person_y), (person_x - 15, person_y + 30), (255, 200, 150), 5)  # Legs
        cv2.line(frame, (person_x, person_y), (person_x + 15, person_y + 30), (255, 200, 150), 5)
        
        # Add suspicious behavior indicators
        if i > 8:
            cv2.putText(frame, "COMPORTEMENT SUSPECT", (10, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            # Show item being concealed
            if person_x > 180 and person_x < 220:
                cv2.rectangle(frame, (person_x + 10, person_y - 15), (person_x + 25, person_y - 5), (255, 255, 0), -1)
        
        # Add camera overlay
        cv2.putText(frame, "CAM-01 MAGASIN SECTION A", (10, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # Add timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(frame, timestamp, (10, 460), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Add frame counter
        cv2.putText(frame, f"Frame {i + 1:03d}", (550, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Encode to base64
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        frames.append({
            'frame_data': frame_base64,
            'frame_count': i + 1,
            'timestamp': datetime.now().isoformat()
        })
    
    return frames


def test_working_video_email():
    """Test sending email with working video link"""
    logger.info("📧 Testing Working Video Email")
    logger.info("=" * 40)
    
    try:
        # Create incident frames
        frames = create_test_frames(15)
        
        incident_data = {
            'incident_type': 'vol_à_létalage',
            'risk_level': 'HIGH',
            'analysis': 'Client observé en train de dissimuler des articles dans ses vêtements près de la section A. Comportement suspect confirmé avec un niveau de confiance élevé.',
            'frame_count': 15,
            'confidence': 0.94
        }
        
        message = """
🚨 INCIDENT DE SÉCURITÉ DÉTECTÉ - SECTION A

Un comportement suspect a été détecté par le système de surveillance IA.
Le client semble dissimuler des articles sans passer en caisse.

⚠️ INTERVENTION IMMÉDIATE REQUISE
Action recommandée: Intervention du personnel de sécurité.

Les preuves vidéo sont disponibles via le lien sécurisé ci-dessous.
"""
        
        logger.info("Sending security alert with working video link...")
        result = send_security_alert_with_video(message, frames, incident_data)
        
        if result['success']:
            logger.info("✅ Email sent successfully!")
            logger.info(f"   Recipient: {result['recipient']}")
            logger.info(f"   Video Link Provided: {result.get('video_link_provided', False)}")
            
            if result.get('video_link_info'):
                video_info = result['video_link_info']
                video_link = video_info['private_link']
                
                logger.info(f"   Video ID: {video_info['video_id']}")
                logger.info(f"   Working Link: {video_link}")
                logger.info(f"   Expiration: {video_info['expiration_time']}")
                
                # Test the link
                logger.info("\n🔗 Testing video link...")
                try:
                    # Extract token from link
                    if '?token=' in video_link:
                        token = video_link.split('?token=')[1]
                        video_id = video_info['video_id']
                        
                        # Test info endpoint
                        info_url = f"{BASE_URL}/video/{video_id}/info?token={token}"
                        info_response = requests.get(info_url, timeout=5)
                        
                        if info_response.status_code == 200:
                            info_data = info_response.json()
                            logger.info("✅ Video link is working!")
                            logger.info(f"   File size: {info_data['size_mb']} MB")
                            logger.info(f"   Available: {info_data['available']}")
                            
                            # Test actual video access
                            video_response = requests.head(video_link, timeout=5)
                            if video_response.status_code == 200:
                                logger.info("✅ Video file is accessible!")
                                logger.info(f"   Content-Type: {video_response.headers.get('Content-Type', 'unknown')}")
                            else:
                                logger.warning(f"⚠️  Video file access returned: {video_response.status_code}")
                        else:
                            logger.error(f"❌ Video link test failed: {info_response.status_code}")
                    
                except Exception as e:
                    logger.error(f"❌ Error testing video link: {e}")
            
            return True
        else:
            logger.error(f"❌ Email sending failed: {result['error']}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


def main():
    """Main test function"""
    logger.info("🎬 WORKING VIDEO LINKS TEST")
    logger.info("=" * 50)
    
    # Start video server if needed
    if not start_server_if_needed():
        logger.error("❌ Cannot start video server - test aborted")
        return False
    
    # Test working video email
    success = test_working_video_email()
    
    if success:
        logger.info("\n🎉 SUCCESS!")
        logger.info("📧 Check your email for the security alert")
        logger.info("🔗 Click the video link - it should work now!")
        logger.info(f"🌐 Video server running at: {BASE_URL}")
        
        logger.info("\n📋 INSTRUCTIONS:")
        logger.info("1. Check your email inbox")
        logger.info("2. Find the security alert email")
        logger.info("3. Click on the 'Lien privé sécurisé' link")
        logger.info("4. Video should play in your browser")
        
        # Keep server running for a while
        logger.info("\n⏳ Keeping server running for 5 minutes...")
        logger.info("   (Press Ctrl+C to stop early)")
        
        try:
            for i in range(300):  # 5 minutes
                time.sleep(1)
                if i % 60 == 0:  # Every minute
                    logger.info(f"   Server still running... {5 - i//60} minutes remaining")
        except KeyboardInterrupt:
            logger.info("\n👋 Stopping server...")
        
        return True
    else:
        logger.error("\n❌ Test failed!")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)