#!/usr/bin/env python3
"""
Test script to verify configuration reading
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import config

def test_config_reading():
    """Test configuration reading"""
    print("🔧 Testing Configuration Reading")
    print("=" * 50)
    
    # Test all email-related config values
    email_configs = [
        'smtp_server',
        'smtp_port', 
        'username',
        'password',
        'from_email',
        'to_email',
        'sender_email',
        'sender_password',
        'admin_email'
    ]
    
    print("Email configuration values from config.ini:")
    for key in email_configs:
        try:
            if key == 'smtp_port':
                value = config.getint('Email', key, 'NOT_SET')
            else:
                value = config.get('Email', key, 'NOT_SET')
            
            if 'password' in key.lower():
                display_value = '*' * len(str(value)) if value != 'NOT_SET' else 'NOT_SET'
            else:
                display_value = value
            
            print(f"  {key}: {display_value}")
        except Exception as e:
            print(f"  {key}: ERROR - {e}")
    
    # Test environment variables
    print(f"\nEnvironment variables:")
    env_vars = [
        'ALERT_SMTP_SERVER',
        'ALERT_SMTP_PORT', 
        'ALERT_EMAIL',
        'ALERT_EMAIL_PASSWORD',
        'ADMIN_EMAIL'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'password' in var.lower():
                display_value = '*' * len(value)
            else:
                display_value = value
            print(f"  {var}: {display_value}")
        else:
            print(f"  {var}: NOT_SET")

if __name__ == '__main__':
    test_config_reading()