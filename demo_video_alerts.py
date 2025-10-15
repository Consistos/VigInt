#!/usr/bin/env python3
"""
Demo script showing working video alerts
"""

import cv2
import base64
import numpy as np
import time
from datetime import datetime
from vigint.app import SecureVideoAnalyzer

def create_demo_video_frames(num_frames=75):
    """Create demo video frames simulating a security incident"""
    frames = []
    
    print(f"Creating {num_frames} demo frames...")
    
    for i in range(num_frames):
        # Create a realistic security camera frame
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Background (store/office environment)
        img[:] = (40, 60, 80)  # Dark blue-gray background
        
        # Add some "shelves" or "furniture"
        cv2.rectangle(img, (50, 200), (200, 400), (60, 80, 100), -1)
        cv2.rectangle(img, (450, 150), (600, 350), (60, 80, 100), -1)
        
        # Simulate a person moving through the scene
        person_x = 100 + (i * 6)  # Person moves across screen
        person_y = 300
        
        if person_x < 640:  # Person is in frame
            # Draw person (simple rectangle)
            cv2.rectangle(img, (person_x, person_y-50), (person_x+40, person_y+50), (120, 150, 180), -1)
            
            # Add "suspicious" behavior in middle frames
            if 25 <= i <= 50:
                # Person near shelf (suspicious activity)
                cv2.circle(img, (person_x+20, person_y-20), 15, (0, 0, 255), -1)  # Red circle (alert indicator)
                cv2.putText(img, 'SUSPICIOUS ACTIVITY', (person_x-50, person_y-70), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # Add timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(img, timestamp, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Add frame counter
        cv2.putText(img, f'Frame {i+1:03d}', (10, 460), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add camera info
        cv2.putText(img, 'CAM-01 DEMO', (500, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Convert to base64 for storage
        _, buffer_img = cv2.imencode('.jpg', img)
        frame_base64 = base64.b64encode(buffer_img).decode('utf-8')
        
        frame_info = {
            'frame_data': frame_base64,
            'frame_count': i + 1,
            'timestamp': timestamp
        }
        
        frames.append(frame_info)
    
    return frames

def demo_video_alert_system():
    """Demonstrate the complete video alert system"""
    print("🎬 Video Alert System Demo")
    print("=" * 50)
    
    # Create analyzer in local mode (no API key needed)
    print("1. Creating video analyzer (local mode)...")
    analyzer = SecureVideoAnalyzer(api_key=None)
    
    # Create demo frames
    print("2. Creating demo security incident frames...")
    demo_frames = create_demo_video_frames(75)  # 3 seconds at 25fps
    
    # Add frames to analyzer's local buffer
    print("3. Adding frames to local buffer...")
    for i, frame_info in enumerate(demo_frames):
        # Decode frame for adding to buffer
        frame_data = base64.b64decode(frame_info['frame_data'])
        frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
        
        analyzer.frame_count = i + 1
        analyzer.add_frame_to_buffer(frame)
    
    print(f"   Buffer size: {len(analyzer.local_frame_buffer)} frames")
    
    # Create incident analysis result
    print("4. Simulating security incident detection...")
    analysis_result = {
        'analysis': '''DEMO SECURITY INCIDENT DETECTED

AI Analysis Results:
- Incident Type: Suspicious behavior near merchandise
- Confidence Level: 92%
- Duration: 3 seconds
- Location: Camera 01 - Main Area

Detected Activities:
1. Individual approached restricted merchandise area
2. Suspicious handling of items observed
3. Concealment behavior detected
4. Person left area quickly after activity

Recommended Actions:
- Review additional camera angles
- Check inventory in affected area
- Consider security personnel dispatch
- Document incident for further review

This is a demonstration of the Vigint video alert system.
The attached video shows the complete incident sequence.''',
        'frame_count': len(demo_frames),
        'risk_level': 'HIGH',
        'confidence': 0.92,
        'has_security_incident': True
    }
    
    # Send video alert
    print("5. Sending video alert with demo footage...")
    success = analyzer._send_local_video_alert(analysis_result)
    
    if success:
        print("✅ Demo video alert sent successfully!")
        print("\nWhat was sent:")
        print("- Professional security alert email")
        print("- 3-second MP4 video attachment")
        print("- Detailed incident analysis")
        print("- Timestamp and metadata")
        print("- Risk level and confidence score")
    else:
        print("❌ Demo video alert failed!")
        print("Check email configuration with: python check_email_config.py")
    
    return success

def demo_fallback_mechanism():
    """Demo the fallback mechanism"""
    print("\n🔄 Fallback Mechanism Demo")
    print("=" * 50)
    
    # Create analyzer with API key but wrong URL (simulates API failure)
    print("1. Creating analyzer with API proxy (will fail)...")
    analyzer = SecureVideoAnalyzer(
        api_base_url='http://localhost:9999',  # Non-existent
        api_key='demo-key'
    )
    
    # Add demo frames
    print("2. Adding demo frames...")
    demo_frames = create_demo_video_frames(50)  # 2 seconds
    
    for i, frame_info in enumerate(demo_frames):
        frame_data = base64.b64decode(frame_info['frame_data'])
        frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
        analyzer.frame_count = i + 1
        analyzer.add_frame_to_buffer(frame)
    
    # Create analysis result
    analysis_result = {
        'analysis': 'FALLBACK DEMO: API proxy unavailable, using local video alert system. This demonstrates the robust fallback mechanism.',
        'frame_count': len(demo_frames),
        'risk_level': 'MEDIUM',
        'confidence': 0.85,
        'has_security_incident': True
    }
    
    print("3. Attempting to send alert (API will fail, local will work)...")
    success = analyzer.send_security_alert(analysis_result)
    
    if success:
        print("✅ Fallback mechanism worked!")
        print("- API proxy failed as expected")
        print("- Local video alert system activated")
        print("- Video alert sent successfully")
    else:
        print("❌ Fallback mechanism failed!")
    
    return success

if __name__ == '__main__':
    print("🚨 Vigint Video Alert System Demo\n")
    
    try:
        # Demo 1: Normal video alert
        demo1_success = demo_video_alert_system()
        
        # Demo 2: Fallback mechanism
        demo2_success = demo_fallback_mechanism()
        
        print("\n" + "=" * 50)
        print("DEMO SUMMARY:")
        print(f"Video Alert System: {'✅ WORKING' if demo1_success else '❌ FAILED'}")
        print(f"Fallback Mechanism: {'✅ WORKING' if demo2_success else '❌ FAILED'}")
        
        if demo1_success and demo2_success:
            print("\n🎉 Video alert system is fully operational!")
            print("\nNext steps:")
            print("1. Check your email for demo alerts")
            print("2. Verify video attachments play correctly")
            print("3. Run with real video: python start_vigint.py --video-input 'video.mp4'")
        else:
            print("\n⚠️ Some issues detected.")
            print("Run: python check_email_config.py")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()