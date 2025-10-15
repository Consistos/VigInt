#!/usr/bin/env python3
"""
Final test for video speed - should be watchable but not too fast or slow
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


def create_watchable_test_frames(analysis_interval=5):
    """Create frames for watchable video speed testing"""
    frames = []
    
    # Create 8 frames representing different time points
    for i in range(8):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Background color
        frame[:, :] = [50, 100, 150]
        
        # Large time display showing progression
        elapsed_time = i * analysis_interval
        minutes = elapsed_time // 60
        seconds = elapsed_time % 60
        time_text = f"{minutes:02d}:{seconds:02d}"
        
        cv2.putText(frame, time_text, (120, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 5, (255, 255, 255), 12)
        
        # Frame info
        cv2.putText(frame, f"Frame {i+1}/8", (10, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3)
        cv2.putText(frame, f"Interval: {analysis_interval}s", (10, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Moving element to show speed
        circle_x = int(50 + 540 * (i / 7))  # Move across screen
        cv2.circle(frame, (circle_x, 350), 30, (255, 255, 0), -1)
        
        # Progress bar
        progress = i / 7 if i < 7 else 1
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


def test_watchable_video_speed():
    """Test that video plays at watchable speed"""
    logger.info("🎬 Testing Watchable Video Speed")
    logger.info("=" * 50)
    
    try:
        # Test with 5-second analysis interval
        frames = create_watchable_test_frames(analysis_interval=5)
        
        incident_data = {
            'incident_type': 'speed_test_watchable',
            'risk_level': 'TEST',
            'analysis': 'Test de vitesse vidéo - doit être regardable (ni trop rapide ni trop lente)',
            'frame_count': len(frames),
            'confidence': 1.0
        }
        
        logger.info(f"Creating video with {len(frames)} frames (5s intervals)")
        logger.info("Expected: Watchable speed - should show time progressing naturally")
        logger.info("Expected FPS: ~4.0 (good viewing speed for 5s intervals)")
        
        # Create video with automatic FPS calculation
        result = create_and_upload_video_from_frames_gdpr(
            frames, 
            incident_data, 
            expiration_hours=1
        )
        
        if result['success']:
            logger.info("✅ Video created successfully!")
            logger.info(f"   Video ID: {result['video_id']}")
            logger.info(f"   Private Link: {result['private_link']}")
            
            logger.info("\n🎯 WATCHABLE SPEED TEST:")
            logger.info("✅ Video should now play at watchable speed")
            logger.info("📹 Time should progress: 00:00 → 00:05 → 00:10 → 00:15 → 00:20 → 00:25 → 00:30 → 00:35")
            logger.info("⏱️  Each frame should display for about 0.25 seconds (4 FPS)")
            logger.info("🎥 Total video duration should be about 2 seconds")
            logger.info("🔵 Yellow circle should move smoothly across screen")
            
            logger.info(f"\n🔗 Test the video:")
            logger.info(f"   {result['private_link']}")
            
            logger.info("\n📋 What to verify:")
            logger.info("1. Video is not too fast (you can read the time)")
            logger.info("2. Video is not too slow (doesn't drag)")
            logger.info("3. Movement appears smooth and natural")
            logger.info("4. Each time increment is visible")
            
            return True
        else:
            logger.error(f"❌ Video creation failed: {result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


def test_different_intervals():
    """Test different analysis intervals to show FPS adaptation"""
    logger.info("\n🎬 Testing Different Analysis Intervals")
    logger.info("=" * 50)
    
    intervals = [3, 5, 10]
    expected_fps = [5.0, 4.0, 3.0]
    
    for interval, exp_fps in zip(intervals, expected_fps):
        logger.info(f"\n🎯 Testing {interval}s interval (expected {exp_fps} FPS)...")
        
        frames = create_watchable_test_frames(analysis_interval=interval)
        
        incident_data = {
            'incident_type': f'speed_test_{interval}s',
            'risk_level': 'TEST',
            'analysis': f'Test avec intervalle de {interval}s - vitesse adaptée',
            'frame_count': len(frames),
            'confidence': 1.0
        }
        
        try:
            result = create_and_upload_video_from_frames_gdpr(frames, incident_data, expiration_hours=1)
            
            if result['success']:
                logger.info(f"✅ {interval}s interval video created")
                logger.info(f"   Link: {result['private_link']}")
            else:
                logger.error(f"❌ {interval}s interval failed: {result.get('error')}")
        
        except Exception as e:
            logger.error(f"❌ {interval}s interval error: {e}")


def main():
    """Main test function"""
    logger.info("🎬 FINAL VIDEO SPEED TEST")
    logger.info("=" * 60)
    logger.info("Testing that videos now play at watchable speed (not too fast or slow)")
    
    # Test main watchable speed
    success = test_watchable_video_speed()
    
    if success:
        # Test different intervals
        test_different_intervals()
        
        logger.info("\n🎉 VIDEO SPEED TESTS COMPLETED!")
        logger.info("✅ Videos should now play at watchable speed")
        logger.info("📧 Check the video links to verify playback speed")
        logger.info("🎥 Videos should be smooth and easy to follow")
        
        logger.info("\n📊 Expected Speeds:")
        logger.info("• 3s intervals → 5 FPS → Smooth, slightly faster")
        logger.info("• 5s intervals → 4 FPS → Good viewing speed")
        logger.info("• 10s intervals → 3 FPS → Moderate, not too slow")
    else:
        logger.error("\n❌ VIDEO SPEED TEST FAILED!")
        logger.error("Videos may still have speed issues")
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)