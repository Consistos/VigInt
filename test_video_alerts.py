#!/usr/bin/env python3
"""
Test script for video alert functionality
"""

import cv2
import base64
import tempfile
import os
from datetime import datetime
from alerts import send_security_alert_with_video

def create_test_frames(num_frames=50):
    """Create test frames for video creation"""
    frames = []
    
    for i in range(num_frames):
        # Create a simple test image
        img = cv2.imread('buffer_video_1.mp4')  # Use existing video frame if available
        
        if img is None:
            # Create a simple colored frame if no video file exists
            import numpy as np
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            img[:] = (50 + i * 4, 100, 150)  # Gradient color
            
            # Add frame number text
            cv2.putText(img, f'Frame {i+1}', (50, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Encode frame to base64
        _, buffer_img = cv2.imencode('.jpg', img)
        frame_base64 = base64.b64encode(buffer_img).decode('utf-8')
        
        frame_info = {
            'frame_data': frame_base64,
            'frame_count': i + 1,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        frames.append(frame_info)
    
    return frames

def test_video_alert():
    """Test sending a security alert with video"""
    print("🧪 Testing video alert functionality...")
    
    # Create test frames
    print("Creating test frames...")
    test_frames = create_test_frames(75)  # 3 seconds at 25fps
    
    # Create incident data
    incident_data = {
        'risk_level': 'HIGH',
        'frame_count': 75,
        'confidence': 0.95,
        'analysis': 'Test security incident detected. This is a simulated alert for testing video attachment functionality.'
    }
    
    # Create alert message
    message = """
TEST SECURITY INCIDENT

This is a test alert to verify video attachment functionality.
The attached video contains test frames to demonstrate the system capability.

Time: """ + datetime.now().isoformat() + """
Status: Test Alert
Confidence: 95%

ANALYSIS:
Test incident detected with high confidence. This alert includes video evidence
created from buffered frames to demonstrate the complete alert workflow.

Please verify that:
1. Email is received successfully
2. Video attachment is present
3. Video plays correctly
4. Incident details are included
"""
    
    print("Sending test alert with video...")
    
    # Send the alert
    result = send_security_alert_with_video(message, test_frames, incident_data)
    
    if result.get('success', False):
        print("✅ Test alert sent successfully!")
        print(f"   Video attached: {result.get('video_attached', False)}")
        print(f"   Recipient: {result.get('recipient', 'Unknown')}")
    else:
        print("❌ Test alert failed!")
        print(f"   Error: {result.get('error', 'Unknown error')}")
    
    return result

if __name__ == '__main__':
    try:
        result = test_video_alert()
        print(f"\nTest result: {result}")
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()