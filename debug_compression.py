#!/usr/bin/env python3
"""
Debug compression issues
"""

import cv2
import numpy as np
import tempfile
import os
import traceback

def create_simple_test_video():
    """Create a simple test video"""
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
        video_path = temp_file.name
    
    # Create a simple video
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Use basic codec first
    out = cv2.VideoWriter(video_path, fourcc, 10, (320, 240))
    
    if not out.isOpened():
        print("❌ Cannot create test video")
        return None
    
    # Create 50 frames (5 seconds at 10fps)
    for i in range(50):
        frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        cv2.putText(frame, f"Frame {i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        out.write(frame)
    
    out.release()
    
    # Check if file was created
    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        print(f"✅ Created test video: {size_mb:.2f} MB")
        return video_path
    else:
        print("❌ Test video creation failed")
        return None

def test_compression_function():
    """Test the compression function directly"""
    print("🔧 Debug Video Compression")
    print("=" * 40)
    
    # Create test video
    video_path = create_simple_test_video()
    if not video_path:
        return
    
    try:
        # Import and test compression function
        # Support both local and distributed deployment
        from config import config
        if config.api_server_url:
            print(f"📡 Using remote API server: {config.api_server_url}")
            from api_client import compress_video_for_email
        else:
            print(f"🏠 Using local API proxy")
            from api_proxy import compress_video_for_email
        
        print(f"\n🔄 Testing compression function...")
        
        # Force compression by setting a very small limit
        result = compress_video_for_email(video_path, max_size_mb=0.01, quality_reduction=0.8)
        
        print(f"Result: {result}")
        
        if result['success']:
            if result['compressed']:
                print(f"✅ Compression successful!")
                print(f"   Original: {result['original_size_mb']:.3f} MB")
                print(f"   Compressed: {result['final_size_mb']:.3f} MB")
                print(f"   Ratio: {result['compression_ratio']:.3f}")
                print(f"   Codec: {result.get('codec_used', 'Unknown')}")
                
                # Clean up compressed file
                if os.path.exists(result['compressed_path']):
                    os.unlink(result['compressed_path'])
            else:
                print(f"ℹ️  No compression needed (file already small enough)")
        else:
            print(f"❌ Compression failed: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"❌ Error testing compression: {e}")
        traceback.print_exc()
    
    finally:
        # Clean up test video
        if os.path.exists(video_path):
            os.unlink(video_path)

if __name__ == '__main__':
    test_compression_function()