#!/usr/bin/env python3
"""Simple video analysis runner that bypasses RTSP complexity"""

import sys
import signal
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from vigint.app import SecureVideoAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

def main():
    """Main entry point for video analysis"""
    if len(sys.argv) != 2:
        print("Usage: python3 run_video_analysis.py <video_file>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("🎯 Starting Vigint Video Analysis")
        logger.info(f"📹 Video file: {video_path}")
        logger.info("🔒 Using API proxy for secure AI processing")
        
        # Create and configure analyzer
        analyzer = SecureVideoAnalyzer()
        
        # Start video analysis (this will loop the video automatically)
        logger.info("🚀 Starting continuous video analysis with looping...")
        analyzer.process_video_stream(video_path)
        
    except KeyboardInterrupt:
        logger.info("Analysis stopped by user")
    except Exception as e:
        logger.error(f"Error during video analysis: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()