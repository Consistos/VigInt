#!/usr/bin/env python3
"""Example usage of the new video link service for security alerts"""

import sys
import logging
from datetime import datetime

# Add current directory to path for imports
sys.path.append('.')

from video_link_service import VideoLinkService, upload_incident_video
from alerts import send_security_alert_with_video

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def example_1_direct_video_upload():
    """Example 1: Upload an existing video file and get a private link"""
    logger.info("=== Example 1: Direct Video Upload ===")
    
    # Assume you have a video file from your security system
    video_file_path = "security_incident_20241219_103000.mp4"
    
    # Incident details
    incident_data = {
        'incident_type': 'shoplifting',
        'risk_level': 'HIGH',
        'analysis': 'Customer observed concealing merchandise in bag without paying',
        'frame_count': 125,
        'confidence': 0.92
    }
    
    # Upload video and get private link
    result = upload_incident_video(
        video_file_path, 
        incident_data, 
        expiration_hours=48  # Link expires in 48 hours
    )
    
    if result['success']:
        logger.info("✅ Video uploaded successfully!")
        logger.info(f"Private Link: {result['private_link']}")
        logger.info(f"Video ID: {result['video_id']}")
        logger.info(f"Expires: {result['expiration_time']}")
        
        # You can now share this private link via email, SMS, etc.
        return result['private_link']
    else:
        logger.error(f"❌ Upload failed: {result['error']}")
        return None


def example_2_alert_with_video_frames():
    """Example 2: Send security alert with video created from frame buffer"""
    logger.info("=== Example 2: Alert with Video from Frames ===")
    
    # Simulate frame buffer from your video analysis system
    # In real usage, these would come from your camera feed
    frames = []
    
    # Example: Add frames to buffer (normally this happens continuously)
    for i in range(75):  # 3 seconds at 25 FPS
        frame_info = {
            'frame_data': 'base64_encoded_frame_data_here',  # Your actual frame data
            'frame_count': i + 1,
            'timestamp': datetime.now().isoformat()
        }
        frames.append(frame_info)
    
    # Incident analysis results
    incident_data = {
        'incident_type': 'suspicious_behavior',
        'risk_level': 'MEDIUM',
        'analysis': 'Person acting suspiciously near electronics section, checking for security tags',
        'frame_count': 75,
        'confidence': 0.78
    }
    
    # Alert message
    alert_message = """
SECURITY ALERT: Suspicious behavior detected in Electronics Section

A customer has been observed acting suspiciously near high-value electronics,
repeatedly checking items for security tags and looking around nervously.

Immediate attention recommended.
    """.strip()
    
    # Send alert with video link (video will be created from frames automatically)
    result = send_security_alert_with_video(alert_message, frames, incident_data)
    
    if result['success']:
        logger.info("✅ Security alert sent successfully!")
        logger.info(f"Sent to: {result['recipient']}")
        
        if result.get('video_link_provided'):
            logger.info("📹 Video link included in email")
            video_info = result.get('video_link_info', {})
            logger.info(f"Video ID: {video_info.get('video_id', 'N/A')}")
            logger.info(f"Private Link: {video_info.get('private_link', 'N/A')}")
        else:
            logger.warning("⚠️ Video link not available")
        
        return True
    else:
        logger.error(f"❌ Alert failed: {result['error']}")
        return False


def example_3_advanced_video_service():
    """Example 3: Advanced usage of VideoLinkService"""
    logger.info("=== Example 3: Advanced Video Service Usage ===")
    
    service = VideoLinkService()
    
    # Check if service is properly configured
    if not service.api_key or service.api_key == 'your-sparse-ai-api-key-here':
        logger.warning("⚠️ Sparse AI API key not configured")
        logger.info("Set SPARSE_AI_API_KEY environment variable or update config.ini")
        return False
    
    # Example video file (you would have a real one)
    video_path = "incident_video.mp4"
    
    # Detailed incident data
    incident_data = {
        'incident_type': 'theft_attempt',
        'risk_level': 'HIGH',
        'analysis': 'Customer attempted to remove security tag from expensive item',
        'frame_count': 200,
        'confidence': 0.95,
        'location': 'Store Section B',
        'camera_id': 'CAM_003',
        'detection_algorithm': 'gemini_1_5_flash'
    }
    
    # Upload with custom expiration
    logger.info("Uploading video with 72-hour expiration...")
    result = service.upload_video(video_path, incident_data, expiration_hours=72)
    
    if result['success']:
        video_id = result['video_id']
        private_link = result['private_link']
        
        logger.info(f"✅ Upload successful: {video_id}")
        logger.info(f"Private Link: {private_link}")
        
        # Extract token from link for verification
        token = private_link.split('token=')[1] if 'token=' in private_link else ''
        
        if token:
            # Verify link is accessible
            logger.info("Verifying link access...")
            verify_result = service.verify_link_access(video_id, token)
            
            if verify_result['valid']:
                logger.info(f"✅ Link verified! Expires in {verify_result.get('remaining_hours', 'N/A')} hours")
                
                # Optionally extend expiration
                logger.info("Extending link expiration by 24 hours...")
                extend_result = service.extend_link_expiration(video_id, additional_hours=24)
                
                if extend_result['success']:
                    logger.info(f"✅ Expiration extended to: {extend_result['new_expiration']}")
                else:
                    logger.warning(f"⚠️ Extension failed: {extend_result['error']}")
            else:
                logger.error(f"❌ Link verification failed: {verify_result.get('error', 'Unknown error')}")
        
        return True
    else:
        logger.error(f"❌ Upload failed: {result['error']}")
        return False


def example_4_error_handling():
    """Example 4: Proper error handling"""
    logger.info("=== Example 4: Error Handling ===")
    
    # This example shows how the system handles various error conditions
    
    # Case 1: Missing video file
    logger.info("Testing with missing video file...")
    result = upload_incident_video("nonexistent_video.mp4", {})
    
    if not result['success']:
        logger.info(f"✅ Properly handled missing file: {result['error']}")
    
    # Case 2: Invalid incident data
    logger.info("Testing with minimal incident data...")
    result = upload_incident_video("test_video.mp4", None)
    
    # The system should handle this gracefully
    logger.info(f"Result with minimal data: {'Success' if result.get('success') else result.get('error', 'Failed')}")
    
    # Case 3: Send alert without video
    logger.info("Testing alert without video frames...")
    result = send_security_alert_with_video("Test alert without video", None, {
        'incident_type': 'test',
        'risk_level': 'LOW',
        'analysis': 'Test alert'
    })
    
    if result['success']:
        logger.info("✅ Alert sent successfully without video")
    else:
        logger.info(f"Alert result: {result.get('error', 'Unknown error')}")
    
    return True


def main():
    """Run all examples"""
    logger.info("Video Link Service Usage Examples")
    logger.info("=" * 50)
    
    examples = [
        ("Direct Video Upload", example_1_direct_video_upload),
        ("Alert with Video Frames", example_2_alert_with_video_frames),
        ("Advanced Video Service", example_3_advanced_video_service),
        ("Error Handling", example_4_error_handling)
    ]
    
    for example_name, example_func in examples:
        logger.info(f"\n--- {example_name} ---")
        try:
            example_func()
        except Exception as e:
            logger.error(f"Example failed: {e}")
        logger.info(f"--- End {example_name} ---")
    
    logger.info("\n" + "=" * 50)
    logger.info("Examples completed!")
    logger.info("\nKey Points:")
    logger.info("• Videos are uploaded to sparse-ai.com instead of email attachments")
    logger.info("• Private links are generated with automatic expiration")
    logger.info("• Email alerts include secure video access links")
    logger.info("• System gracefully handles errors and missing configuration")
    logger.info("• No changes needed to existing alert code - just configure API key")


if __name__ == '__main__':
    main()