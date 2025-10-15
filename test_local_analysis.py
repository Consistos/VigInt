#!/usr/bin/env python3
"""
Test local analysis functionality
"""

import os
from vigint.app import SecureVideoAnalyzer
import cv2
import base64
import numpy as np
from datetime import datetime

def test_local_analysis():
    """Test the local analysis functionality"""
    print("🧪 Testing Local Analysis Functionality")
    print("=" * 50)
    
    # Create analyzer without API key to force local mode
    print("1. Creating analyzer in local mode...")
    analyzer = SecureVideoAnalyzer(api_key=None)
    
    # Create a test frame
    print("2. Creating test frame...")
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (100, 150, 200)  # Blue background
    cv2.putText(img, 'Security Test Frame', (50, 50), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(img, datetime.now().strftime('%H:%M:%S'), (50, 100), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    
    # Add frame to local buffer
    analyzer.frame_count = 1
    analyzer.add_frame_to_buffer(img)
    
    print(f"3. Local buffer size: {len(analyzer.local_frame_buffer)} frames")
    
    # Test local analysis
    print("4. Testing local frame analysis...")
    result = analyzer.analyze_recent_frames()
    
    if result:
        print("✅ Local analysis successful!")
        print(f"   Source: {result.get('source', 'unknown')}")
        print(f"   Incident detected: {result.get('has_security_incident', False)}")
        print(f"   Risk level: {result.get('risk_level', 'UNKNOWN')}")
        print(f"   Confidence: {result.get('confidence', 0):.2f}")
        print(f"   Analysis preview: {result.get('analysis', '')[:100]}...")
        
        # Test alert sending if incident detected
        if result.get('has_security_incident', False):
            print("5. Testing alert sending...")
            alert_sent = analyzer.send_security_alert(result)
            if alert_sent:
                print("✅ Alert sent successfully!")
            else:
                print("❌ Alert sending failed")
        else:
            print("5. No incident detected, skipping alert test")
        
        return True
    else:
        print("❌ Local analysis failed")
        return False

def test_with_api_key():
    """Test with API key to trigger fallback"""
    print("\n🔄 Testing API Fallback to Local Analysis")
    print("=" * 50)
    
    # Create analyzer with API key but wrong URL
    print("1. Creating analyzer with API key (will fail and fallback)...")
    analyzer = SecureVideoAnalyzer(
        api_base_url='http://localhost:9999',  # Non-existent
        api_key='test-key'
    )
    
    # Add test frame
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (150, 100, 200)  # Purple background
    cv2.putText(img, 'Fallback Test Frame', (50, 50), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    analyzer.frame_count = 1
    analyzer.add_frame_to_buffer(img)
    
    print("2. Testing API fallback to local analysis...")
    result = analyzer.analyze_recent_frames()
    
    if result:
        print("✅ Fallback analysis successful!")
        print(f"   Source: {result.get('source', 'unknown')}")
        print(f"   Incident detected: {result.get('has_security_incident', False)}")
        print(f"   Risk level: {result.get('risk_level', 'UNKNOWN')}")
        return True
    else:
        print("❌ Fallback analysis failed")
        return False

def check_gemini_availability():
    """Check if Gemini API is available for local analysis"""
    print("\n🔍 Checking Gemini API Availability")
    print("=" * 50)
    
    gemini_key = os.getenv('GOOGLE_API_KEY')
    if gemini_key:
        print(f"✅ GOOGLE_API_KEY is set: {gemini_key[:10]}...")
        
        try:
            import google.generativeai as genai
            print("✅ Google Generative AI library available")
            
            # Test connection
            genai.configure(
                api_key=gemini_key,
                transport='rest'
            )
            model = genai.GenerativeModel('gemini-1.5-flash')
            print("✅ Gemini model configured successfully")
            
            return True
        except ImportError:
            print("❌ Google Generative AI library not installed")
            return False
        except Exception as e:
            print(f"❌ Gemini configuration failed: {e}")
            return False
    else:
        print("❌ GOOGLE_API_KEY not set")
        print("   Local analysis will use mock results")
        return False

if __name__ == '__main__':
    print("🚨 Local Analysis Testing\n")
    
    # Check Gemini availability
    gemini_available = check_gemini_availability()
    
    # Test local analysis
    local_test = test_local_analysis()
    
    # Test fallback mechanism
    fallback_test = test_with_api_key()
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY:")
    print(f"Gemini API Available: {'✅ YES' if gemini_available else '❌ NO (will use mock)'}")
    print(f"Local Analysis: {'✅ WORKING' if local_test else '❌ FAILED'}")
    print(f"Fallback Mechanism: {'✅ WORKING' if fallback_test else '❌ FAILED'}")
    
    if local_test and fallback_test:
        print("\n🎉 Local analysis system is working!")
        print("Your system will now analyze frames locally when API proxy fails.")
        if gemini_available:
            print("Real AI analysis will be used.")
        else:
            print("Mock analysis will be used (set GOOGLE_API_KEY for real AI).")
    else:
        print("\n⚠️ Some issues detected with local analysis.")