#!/usr/bin/env python3
"""Test distributed mode is working"""

import cv2
import numpy as np
from video_analyzer import VideoAnalyzer

print("=== Testing Distributed Video Analysis ===\n")

# Initialize analyzer
analyzer = VideoAnalyzer()

print(f"Mode: {'CLIENT (Remote API)' if analyzer.use_remote_api else 'LOCAL'}")
print(f"API Server: {analyzer.api_server_url or 'None'}")
print(f"API Client: {'✅ Initialized' if analyzer.api_client else '❌ None'}\n")

if analyzer.use_remote_api and analyzer.api_client:
    print("Testing frame analysis via server...")
    
    # Create a test frame
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(test_frame, "Test Frame", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    
    try:
        result = analyzer.analyze_frame(test_frame)
        
        if result:
            print(f"✅ Analysis successful!")
            print(f"   Incident detected: {result.get('incident_detected', False)}")
            print(f"   Analysis: {result.get('analysis', '')[:100]}...")
            print(f"   Method: {'Server API' if analyzer.use_remote_api else 'Local'}")
        else:
            print("❌ Analysis returned no result")
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
else:
    print("❌ Not in client mode or API client not initialized")
    print("   Check your config.ini has: api_server_url = https://vigint.onrender.com")
    print("   Check your .env has: VIGINT_API_KEY=...")
