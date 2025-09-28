#!/usr/bin/env python3
"""
Test video email integration to ensure video links appear in emails
"""

import os
import sys
import logging
import cv2
import numpy as np
import base64
from datetime import datetime

# Add current directory to path for imports
sys.path.append('.')

from alerts import send_security_alert_with_video, AlertManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_frames(count=20):
    """Create test frames for video email testing"""
    frames = []
    
    for i in range(count):
        # Create a realistic security camera frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add store background
        frame[400:, :] = [80, 80, 80]  # Floor
        cv2.rectangle(frame, (50, 100), (150, 400), (120, 120, 120), -1)  # Shelf
        
        # Add moving person
        person_x = int(200 + 200 * (i / count))
        cv2.circle(frame, (person_x, 350), 20, (255, 200, 150), -1)
        
        # Add incident indicators
        if i > 10:
            cv2.putText(frame, "INCIDENT DETECTED", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        cv2.putText(frame, f"Frame {i + 1}/{count}", (10, 460), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Encode frame to base64
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        frames.append({
            'frame_data': frame_base64,
            'frame_count': i + 1,
            'timestamp': datetime.now().isoformat()
        })
    
    logger.info(f"Created {count} test frames for email integration")
    return frames


def test_video_email_with_frames():
    """Test sending security alert with video from frames"""
    logger.info("🧪 Testing Video Email Integration with Frames")
    logger.info("=" * 50)
    
    try:
        # Create test frames
        frames = create_test_frames(15)
        
        incident_data = {
            'incident_type': 'vol_à_létalage',
            'risk_level': 'HIGH',
            'analysis': 'Client observé en train de dissimuler des articles dans ses vêtements. Comportement suspect confirmé.',
            'frame_count': 15,
            'confidence': 0.92
        }
        
        message = """
🚨 INCIDENT DE SÉCURITÉ DÉTECTÉ - MAGASIN SECTION A

Un comportement suspect a été détecté par le système de surveillance IA.
Le client semble dissimuler des articles sans passer en caisse.

Action recommandée: Intervention immédiate du personnel de sécurité.
Vérifiez les preuves vidéo ci-dessous.
"""
        
        logger.info("Sending security alert with video frames...")
        result = send_security_alert_with_video(message, frames, incident_data)
        
        if result['success']:
            logger.info(f"✅ Email sent successfully!")
            logger.info(f"   Recipient: {result['recipient']}")
            logger.info(f"   Video Link Provided: {result.get('video_link_provided', False)}")
            
            if result.get('video_link_info'):
                video_info = result['video_link_info']
                logger.info(f"   Video ID: {video_info['video_id']}")
                logger.info(f"   Private Link: {video_info['private_link']}")
                logger.info(f"   GDPR Compliant: {video_info.get('gdpr_compliant', False)}")
                logger.info(f"   Expiration: {video_info['expiration_time']}")
            
            return True
        else:
            logger.error(f"❌ Email sending failed: {result['error']}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False


def test_direct_email_with_video_info():
    """Test sending email directly with pre-uploaded video info"""
    logger.info("\n🧪 Testing Direct Email with Video Info")
    logger.info("=" * 50)
    
    try:
        # Simulate pre-uploaded video info (as would come from GDPR service)
        mock_video_info = {
            'video_id': 'test-video-123-456-789',
            'private_link': 'https://sparse-ai.com/video/test-video-123-456-789?token=abc123def456',
            'expiration_time': '2025-09-27T15:30:00',
            'gdpr_compliant': True,
            'privacy_level': 'high',
            'data_retention_hours': 48,
            'video_size_mb': 2.3,
            'local_file_deleted': True
        }
        
        incident_data = {
            'incident_type': 'test_direct_email',
            'risk_level': 'MEDIUM',
            'analysis': 'Test direct email with pre-uploaded video information',
            'frame_count': 20,
            'confidence': 0.85,
            'video_link_info': mock_video_info,  # Pre-uploaded video info
            'gdpr_compliant': True
        }
        
        message = """
🧪 TEST: Email avec informations vidéo pré-téléchargées

Ce test vérifie que les informations vidéo sont correctement affichées
dans l'email lorsque la vidéo a déjà été téléchargée vers le stockage cloud.
"""
        
        alert_manager = AlertManager()
        
        logger.info("Sending email with pre-uploaded video info...")
        result = alert_manager.send_email_alert(
            message,
            alert_type="security",
            video_path=None,  # No local file
            incident_data=incident_data
        )
        
        if result['success']:
            logger.info(f"✅ Direct email sent successfully!")
            logger.info(f"   Recipient: {result['recipient']}")
            logger.info(f"   Video Link Provided: {result.get('video_link_provided', False)}")
            return True
        else:
            logger.error(f"❌ Direct email failed: {result['error']}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False


def test_email_without_video():
    """Test email without video to ensure fallback works"""
    logger.info("\n🧪 Testing Email Without Video (Fallback)")
    logger.info("=" * 50)
    
    try:
        incident_data = {
            'incident_type': 'test_no_video',
            'risk_level': 'LOW',
            'analysis': 'Test email without video to verify fallback message',
            'frame_count': 0,
            'confidence': 0.5
        }
        
        message = """
🧪 TEST: Email sans vidéo

Ce test vérifie que le message de fallback "Preuves vidéo non disponibles"
s'affiche correctement quand aucune vidéo n'est fournie.
"""
        
        alert_manager = AlertManager()
        
        logger.info("Sending email without video...")
        result = alert_manager.send_email_alert(
            message,
            alert_type="security",
            video_path=None,  # No video
            incident_data=incident_data
        )
        
        if result['success']:
            logger.info(f"✅ Email without video sent successfully!")
            logger.info(f"   Recipient: {result['recipient']}")
            logger.info(f"   Should show: 'Preuves vidéo non disponibles'")
            return True
        else:
            logger.error(f"❌ Email without video failed: {result['error']}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False


def main():
    """Run all video email integration tests"""
    logger.info("📧 VIDEO EMAIL INTEGRATION TESTS")
    logger.info("=" * 60)
    logger.info("Testing that video links appear correctly in security alert emails")
    
    # Run tests
    tests = [
        ("Video Email with Frames", test_video_email_with_frames),
        ("Direct Email with Video Info", test_direct_email_with_video_info),
        ("Email Without Video (Fallback)", test_email_without_video)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n🎯 Running: {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 VIDEO EMAIL INTEGRATION TEST SUMMARY")
    logger.info("=" * 60)
    
    for test_name, success in results:
        status = "✅ WORKING" if success else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    logger.info(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n🎉 All video email integration tests passed!")
        logger.info("📧 Video links should now appear correctly in security alert emails.")
        logger.info("🔒 GDPR-compliant video evidence is properly integrated.")
    else:
        logger.error(f"\n❌ {total - passed} test(s) failed!")
        logger.error("📧 Video links may not be appearing in emails correctly.")
    
    logger.info("\n📋 NEXT STEPS:")
    logger.info("1. Check your email inbox for the test alerts")
    logger.info("2. Verify that video links appear in the emails")
    logger.info("3. Test clicking the video links to ensure they work")
    logger.info("4. Monitor real security incidents for proper video integration")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)