#!/usr/bin/env python3
"""Test email configuration loading"""

from config import config

print("Testing email configuration loading...")
print()

# Test email configuration
email_config = {
    'smtp_server': config.get('Email', 'smtp_server', 'smtp.gmail.com'),
    'smtp_port': config.getint('Email', 'smtp_port', 587),
    'username': config.get('Email', 'username', ''),
    'password': config.get('Email', 'password', ''),
    'from_email': config.get('Email', 'from_email', ''),
    'to_email': config.get('Email', 'to_email', '')
}

print("Email configuration loaded:")
for key, value in email_config.items():
    if key == 'password':
        print(f"  {key}: {'*' * len(value) if value else '(empty)'}")
    else:
        print(f"  {key}: {value if value else '(empty)'}")

print()
print("Configuration check:")
print(f"  Username present: {bool(email_config['username'])}")
print(f"  To email present: {bool(email_config['to_email'])}")
print(f"  Password present: {bool(email_config['password'])}")

if email_config['username'] and email_config['to_email']:
    print("✅ Email configuration is complete!")
else:
    print("❌ Email configuration is incomplete!")
    if not email_config['username']:
        print("  - Missing username")
    if not email_config['to_email']:
        print("  - Missing to_email")