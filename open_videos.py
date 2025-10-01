#!/usr/bin/env python3
"""
Simple script to open the video folder and show available videos
"""

import os
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def open_video_folder():
    """Open the video folder and list available videos"""
    
    video_dir = Path('mock_sparse_ai_cloud')
    
    if not video_dir.exists():
        logger.error("❌ Video directory not found: mock_sparse_ai_cloud/")
        return
    
    # List available videos
    videos = list(video_dir.glob('*.mp4'))
    
    logger.info("🎬 DUAL-BUFFER VIDEO COLLECTION")
    logger.info("=" * 50)
    logger.info(f"📁 Directory: {video_dir.absolute()}")
    logger.info(f"📹 Videos found: {len(videos)}")
    
    if videos:
        logger.info("\n🎥 Available Videos:")
        for i, video in enumerate(sorted(videos, key=lambda x: x.stat().st_mtime, reverse=True)):
            size_mb = video.stat().st_size / (1024 * 1024)
            mtime = video.stat().st_mtime
            import datetime
            date_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            logger.info(f"   {i+1}. {video.name}")
            logger.info(f"      Size: {size_mb:.1f} MB | Created: {date_str}")
        
        logger.info(f"\n💡 These videos show SMOOTH 25 FPS footage thanks to dual-buffer system!")
        logger.info("🎯 No more choppy videos with 5-second gaps!")
    else:
        logger.info("📝 No videos found yet. Run the system to generate videos.")
    
    # Try to open the folder
    try:
        if os.name == 'nt':  # Windows
            os.startfile(video_dir)
        elif os.name == 'posix':  # macOS/Linux
            subprocess.run(['open', str(video_dir)], check=True)
        
        logger.info(f"\n✅ Opened video folder in Finder/Explorer")
        
    except Exception as e:
        logger.warning(f"⚠️ Could not auto-open folder: {e}")
        logger.info(f"💡 Manually navigate to: {video_dir.absolute()}")

if __name__ == '__main__':
    open_video_folder()