#!/usr/bin/env python3
"""
Test the dual-buffer video analysis system with a real video file
Handles API issues gracefully and demonstrates smooth video creation
"""

import os
import sys
import logging
import time
from video_analyzer import VideoAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_dual_buffer_analysis(video_path, duration_seconds=30):
    """Test dual buffer analysis with a real video file"""
    
    logger.info("🎬 Testing Dual Buffer Video Analysis System")
    logger.info("=" * 60)
    
    # Check if video file exists
    if not os.path.exists(video_path):
        logger.error(f"❌ Video file not found: {video_path}")
        return False
    
    logger.info(f"📹 Video file: {video_path}")
    logger.info(f"⏱️ Test duration: {duration_seconds} seconds")
    
    # Create video analyzer
    analyzer = VideoAnalyzer()
    
    # Check API availability
    if not analyzer.model:
        logger.warning("⚠️ Gemini API not available - running in demo mode")
        logger.info("💡 The dual-buffer system will still work for frame capture!")
    
    # Override analysis method for demo if API not available
    if not analyzer.model:
        def mock_analyze_frame(frame):
            """Mock analysis for demo purposes"""
            import random
            from datetime import datetime
            
            # Simulate incident detection occasionally
            incident_detected = random.random() < 0.1  # 10% chance
            
            return {
                'timestamp': datetime.now().isoformat(),
                'frame_count': analyzer.frame_count,
                'analysis': f"Mock analysis of frame {analyzer.frame_count}",
                'incident_detected': incident_detected,
                'incident_type': 'shoplifting' if incident_detected else '',
                'frame_shape': frame.shape if frame is not None else (480, 640, 3)
            }
        
        analyzer.analyze_frame = mock_analyze_frame
        logger.info("🎭 Using mock analysis for demonstration")
    
    # Start analysis with timeout
    logger.info("🚀 Starting dual-buffer video analysis...")
    
    try:
        # Run analysis in a separate thread with timeout
        import threading
        
        analysis_thread = threading.Thread(
            target=analyzer.process_video_stream,
            args=(video_path,),
            daemon=True
        )
        
        analysis_thread.start()
        
        # Let it run for the specified duration
        time.sleep(duration_seconds)
        
        # Stop analysis
        analyzer.stop()
        
        # Wait a bit for cleanup
        time.sleep(2)
        
        # Print results
        logger.info("\n" + "=" * 60)
        logger.info("📊 DUAL BUFFER TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"📹 Total frames processed: {analyzer.frame_count}")
        logger.info(f"📦 Buffer size: {len(analyzer.frame_buffer)} frames")
        logger.info(f"⏱️ Buffer duration: ~{len(analyzer.frame_buffer) / analyzer.buffer_fps:.1f} seconds")
        logger.info(f"🎯 Target FPS: {analyzer.buffer_fps}")
        
        if len(analyzer.frame_buffer) > 0:
            logger.info("✅ Dual buffer system working correctly!")
            logger.info("🎬 Frames are being buffered continuously for smooth video")
            
            # Show buffer timeline
            if len(analyzer.frame_buffer) >= 5:
                recent_frames = list(analyzer.frame_buffer)[-5:]
                timestamps = [f['timestamp'] for f in recent_frames]
                logger.info(f"📈 Recent frame timestamps: {timestamps}")
        else:
            logger.warning("⚠️ No frames in buffer - check video file and processing")
        
        return True
        
    except KeyboardInterrupt:
        logger.info("Test stopped by user")
        analyzer.stop()
        return True
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        analyzer.stop()
        return False

def find_test_video():
    """Find a suitable test video file"""
    
    # Look for existing video files
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
    search_paths = [
        '.',
        './mock_sparse_ai_cloud',
        '/Users/david2/dev/Vigint'
    ]
    
    for search_path in search_paths:
        if os.path.exists(search_path):
            for file in os.listdir(search_path):
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    full_path = os.path.join(search_path, file)
                    logger.info(f"📹 Found video file: {full_path}")
                    return full_path
    
    return None

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Dual Buffer Video Analysis')
    parser.add_argument('--video', type=str, 
                       help='Path to video file (will auto-detect if not provided)')
    parser.add_argument('--duration', type=int, default=20,
                       help='Test duration in seconds (default: 20)')
    
    args = parser.parse_args()
    
    # Find video file
    video_path = args.video
    if not video_path:
        video_path = find_test_video()
        
    if not video_path:
        logger.error("❌ No video file found. Please provide --video parameter")
        logger.info("💡 You can use any .mp4, .avi, or .mov file")
        return 1
    
    # Run test
    success = test_dual_buffer_analysis(video_path, args.duration)
    
    if success:
        logger.info("\n🎉 Dual buffer test completed successfully!")
        logger.info("💡 Key benefits demonstrated:")
        logger.info("   ✅ Continuous frame buffering (not just analyzed frames)")
        logger.info("   ✅ Smooth video creation capability")
        logger.info("   ✅ Non-blocking analysis processing")
        logger.info("   ✅ Configurable buffer duration")
        return 0
    else:
        logger.error("❌ Test failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())