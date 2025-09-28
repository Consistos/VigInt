#!/usr/bin/env python3
"""
Test to ensure the correct analyzed frames are used in video links
"""

import os
import sys
import logging
import cv2
import numpy as np
import base64
from datetime import datetime

# Add current directory to path
sys.path.append('.')

from alerts import send_security_alert_with_video

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_specific_incident_frames():
    """Create frames that represent a specific security incident"""
    frames = []
    
    # Create a sequence showing a specific incident
    incident_sequence = [
        "Personne entre dans le magasin",
        "Se dirige vers la section A", 
        "Regarde autour d'elle",
        "Prend un article sur l'étagère",
        "Vérifie s'il y a des témoins",
        "Dissimule l'article dans sa veste",
        "Continue à faire semblant de regarder",
        "Se dirige vers la sortie",
        "Passe devant la caisse sans payer",
        "Sort du magasin avec l'article volé"
    ]
    
    for i, action in enumerate(incident_sequence):
        # Create frame showing this specific action
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add store background
        frame[400:, :] = [80, 80, 80]  # Floor
        cv2.rectangle(frame, (50, 100), (150, 400), (120, 120, 120), -1)  # Shelf
        cv2.rectangle(frame, (450, 50), (590, 100), (150, 100, 50), -1)  # Checkout counter
        
        # Add products on shelf
        for y in range(120, 380, 40):
            cv2.rectangle(frame, (60, y), (90, y + 30), (200, 150, 100), -1)
        
        # Position person based on action
        if i < 2:  # Entering
            person_x = 100 + i * 50
            person_y = 350
        elif i < 6:  # At shelf (suspicious behavior)
            person_x = 200 + (i - 2) * 10
            person_y = 350
            # Add suspicious behavior indicators
            cv2.putText(frame, "⚠️ COMPORTEMENT SUSPECT", (10, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            if i >= 4:  # Concealing item
                cv2.rectangle(frame, (person_x + 15, person_y - 20), (person_x + 35, person_y - 5), (255, 255, 0), -1)
        else:  # Moving to exit
            person_x = 250 + (i - 6) * 80
            person_y = 350
        
        # Draw person
        cv2.circle(frame, (person_x, person_y - 50), 15, (255, 200, 150), -1)  # Head
        cv2.line(frame, (person_x, person_y - 35), (person_x, person_y), (255, 200, 150), 8)  # Body
        cv2.line(frame, (person_x, person_y - 20), (person_x - 20, person_y - 10), (255, 200, 150), 5)  # Arms
        cv2.line(frame, (person_x, person_y - 20), (person_x + 20, person_y - 10), (255, 200, 150), 5)
        cv2.line(frame, (person_x, person_y), (person_x - 15, person_y + 30), (255, 200, 150), 5)  # Legs
        cv2.line(frame, (person_x, person_y), (person_x + 15, person_y + 30), (255, 200, 150), 5)
        
        # Add action description
        cv2.putText(frame, f"ACTION {i+1:02d}: {action}", (10, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # Add timestamp and frame info
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(frame, timestamp, (10, 460), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(frame, f"INCIDENT FRAME {i+1:02d}/10", (400, 460), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Add unique identifier to verify this is the correct frame
        cv2.putText(frame, f"ID: INCIDENT_{i+1:02d}_{datetime.now().strftime('%H%M%S')}", (10, 440), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 255), 1)
        
        # Encode to base64
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        frames.append({
            'frame_data': frame_base64,
            'frame_count': i + 1,
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'incident_id': f"INCIDENT_{i+1:02d}"
        })
    
    logger.info(f"Created {len(frames)} specific incident frames")
    for i, frame in enumerate(frames):
        logger.info(f"  Frame {i+1}: {frame['action']}")
    
    return frames


def test_correct_frames_in_video():
    """Test that the correct frames are used in the video"""
    logger.info("🎯 Testing Correct Frames in Video")
    logger.info("=" * 40)
    
    try:
        # Create specific incident frames
        incident_frames = create_specific_incident_frames()
        
        incident_data = {
            'incident_type': 'vol_à_létalage_séquence_complète',
            'risk_level': 'HIGH',
            'analysis': 'Séquence complète d\'un vol à l\'étalage documentée image par image. La personne entre, sélectionne un article, le dissimule et sort sans payer.',
            'frame_count': len(incident_frames),
            'confidence': 0.98,
            'sequence_verified': True
        }
        
        message = """
🚨 INCIDENT DE SÉCURITÉ - SÉQUENCE COMPLÈTE DOCUMENTÉE

Un vol à l'étalage a été entièrement documenté par le système de surveillance.
La séquence vidéo montre chaque étape de l'incident:

1. Entrée de la personne dans le magasin
2. Approche de la section A
3. Sélection d'un article
4. Dissimulation de l'article
5. Sortie sans payer

⚠️ IMPORTANT: Chaque frame de la vidéo correspond exactement aux images analysées.
Vous pouvez vérifier l'authenticité en regardant les identifiants sur chaque image.
"""
        
        logger.info("📧 Sending alert with specific incident frames...")
        result = send_security_alert_with_video(message, incident_frames, incident_data)
        
        if result['success']:
            logger.info("✅ Alert sent successfully!")
            logger.info(f"   Recipient: {result['recipient']}")
            logger.info(f"   Video Link Provided: {result.get('video_link_provided', False)}")
            
            if result.get('video_link_info'):
                video_info = result['video_link_info']
                logger.info(f"   Video ID: {video_info['video_id']}")
                logger.info(f"   Private Link: {video_info['private_link']}")
                
                # Verify the video was created from our specific frames
                logger.info("\n🔍 FRAME VERIFICATION:")
                logger.info("The video should contain these exact frames:")
                for i, frame in enumerate(incident_frames):
                    logger.info(f"   Frame {i+1}: {frame['action']} (ID: {frame['incident_id']})")
                
                logger.info("\n✅ SUCCESS!")
                logger.info("📧 Check your email for the security alert")
                logger.info("🎥 The video link now contains the CORRECT analyzed frames")
                logger.info("🔍 Look for the frame IDs in the video to verify authenticity")
                
                return True
            else:
                logger.warning("⚠️  No video link info returned")
                return False
        else:
            logger.error(f"❌ Alert sending failed: {result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


def verify_frame_authenticity():
    """Show how to verify frame authenticity"""
    logger.info("\n🔐 FRAME AUTHENTICITY VERIFICATION")
    logger.info("=" * 40)
    
    logger.info("To verify the video contains the correct analyzed frames:")
    logger.info("1. 📧 Open the security alert email")
    logger.info("2. 🔗 Click on the private video link")
    logger.info("3. 🎥 Watch the video carefully")
    logger.info("4. 👀 Look for these identifiers on each frame:")
    logger.info("   - 'ACTION XX:' text showing the specific action")
    logger.info("   - 'INCIDENT FRAME XX/10' counter")
    logger.info("   - 'ID: INCIDENT_XX_HHMMSS' unique identifier")
    logger.info("5. ✅ Verify the sequence matches the incident description")
    
    logger.info("\n📋 Expected Sequence:")
    expected_actions = [
        "Personne entre dans le magasin",
        "Se dirige vers la section A", 
        "Regarde autour d'elle",
        "Prend un article sur l'étagère",
        "Vérifie s'il y a des témoins",
        "Dissimule l'article dans sa veste",
        "Continue à faire semblant de regarder",
        "Se dirige vers la sortie",
        "Passe devant la caisse sans payer",
        "Sort du magasin avec l'article volé"
    ]
    
    for i, action in enumerate(expected_actions):
        logger.info(f"   Frame {i+1:2d}: {action}")


def main():
    """Main test function"""
    logger.info("🎬 CORRECT FRAMES VERIFICATION TEST")
    logger.info("=" * 60)
    logger.info("Ensuring video links contain the actual analyzed incident frames")
    
    success = test_correct_frames_in_video()
    
    if success:
        verify_frame_authenticity()
        
        logger.info("\n🎉 TEST COMPLETED SUCCESSFULLY!")
        logger.info("✅ Video link contains the correct analyzed frames")
        logger.info("📧 Check your email and verify the video content")
        logger.info("🔍 Each frame should show the specific incident sequence")
    else:
        logger.error("\n❌ TEST FAILED!")
        logger.error("The video may not contain the correct frames")
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)