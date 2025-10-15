#!/usr/bin/env python3
"""
Test script to demonstrate the dual-buffer video analysis system
Shows how frames are buffered BEFORE analysis for smooth video creation
"""

import cv2
import time
import logging
import base64
from datetime import datetime
from collections import deque
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DualBufferDemo:
    """Demonstrates the dual buffer approach for smooth video creation"""
    
    def __init__(self):
        # Dual buffer configuration
        self.short_buffer_duration = 3   # seconds for analysis
        self.long_buffer_duration = 10   # seconds for video evidence
        self.buffer_fps = 25             # target FPS
        self.analysis_interval = 3       # analyze every 3 seconds
        
        # Calculate buffer sizes
        max_frames = self.long_buffer_duration * self.buffer_fps
        
        # Continuous frame buffer - ALL frames go here FIRST
        self.continuous_buffer = deque(maxlen=max_frames)
        
        # Statistics
        self.frame_count = 0
        self.analysis_count = 0
        self.last_analysis_time = 0
        
        logger.info("🎬 Dual Buffer Video Demo Initialized")
        logger.info(f"📹 Continuous buffer: {self.long_buffer_duration}s ({max_frames} frames)")
        logger.info(f"🔍 Analysis every: {self.analysis_interval}s")
        logger.info(f"🎯 Target FPS: {self.buffer_fps}")
    
    def add_frame_to_buffer(self, frame):
        """Add frame to continuous buffer BEFORE any analysis"""
        try:
            # Convert frame to base64 for storage
            _, buffer_img = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_base64 = base64.b64encode(buffer_img).decode('utf-8')
            
            frame_info = {
                'frame_data': frame_base64,
                'frame_count': self.frame_count,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                'buffer_size': len(self.continuous_buffer)
            }
            
            # Add to continuous buffer - this happens for EVERY frame
            self.continuous_buffer.append(frame_info)
            
            # Log buffer status periodically
            if self.frame_count % 50 == 0:
                logger.info(f"📹 Buffer status: {len(self.continuous_buffer)} frames, "
                          f"latest: {frame_info['timestamp']}")
            
        except Exception as e:
            logger.error(f"Error adding frame to buffer: {e}")
    
    def simulate_analysis(self):
        """Simulate AI analysis of recent frames"""
        self.analysis_count += 1
        
        if len(self.continuous_buffer) == 0:
            logger.warning("🔍 No frames available for analysis")
            return False
        
        # Get recent frames for analysis (short buffer)
        analysis_frames_count = min(
            self.short_buffer_duration * self.buffer_fps,
            len(self.continuous_buffer)
        )
        
        recent_frames = list(self.continuous_buffer)[-analysis_frames_count:]
        
        logger.info(f"🔍 Analysis #{self.analysis_count}: Analyzing {len(recent_frames)} recent frames")
        
        # Simulate incident detection (every 4th analysis for demo)
        incident_detected = (self.analysis_count % 4 == 0)
        
        if incident_detected:
            logger.warning("🚨 SIMULATED SECURITY INCIDENT DETECTED!")
            self.create_incident_video()
            return True
        else:
            logger.info("✅ No security incident detected")
            return False
    
    def create_incident_video(self):
        """Create video from ALL buffered frames (not just analyzed ones)"""
        try:
            # Get ALL frames from continuous buffer for smooth video
            all_frames = list(self.continuous_buffer)
            
            if len(all_frames) < 10:
                logger.warning("⚠️ Insufficient frames for video creation")
                return None
            
            logger.info(f"🎬 Creating incident video from {len(all_frames)} continuous frames")
            logger.info(f"📊 Video duration: ~{len(all_frames) / self.buffer_fps:.1f} seconds")
            
            # Create video filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            video_filename = f"incident_video_{timestamp}.mp4"
            
            # Decode first frame to get dimensions
            first_frame_data = base64.b64decode(all_frames[0]['frame_data'])
            import numpy as np
            first_frame = cv2.imdecode(
                np.frombuffer(first_frame_data, dtype=np.uint8), 
                cv2.IMREAD_COLOR
            )
            height, width = first_frame.shape[:2]
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(
                video_filename, 
                fourcc, 
                self.buffer_fps, 
                (width, height)
            )
            
            # Write all frames to video
            frames_written = 0
            for frame_info in all_frames:
                try:
                    # Decode frame
                    frame_data = base64.b64decode(frame_info['frame_data'])
                    frame = cv2.imdecode(
                        np.frombuffer(frame_data, dtype=np.uint8), 
                        cv2.IMREAD_COLOR
                    )
                    
                    # Add timestamp overlay
                    cv2.putText(
                        frame, 
                        f"Frame: {frame_info['frame_count']} | {frame_info['timestamp']}", 
                        (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.7, 
                        (0, 255, 0), 
                        2
                    )
                    
                    video_writer.write(frame)
                    frames_written += 1
                    
                except Exception as e:
                    logger.error(f"Error writing frame {frame_info['frame_count']}: {e}")
            
            video_writer.release()
            
            # Get file size
            file_size = os.path.getsize(video_filename) / (1024 * 1024)  # MB
            
            logger.info(f"✅ Video created successfully!")
            logger.info(f"📁 Filename: {video_filename}")
            logger.info(f"🎬 Frames written: {frames_written}")
            logger.info(f"📊 File size: {file_size:.1f} MB")
            logger.info(f"⏱️ Duration: ~{frames_written / self.buffer_fps:.1f} seconds")
            logger.info(f"🎯 This video shows CONTINUOUS footage, not just analyzed frames!")
            
            return video_filename
            
        except Exception as e:
            logger.error(f"Error creating incident video: {e}")
            return None
    
    def run_demo(self, video_source="test_video.mp4", duration_seconds=30):
        """Run the dual buffer demo"""
        logger.info(f"🚀 Starting dual buffer demo with {video_source}")
        logger.info(f"⏱️ Demo duration: {duration_seconds} seconds")
        
        # Try to open video source
        cap = cv2.VideoCapture(video_source)
        
        if not cap.isOpened():
            logger.error(f"❌ Failed to open video source: {video_source}")
            logger.info("💡 Creating synthetic frames for demo...")
            self.run_synthetic_demo(duration_seconds)
            return
        
        logger.info(f"✅ Video source opened successfully")
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration_seconds:
                ret, frame = cap.read()
                
                if not ret:
                    # Loop video
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                
                self.frame_count += 1
                current_time = time.time()
                
                # CRITICAL: Add EVERY frame to buffer FIRST
                self.add_frame_to_buffer(frame.copy())
                
                # Analyze periodically (not every frame)
                if current_time - self.last_analysis_time >= self.analysis_interval:
                    self.last_analysis_time = current_time
                    self.simulate_analysis()
                
                # Maintain target FPS
                time.sleep(1.0 / self.buffer_fps)
        
        except KeyboardInterrupt:
            logger.info("Demo stopped by user")
        finally:
            cap.release()
            
        self.print_demo_summary()
    
    def run_synthetic_demo(self, duration_seconds=30):
        """Run demo with synthetic frames"""
        logger.info("🎨 Running synthetic frame demo")
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration_seconds:
                # Create synthetic frame
                frame = self.create_synthetic_frame()
                
                self.frame_count += 1
                current_time = time.time()
                
                # Add frame to buffer FIRST
                self.add_frame_to_buffer(frame)
                
                # Analyze periodically
                if current_time - self.last_analysis_time >= self.analysis_interval:
                    self.last_analysis_time = current_time
                    self.simulate_analysis()
                
                # Maintain target FPS
                time.sleep(1.0 / self.buffer_fps)
        
        except KeyboardInterrupt:
            logger.info("Demo stopped by user")
        
        self.print_demo_summary()
    
    def create_synthetic_frame(self):
        """Create a synthetic frame for demo purposes"""
        import numpy as np
        
        # Create a colorful frame with timestamp
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add some color patterns
        frame[:, :, 0] = (self.frame_count * 2) % 255  # Blue channel
        frame[:, :, 1] = (self.frame_count * 3) % 255  # Green channel
        frame[:, :, 2] = (self.frame_count * 5) % 255  # Red channel
        
        # Add frame counter text
        cv2.putText(
            frame, 
            f"Frame: {self.frame_count}", 
            (50, 100), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            2, 
            (255, 255, 255), 
            3
        )
        
        # Add timestamp
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        cv2.putText(
            frame, 
            timestamp, 
            (50, 200), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            1, 
            (255, 255, 255), 
            2
        )
        
        return frame
    
    def print_demo_summary(self):
        """Print summary of the demo"""
        logger.info("\n" + "="*60)
        logger.info("📊 DUAL BUFFER DEMO SUMMARY")
        logger.info("="*60)
        logger.info(f"📹 Total frames captured: {self.frame_count}")
        logger.info(f"🔍 Total analyses performed: {self.analysis_count}")
        logger.info(f"📊 Buffer size at end: {len(self.continuous_buffer)} frames")
        logger.info(f"⏱️ Buffer duration: ~{len(self.continuous_buffer) / self.buffer_fps:.1f} seconds")
        logger.info(f"🎯 Analysis frequency: Every {self.analysis_interval} seconds")
        logger.info(f"💡 Key insight: ALL frames are buffered for smooth video!")
        logger.info("="*60)


def main():
    """Main function to run the dual buffer demo"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dual Buffer Video Analysis Demo')
    parser.add_argument('--video', type=str, default='test_video.mp4',
                       help='Video file to use for demo (default: synthetic frames)')
    parser.add_argument('--duration', type=int, default=30,
                       help='Demo duration in seconds (default: 30)')
    
    args = parser.parse_args()
    
    # Create and run demo
    demo = DualBufferDemo()
    demo.run_demo(args.video, args.duration)


if __name__ == '__main__':
    main()