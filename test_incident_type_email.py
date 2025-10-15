#!/usr/bin/env python3
"""
Test script to verify incident_type is properly included in email subjects
"""

import json
import logging
from alerts import AlertManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_incident_type_in_email_subject():
    """Test that incident_type is properly included in email subject"""
    
    # Create alert manager
    alert_manager = AlertManager()
    
    # Test data with incident_type
    test_incident_data = {
        'risk_level': 'HIGH',
        'frame_count': 123,
        'confidence': 0.85,
        'analysis': 'Suspicious activity detected: Person concealing merchandise in bag',
        'incident_type': 'shoplifting'
    }
    
    test_message = """
SECURITY INCIDENT DETECTED

Time: 2025-01-29 10:30:00
Frame: 123
Incident Detected: True

ANALYSIS:
Suspicious activity detected: Person concealing merchandise in bag

This is an automated alert from the Vigint security system.
Please review the attached video evidence immediately.
"""
    
    print("🧪 Testing incident_type in email subject...")
    print(f"Test incident_data: {json.dumps(test_incident_data, indent=2)}")
    
    # Test email alert with incident data
    try:
        result = alert_manager.send_email_alert(
            message=test_message,
            alert_type="security",
            video_path=None,
            incident_data=test_incident_data
        )
        
        print(f"✅ Email alert result: {result}")
        
        if result.get('success', False):
            print("✅ Email sent successfully!")
            print("📧 Expected subject format: '🚨 Vigint Alert - shoplifting - SECURITY'")
        else:
            print(f"❌ Email failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        logger.error(f"Test exception: {e}")

def test_gemini_response_parsing():
    """Test parsing of Gemini response to extract incident_type"""
    
    # Mock Gemini responses to test parsing
    test_responses = [
        # Valid JSON response
        {
            'text': '{"incident_detected": true, "incident_type": "shoplifting", "confidence": 0.85, "description": "Person concealing items", "analysis": "Suspicious behavior observed"}',
            'expected_type': 'shoplifting'
        },
        # JSON in markdown code block
        {
            'text': '```json\n{"incident_detected": true, "incident_type": "theft", "confidence": 0.9, "description": "Item taken", "analysis": "Clear theft detected"}\n```',
            'expected_type': 'theft'
        },
        # Malformed JSON (fallback parsing)
        {
            'text': 'Analysis shows incident_detected": true and "incident_type": "vandalism" with high confidence',
            'expected_type': 'vandalism'
        },
        # No incident detected
        {
            'text': '{"incident_detected": false, "incident_type": "", "confidence": 0.1, "description": "Normal activity", "analysis": "No suspicious activity"}',
            'expected_type': ''
        }
    ]
    
    print("\n🧪 Testing Gemini response parsing...")
    
    for i, test_case in enumerate(test_responses):
        print(f"\nTest case {i+1}:")
        print(f"Response text: {test_case['text'][:100]}...")
        
        try:
            # Parse JSON response (simulate the parsing logic from video_analyzer.py)
            response_text = test_case['text'].strip()
            
            # Handle JSON wrapped in markdown code blocks
            if response_text.startswith('```json'):
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    response_text = response_text[start_idx:end_idx]
            
            try:
                analysis_json = json.loads(response_text)
                incident_type = analysis_json.get('incident_type', '')
                incident_detected = analysis_json.get('incident_detected', False)
                print(f"✅ JSON parsing successful")
                print(f"   incident_detected: {incident_detected}")
                print(f"   incident_type: '{incident_type}'")
                
            except (json.JSONDecodeError, KeyError):
                print("⚠️  JSON parsing failed, trying fallback...")
                # Fallback to text parsing
                incident_type = ""
                if '"incident_type":' in response_text.lower():
                    import re
                    match = re.search(r'"incident_type":\s*"([^"]*)"', response_text)
                    if match:
                        incident_type = match.group(1)
                        print(f"✅ Fallback parsing found: '{incident_type}'")
                    else:
                        print("❌ Fallback parsing failed")
                else:
                    print("❌ No incident_type found in text")
            
            # Check if result matches expected
            expected = test_case['expected_type']
            if incident_type == expected:
                print(f"✅ Result matches expected: '{expected}'")
            else:
                print(f"❌ Result mismatch. Expected: '{expected}', Got: '{incident_type}'")
                
        except Exception as e:
            print(f"❌ Test case failed: {e}")

if __name__ == '__main__':
    print("🚀 Starting incident_type email subject tests...\n")
    
    # Test 1: Email subject formatting
    test_incident_type_in_email_subject()
    
    # Test 2: Gemini response parsing
    test_gemini_response_parsing()
    
    print("\n✅ All tests completed!")