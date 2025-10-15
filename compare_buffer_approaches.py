#!/usr/bin/env python3
"""
Comparison script showing the difference between:
1. Old approach: Only analyzed frames → choppy video
2. New approach: All frames buffered → smooth video
"""

import time
import logging
from collections import deque

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class OldChoppyApproach:
    """Simulates the old system that only saved analyzed frames"""
    
    def __init__(self):
        self.analyzed_frames = []
        self.analysis_interval = 5  # analyze every 5 seconds
        self.frame_count = 0
        
    def process_frames(self, duration_seconds=15):
        """Process frames the old way - only save analyzed frames"""
        logger.info("🔴 OLD APPROACH: Only saving analyzed frames")
        
        start_time = time.time()
        last_analysis = 0
        
        while time.time() - start_time < duration_seconds:
            self.frame_count += 1
            current_time = time.time() - start_time
            
            # Only save frames when analysis happens
            if current_time - last_analysis >= self.analysis_interval:
                last_analysis = current_time
                
                # Simulate analysis and save this frame
                self.analyzed_frames.append({
                    'frame_count': self.frame_count,
                    'timestamp': current_time,
                    'type': 'analyzed'
                })
                
                logger.info(f"📊 Analyzed and saved frame {self.frame_count} at {current_time:.1f}s")
            
            # Simulate 25 FPS
            time.sleep(0.04)
        
        logger.info(f"🔴 OLD RESULT: {len(self.analyzed_frames)} frames saved for video")
        logger.info(f"   Video would be {len(self.analyzed_frames) / 25:.1f} seconds long")
        logger.info(f"   Effective FPS: {len(self.analyzed_frames) / duration_seconds:.1f}")
        return self.analyzed_frames

class NewSmoothApproach:
    """Simulates the new dual-buffer system"""
    
    def __init__(self):
        self.continuous_buffer = deque(maxlen=375)  # 15 seconds at 25 FPS
        self.analysis_interval = 3  # analyze every 3 seconds
        self.frame_count = 0
        self.analysis_count = 0
        
    def process_frames(self, duration_seconds=15):
        """Process frames the new way - buffer all frames continuously"""
        logger.info("🟢 NEW APPROACH: Buffering ALL frames continuously")
        
        start_time = time.time()
        last_analysis = 0
        
        while time.time() - start_time < duration_seconds:
            self.frame_count += 1
            current_time = time.time() - start_time
            
            # ALWAYS add frame to buffer (this is the key difference)
            self.continuous_buffer.append({
                'frame_count': self.frame_count,
                'timestamp': current_time,
                'type': 'continuous'
            })
            
            # Analyze periodically (but don't block buffering)
            if current_time - last_analysis >= self.analysis_interval:
                last_analysis = current_time
                self.analysis_count += 1
                
                logger.info(f"🔍 Analysis #{self.analysis_count} at {current_time:.1f}s "
                          f"(buffer has {len(self.continuous_buffer)} frames)")
            
            # Simulate 25 FPS
            time.sleep(0.04)
        
        logger.info(f"🟢 NEW RESULT: {len(self.continuous_buffer)} frames saved for video")
        logger.info(f"   Video would be {len(self.continuous_buffer) / 25:.1f} seconds long")
        logger.info(f"   Effective FPS: {len(self.continuous_buffer) / duration_seconds:.1f}")
        return list(self.continuous_buffer)

def compare_approaches():
    """Compare both approaches side by side"""
    logger.info("=" * 60)
    logger.info("🎬 COMPARING VIDEO BUFFER APPROACHES")
    logger.info("=" * 60)
    
    duration = 15  # seconds
    
    # Test old approach
    logger.info("\n" + "=" * 30)
    old_system = OldChoppyApproach()
    old_frames = old_system.process_frames(duration)
    
    # Test new approach  
    logger.info("\n" + "=" * 30)
    new_system = NewSmoothApproach()
    new_frames = new_system.process_frames(duration)
    
    # Compare results
    logger.info("\n" + "=" * 60)
    logger.info("📊 COMPARISON RESULTS")
    logger.info("=" * 60)
    
    logger.info(f"🔴 Old Approach:")
    logger.info(f"   Frames for video: {len(old_frames)}")
    logger.info(f"   Video duration: {len(old_frames) / 25:.1f} seconds")
    logger.info(f"   Playback quality: CHOPPY (frames every {old_system.analysis_interval}s)")
    
    logger.info(f"\n🟢 New Approach:")
    logger.info(f"   Frames for video: {len(new_frames)}")
    logger.info(f"   Video duration: {len(new_frames) / 25:.1f} seconds")
    logger.info(f"   Playback quality: SMOOTH (continuous frames)")
    
    improvement = len(new_frames) / len(old_frames) if len(old_frames) > 0 else float('inf')
    logger.info(f"\n🎯 IMPROVEMENT:")
    logger.info(f"   {improvement:.1f}x more frames for smoother video")
    logger.info(f"   From {len(old_frames)} choppy frames to {len(new_frames)} smooth frames")
    
    # Show frame timeline
    logger.info(f"\n📈 FRAME TIMELINE COMPARISON:")
    logger.info(f"🔴 Old: Frames at {[f['timestamp'] for f in old_frames[:5]][:5]}... (gaps of {old_system.analysis_interval}s)")
    logger.info(f"🟢 New: Continuous frames every 0.04s (25 FPS)")
    
    logger.info("\n💡 KEY INSIGHT:")
    logger.info("   The new approach buffers BEFORE analysis, not after!")
    logger.info("   This ensures smooth video regardless of analysis timing.")

if __name__ == '__main__':
    compare_approaches()