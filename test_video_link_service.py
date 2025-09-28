#!/usr/bin/env python3
"""Test script for the video link service functionality"""

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

from video_link_service import VideoLinkService, upload_incident_video, create_and_upload_video_from_frames
from alerts import AlertManager, send_security_alert_with_video

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_video(duration_seconds=5, fps=25, width=640, height=480):
    """Create a test video file for testing purposes"""
    temp_fd, temp_path = tempfile.mkstemp(suffix='.mp4', prefix='test_video_')
    os.close(temp_fd)
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))
    
    if not out.isOpened():
        logger.error("Failed to create video writer")
        return None
    
    total_frames = duration_seconds * fps
    
    for frame_num in range(total_frames):
        # Create a test frame with moving elements
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add background color gradient
        for y in range(height):
            frame[y, :] = [int(255 * y / height), 50, 100]
        
        # Add moving circle
        center_x = int(width * 0.3 + (width * 0.4) * (frame_num / total_frames))
        center_y = int(height * 0.5)
        cv2.circle(frame, (center_x, center_y), 30, (255, 255, 255), -1)
        
        # Add frame number text
        cv2.putText(frame, f'Frame {frame_num + 1}/{total_frames}', 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Add timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(frame, timestamp, 
                   (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        out.write(frame)
    
    out.release()
    
    if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
        logger.info(f"Created test video: {temp_path} ({os.path.getsize(temp_path) / (1024*1024):.1f} MB)")
        return temp_path
    else:
        logger.error("Failed to create test video")
        return None


def create_test_frames(count=50):
    """Create test frames for frame-based video creation"""
    frames = []
    
    for i in range(count):
        # Create a test frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add background
        frame[:, :] = [50, 100, 150]
        
        # Add moving rectangle
        x = int(50 + (540 * i / count))
        cv2.rectangle(frame, (x, 200), (x + 50, 280), (255, 255, 255), -1)
        
        # Add frame info
        cv2.putText(frame, f'Test Frame {i + 1}/{count}', 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Encode frame to base64
        _, buffer = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        frames.append({
            'frame_data': frame_base64,
            'frame_count': i + 1,
            'timestamp': datetime.now().isoformat()
        })
    
    logger.info(f"Created {count} test frames")
    return frames


def test_video_link_service():
    """Test the VideoLinkService functionality"""
    logger.info("=== Testing VideoLinkService ===")
    
    # Create test video
    test_video_path = create_test_video(duration_seconds=3)
    if not test_video_path:
        logger.error("Failed to create test video")
        return False
    
    try:
        # Test video upload
        service = VideoLinkService()
        
        # Test incident data
        incident_data = {
            'incident_type': 'test_incident',
            'risk_level': 'MEDIUM',
            'analysis': 'This is a test security incident for video link service testing',
            'frame_count': 75,
            'confidence': 0.75
        }
        
        logger.info("Uploading test video to sparse-ai.com...")
        result = service.upload_video(test_video_path, incident_data, expiration_hours=1)
        
        if result['success']:
            logger.info(f"✅ Video upload successful!")
            logger.info(f"   Video ID: {result['video_id']}")
            logger.info(f"   Private Link: {result['private_link']}")
            logger.info(f"   Expiration: {result['expiration_time']}")
            logger.info(f"   File Hash: {result['file_hash']}")
            
            # Test link verification
            video_id = result['video_id']
            token = result['private_link'].split('token=')[1] if 'token=' in result['private_link'] else ''
            
            if token:
                logger.info("Testing link verification...")
                verify_result = service.verify_link_access(video_id, token)
                if verify_result['valid']:
                    logger.info(f"✅ Link verification successful! Remaining hours: {verify_result.get('remaining_hours', 'N/A')}")
                else:
                    logger.warning(f"❌ Link verification failed: {verify_result.get('error', 'Unknown error')}")
            
            return True
        else:
            logger.error(f"❌ Video upload failed: {result['error']}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False
    
    finally:
        # Clean up test video
        if os.path.exists(test_video_path):
            os.unlink(test_video_path)
            logger.info("Test video cleaned up")


def test_convenience_functions():
    """Test convenience functions"""
    logger.info("=== Testing Convenience Functions ===")
    
    # Test upload_incident_video function
    test_video_path = create_test_video(duration_seconds=2)
    if not test_video_path:
        logger.error("Failed to create test video")
        return False
    
    try:
        incident_data = {
            'incident_type': 'shoplifting',
            'risk_level': 'HIGH',
            'analysis': 'Customer concealing merchandise in bag',
            'frame_count': 50,
            'confidence': 0.9
        }
        
        logger.info("Testing upload_incident_video function...")
        result = upload_incident_video(test_video_path, incident_data, expiration_hours=2)
        
        if result['success']:
            logger.info(f"✅ upload_incident_video successful!")
            logger.info(f"   Private Link: {result['private_link']}")
            return True
        else:
            logger.error(f"❌ upload_incident_video failed: {result['error']}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False
    
    finally:
        if os.path.exists(test_video_path):
            os.unlink(test_video_path)


def test_frame_based_upload():
    """Test creating and uploading video from frames"""
    logger.info("=== Testing Frame-Based Video Upload ===")
    
    try:
        # Create test frames
        frames = create_test_frames(30)
        
        incident_data = {
            'incident_type': 'suspicious_behavior',
            'risk_level': 'MEDIUM',
            'analysis': 'Person acting suspiciously near high-value items',
            'frame_count': 30,
            'confidence': 0.7
        }
        
        logger.info("Creating video from frames and uploading...")
        result = create_and_upload_video_from_frames(frames, incident_data, expiration_hours=1)
        
        if result['success']:
            logger.info(f"✅ Frame-based upload successful!")
            logger.info(f"   Private Link: {result['private_link']}")
            logger.info(f"   Video ID: {result['video_id']}")
            return True
        else:
            logger.error(f"❌ Frame-based upload failed: {result['error']}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False


def test_email_integration():
    """Test email integration with video links"""
    logger.info("=== Testing Email Integration ===")
    
    try:
        # Create test frames
        frames = create_test_frames(25)
        
        incident_data = {
            'incident_type': 'security_breach',
            'risk_level': 'HIGH',
            'analysis': 'Unauthorized access detected in restricted area',
            'frame_count': 25,
            'confidence': 0.95
        }
        
        message = "URGENT: Security breach detected in Store Section A. Immediate attention required."
        
        logger.info("Sending security alert with video link...")
        result = send_security_alert_with_video(message, frames, incident_data)
        
        if result['success']:
            logger.info(f"✅ Email with video link sent successfully!")
            logger.info(f"   Recipient: {result['recipient']}")
            logger.info(f"   Video link provided: {result.get('video_link_provided', False)}")
            if result.get('video_link_info'):
                logger.info(f"   Video ID: {result['video_link_info']['video_id']}")
                logger.info(f"   Private Link: {result['video_link_info']['private_link']}")
            return True
        else:
            logger.error(f"❌ Email sending failed: {result['error']}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False


def main():
    """Run all tests"""
    logger.info("Starting Video Link Service Tests")
    logger.info("=" * 50)
    
    # Check if Sparse AI API key is configured
    service = VideoLinkService()
    if not service.api_key or service.api_key == 'your-sparse-ai-api-key-here':
        logger.warning("⚠️  Sparse AI API key not configured - tests will simulate upload failures")
        logger.warning("   Set SPARSE_AI_API_KEY environment variable or update config.ini")
        logger.warning("   Tests will continue to demonstrate error handling")
    
    tests = [
        ("Video Link Service", test_video_link_service),
        ("Convenience Functions", test_convenience_functions),
        ("Frame-Based Upload", test_frame_based_upload),
        ("Email Integration", test_email_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            success = test_func()
            results.append((test_name, success))
            logger.info(f"--- {test_name} Test {'PASSED' if success else 'FAILED'} ---")
        except Exception as e:
            logger.error(f"--- {test_name} Test FAILED with exception: {e} ---")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("TEST SUMMARY")
    logger.info("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Video link service is working correctly.")
    else:
        logger.warning(f"⚠️  {total - passed} test(s) failed. Check configuration and logs.")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)