#!/usr/bin/env python3
"""
Test script to verify video compression quality improvements
"""

import cv2
import numpy as np
import tempfile
import os
import sys
from datetime import datetime

def create_test_video(output_path, duration_seconds=5, fps=25, resolution=(640, 480)):
    """Create a test video with some visual patterns"""
    fourcc = cv2.VideoWriter_fourcc(*'H264')
    out = cv2.VideoWriter(output_path, fourcc, fps, resolution)
    
    if not out.isOpened():
        # Fallback codec
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, resolution)
    
    total_frames = duration_seconds * fps
    
    for frame_num in range(total_frames):
        # Create a test pattern with text and shapes
        frame = np.zeros((resolution[1], resolution[0], 3), dtype=np.uint8)
        
        # Add gradient background
        for y in range(resolution[1]):
            frame[y, :] = [int(255 * y / resolution[1]), 50, 100]
        
        # Add moving circle
        center_x = int(resolution[0] * (0.5 + 0.3 * np.sin(frame_num * 0.1)))
        center_y = int(resolution[1] * 0.5)
        cv2.circle(frame, (center_x, center_y), 30, (255, 255, 255), -1)
        
        # Add frame counter text
        cv2.putText(frame, f"Frame {frame_num}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        cv2.putText(frame, timestamp, (10, resolution[1] - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        out.write(frame)
    
    out.release()
    return total_frames

def analyze_video_quality(video_path):
    """Analyze video quality metrics"""
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        return None
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Calculate file size
    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    
    cap.release()
    
    return {
        'fps': fps,
        'resolution': f"{width}x{height}",
        'frame_count': frame_count,
        'duration': frame_count / fps if fps > 0 else 0,
        'file_size_mb': file_size_mb,
        'bitrate_kbps': (file_size_mb * 8 * 1024) / (frame_count / fps) if fps > 0 and frame_count > 0 else 0
    }

def test_compression_quality():
    """Test the compression quality with different settings"""
    print("🎬 Testing Video Compression Quality")
    print("=" * 50)
    
    # Create test video
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
        test_video_path = temp_file.name
    
    try:
        print("📹 Creating test video...")
        frames_created = create_test_video(test_video_path, duration_seconds=10)
        print(f"✅ Created test video with {frames_created} frames")
        
        # Analyze original video
        original_stats = analyze_video_quality(test_video_path)
        if original_stats:
            print(f"\n📊 Original Video Stats:")
            print(f"   Resolution: {original_stats['resolution']}")
            print(f"   FPS: {original_stats['fps']:.1f}")
            print(f"   Duration: {original_stats['duration']:.1f}s")
            print(f"   File Size: {original_stats['file_size_mb']:.2f} MB")
            print(f"   Bitrate: {original_stats['bitrate_kbps']:.0f} kbps")
        
        # Test compression if the API function is available
        try:
            # Import the compression function
            sys.path.append('.')
            from api_proxy import compress_video_for_email
            
            print(f"\n🔄 Testing compression...")
            
            # Test with different quality settings
            quality_levels = [0.95, 0.85, 0.7, 0.5]
            
            for quality in quality_levels:
                print(f"\n   Testing quality level: {quality}")
                
                # Force compression by using a very small limit
                result = compress_video_for_email(
                    test_video_path, 
                    max_size_mb=0.01,  # Very small limit to force compression
                    quality_reduction=quality
                )
                
                if result['success'] and result['compressed']:
                    compressed_stats = analyze_video_quality(result['compressed_path'])
                    if compressed_stats:
                        print(f"   ✅ Compressed: {compressed_stats['resolution']} @ {compressed_stats['fps']:.1f}fps")
                        print(f"      Size: {original_stats['file_size_mb']:.2f} MB → {compressed_stats['file_size_mb']:.2f} MB")
                        print(f"      Ratio: {compressed_stats['file_size_mb']/original_stats['file_size_mb']:.2f}")
                        print(f"      Codec: {result.get('codec_used', 'Unknown')}")
                    
                    # Clean up compressed file
                    if os.path.exists(result['compressed_path']):
                        os.unlink(result['compressed_path'])
                else:
                    print(f"   ❌ Compression failed: {result.get('error', 'Unknown error')}")
        
        except ImportError as e:
            print(f"\n⚠️  Cannot test compression function: {e}")
            print("   Make sure you're running this from the project directory")
        
    finally:
        # Clean up test video
        if os.path.exists(test_video_path):
            os.unlink(test_video_path)
    
    print(f"\n✅ Video compression test completed!")

if __name__ == '__main__':
    test_compression_quality()