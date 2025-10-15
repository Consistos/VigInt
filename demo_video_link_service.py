#!/usr/bin/env python3
"""
Demo: Video Link Service Integration
Shows how the system now sends private video links instead of email attachments
"""

import os
import sys
import logging
import tempfile
import cv2
import numpy as np
import base64
from datetime import datetime

# Add current directory to path for imports
sys.path.append('.')

from video_link_service import VideoLinkService, upload_incident_video
from alerts import send_security_alert_with_video

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_demo_frames(count=40):
    """Create demo frames showing a security incident"""
    frames = []
    
    for i in range(count):
        # Create a realistic security camera frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add store background (gray floor, shelves)
        frame[400:, :] = [80, 80, 80]  # Floor
        cv2.rectangle(frame, (50, 100), (150, 400), (120, 120, 120), -1)  # Shelf 1
        cv2.rectangle(frame, (490, 100), (590, 400), (120, 120, 120), -1)  # Shelf 2
        
        # Add "products" on shelves
        for shelf_x in [50, 490]:
            for y in range(120, 380, 40):
                cv2.rectangle(frame, (shelf_x + 10, y), (shelf_x + 40, y + 30), (200, 150, 100), -1)
        
        # Add moving person (simulating suspicious behavior)
        person_x = int(200 + 200 * (i / count))
        person_y = 350
        
        # Draw person (simple stick figure)
        cv2.circle(frame, (person_x, person_y - 50), 15, (255, 200, 150), -1)  # Head
        cv2.line(frame, (person_x, person_y - 35), (person_x, person_y), (255, 200, 150), 8)  # Body
        cv2.line(frame, (person_x, person_y - 20), (person_x - 20, person_y - 10), (255, 200, 150), 5)  # Arm 1
        cv2.line(frame, (person_x, person_y - 20), (person_x + 20, person_y - 10), (255, 200, 150), 5)  # Arm 2
        cv2.line(frame, (person_x, person_y), (person_x - 15, person_y + 30), (255, 200, 150), 5)  # Leg 1
        cv2.line(frame, (person_x, person_y), (person_x + 15, person_y + 30), (255, 200, 150), 5)  # Leg 2
        
        # Add suspicious behavior indicators in later frames
        if i > 20:
            # Person near shelf, "taking" items
            if person_x > 180 and person_x < 220:
                cv2.putText(frame, "SUSPICIOUS ACTIVITY", (10, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                # Show item being concealed
                cv2.rectangle(frame, (person_x + 10, person_y - 15), (person_x + 25, person_y - 5), (255, 255, 0), -1)
        
        # Add camera info overlay
        cv2.putText(frame, "CAM-01 STORE SECTION A", (10, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Add timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(frame, timestamp, (10, 460), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add frame counter
        cv2.putText(frame, f"Frame {i + 1:03d}", (550, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Encode frame to base64
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        frames.append({
            'frame_data': frame_base64,
            'frame_count': i + 1,
            'timestamp': datetime.now().isoformat()
        })
    
    logger.info(f"Created {count} demo security frames")
    return frames


def demo_video_link_workflow():
    """Demonstrate the complete video link workflow"""
    logger.info("🎬 DEMO: Video Link Service Workflow")
    logger.info("=" * 60)
    
    # Step 1: Create incident frames
    logger.info("📹 Step 1: Creating security incident frames...")
    frames = create_demo_frames(40)
    
    # Step 2: Prepare incident data
    incident_data = {
        'incident_type': 'vol à l\'étalage',  # Shoplifting in French
        'risk_level': 'HIGH',
        'analysis': 'Client observé en train de dissimuler des articles dans ses vêtements près de la section A. Comportement suspect détecté avec un niveau de confiance élevé.',
        'frame_count': 40,
        'confidence': 0.92
    }
    
    logger.info("🔍 Step 2: Incident Analysis Complete")
    logger.info(f"   Type: {incident_data['incident_type']}")
    logger.info(f"   Risk Level: {incident_data['risk_level']}")
    logger.info(f"   Confidence: {incident_data['confidence']}")
    
    # Step 3: Send alert with video link
    logger.info("📧 Step 3: Sending security alert with video link...")
    
    message = """
🚨 INCIDENT DE SÉCURITÉ DÉTECTÉ - SECTION A

Un comportement suspect a été détecté par le système de surveillance IA.
Le client semble dissimuler des articles sans passer en caisse.

Action recommandée: Intervention immédiate du personnel de sécurité.
"""
    
    try:
        result = send_security_alert_with_video(message, frames, incident_data)
        
        if result['success']:
            logger.info("✅ Step 3: Alert sent successfully!")
            logger.info(f"   📧 Email sent to: {result['recipient']}")
            logger.info(f"   🔗 Video link included: {result.get('video_link_provided', False)}")
            
            if result.get('video_link_info'):
                video_info = result['video_link_info']
                logger.info(f"   🎥 Video ID: {video_info['video_id']}")
                logger.info(f"   🔒 Private Link: {video_info['private_link']}")
                logger.info(f"   ⏰ Expires: {video_info['expiration_time']}")
                logger.info(f"   🔐 File Hash: {video_info['file_hash'][:16]}...")
            
            return True
        else:
            logger.error(f"❌ Step 3: Alert failed: {result['error']}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Step 3: Exception occurred: {e}")
        return False


def demo_direct_upload():
    """Demonstrate direct video upload to sparse-ai.com"""
    logger.info("\n🎬 DEMO: Direct Video Upload")
    logger.info("=" * 60)
    
    # Create a temporary video file
    logger.info("📹 Creating temporary demo video...")
    
    temp_fd, temp_path = tempfile.mkstemp(suffix='.mp4', prefix='demo_incident_')
    os.close(temp_fd)
    
    try:
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_path, fourcc, 25, (640, 480))
        
        if not out.isOpened():
            logger.error("Failed to create video writer")
            return False
        
        # Create 3 seconds of demo video
        for frame_num in range(75):  # 3 seconds at 25fps
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # Add store scene
            frame[400:, :] = [80, 80, 80]  # Floor
            cv2.rectangle(frame, (50, 100), (150, 400), (120, 120, 120), -1)  # Shelf
            
            # Add moving person
            person_x = int(200 + 200 * (frame_num / 75))
            cv2.circle(frame, (person_x, 350), 20, (255, 200, 150), -1)
            
            # Add overlay
            cv2.putText(frame, "DEMO SECURITY INCIDENT", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, f"Frame {frame_num + 1}/75", (10, 460), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            out.write(frame)
        
        out.release()
        
        # Upload video
        logger.info("☁️  Uploading video to sparse-ai.com...")
        
        incident_data = {
            'incident_type': 'demonstration',
            'risk_level': 'DEMO',
            'analysis': 'This is a demonstration of the video link service functionality',
            'frame_count': 75,
            'confidence': 1.0
        }
        
        result = upload_incident_video(temp_path, incident_data, expiration_hours=1)
        
        if result['success']:
            logger.info("✅ Video upload successful!")
            logger.info(f"   🎥 Video ID: {result['video_id']}")
            logger.info(f"   🔒 Private Link: {result['private_link']}")
            logger.info(f"   ⏰ Expires in: 1 hour")
            logger.info(f"   📁 File Size: {os.path.getsize(temp_path) / (1024*1024):.1f} MB")
            return True
        else:
            logger.error(f"❌ Upload failed: {result['error']}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        return False
    
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)
            logger.info("🧹 Temporary video cleaned up")


def show_configuration_info():
    """Show current configuration for video links"""
    logger.info("\n⚙️  CONFIGURATION INFO")
    logger.info("=" * 60)
    
    service = VideoLinkService()
    
    logger.info(f"🌐 Sparse AI Base URL: {service.base_url}")
    logger.info(f"🔑 API Key Configured: {'Yes' if service.api_key and service.api_key != 'your-sparse-ai-api-key-here' else 'No'}")
    logger.info(f"⏰ Default Expiration: {service.default_expiration_hours} hours")
    logger.info(f"📤 Upload Endpoint: {service.upload_endpoint}")
    logger.info(f"🔗 Link Endpoint: {service.link_endpoint}")
    
    if not service.api_key or service.api_key == 'your-sparse-ai-api-key-here':
        logger.warning("⚠️  Sparse AI API key not configured!")
        logger.warning("   Set SPARSE_AI_API_KEY environment variable or update config.ini")
        logger.warning("   Video uploads will fail until configured")
    else:
        logger.info("✅ Video link service ready!")


def main():
    """Run the video link service demonstration"""
    logger.info("🎬 VIGINT VIDEO LINK SERVICE DEMONSTRATION")
    logger.info("=" * 60)
    logger.info("This demo shows how the system now sends private video links")
    logger.info("instead of large email attachments for security incidents.")
    logger.info("")
    
    # Show configuration
    show_configuration_info()
    
    # Run demos
    demos = [
        ("Complete Workflow (Frames → Video → Email)", demo_video_link_workflow),
        ("Direct Video Upload", demo_direct_upload)
    ]
    
    results = []
    for demo_name, demo_func in demos:
        logger.info(f"\n🎯 Running: {demo_name}")
        try:
            success = demo_func()
            results.append((demo_name, success))
        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
            results.append((demo_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 DEMO SUMMARY")
    logger.info("=" * 60)
    
    for demo_name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"{demo_name}: {status}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    logger.info(f"\n🎯 Overall: {passed}/{total} demos completed successfully")
    
    if passed == total:
        logger.info("\n🎉 All demos completed! The video link service is working.")
        logger.info("📧 Security alerts now include private video links instead of attachments.")
        logger.info("🔒 Videos are securely hosted on sparse-ai.com with expiring links.")
    else:
        logger.warning(f"\n⚠️  {total - passed} demo(s) failed. Check configuration.")
    
    logger.info("\n📋 NEXT STEPS:")
    logger.info("1. Configure your Sparse AI API key in .env or config.ini")
    logger.info("2. Test with real security incidents")
    logger.info("3. Monitor video link expiration and cleanup")
    logger.info("4. Customize link expiration times as needed")


if __name__ == '__main__':
    main()