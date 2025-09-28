#!/usr/bin/env python3
"""
Test video server connection and functionality
"""
import requests
import subprocess
import time
import socket
import sys

def check_port_open(port):
    """Check if port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Error checking port {port}: {e}")
        return False

def test_server():
    """Test the video server"""
    print("🔍 Testing video server connection...")
    
    # Check if port 9999 is open
    if not check_port_open(9999):
        print("❌ Port 9999 is not open")
        print("🚀 Starting simple video server...")
        
        # Start the server
        process = subprocess.Popen([
            sys.executable, 'simple_video_server.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Wait for server to start
        for i in range(10):
            time.sleep(1)
            if check_port_open(9999):
                print("✅ Server started successfully")
                break
        else:
            print("❌ Server failed to start")
            stdout, stderr = process.communicate(timeout=2)
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return False
    else:
        print("✅ Port 9999 is open")
    
    # Test health endpoint
    try:
        response = requests.get('http://127.0.0.1:9999/health', timeout=5)
        print(f"Health check: {response.status_code} - {response.text}")
        
        if response.status_code == 200:
            print("✅ Health check passed")
        else:
            print("❌ Health check failed")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Request error: {e}")
        return False
    
    # Test videos endpoint
    try:
        response = requests.get('http://127.0.0.1:9999/videos', timeout=5)
        print(f"Videos endpoint: {response.status_code}")
        
        if response.status_code == 200:
            videos = response.json()
            print(f"✅ Found {len(videos)} videos")
            if videos:
                print(f"First video: {videos[0]['video_id']}")
        else:
            print("❌ Videos endpoint failed")
            
    except Exception as e:
        print(f"❌ Videos request error: {e}")
    
    return True

if __name__ == "__main__":
    test_server()