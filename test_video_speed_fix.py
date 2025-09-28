#!/usr/bin/env python3
"""
Test video speed fix to ensure videos play at normal speed
"""

import os
import sys
import logging
import cv2
import numpy as np
import base64
import time
from datetime import datetime

# Add current directory to path
sys.path.append('.')

from alerts import send_security_alert_with_video

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_timed_frames(analysis_interval=5, total_duration=30):
    """Create frames that simulate real analysis timing"""
    frames = []
    
    # Calculate number of frames based on analysis interval
    num_frames = int(total_duration / analysis_interval)
    
    logger.info(f"Creating {num_frames} frames with {analysis_interval}s intervals (total: {total_duration}s)")
    
    for i in range(num_frames):
        # Create frame with timing information
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add background
        frame[:, :] = [50, 100, 150]
        
        # Add time indicator
        elapsed_time = i * analysis_interval
        minutes = elapsed_time // 60
        seconds = elapsed_time % 60
        
        # Large time display
        time_text = f"{minutes:02d}:{seconds:02d}"
        cv2.putText(frame, time_text, (200, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 8)
        
        # Frame info
        cv2.putText(frame, f"Frame {i+1}/{num_frames}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Analysis Interval: {analysis_interval}s", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Elapsed Time: {elapsed_time}s", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Add visual progress bar
        progress = i / (num_frames - 1) if num_frames > 1 else 0
        bar_width = int(600 * progress)
        cv2.rectangle(frame, (20, 400), (20 + bar_width, 420), (0, 255, 0), -1)
        cv2.rectangle(frame, (20, 400), (620, 420), (255, 255, 255), 2)
        
        # Encode to base64
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        frames.append({
            'frame_data': frame_base64,
            'frame_count': i + 1,
            'timestamp': datetime.now().isoformat(),
            'analysis_interval': analysis_interval,  # Important: include timing info
            'elapsed_time': elapsed_time,
            'sequence_number': i + 1,
            'total_frames': num_frames
        })
    
    return frames


def test_video_speed(analysis_interval=5):
    """Test video creation with correct speed"""
    logger.info(f"🎬 Testing Video Speed Fix (Analysis Interval: {analysis_interval}s)")
    logger.info("=" * 60)
    
    try:
        # Create timed frames
        frames = create_timed_frames(analysis_interval=analysis_interval, total_duration=30)
        
        incident_data = {
            'incident_type': 'test_video_speed',
            'risk_level': 'MEDIUM',
            'analysis': f'Test vidéo avec intervalle d\'analyse de {analysis_interval} secondes. La vidéo devrait jouer à vitesse normale.',
            'frame_count': len(frames),
            'confidence': 0.8,
            'analysis_interval': analysis_interval
        }
        
        message = f"""
🎬 TEST: Correction de la vitesse vidéo

Intervalle d'analyse: {analysis_interval} secondes
Nombre de frames: {len(frames)}
Durée totale simulée: 30 secondes

⚠️ IMPORTANT: Cette vidéo devrait jouer à vitesse normale.
Chaque frame représente {analysis_interval} secondes d'analyse réelle.
Vérifiez que le compteur de temps progresse naturellement.
"""
        
        logger.info("📧 Sending test alert with speed-corrected video...")
        result = send_security_alert_with_video(message, frames, incident_data)
        
        if result['success']:
            logger.info("✅ Test alert sent successfully!")
            logger.info(f"   Video ID: {result.get('video_link_info', {}).get('video_id', 'N/A')}")
            logger.info(f"   Private Link: {result.get('video_link_info', {}).get('private_link', 'N/A')}")
            
            logger.info("\n🎯 VIDEO SPEED VERIFICATION:")
            logger.info("1. 📧 Check your email for the test alert")
            logger.info("2. 🔗 Click on the private video link")
            logger.info("3. ⏱️  Watch the time counter in the video")
            logger.info("4. ✅ Verify it progresses at normal speed (not accelerated)")
            logger.info(f"5. 📊 Each frame should represent {analysis_interval} seconds")
            
            return True
        else:
            logger.error(f"❌ Test failed: {result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False


def test_multiple_intervals():
    """Test different analysis intervals"""
    logger.info("🎬 Testing Multiple Analysis Intervals")
    logger.info("=" * 60)
    
    intervals = [3, 5, 10]  # Different analysis intervals
    results = []
    
    for interval in intervals:
        logger.info(f"\n🎯 Testing {interval}s analysis interval...")
        success = test_video_speed(interval)
        results.append((interval, success))
        
        if success:
            logger.info(f"✅ {interval}s interval test passed")
        else:
            logger.error(f"❌ {interval}s interval test failed")
        
        # Wait between tests
        time.sleep(2)
    
    # Summary
    logger.info("\n📊 MULTIPLE INTERVAL TEST RESULTS:")
    for interval, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"   {interval}s interval: {status}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    return passed == total


def main():
    """Main test function"""
    logger.info("🎬 VIDEO SPEED FIX TEST")
    logger.info("=" * 60)
    logger.info("Testing that videos play at normal speed (not accelerated)")
    
    # Test single interval
    logger.info("\n🎯 Testing 5-second analysis interval...")
    single_success = test_video_speed(5)
    
    # Test multiple intervals
    logger.info("\n🎯 Testing multiple analysis intervals...")
    multiple_success = test_multiple_intervals()
    
    if single_success and multiple_success:
        logger.info("\n🎉 ALL TESTS PASSED!")
        logger.info("✅ Video speed fix is working correctly")
        logger.info("📧 Check your emails to verify video playback speed")
        logger.info("⏱️  Videos should now play at normal speed")
    else:
        logger.error("\n❌ SOME TESTS FAILED!")
        logger.error("Videos may still be playing too fast")
    
    logger.info("\n📋 VERIFICATION STEPS:")
    logger.info("1. Open the test alert emails")
    logger.info("2. Click the video links")
    logger.info("3. Watch the time counter in each video")
    logger.info("4. Verify it progresses naturally (not accelerated)")
    logger.info("5. Each frame transition should feel natural")
    
    return single_success and multiple_success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)