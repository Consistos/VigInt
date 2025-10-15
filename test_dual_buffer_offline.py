#!/usr/bin/env python3
"""
Test dual-buffer system without external APIs
Demonstrates the core buffering concept with local processing
"""

import cv2
import time
import logging
import base64
import os
import random
from datetime import datetime
from collections import deque
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OfflineDualBufferAnalyzer:
    """Dual buffer video analyzer that works without external APIs"""
    
    def __init__(self):
        # Dual buffer configuration
        self.short_buffer_duration = 3   # seconds for analysis
        self.long_buffer_duration = 15   # seconds for video evidence
        self.buffer_fps = 25             # target FPS
        self.analysis_interval = 3       # analyze every 3 seconds
        
        # Calculate buffer sizes
        max_frames = self.long_buffer_duration * self.buffer_fps
        
        # Continuous frame buffer - ALL frames go here FIRST
        self.frame_buffer = deque(maxlen=max_frames)
        
        # Statistics
        self.frame_count = 0
        self.analysis_count = 0
        self.incident_count = 0
        self.last_analysis_time = 0
        self.running = False
        
        logger.info("🎬 Offline Dual Buffer Analyzer Initialized")
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
                'buffer_size': len(self.frame_buffer)
            }
            
            # Add to continuous buffer - this happens for EVERY frame
            self.frame_buffer.append(frame_info)
            
            # Log buffer status periodically
            if self.frame_count % 100 == 0:
                logger.info(f"📹 Buffer: {len(self.frame_buffer)} frames, "
                          f"latest: frame {self.frame_count}")
            
        except Exception as e:
            logger.error(f"Error adding frame to buffer: {e}")
    
    def mock_analyze_frames(self):
        """Mock analysis that simulates AI processing"""
        self.analysis_count += 1
        
        if len(self.frame_buffer) == 0:
            logger.warning("🔍 No frames available for analysis")
            return False
        
        # Get recent frames for analysis (short buffer)
        analysis_frames_count = min(
            self.short_buffer_duration * self.buffer_fps,
            len(self.frame_buffer)
        )
        
        recent_frames = list(self.frame_buffer)[-analysis_frames_count:]
        
        logger.info(f"🔍 Analysis #{self.analysis_count}: Processing {len(recent_frames)} recent frames")
        
        # Simulate incident detection (80% chance for demo)
        incident_detected = random.random() < 0.8
        
        if incident_detected:
            self.incident_count += 1
            logger.warning(f"🚨 MOCK SECURITY INCIDENT #{self.incident_count} DETECTED!")
            self.create_incident_video()
            return True
        else:
            logger.info("✅ No security incident detected")
            return False
    
    def create_incident_video(self):
        """Create video from ALL buffered frames (not just analyzed ones)"""
        try:
            # Get ALL frames from continuous buffer for smooth video
            all_frames = list(self.frame_buffer)
            
            if len(all_frames) < 10:
                logger.warning("⚠️ Insufficient frames for video creation")
                return None
            
            logger.info(f"🎬 Creating incident video from {len(all_frames)} continuous frames")
            logger.info(f"📊 Video duration: ~{len(all_frames) / self.buffer_fps:.1f} seconds")
            
            # Create video filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            video_filename = f"offline_incident_{timestamp}.mp4"
            
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
            for i, frame_info in enumerate(all_frames):
                try:
                    # Decode frame
                    frame_data = base64.b64decode(frame_info['frame_data'])
                    frame = cv2.imdecode(
                        np.frombuffer(frame_data, dtype=np.uint8), 
                        cv2.IMREAD_COLOR
                    )
                    
                    # Add overlay showing this is continuous footage
                    cv2.putText(
                        frame, 
                        f"CONTINUOUS BUFFER - Frame: {frame_info['frame_count']}", 
                        (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.7, 
                        (0, 255, 0), 
                        2
                    )
                    
                    cv2.putText(
                        frame, 
                        f"Timestamp: {frame_info['timestamp']}", 
                        (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.5, 
                        (0, 255, 0), 
                        1
                    )
                    
                    # Highlight incident detection frame
                    if i == len(all_frames) - 1:  # Last frame (when incident was detected)
                        cv2.putText(
                            frame, 
                            "🚨 INCIDENT DETECTED HERE", 
                            (10, 100), 
                            cv2.FONT_HERSHEY_SIMPLEX, 
                            0.8, 
                            (0, 0, 255), 
                            2
                        )
                    
                    video_writer.write(frame)
                    frames_written += 1
                    
                except Exception as e:
                    logger.error(f"Error writing frame {frame_info['frame_count']}: {e}")
            
            video_writer.release()
            
            # Get file size
            file_size = os.path.getsize(video_filename) / (1024 * 1024)  # MB
            
            logger.info(f"✅ Incident video created successfully!")
            logger.info(f"📁 Filename: {video_filename}")
            logger.info(f"🎬 Frames written: {frames_written}")
            logger.info(f"📊 File size: {file_size:.1f} MB")
            logger.info(f"⏱️ Duration: ~{frames_written / self.buffer_fps:.1f} seconds")
            logger.info(f"🎯 Video shows CONTINUOUS footage leading up to incident!")
            
            return video_filename
            
        except Exception as e:
            logger.error(f"Error creating incident video: {e}")
            return None
    
    def process_video_stream(self, video_path):
        """Process video with dual buffer system"""
        logger.info(f"🚀 Starting offline dual-buffer analysis: {video_path}")
        
        # Open video capture
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logger.error(f"❌ Failed to open video: {video_path}")
            return False
        
        logger.info("✅ Video opened successfully")
        logger.info("📹 Buffering ALL frames continuously...")
        logger.info("🔍 Analyzing frames periodically...")
        
        self.running = True
        
        try:
            while self.running:
                ret, frame = cap.read()
                
                if not ret:
                    # Loop video for continuous demo
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                
                self.frame_count += 1
                current_time = time.time()
                
                # CRITICAL: Add EVERY frame to buffer FIRST
                self.add_frame_to_buffer(frame.copy())
                
                # Analyze frames periodically (not every frame)
                if current_time - self.last_analysis_time >= self.analysis_interval:
                    self.last_analysis_time = current_time
                    
                    # Analyze recent frames in separate thread
                    threading.Thread(
                        target=self.mock_analyze_frames,
                        daemon=True
                    ).start()
                
                # Maintain target FPS
                time.sleep(1.0 / self.buffer_fps)
        
        except KeyboardInterrupt:
            logger.info("Analysis stopped by user")
        finally:
            cap.release()
            self.running = False
            logger.info("Video capture released")
    
    def stop(self):
        """Stop video analysis"""
        self.running = False
    
    def print_summary(self):
        """Print analysis summary"""
        logger.info("\n" + "="*60)
        logger.info("📊 OFFLINE DUAL BUFFER ANALYSIS SUMMARY")
        logger.info("="*60)
        logger.info(f"📹 Total frames processed: {self.frame_count}")
        logger.info(f"🔍 Total analyses performed: {self.analysis_count}")
        logger.info(f"🚨 Security incidents detected: {self.incident_count}")
        logger.info(f"📦 Final buffer size: {len(self.frame_buffer)} frames")
        logger.info(f"⏱️ Buffer duration: ~{len(self.frame_buffer) / self.buffer_fps:.1f} seconds")
        logger.info(f"🎯 Key insight: ALL frames buffered for smooth video!")
        logger.info("="*60)

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Offline Dual Buffer Video Analysis')
    parser.add_argument('--video', type=str, required=True,
                       help='Path to video file')
    parser.add_argument('--duration', type=int, default=30,
                       help='Analysis duration in seconds (default: 30)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video):
        logger.error(f"❌ Video file not found: {args.video}")
        return 1
    
    # Create analyzer
    analyzer = OfflineDualBufferAnalyzer()
    
    try:
        # Start analysis in thread
        analysis_thread = threading.Thread(
            target=analyzer.process_video_stream,
            args=(args.video,),
            daemon=True
        )
        
        analysis_thread.start()
        
        # Let it run for specified duration
        time.sleep(args.duration)
        
        # Stop analysis
        analyzer.stop()
        time.sleep(2)  # Allow cleanup
        
        # Print summary
        analyzer.print_summary()
        
        logger.info("\n🎉 Offline dual buffer test completed!")
        logger.info("💡 This demonstrates the core concept:")
        logger.info("   ✅ Buffer EVERY frame continuously")
        logger.info("   ✅ Analyze frames periodically") 
        logger.info("   ✅ Create smooth videos from ALL buffered frames")
        logger.info("   ✅ No dependency on external APIs")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Test stopped by user")
        analyzer.stop()
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())