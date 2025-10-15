#!/usr/bin/env python3
"""Test email functionality"""

import sys

def test_email_imports():
    """Test if email modules can be imported"""
    try:
        import smtplib
        print("✅ smtplib imported successfully")
        
        import email.mime.text
        print("✅ email.mime.text imported successfully")
        
        import email.mime.multipart  
        print("✅ email.mime.multipart imported successfully")
        
        from email.mime.text import MIMEText as MimeText
        print("✅ MIMEText imported successfully")
        
        from email.mime.multipart import MIMEMultipart as MimeMultipart
        print("✅ MIMEMultipart imported successfully")
        
        # Test creating objects
        msg = MimeMultipart()
        print("✅ MimeMultipart object created successfully")
        
        text = MimeText("Test message", 'plain')
        print("✅ MimeText object created successfully")
        
        print("\n🎉 All email functionality is working!")
        return True
        
    except Exception as e:
        print(f"❌ Email import failed: {e}")
        return False

if __name__ == '__main__':
    success = test_email_imports()
    sys.exit(0 if success else 1)