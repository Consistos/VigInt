#!/usr/bin/env python3
"""
Test visual deduplication directly without video streaming
"""

import cv2
import sys
from video_analyzer import _get_frame_hash

def test_same_frame():
    """Test that same frame produces same hash"""
    print("Testing visual deduplication...")
    
    # Read a video file
    video_path = sys.argv[1] if len(sys.argv) > 1 else 'test.mp4'
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"❌ Failed to open video: {video_path}")
        return
    
    print(f"✅ Opened video: {video_path}")
    
    # Read frames throughout the video and hash them
    frame_hashes = []
    frame_indices = []
    
    # Sample frames at different times in the video
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    print(f"Video info: {total_frames} frames, {fps} fps, {total_frames/fps:.1f}s duration\n")
    
    # Sample every 30 frames (about 1 second at 30fps)
    for i in range(0, min(total_frames, 300), 30):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_hash = _get_frame_hash(frame)
        frame_hashes.append(frame_hash)
        frame_indices.append(i)
        print(f"Frame {i:3d} ({i/fps:5.1f}s): {frame_hash[:8]}... (shape: {frame.shape})")
    
    cap.release()
    
    # Check for duplicates
    unique_hashes = set(frame_hashes)
    print(f"\n📊 Results:")
    print(f"   Total frames: {len(frame_hashes)}")
    print(f"   Unique hashes: {len(unique_hashes)}")
    print(f"   Duplicates: {len(frame_hashes) - len(unique_hashes)}")
    
    # Test that same frame gives same hash
    cap = cv2.VideoCapture(video_path)
    ret, frame1 = cap.read()
    cap.release()
    
    hash1 = _get_frame_hash(frame1)
    hash2 = _get_frame_hash(frame1)  # Same frame
    
    if hash1 == hash2:
        print(f"\n✅ Same frame produces same hash: {hash1[:8]}...")
    else:
        print(f"\n❌ ERROR: Same frame produces different hashes!")
        print(f"   Hash 1: {hash1}")
        print(f"   Hash 2: {hash2}")

if __name__ == '__main__':
    test_same_frame()
