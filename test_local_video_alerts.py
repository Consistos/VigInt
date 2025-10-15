#!/usr/bin/env python3
"""
Test local video alert functionality without API proxy
"""

import cv2
import base64
import numpy as np
from datetime import datetime
from vigint.app import SecureVideoAnalyzer

def create_test_analyzer():
    """Create a test analyzer without API key to test local functionality"""
    analyzer = SecureVideoAnalyzer(api_key=None)  # No API key = local mode
    return analyzer

def create_test_frame(frame_number):
    """Create a test frame with frame number"""
    # Create a simple test image
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (50 + frame_number * 2, 100, 150)  # Gradient color
    
    # Add frame number text
    cv2.putText(img, f'Test Frame {frame_number}', (50, 50), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(img, datetime.now().strftime('%H:%M:%S'), (50, 100), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    
    return img

def test_local_video_alert():
    """Test local video alert functionality"""
    print("🧪 Testing local video alert functionality...")
    
    # Create test analyzer
    analyzer = create_test_analyzer()
    
    # Add some test frames to local buffer
    print("Adding test frames to local buffer...")
    for i in range(50):  # 2 seconds at 25fps
        frame = create_test_frame(i + 1)
        analyzer.frame_count = i + 1
        analyzer.add_frame_to_buffer(frame)
    
    print(f"Local buffer size: {len(analyzer.local_frame_buffer)} frames")
    
    # Create test analysis result
    analysis_result = {
        'analysis': 'Test security incident detected for local video alert testing. This simulates a high-confidence security event.',
        'frame_count': 50,
        'risk_level': 'HIGH',
        'confidence': 0.95,
        'has_security_incident': True
    }
    
    print("Sending local video alert...")
    
    # Test local video alert
    success = analyzer._send_local_video_alert(analysis_result)
    
    if success:
        print("✅ Local video alert sent successfully!")
    else:
        print("❌ Local video alert failed!")
    
    return success

def test_fallback_mechanism():
    """Test the fallback mechanism when API proxy is unavailable"""
    print("\n🧪 Testing fallback mechanism...")
    
    # Create analyzer with API key but wrong URL (to simulate API proxy failure)
    analyzer = SecureVideoAnalyzer(
        api_base_url='http://localhost:9999',  # Non-existent port
        api_key='test-key'
    )
    
    # Add test frames
    print("Adding test frames...")
    for i in range(25):  # 1 second at 25fps
        frame = create_test_frame(i + 1)
        analyzer.frame_count = i + 1
        analyzer.add_frame_to_buffer(frame)
    
    # Create test analysis result
    analysis_result = {
        'analysis': 'Test fallback mechanism - API proxy unavailable, using local video alert system.',
        'frame_count': 25,
        'risk_level': 'MEDIUM',
        'confidence': 0.85,
        'has_security_incident': True
    }
    
    print("Testing fallback alert (API proxy should fail, local should work)...")
    
    # This should fail on API proxy and fallback to local
    success = analyzer.send_security_alert(analysis_result)
    
    if success:
        print("✅ Fallback mechanism worked successfully!")
    else:
        print("❌ Fallback mechanism failed!")
    
    return success

if __name__ == '__main__':
    print("🚨 Local Video Alert Testing\n")
    
    try:
        # Test 1: Direct local video alert
        print("=" * 60)
        test1_success = test_local_video_alert()
        
        # Test 2: Fallback mechanism
        print("=" * 60)
        test2_success = test_fallback_mechanism()
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY:")
        print(f"Local video alert: {'✅ PASS' if test1_success else '❌ FAIL'}")
        print(f"Fallback mechanism: {'✅ PASS' if test2_success else '❌ FAIL'}")
        
        if test1_success and test2_success:
            print("\n🎉 All tests passed! Local video alerts are working.")
        else:
            print("\n⚠️ Some tests failed. Check email configuration and dependencies.")
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()