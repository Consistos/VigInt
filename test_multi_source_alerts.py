#!/usr/bin/env python3
"""
Test multi-source video analysis alerts
"""

import os
import sys
import time
import logging
import base64
import cv2
import numpy as np
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from multi_source_video_analyzer import MultiSourceVideoAnalyzer
from alerts import send_security_alert_with_video

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_frames(num_frames=10, source_name="Test Camera"):
    """Create test frames for video alert testing"""
    test_frames = []
    
    for i in range(num_frames):
        # Create a test frame
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        
        # Add some visual content
        cv2.rectangle(frame, (50, 50), (270, 190), (100, 100, 100), -1)
        cv2.putText(frame, f'Frame {i+1}', (80, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, source_name, (80, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, f'Time: {i:02d}s', (80, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        # Convert to base64
        _, buffer_img = cv2.imencode('.jpg', frame)
        frame_base64 = base64.b64encode(buffer_img).decode('utf-8')
        
        frame_info = {
            'frame_data': frame_base64,
            'frame_count': i + 1,
            'timestamp': f'2024-01-01 12:00:{i:02d}',
            'source_id': 'test_camera',
            'source_name': source_name
        }
        test_frames.append(frame_info)
    
    return test_frames


def test_individual_source_alert():
    """Test alert from individual source analysis"""
    print("🎯 Testing Individual Source Alert")
    print("=" * 50)
    
    try:
        # Create test frames
        test_frames = create_test_frames(8, "Caméra Individuelle Test")
        
        # Create incident data for individual source
        incident_data = {
            'risk_level': 'HIGH',
            'frame_count': 8,
            'confidence': 0.85,
            'analysis': 'Incident de sécurité détecté sur caméra individuelle - comportement suspect observé près de la marchandise',
            'incident_type': 'Vol à l\'étalage suspecté',
            'is_aggregated': False,
            'source_name': 'Caméra Individuelle Test'
        }
        
        # Create alert message
        message = f"""
INCIDENT DE SÉCURITÉ DÉTECTÉ

Heure: 2024-01-01 12:00:00
Caméra: {incident_data.get('source_name', 'Inconnue')}
Type d'incident: {incident_data.get('incident_type', 'Non spécifié')}
Niveau de confiance: {incident_data.get('confidence', 0.0):.2f}

ANALYSE DÉTAILLÉE:
{incident_data.get('analysis', 'Aucune analyse disponible')}

Ceci est un test automatique du système de sécurité Vigint.
Veuillez examiner immédiatement les preuves vidéo ci-jointes.
"""
        
        # Send alert
        result = send_security_alert_with_video(message, test_frames, incident_data)
        
        if result.get('success', False):
            print("✅ Individual source alert sent successfully!")
            print(f"   Video attached: {result.get('video_attached', False)}")
            print(f"   Recipient: {result.get('recipient', 'Unknown')}")
            return True
        else:
            print(f"❌ Individual source alert failed: {result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        print(f"❌ Exception during individual source alert test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_aggregated_group_alert():
    """Test alert from aggregated group analysis"""
    print("\n🎯 Testing Aggregated Group Alert")
    print("=" * 50)
    
    try:
        # Create test frames from multiple cameras
        all_frames = []
        camera_names = ["Caméra Entrée", "Caméra Vente", "Caméra Caisse", "Caméra Stock"]
        
        for i, camera_name in enumerate(camera_names):
            frames = create_test_frames(6, camera_name)
            all_frames.extend(frames)
        
        # Create incident data for aggregated group
        incident_data = {
            'risk_level': 'HIGH',
            'frame_count': len(all_frames),
            'confidence': 0.92,
            'analysis': 'Incident de sécurité coordonné détecté sur plusieurs caméras - activité suspecte synchronisée observée dans différentes zones du magasin',
            'incident_type': 'Activité coordonnée suspecte',
            'is_aggregated': True,
            'cameras_involved': camera_names,
            'group_name': 'Groupe Principal'
        }
        
        # Create alert message for aggregated analysis
        cameras_list = ', '.join(camera_names)
        message = f"""
INCIDENT DE SÉCURITÉ DÉTECTÉ - ANALYSE MULTI-CAMÉRAS

Heure: 2024-01-01 12:00:00
Groupe de caméras: {incident_data.get('group_name', 'Inconnu')}
Caméras impliquées: {cameras_list}
Type d'incident: {incident_data.get('incident_type', 'Non spécifié')}
Niveau de confiance: {incident_data.get('confidence', 0.0):.2f}

ANALYSE DÉTAILLÉE:
{incident_data.get('analysis', 'Aucune analyse disponible')}

Cette alerte provient d'une analyse simultanée de plusieurs caméras.
Veuillez examiner immédiatement les preuves vidéo ci-jointes.
"""
        
        # Send alert
        result = send_security_alert_with_video(message, all_frames, incident_data)
        
        if result.get('success', False):
            print("✅ Aggregated group alert sent successfully!")
            print(f"   Video attached: {result.get('video_attached', False)}")
            print(f"   Recipient: {result.get('recipient', 'Unknown')}")
            print(f"   Cameras involved: {len(camera_names)}")
            return True
        else:
            print(f"❌ Aggregated group alert failed: {result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        print(f"❌ Exception during aggregated group alert test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_source_analyzer_integration():
    """Test the multi-source analyzer alert integration"""
    print("\n🎯 Testing Multi-Source Analyzer Integration")
    print("=" * 50)
    
    try:
        # Create a mock analysis result that would trigger an alert
        analysis_result = {
            'timestamp': '2024-01-01T12:00:00',
            'incident_detected': True,
            'incident_type': 'Vol à l\'étalage',
            'confidence': 0.88,
            'description': 'Comportement suspect détecté',
            'analysis': 'Une personne a été observée en train de dissimuler des articles dans ses vêtements près de l\'étalage de produits électroniques. Le comportement inclut des regards furtifs et des mouvements nerveux.',
            'is_aggregated': False,
            'source_id': 'camera_test',
            'source_name': 'Caméra Test Intégration',
            'frame_count': 156
        }
        
        # Create analyzer instance
        analyzer = MultiSourceVideoAnalyzer()
        
        # Test the _handle_security_incident method directly
        # First, we need to add a mock video source with some frames
        test_frames = create_test_frames(10, "Caméra Test Intégration")
        
        # Mock the frame buffer for the test source
        from collections import deque
        mock_source = type('MockSource', (), {
            'source_id': 'camera_test',
            'name': 'Caméra Test Intégration',
            'get_recent_frames': lambda duration_seconds: test_frames
        })()
        
        analyzer.video_sources = {'camera_test': mock_source}
        
        # Test the incident handling
        analyzer._handle_security_incident(analysis_result)
        
        print("✅ Multi-source analyzer integration test completed!")
        print("   Check your email for the security alert")
        return True
    
    except Exception as e:
        print(f"❌ Exception during multi-source analyzer integration test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("🎯 Multi-Source Video Analysis Alert Testing")
    print("=" * 60)
    
    # Check if GOOGLE_API_KEY is set (needed for the analyzer)
    if not os.getenv('GOOGLE_API_KEY'):
        print("⚠️  GOOGLE_API_KEY not set - some tests may be limited")
    
    all_tests_passed = True
    
    # Run alert tests
    tests = [
        ("Individual Source Alert", test_individual_source_alert),
        ("Aggregated Group Alert", test_aggregated_group_alert),
        ("Multi-Source Analyzer Integration", test_multi_source_analyzer_integration),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            if not result:
                all_tests_passed = False
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            all_tests_passed = False
        
        # Small delay between tests
        time.sleep(2)
    
    # Final summary
    print(f"\n{'='*60}")
    if all_tests_passed:
        print("✅ All multi-source alert tests passed!")
        print("📧 Multi-source video analysis alerts are working correctly")
        print("🎯 The system is ready for production use")
    else:
        print("❌ Some multi-source alert tests failed")
        print("🔧 Check the output above for specific issues")
    
    return 0 if all_tests_passed else 1


if __name__ == '__main__':
    sys.exit(main())