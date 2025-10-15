#!/usr/bin/env python3
"""
Debug script to trace incident_type flow through the system
"""

import json
import logging
import base64
import cv2
import numpy as np
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_test_frame():
    """Create a test frame"""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(frame, (50, 50), (200, 150), (100, 100, 100), -1)
    cv2.putText(frame, "TEST SECURITY CAM", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return frame

def test_gemini_response_parsing():
    """Test parsing of various Gemini response formats"""
    
    print("🔍 Testing Gemini response parsing for incident_type...\n")
    
    # Simulate different response formats from Gemini
    test_responses = [
        {
            'name': 'Clean JSON',
            'text': '{"incident_detected": true, "incident_type": "shoplifting", "confidence": 0.85, "description": "Person concealing items", "analysis": "Suspicious behavior detected"}',
        },
        {
            'name': 'JSON with markdown',
            'text': '```json\n{"incident_detected": true, "incident_type": "vol à l\'étalage", "confidence": 0.9, "description": "Personne cachant des objets", "analysis": "Comportement suspect détecté"}\n```',
        },
        {
            'name': 'Malformed JSON',
            'text': 'Analysis shows incident_detected": true and "incident_type": "theft" with confidence 0.8',
        },
        {
            'name': 'No incident',
            'text': '{"incident_detected": false, "incident_type": "", "confidence": 0.1, "description": "Normal activity", "analysis": "Aucune activité suspecte"}',
        }
    ]
    
    for test_case in test_responses:
        print(f"Testing: {test_case['name']}")
        print(f"Raw response: {test_case['text'][:100]}...")
        
        # Simulate the parsing logic from api_proxy.py
        try:
            response_text = test_case['text'].strip()
            
            # Handle JSON wrapped in markdown code blocks
            if response_text.startswith('```json'):
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    response_text = response_text[start_idx:end_idx]
            
            try:
                analysis_json = json.loads(response_text)
                
                has_security_incident = analysis_json.get('incident_detected', False)
                confidence = analysis_json.get('confidence', 0.0)
                description = analysis_json.get('description', '')
                analysis_text = analysis_json.get('analysis', '')
                incident_type = analysis_json.get('incident_type', '')
                
                print(f"  ✅ JSON parsing successful")
                print(f"  incident_detected: {has_security_incident}")
                print(f"  incident_type: '{incident_type}'")
                print(f"  confidence: {confidence}")
                
            except (json.JSONDecodeError, KeyError) as e:
                print(f"  ⚠️  JSON parsing failed: {e}")
                print(f"  Trying fallback parsing...")
                
                # Fallback parsing
                analysis_text = test_case['text']
                analysis_text_lower = analysis_text.lower()
                has_security_incident = 'incident_detected": true' in analysis_text_lower
                
                incident_type = ""
                if '"incident_type":' in analysis_text_lower:
                    import re
                    match = re.search(r'"incident_type":\s*"([^"]*)"', analysis_text)
                    if match:
                        incident_type = match.group(1)
                        print(f"  ✅ Fallback found incident_type: '{incident_type}'")
                    else:
                        print(f"  ❌ Fallback failed to extract incident_type")
                else:
                    print(f"  ❌ No incident_type found in text")
            
            # Create the result that would be returned
            result = {
                'analysis': analysis_text,
                'has_security_incident': has_security_incident,
                'risk_level': 'HIGH' if confidence >= 0.8 else 'MEDIUM' if confidence >= 0.5 else 'LOW',
                'timestamp': datetime.now().isoformat(),
                'frame_count': 123,
                'incident_type': incident_type
            }
            
            print(f"  📤 Final result incident_type: '{result['incident_type']}'")
            
        except Exception as e:
            print(f"  ❌ Parsing failed with exception: {e}")
        
        print()

def test_alert_payload_creation():
    """Test alert payload creation"""
    
    print("🔍 Testing alert payload creation...\n")
    
    # Mock analysis result from API
    mock_analysis_result = {
        'analysis': 'Comportement suspect détecté: personne cachant des objets dans un sac',
        'has_security_incident': True,
        'risk_level': 'HIGH',
        'timestamp': datetime.now().isoformat(),
        'frame_count': 456,
        'incident_type': 'vol à l\'étalage'
    }
    
    print(f"Mock analysis result:")
    print(json.dumps(mock_analysis_result, indent=2))
    
    # Simulate payload creation from secure_video_analyzer.py
    payload = {
        'analysis': mock_analysis_result['analysis'],
        'frame_count': mock_analysis_result['frame_count'],
        'incident_type': mock_analysis_result.get('incident_type', ''),
        'risk_level': 'HIGH' if mock_analysis_result.get('has_security_incident', False) else 'MEDIUM'
    }
    
    print(f"\n📤 Alert payload:")
    print(json.dumps(payload, indent=2))
    
    if payload['incident_type']:
        print(f"✅ incident_type properly included: '{payload['incident_type']}'")
    else:
        print(f"❌ incident_type missing or empty")

def test_email_subject_creation():
    """Test email subject creation"""
    
    print("🔍 Testing email subject creation...\n")
    
    # Mock alert data that would be received by /api/video/alert
    mock_alert_data = {
        'analysis': 'Comportement suspect détecté: personne cachant des objets dans un sac',
        'frame_count': 456,
        'risk_level': 'HIGH',
        'incident_type': 'vol à l\'étalage'
    }
    
    print(f"Mock alert data:")
    print(json.dumps(mock_alert_data, indent=2))
    
    # Simulate subject creation from api_proxy.py
    incident_type = mock_alert_data.get('incident_type', '')
    risk_level = mock_alert_data.get('risk_level', 'MEDIUM')
    
    print(f"\nExtracting from alert data:")
    print(f"  incident_type: '{incident_type}'")
    print(f"  risk_level: '{risk_level}'")
    
    # Create subject with incident type if available
    subject = f"🚨 Vigint Security Alert [{risk_level}]"
    if incident_type:
        subject = f"🚨 Vigint Alert - {incident_type} - [{risk_level}]"
    subject += f" - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    print(f"\n📧 Generated email subject:")
    print(f"  {subject}")
    
    if incident_type and incident_type in subject:
        print(f"✅ incident_type properly included in subject")
    elif incident_type:
        print(f"❌ incident_type '{incident_type}' not found in subject")
    else:
        print(f"⚠️  No incident_type to include")

def test_direct_video_analyzer():
    """Test direct video analyzer flow"""
    
    print("🔍 Testing direct video analyzer flow...\n")
    
    try:
        from video_analyzer import VideoAnalyzer
        
        # Create analyzer
        analyzer = VideoAnalyzer()
        
        # Mock analysis result
        mock_analysis_result = {
            'timestamp': datetime.now().isoformat(),
            'frame_count': 789,
            'analysis': 'Activité suspecte: personne dissimulant des marchandises',
            'incident_detected': True,
            'incident_type': 'shoplifting',
            'confidence': 0.87,
            'frame_shape': [480, 640, 3]
        }
        
        print(f"Mock analysis result:")
        print(json.dumps(mock_analysis_result, indent=2))
        
        # Test incident data creation
        incident_data = {
            'risk_level': 'HIGH' if mock_analysis_result.get('incident_detected', False) else 'MEDIUM',
            'frame_count': mock_analysis_result.get('frame_count', 0),
            'confidence': mock_analysis_result.get('confidence', 0.0),
            'analysis': mock_analysis_result.get('analysis', ''),
            'incident_type': mock_analysis_result.get('incident_type', '')
        }
        
        print(f"\n📋 Incident data:")
        print(json.dumps(incident_data, indent=2))
        
        if incident_data['incident_type']:
            print(f"✅ incident_type properly extracted: '{incident_data['incident_type']}'")
        else:
            print(f"❌ incident_type missing from incident_data")
            
    except Exception as e:
        print(f"❌ Direct video analyzer test failed: {e}")

if __name__ == '__main__':
    print("🚀 Starting incident_type flow debugging...\n")
    
    # Test 1: Gemini response parsing
    test_gemini_response_parsing()
    
    # Test 2: Alert payload creation
    test_alert_payload_creation()
    
    # Test 3: Email subject creation
    test_email_subject_creation()
    
    # Test 4: Direct video analyzer
    test_direct_video_analyzer()
    
    print("✅ Debugging completed!")
    print("\n📋 Check each step to identify where incident_type might be lost")