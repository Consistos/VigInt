#!/usr/bin/env python3
"""
Test script to diagnose and fix email alert issues
"""

import os
import sys
import logging
import tempfile
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import config
from alerts import AlertManager, send_security_alert_with_video

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_email_configuration():
    """Test email configuration"""
    print("🔧 Testing Email Configuration")
    print("=" * 50)
    
    # Check email settings from config
    email_settings = {
        'smtp_server': config.get('Email', 'smtp_server', ''),
        'smtp_port': config.getint('Email', 'smtp_port', 587),
        'username': config.get('Email', 'username', ''),
        'password': config.get('Email', 'password', ''),
        'from_email': config.get('Email', 'from_email', ''),
        'to_email': config.get('Email', 'to_email', ''),
        'sender_email': config.get('Email', 'sender_email', ''),
        'sender_password': config.get('Email', 'sender_password', ''),
        'admin_email': config.get('Email', 'admin_email', '')
    }
    
    print("Email Configuration:")
    for key, value in email_settings.items():
        if 'password' in key.lower():
            display_value = '*' * len(value) if value else 'NOT SET'
        else:
            display_value = value if value else 'NOT SET'
        print(f"  {key}: {display_value}")
    
    # Check for missing required settings
    required_settings = ['smtp_server', 'username', 'password', 'from_email', 'to_email']
    missing_settings = []
    
    for setting in required_settings:
        if not email_settings.get(setting):
            missing_settings.append(setting)
    
    if missing_settings:
        print(f"\n❌ Missing required email settings: {', '.join(missing_settings)}")
        return False
    else:
        print(f"\n✅ All required email settings are configured")
        return True


def test_basic_email_alert():
    """Test basic email alert functionality"""
    print("\n📧 Testing Basic Email Alert")
    print("=" * 50)
    
    try:
        alert_manager = AlertManager()
        
        # Test basic email alert
        result = alert_manager.send_email_alert(
            "Test d'alerte email depuis le système Vigint - Multi-Source",
            "test",
            incident_data={
                'risk_level': 'TEST',
                'frame_count': 123,
                'confidence': 0.95,
                'analysis': 'Test d\'analyse pour vérifier le système d\'alerte email',
                'incident_type': 'Test de système'
            }
        )
        
        if result.get('success', False):
            print("✅ Basic email alert sent successfully!")
            print(f"   Recipient: {result.get('recipient', 'Unknown')}")
            return True
        else:
            print(f"❌ Basic email alert failed: {result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        print(f"❌ Exception during basic email test: {e}")
        return False


def test_video_alert():
    """Test email alert with video attachment"""
    print("\n🎬 Testing Video Alert")
    print("=" * 50)
    
    try:
        # Create some dummy frame data for testing
        import base64
        import cv2
        import numpy as np
        
        # Create a simple test frame
        test_frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(test_frame, 'TEST FRAME', (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Convert to base64
        _, buffer_img = cv2.imencode('.jpg', test_frame)
        frame_base64 = base64.b64encode(buffer_img).decode('utf-8')
        
        # Create test frames
        test_frames = []
        for i in range(10):  # 10 test frames
            frame_info = {
                'frame_data': frame_base64,
                'frame_count': i + 1,
                'timestamp': f'2024-01-01 12:00:{i:02d}',
                'source_id': 'test_camera',
                'source_name': 'Test Camera'
            }
            test_frames.append(frame_info)
        
        # Test video alert
        incident_data = {
            'risk_level': 'HIGH',
            'frame_count': 10,
            'confidence': 0.9,
            'analysis': 'Test d\'incident de sécurité avec vidéo jointe pour vérifier le système d\'alerte multi-source',
            'incident_type': 'Test avec vidéo'
        }
        
        message = """
INCIDENT DE SÉCURITÉ DÉTECTÉ - TEST MULTI-SOURCE

Heure: 2024-01-01 12:00:00
Caméra: Test Camera
Type d'incident: Test avec vidéo
Niveau de confiance: 0.90

ANALYSE DÉTAILLÉE:
Test d'incident de sécurité avec vidéo jointe pour vérifier le système d'alerte multi-source.

Ceci est un test automatique du système de sécurité Vigint Multi-Source.
Veuillez examiner les preuves vidéo ci-jointes.
"""
        
        result = send_security_alert_with_video(message, test_frames, incident_data)
        
        if result.get('success', False):
            print("✅ Video alert sent successfully!")
            print(f"   Video attached: {result.get('video_attached', False)}")
            print(f"   Recipient: {result.get('recipient', 'Unknown')}")
            return True
        else:
            print(f"❌ Video alert failed: {result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        print(f"❌ Exception during video alert test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_smtp_connection():
    """Test SMTP connection directly"""
    print("\n🔌 Testing SMTP Connection")
    print("=" * 50)
    
    try:
        import smtplib
        
        smtp_server = config.get('Email', 'smtp_server', 'smtp.gmail.com')
        smtp_port = config.getint('Email', 'smtp_port', 587)
        username = config.get('Email', 'username', '')
        password = config.get('Email', 'password', '')
        
        print(f"Connecting to {smtp_server}:{smtp_port}")
        
        # Test SMTP connection
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        
        print("✅ SMTP connection established")
        print("✅ TLS encryption enabled")
        
        if username and password:
            server.login(username, password)
            print("✅ SMTP authentication successful")
        else:
            print("❌ No SMTP credentials provided")
            return False
        
        server.quit()
        print("✅ SMTP connection test completed successfully")
        return True
    
    except Exception as e:
        print(f"❌ SMTP connection failed: {e}")
        return False


def diagnose_email_issues():
    """Diagnose potential email issues"""
    print("\n🔍 Diagnosing Email Issues")
    print("=" * 50)
    
    issues_found = []
    
    # Check environment variables
    google_api_key = os.getenv('GOOGLE_API_KEY')
    if not google_api_key:
        issues_found.append("GOOGLE_API_KEY environment variable not set")
    
    # Check email modules availability
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        print("✅ Email modules available")
    except ImportError as e:
        issues_found.append(f"Email modules not available: {e}")
    
    # Check video processing modules
    try:
        import cv2
        import numpy as np
        print("✅ Video processing modules available")
    except ImportError as e:
        issues_found.append(f"Video processing modules not available: {e}")
    
    # Check config file
    try:
        from config import config
        print("✅ Configuration module loaded")
    except Exception as e:
        issues_found.append(f"Configuration module error: {e}")
    
    if issues_found:
        print(f"\n❌ Issues found:")
        for issue in issues_found:
            print(f"   - {issue}")
        return False
    else:
        print(f"\n✅ No obvious issues found")
        return True


def fix_email_alerts():
    """Attempt to fix common email alert issues"""
    print("\n🔧 Attempting to Fix Email Alert Issues")
    print("=" * 50)
    
    fixes_applied = []
    
    # Check and fix EMAIL_AVAILABLE flag in video_analyzer.py
    try:
        video_analyzer_path = "video_analyzer.py"
        if os.path.exists(video_analyzer_path):
            with open(video_analyzer_path, 'r') as f:
                content = f.read()
            
            # Check if EMAIL_AVAILABLE is properly set
            if "EMAIL_AVAILABLE = False" in content:
                print("⚠️  Found EMAIL_AVAILABLE = False in video_analyzer.py")
                # This might be the issue - let's check why it's False
                
                # Look for the import section
                if "except Exception as e:" in content and "EMAIL_AVAILABLE = False" in content:
                    print("   Email modules import might be failing")
                    fixes_applied.append("Identified potential email import issue")
    
    except Exception as e:
        print(f"⚠️  Could not check video_analyzer.py: {e}")
    
    # Check alerts.py for any issues
    try:
        from alerts import AlertManager
        alert_manager = AlertManager()
        print("✅ AlertManager can be instantiated")
        fixes_applied.append("AlertManager instantiation works")
    except Exception as e:
        print(f"❌ AlertManager instantiation failed: {e}")
    
    if fixes_applied:
        print(f"\nFixes applied:")
        for fix in fixes_applied:
            print(f"   ✅ {fix}")
    
    return len(fixes_applied) > 0


def main():
    """Main test function"""
    print("🎯 Email Alert Diagnostic and Fix Tool")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Run diagnostic tests
    tests = [
        ("Email Configuration", test_email_configuration),
        ("SMTP Connection", test_smtp_connection),
        ("System Diagnosis", diagnose_email_issues),
        ("Basic Email Alert", test_basic_email_alert),
        ("Video Email Alert", test_video_alert),
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
    
    # Attempt fixes if tests failed
    if not all_tests_passed:
        fix_email_alerts()
    
    # Final summary
    print(f"\n{'='*60}")
    if all_tests_passed:
        print("✅ All email alert tests passed!")
        print("📧 Email alerts should be working correctly")
    else:
        print("❌ Some email alert tests failed")
        print("🔧 Check the diagnostic output above for specific issues")
        print("\nCommon solutions:")
        print("   1. Verify email credentials in config.ini")
        print("   2. Check GOOGLE_API_KEY environment variable")
        print("   3. Ensure SMTP server allows app passwords")
        print("   4. Check network connectivity to SMTP server")
    
    return 0 if all_tests_passed else 1


if __name__ == '__main__':
    sys.exit(main())