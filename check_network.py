#!/usr/bin/env python3
"""
Quick network connectivity check for Vigint system
"""

import socket
import subprocess
import sys

def check_dns_resolution(hostname):
    """Check if hostname can be resolved"""
    try:
        ip = socket.gethostbyname(hostname)
        return True, ip
    except socket.gaierror as e:
        return False, str(e)

def check_internet():
    """Check basic internet connectivity"""
    print("\n" + "="*70)
    print("NETWORK CONNECTIVITY CHECK")
    print("="*70)
    
    # Test DNS resolution for critical services
    services = {
        'Google DNS': '8.8.8.8',
        'Sparse AI Server': 'sparse-ai-video-server.onrender.com',
        'Gmail SMTP': 'smtp.gmail.com',
        'Cloudflare': '1.1.1.1'
    }
    
    print("\n1. DNS Resolution Tests:")
    all_ok = True
    for name, host in services.items():
        # For IPs, just check if we can reach them
        if host.replace('.', '').isdigit():
            try:
                socket.create_connection((host, 53), timeout=3)
                print(f"   ✅ {name} ({host}): Reachable")
            except:
                print(f"   ❌ {name} ({host}): Not reachable")
                all_ok = False
        else:
            success, result = check_dns_resolution(host)
            if success:
                print(f"   ✅ {name} ({host}): Resolves to {result}")
            else:
                print(f"   ❌ {name} ({host}): Cannot resolve - {result}")
                all_ok = False
    
    # Test actual connectivity
    print("\n2. Connectivity Tests:")
    
    # Test ping to Google DNS
    try:
        result = subprocess.run(['ping', '-c', '1', '-W', '2', '8.8.8.8'], 
                              capture_output=True, timeout=5)
        if result.returncode == 0:
            print(f"   ✅ Ping to 8.8.8.8: Success")
        else:
            print(f"   ❌ Ping to 8.8.8.8: Failed")
            all_ok = False
    except:
        print(f"   ❌ Ping to 8.8.8.8: Timeout")
        all_ok = False
    
    # Test HTTPS connectivity
    try:
        import urllib.request
        urllib.request.urlopen('https://www.google.com', timeout=5)
        print(f"   ✅ HTTPS to google.com: Success")
    except:
        print(f"   ❌ HTTPS to google.com: Failed")
        all_ok = False
    
    print("\n" + "="*70)
    if all_ok:
        print("✅ NETWORK STATUS: All checks passed")
        print("   System should be able to send emails and upload videos")
    else:
        print("⚠️  NETWORK STATUS: Issues detected")
        print("   System will work in OFFLINE MODE:")
        print("   - Videos saved to: mock_sparse_ai_cloud/")
        print("   - Incidents saved to: offline_incidents/")
    print("="*70)
    
    return all_ok

if __name__ == '__main__':
    try:
        is_online = check_internet()
        sys.exit(0 if is_online else 1)
    except KeyboardInterrupt:
        print("\n\nCheck cancelled by user")
        sys.exit(1)
