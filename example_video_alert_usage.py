#!/usr/bin/env python3
"""
Example usage of the enhanced video alert system
"""

from alerts import AlertManager, send_security_alert_with_video
from datetime import datetime
import base64
import cv2

def example_basic_alert():
    """Example of sending a basic alert without video"""
    print("📧 Sending basic alert...")
    
    alert_manager = AlertManager()
    
    result = alert_manager.send_email_alert(
        message="Test security event detected",
        alert_type="security",
        incident_data={
            'risk_level': 'MEDIUM',
            'frame_count': 100,
            'confidence': 0.75,
            'analysis': 'Suspicious activity detected in camera feed'
        }
    )
    
    print(f"Basic alert result: {result}")
    return result

def example_video_alert_with_frames():
    """Example of sending alert with video created from frames"""
    print("🎥 Sending alert with video...")
    
    # Simulate frame data (in real usage, this comes from video buffer)
    frames = []
    
    # Create some test frames
    for i in range(25):  # 1 second at 25fps
        # Create a simple test image
        import numpy as np
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (100, 150, 200)  # Blue background
        
        # Add frame info
        cv2.putText(img, f'Security Frame {i+1}', (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(img, datetime.now().strftime('%H:%M:%S'), (50, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Encode to base64
        _, buffer_img = cv2.imencode('.jpg', img)
        frame_base64 = base64.b64encode(buffer_img).decode('utf-8')
        
        frames.append({
            'frame_data': frame_base64,
            'frame_count': i + 1,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # Incident data
    incident_data = {
        'risk_level': 'HIGH',
        'frame_count': len(frames),
        'confidence': 0.92,
        'analysis': 'High-confidence security incident detected. Suspicious individual observed near restricted area.'
    }
    
    # Alert message
    message = f"""
SECURITY INCIDENT DETECTED

Time: {datetime.now().isoformat()}
Location: Camera Zone A
Risk Level: HIGH
Confidence: 92%

INCIDENT DETAILS:
A suspicious individual has been detected near the restricted area.
The person appears to be attempting unauthorized access.

RECOMMENDED ACTIONS:
1. Dispatch security personnel immediately
2. Review additional camera angles
3. Check access logs for the time period
4. Consider lockdown procedures if necessary

This alert includes video evidence from the incident timeframe.
"""
    
    # Send alert with video
    result = send_security_alert_with_video(message, frames, incident_data)
    
    print(f"Video alert result: {result}")
    return result

def example_alert_manager_with_video():
    """Example using AlertManager directly with video path"""
    print("📁 Sending alert with video file...")
    
    alert_manager = AlertManager()
    
    # Create a simple test video file
    import tempfile
    temp_fd, video_path = tempfile.mkstemp(suffix='.mp4', prefix='test_incident_')
    os.close(temp_fd)
    
    try:
        # Create a simple test video
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(video_path, fourcc, 25, (640, 480))
        
        for i in range(50):  # 2 seconds at 25fps
            import numpy as np
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            img[:] = (50, 100 + i * 2, 150)  # Gradient
            
            cv2.putText(img, f'Incident Frame {i+1}', (50, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            out.write(img)
        
        out.release()
        
        # Send alert with video file
        result = alert_manager.send_email_alert(
            message="Security incident with pre-created video",
            alert_type="security",
            video_path=video_path,
            incident_data={
                'risk_level': 'HIGH',
                'frame_count': 50,
                'confidence': 0.88,
                'analysis': 'Security breach detected with video evidence'
            }
        )
        
        print(f"Video file alert result: {result}")
        return result
        
    finally:
        # Clean up
        if os.path.exists(video_path):
            os.unlink(video_path)

if __name__ == '__main__':
    print("🚨 Video Alert System Examples\n")
    
    try:
        # Example 1: Basic alert without video
        print("=" * 50)
        example_basic_alert()
        
        print("\n" + "=" * 50)
        # Example 2: Alert with video from frames
        example_video_alert_with_frames()
        
        print("\n" + "=" * 50)
        # Example 3: Alert with video file
        example_alert_manager_with_video()
        
        print("\n✅ All examples completed!")
        
    except Exception as e:
        print(f"❌ Example failed: {e}")
        import traceback
        traceback.print_exc()