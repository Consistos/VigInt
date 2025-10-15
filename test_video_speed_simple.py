#!/usr/bin/env python3
"""
Simple test for video speed fix without AI analysis
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

from gdpr_compliant_video_service import create_and_upload_video_from_frames_gdpr

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_speed_test_frames(analysis_interval=5):
    """Create frames with timing information for speed testing"""
    frames = []
    
    # Create 6 frames representing 30 seconds of analysis (5s intervals)
    for i in range(6):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Background color
        frame[:, :] = [50, 100, 150]
        
        # Large time display
        elapsed_time = i * analysis_interval
        minutes = elapsed_time // 60
        seconds = elapsed_time % 60
        time_text = f"{minutes:02d}:{seconds:02d}"
        
        cv2.putText(frame, time_text, (150, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 4, (255, 255, 255), 10)
        
        # Frame info
        cv2.putText(frame, f"Frame {i+1}/6", (10, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3)
        cv2.putText(frame, f"Interval: {analysis_interval}s", (10, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Progress indicator
        progress = i / 5 if i < 5 else 1
        bar_width = int(600 * progress)
        cv2.rectangle(frame, (20, 400), (20 + bar_width, 430), (0, 255, 0), -1)
        cv2.rectangle(frame, (20, 400), (620, 430), (255, 255, 255), 3)
        
        # Encode to base64
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        frames.append({
            'frame_data': frame_base64,
            'frame_count': i + 1,
            'timestamp': datetime.now().isoformat(),
            'analysis_interval': analysis_interval,
            'elapsed_time': elapsed_time
        })
    
    return frames


def test_video_speed_direct():
    """Test video speed directly without email"""
    logger.info("🎬 Testing Video Speed Fix (Direct)")
    logger.info("=" * 50)
    
    try:
        # Create test frames with 5-second intervals
        frames = create_speed_test_frames(analysis_interval=5)
        
        incident_data = {
            'incident_type': 'speed_test',
            'risk_level': 'TEST',
            'analysis': 'Test de vitesse vidéo - 5 secondes par frame',
            'frame_count': len(frames),
            'confidence': 1.0
        }
        
        logger.info(f"Creating video with {len(frames)} frames (5s intervals)")
        logger.info("Expected video duration: ~6 seconds at proper speed")
        
        # Create video with correct FPS
        result = create_and_upload_video_from_frames_gdpr(
            frames, 
            incident_data, 
            expiration_hours=1,
            target_fps=0.2  # 1 frame every 5 seconds = 0.2 FPS
        )
        
        if result['success']:
            logger.info("✅ Video created successfully!")
            logger.info(f"   Video ID: {result['video_id']}")
            logger.info(f"   Private Link: {result['private_link']}")
            
            logger.info("\n🎯 SPEED TEST RESULTS:")
            logger.info("✅ Video created with 0.2 FPS (1 frame every 5 seconds)")
            logger.info("📹 Video should show time progressing: 00:00 → 00:05 → 00:10 → 00:15 → 00:20 → 00:25")
            logger.info("⏱️  Each frame should display for 5 seconds")
            
            logger.info(f"\n🔗 Test the video link:")
            logger.info(f"   {result['private_link']}")
            logger.info("\n📋 Verification:")
            logger.info("1. Click the link above")
            logger.info("2. Watch the time counter")
            logger.info("3. Each frame should show for 5 seconds")
            logger.info("4. Total video should be about 30 seconds long")
            
            return True
        else:
            logger.error(f"❌ Video creation failed: {result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


def main():
    """Main test function"""
    logger.info("🎬 SIMPLE VIDEO SPEED TEST")
    logger.info("=" * 50)
    logger.info("Testing video speed fix without AI analysis")
    
    success = test_video_speed_direct()
    
    if success:
        logger.info("\n🎉 SUCCESS!")
        logger.info("✅ Video speed fix appears to be working")
        logger.info("🔗 Click the video link to verify playback speed")
    else:
        logger.error("\n❌ FAILED!")
        logger.error("Video speed fix may not be working correctly")
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)