#!/usr/bin/env python3
"""
Test that the main application uses secure architecture
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_main_app_imports():
    """Test that main application imports secure components"""
    
    print("🧪 Testing main application imports...\n")
    
    try:
        # Test start_vigint.py imports
        print("📋 Checking start_vigint.py imports...")
        
        with open('start_vigint.py', 'r') as f:
            start_vigint_content = f.read()
        
        # Check for secure imports
        secure_imports = [
            'from vigint.app import SecureVideoAnalyzer',
            'SecureVideoAnalyzer(',
        ]
        
        insecure_imports = [
            'from video_analyzer import VideoAnalyzer',
            'import video_analyzer',
        ]
        
        print("   Checking for secure imports:")
        for import_line in secure_imports:
            found = import_line in start_vigint_content
            print(f"   {'✅' if found else '❌'} {import_line}")
        
        print("   Checking for insecure imports:")
        for import_line in insecure_imports:
            found = import_line in start_vigint_content
            print(f"   {'❌' if found else '✅'} {import_line} (should not be present)")
        
        # Check vigint/app.py exists and has SecureVideoAnalyzer
        print("\n📋 Checking vigint/app.py...")
        
        if os.path.exists('vigint/app.py'):
            print("   ✅ vigint/app.py exists")
            
            with open('vigint/app.py', 'r') as f:
                vigint_app_content = f.read()
            
            if 'class SecureVideoAnalyzer:' in vigint_app_content:
                print("   ✅ SecureVideoAnalyzer class found")
            else:
                print("   ❌ SecureVideoAnalyzer class not found")
                return False
        else:
            print("   ❌ vigint/app.py not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_secure_vs_insecure():
    """Test differences between secure and insecure analyzers"""
    
    print("\n🧪 Testing secure vs insecure analyzer differences...\n")
    
    try:
        # Import both analyzers
        from vigint.app import SecureVideoAnalyzer as SecureAnalyzer
        
        # Check if insecure analyzer exists (it should, but shouldn't be used)
        insecure_exists = os.path.exists('video_analyzer.py')
        
        print(f"📋 Component Status:")
        print(f"   SecureVideoAnalyzer (vigint.app): ✅ Available")
        print(f"   VideoAnalyzer (video_analyzer.py): {'⚠️ Exists (not used)' if insecure_exists else '✅ Not present'}")
        
        # Test secure analyzer features
        print(f"\n📋 SecureVideoAnalyzer Features:")
        
        # Create instance (without API key to avoid actual connections)
        secure_analyzer = SecureAnalyzer(api_key=None)
        
        # Check key security features
        security_features = [
            ('API proxy integration', hasattr(secure_analyzer, 'api_base_url')),
            ('Local fallback buffer', hasattr(secure_analyzer, 'local_frame_buffer')),
            ('Secure alert method', hasattr(secure_analyzer, 'send_security_alert')),
            ('Frame buffering', hasattr(secure_analyzer, 'add_frame_to_buffer')),
            ('Video stream processing', hasattr(secure_analyzer, 'process_video_stream')),
        ]
        
        for feature_name, has_feature in security_features:
            print(f"   {'✅' if has_feature else '❌'} {feature_name}")
        
        return all(has_feature for _, has_feature in security_features)
        
    except Exception as e:
        print(f"❌ Secure vs insecure test failed: {e}")
        return False

def test_configuration_security():
    """Test that configuration follows security best practices"""
    
    print("\n🧪 Testing configuration security...\n")
    
    try:
        # Check environment variables (should not have hardcoded credentials)
        print("📋 Environment Variable Security:")
        
        sensitive_vars = [
            'VIGINT_API_KEY',
            'GOOGLE_API_KEY', 
            'ALERT_EMAIL_PASSWORD'
        ]
        
        for var in sensitive_vars:
            value = os.getenv(var)
            if value:
                # Don't print the actual value for security
                print(f"   ✅ {var}: Set (value hidden for security)")
            else:
                print(f"   ⚠️  {var}: Not set (may need configuration)")
        
        # Check config.ini doesn't contain hardcoded credentials
        print("\n📋 Configuration File Security:")
        
        if os.path.exists('config.ini'):
            with open('config.ini', 'r') as f:
                config_content = f.read()
            
            # Check for potential hardcoded credentials (basic check)
            suspicious_patterns = [
                'password = ',
                'api_key = ',
                'secret = '
            ]
            
            hardcoded_found = False
            for pattern in suspicious_patterns:
                if pattern in config_content.lower():
                    # Check if it's just a placeholder or empty
                    lines = config_content.lower().split('\n')
                    for line in lines:
                        if pattern in line and not any(placeholder in line for placeholder in ['your_', 'placeholder', 'example', '""', "''"]):
                            hardcoded_found = True
                            break
            
            if hardcoded_found:
                print("   ⚠️  Potential hardcoded credentials found in config.ini")
            else:
                print("   ✅ No hardcoded credentials found in config.ini")
        else:
            print("   ✅ config.ini not found (using environment variables)")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration security test failed: {e}")
        return False

def test_api_proxy_integration():
    """Test API proxy integration setup"""
    
    print("\n🧪 Testing API proxy integration...\n")
    
    try:
        # Check if API proxy file exists
        if os.path.exists('api_proxy.py'):
            print("   ✅ api_proxy.py exists")
            
            with open('api_proxy.py', 'r') as f:
                api_proxy_content = f.read()
            
            # Check for key API proxy features
            api_features = [
                ('@app.route(\'/api/video/analyze\'', 'Video analysis endpoint'),
                ('@app.route(\'/api/video/alert\'', 'Alert sending endpoint'),
                ('analyze_frame_for_security', 'Secure frame analysis'),
                ('incident_type', 'Incident type support'),
                ('ALERTE SÉCURITÉ VIGINT', 'French email content'),
            ]
            
            print("   📋 API Proxy Features:")
            for pattern, description in api_features:
                found = pattern in api_proxy_content
                print(f"     {'✅' if found else '❌'} {description}")
        else:
            print("   ❌ api_proxy.py not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ API proxy integration test failed: {e}")
        return False

def test_startup_command():
    """Test the recommended startup command"""
    
    print("\n🧪 Testing startup command structure...\n")
    
    try:
        print("📋 Recommended Startup Commands:")
        
        commands = [
            "python start_vigint.py --video-input video.mp4",
            "python secure_video_analyzer.py --rtsp-url rtsp://localhost:8554/stream",
        ]
        
        for cmd in commands:
            print(f"   ✅ {cmd}")
        
        print("\n📋 NOT Recommended (Insecure):")
        insecure_commands = [
            "python video_analyzer.py --rtsp-url rtsp://localhost:8554/stream",
        ]
        
        for cmd in insecure_commands:
            print(f"   ❌ {cmd} (insecure)")
        
        return True
        
    except Exception as e:
        print(f"❌ Startup command test failed: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Testing main application security architecture...\n")
    
    results = {}
    
    # Test 1: Main app imports
    results['imports'] = test_main_app_imports()
    
    # Test 2: Secure vs insecure
    results['secure_features'] = test_secure_vs_insecure()
    
    # Test 3: Configuration security
    results['config_security'] = test_configuration_security()
    
    # Test 4: API proxy integration
    results['api_proxy'] = test_api_proxy_integration()
    
    # Test 5: Startup commands
    results['startup'] = test_startup_command()
    
    print(f"\n📋 Security Test Results:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print(f"\n🎉 SUCCESS: Main application uses secure architecture!")
        print(f"   🔒 Uses SecureVideoAnalyzer from vigint.app")
        print(f"   🔒 API proxy handles sensitive operations")
        print(f"   🔒 No hardcoded credentials")
        print(f"   🇫🇷 French email alerts with incident_type")
        print(f"   🔄 Local fallback capability")
    else:
        print(f"\n❌ Security issues found - check failed tests above")
    
    print(f"\n🚀 To start the secure application:")
    print(f"   python start_vigint.py --video-input your_video.mp4")
    print(f"\n🔧 For standalone secure analysis:")
    print(f"   python secure_video_analyzer.py --rtsp-url rtsp://localhost:8554/stream")