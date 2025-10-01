#!/usr/bin/env python3
"""
Check email configuration for video alerts
"""

import os
import smtplib
from email.mime.text import MIMEText
from config import config

def check_email_config():
    """Check email configuration and test connectivity"""
    print("📧 Checking email configuration...\n")
    
    # Check environment variables
    print("Environment Variables:")
    env_vars = [
        'ALERT_SMTP_SERVER', 'ALERT_SMTP_PORT', 'ALERT_EMAIL', 
        'ALERT_EMAIL_PASSWORD', 'ADMIN_EMAIL'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Hide password for security
            display_value = '***' if 'PASSWORD' in var else value
            print(f"  {var}: {display_value}")
        else:
            print(f"  {var}: Not set")
    
    print("\nConfig File Settings:")
    try:
        smtp_server = config.get('Email', 'smtp_server', 'smtp.gmail.com')
        smtp_port = config.get('Email', 'smtp_port', '587')
        sender_email = config.get('Email', 'sender_email', '')
        admin_email = config.get('Email', 'admin_email', '')
        
        print(f"  SMTP Server: {smtp_server}")
        print(f"  SMTP Port: {smtp_port}")
        print(f"  Sender Email: {sender_email}")
        print(f"  Admin Email: {admin_email}")
        
    except Exception as e:
        print(f"  Error reading config: {e}")
    
    # Get final configuration (env vars override config file)
    print("\nFinal Configuration:")
    smtp_server = os.getenv('ALERT_SMTP_SERVER') or config.get('Email', 'smtp_server', 'smtp.gmail.com')
    smtp_port = int(os.getenv('ALERT_SMTP_PORT') or config.get('Email', 'smtp_port', '587'))
    sender_email = os.getenv('ALERT_EMAIL') or config.get('Email', 'sender_email', '')
    sender_password = os.getenv('ALERT_EMAIL_PASSWORD') or config.get('Email', 'sender_password', '')
    admin_email = os.getenv('ADMIN_EMAIL') or config.get('Email', 'admin_email', '')
    
    print(f"  SMTP Server: {smtp_server}")
    print(f"  SMTP Port: {smtp_port}")
    print(f"  Sender Email: {sender_email}")
    print(f"  Admin Email: {admin_email}")
    print(f"  Password: {'Set' if sender_password else 'Not set'}")
    
    # Check for missing configuration
    missing = []
    if not sender_email:
        missing.append('Sender email')
    if not sender_password:
        missing.append('Sender password')
    if not admin_email:
        missing.append('Admin email')
    
    if missing:
        print(f"\n❌ Missing configuration: {', '.join(missing)}")
        print("\nTo fix this, either:")
        print("1. Set environment variables:")
        for var in env_vars:
            if any(item.lower().replace(' ', '_') in var.lower() for item in missing):
                print(f"   export {var}='your_value'")
        print("\n2. Or update config.ini [Email] section")
        return False
    
    print("\n✅ Configuration appears complete")
    return True

def test_smtp_connection():
    """Test SMTP connection"""
    print("\n🔌 Testing SMTP connection...\n")
    
    try:
        # Get configuration
        smtp_server = os.getenv('ALERT_SMTP_SERVER') or config.get('Email', 'smtp_server', 'smtp.gmail.com')
        smtp_port = int(os.getenv('ALERT_SMTP_PORT') or config.get('Email', 'smtp_port', '587'))
        sender_email = os.getenv('ALERT_EMAIL') or config.get('Email', 'sender_email', '')
        sender_password = os.getenv('ALERT_EMAIL_PASSWORD') or config.get('Email', 'sender_password', '')
        
        if not sender_email or not sender_password:
            print("❌ Cannot test connection - missing email or password")
            return False
        
        print(f"Connecting to {smtp_server}:{smtp_port}...")
        
        # Test connection
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        print("✅ Connected to SMTP server")
        
        # Test TLS
        server.starttls()
        print("✅ TLS connection established")
        
        # Test authentication
        server.login(sender_email, sender_password)
        print("✅ Authentication successful")
        
        server.quit()
        print("✅ SMTP connection test passed")
        return True
        
    except Exception as e:
        print(f"❌ SMTP connection failed: {e}")
        return False

def send_test_email():
    """Send a test email"""
    print("\n📤 Sending test email...\n")
    
    try:
        from alerts import AlertManager
        
        alert_manager = AlertManager()
        
        test_message = f"""
This is a test email from the Vigint video alert system.

Test Details:
- Time: {os.popen('date').read().strip()}
- System: Video Alert Configuration Test
- Purpose: Verify email delivery functionality

If you receive this email, the basic email functionality is working.
Video attachments will be tested separately.

Next steps:
1. Verify this email was received
2. Test video alert functionality
3. Check video attachment capability
"""
        
        result = alert_manager.send_email_alert(
            message=test_message,
            alert_type="test"
        )
        
        if result.get('success', False):
            print("✅ Test email sent successfully!")
            print(f"   Recipient: {result.get('recipient', 'Unknown')}")
            return True
        else:
            print(f"❌ Test email failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test email failed with exception: {e}")
        return False

if __name__ == '__main__':
    print("🚨 Vigint Email Configuration Checker\n")
    print("=" * 60)
    
    try:
        # Check configuration
        config_ok = check_email_config()
        
        if config_ok:
            # Test SMTP connection
            smtp_ok = test_smtp_connection()
            
            if smtp_ok:
                # Send test email
                email_ok = send_test_email()
                
                print("\n" + "=" * 60)
                print("SUMMARY:")
                print(f"Configuration: {'✅ OK' if config_ok else '❌ FAIL'}")
                print(f"SMTP Connection: {'✅ OK' if smtp_ok else '❌ FAIL'}")
                print(f"Test Email: {'✅ OK' if email_ok else '❌ FAIL'}")
                
                if config_ok and smtp_ok and email_ok:
                    print("\n🎉 Email system is ready for video alerts!")
                else:
                    print("\n⚠️ Some issues found. Please fix before using video alerts.")
            else:
                print("\n❌ SMTP connection failed. Cannot proceed with email test.")
        else:
            print("\n❌ Configuration incomplete. Please fix configuration first.")
            
    except Exception as e:
        print(f"❌ Configuration check failed: {e}")
        import traceback
        traceback.print_exc()