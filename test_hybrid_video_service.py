#!/usr/bin/env python3
"""
Test the hybrid video service that works with or without Sparse AI
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

from local_video_link_service import create_hybrid_video_service, LocalVideoLinkService
from alerts import send_security_alert_with_video

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_video(duration_seconds=3, fps=25):
    """Create a test video file"""
    temp_fd, temp_path = tempfile.mkstemp(suffix='.mp4', prefix='test_hybrid_')
    os.close(temp_fd)
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_path, fourcc, fps, (640, 480))
    
    if not out.isOpened():
        logger.error("Failed to create video writer")
        return None
    
    total_frames = duration_seconds * fps
    
    for frame_num in range(total_frames):
        # Create a test frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add background
        frame[:, :] = [50, 100, 150]
        
        # Add moving circle
        center_x = int(100 + (440 * frame_num / total_frames))
        cv2.circle(frame, (center_x, 240), 30, (255, 255, 255), -1)
        
        # Add text
        cv2.putText(frame, f'HYBRID TEST {frame_num + 1}/{total_frames}', 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Add timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(frame, timestamp, 
                   (10, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        out.write(frame)
    
    out.release()
    
    if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
        logger.info(f"Created test video: {temp_path} ({os.path.getsize(temp_path) / (1024*1024):.1f} MB)")
        return temp_path
    else:
        logger.error("Failed to create test video")
        return None


def create_test_frames(count=30):
    """Create test frames for frame-based testing"""
    frames = []
    
    for i in range(count):
        # Create a test frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add store scene
        frame[400:, :] = [80, 80, 80]  # Floor
        cv2.rectangle(frame, (50, 100), (150, 400), (120, 120, 120), -1)  # Shelf
        
        # Add moving person
        person_x = int(200 + 200 * (i / count))
        cv2.circle(frame, (person_x, 350), 20, (255, 200, 150), -1)
        
        # Add overlay
        cv2.putText(frame, "HYBRID SERVICE TEST", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
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
    
    logger.info(f"Created {count} test frames")
    return frames


def test_hybrid_service_direct():
    """Test the hybrid service directly"""
    logger.info("🧪 Testing Hybrid Video Service (Direct)")
    logger.info("=" * 50)
    
    # Create test video
    test_video_path = create_test_video(duration_seconds=2)
    if not test_video_path:
        return False
    
    try:
        # Create hybrid service
        service = create_hybrid_video_service()
        
        # Test incident data
        incident_data = {
            'incident_type': 'test_hybrid',
            'risk_level': 'MEDIUM',
            'analysis': 'Testing hybrid video service functionality',
            'frame_count': 50,
            'confidence': 0.8
        }
        
        logger.info("Uploading test video using hybrid service...")
        result = service.upload_video(test_video_path, incident_data, expiration_hours=1)
        
        if result['success']:
            storage_type = result.get('storage_type', 'unknown')
            logger.info(f"✅ Video upload successful! (Storage: {storage_type})")
            logger.info(f"   Video ID: {result['video_id']}")
            
            if storage_type == 'local':
                logger.info(f"   Local Path: {result.get('local_path', 'N/A')}")
            else:
                logger.info(f"   Private Link: {result.get('private_link', 'N/A')}")
            
            logger.info(f"   File Hash: {result['file_hash'][:16]}...")
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


def test_email_integration():
    """Test email integration with hybrid service"""
    logger.info("\n🧪 Testing Email Integration (Hybrid)")
    logger.info("=" * 50)
    
    try:
        # Create test frames
        frames = create_test_frames(25)
        
        incident_data = {
            'incident_type': 'test_email_hybrid',
            'risk_level': 'HIGH',
            'analysis': 'Testing email integration with hybrid video service',
            'frame_count': 25,
            'confidence': 0.9
        }
        
        message = """
🧪 TEST: Hybrid Video Service Integration

This is a test of the hybrid video service that works with or without Sparse AI.
The system should automatically choose the best available storage option.
"""
        
        logger.info("Sending security alert with hybrid video service...")
        result = send_security_alert_with_video(message, frames, incident_data)
        
        if result['success']:
            logger.info(f"✅ Email with video sent successfully!")
            logger.info(f"   Recipient: {result['recipient']}")
            logger.info(f"   Video link provided: {result.get('video_link_provided', False)}")
            
            if result.get('video_link_info'):
                video_info = result['video_link_info']
                storage_type = video_info.get('storage_type', 'remote')
                logger.info(f"   Storage type: {storage_type}")
                logger.info(f"   Video ID: {video_info['video_id']}")
                
                if storage_type == 'local':
                    logger.info(f"   Local path: {video_info.get('local_path', 'N/A')}")
                else:
                    logger.info(f"   Private link: {video_info.get('private_link', 'N/A')}")
            
            return True
        else:
            logger.error(f"❌ Email sending failed: {result['error']}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False


def test_local_service_only():
    """Test the local service independently"""
    logger.info("\n🧪 Testing Local Service Only")
    logger.info("=" * 50)
    
    # Create test video
    test_video_path = create_test_video(duration_seconds=1)
    if not test_video_path:
        return False
    
    try:
        # Create local service
        service = LocalVideoLinkService()
        
        incident_data = {
            'incident_type': 'test_local_only',
            'risk_level': 'LOW',
            'analysis': 'Testing local video service only',
            'frame_count': 25,
            'confidence': 0.6
        }
        
        logger.info("Storing video locally...")
        result = service.upload_video(test_video_path, incident_data, expiration_hours=1)
        
        if result['success']:
            logger.info(f"✅ Local storage successful!")
            logger.info(f"   Video ID: {result['video_id']}")
            logger.info(f"   Local Path: {result['local_path']}")
            logger.info(f"   File Hash: {result['file_hash'][:16]}...")
            
            # List stored videos
            videos = service.list_stored_videos()
            logger.info(f"   Total stored videos: {len(videos)}")
            
            return True
        else:
            logger.error(f"❌ Local storage failed: {result['error']}")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False
    
    finally:
        # Clean up test video
        if os.path.exists(test_video_path):
            os.unlink(test_video_path)


def show_storage_status():
    """Show current storage status"""
    logger.info("\n📊 Storage Status")
    logger.info("=" * 50)
    
    # Check Sparse AI availability
    try:
        from video_link_service import VideoLinkService
        sparse_service = VideoLinkService()
        sparse_available = (
            sparse_service.api_key and 
            sparse_service.api_key != 'your-sparse-ai-api-key-here'
        )
        logger.info(f"🌐 Sparse AI: {'✅ Available' if sparse_available else '❌ Not configured'}")
    except Exception as e:
        logger.info(f"🌐 Sparse AI: ❌ Error ({e})")
    
    # Check local storage
    try:
        local_service = LocalVideoLinkService()
        videos = local_service.list_stored_videos()
        total_size = sum(v['size_mb'] for v in videos)
        
        logger.info(f"💾 Local Storage: ✅ Available")
        logger.info(f"   Directory: {local_service.storage_dir.absolute()}")
        logger.info(f"   Stored videos: {len(videos)}")
        logger.info(f"   Total size: {total_size:.1f} MB")
        
        if videos:
            logger.info("   Recent videos:")
            for video in videos[-3:]:  # Show last 3
                logger.info(f"     - {video['filename']} ({video['size_mb']} MB) - {video['risk_level']}")
    
    except Exception as e:
        logger.info(f"💾 Local Storage: ❌ Error ({e})")


def main():
    """Run all hybrid service tests"""
    logger.info("🎬 HYBRID VIDEO SERVICE TESTS")
    logger.info("=" * 60)
    logger.info("Testing video service that works with or without Sparse AI")
    
    # Show current status
    show_storage_status()
    
    # Run tests
    tests = [
        ("Hybrid Service Direct", test_hybrid_service_direct),
        ("Email Integration", test_email_integration),
        ("Local Service Only", test_local_service_only)
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
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 60)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    logger.info(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n🎉 All tests passed! Hybrid video service is working.")
        logger.info("📧 The system will now work with or without Sparse AI configuration.")
        logger.info("💾 Videos are stored locally when Sparse AI is not available.")
    else:
        logger.warning(f"\n⚠️  {total - passed} test(s) failed. Check logs for details.")
    
    # Show next steps
    logger.info("\n📋 NEXT STEPS:")
    logger.info("1. Configure Sparse AI API key for cloud storage (optional)")
    logger.info("2. System will automatically use local storage as fallback")
    logger.info("3. Check local_videos/ directory for stored videos")
    logger.info("4. Monitor disk space for local video storage")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)