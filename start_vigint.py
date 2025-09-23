#!/usr/bin/env python3
"""Main entry point for Vigint application"""

import os
import sys
import logging
import argparse
import signal
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import config
from rtsp_server import rtsp_server
from vigint.models import db
from flask import Flask


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.get('Logging', 'level', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Reduce werkzeug (Flask) logging verbosity
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.WARNING)


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configure Flask app
    app.config['SECRET_KEY'] = config.secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = config.database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    return app


def initialize_database(app):
    """Initialize the database with tables"""
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    return True


def start_rtsp_server():
    """Start the RTSP server"""
    logger.info("Starting RTSP server...")
    if rtsp_server.start():
        logger.info("RTSP server started successfully")
        return True
    else:
        logger.error("Failed to start RTSP server")
        return False


def stop_rtsp_server():
    """Stop the RTSP server"""
    logger.info("Stopping RTSP server...")
    rtsp_server.stop()


def setup_video_streaming(video_path):
    """Setup video streaming for the provided video file"""
    import subprocess
    import threading
    
    logger.info(f"Setting up video streaming for: {video_path}")
    
    # Verify video file exists
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return False
    
    # Get video file info
    file_size = os.path.getsize(video_path)
    logger.info(f"Video file: {os.path.basename(video_path)} ({file_size} bytes)")
    
    # Create stream name from filename
    stream_name = os.path.splitext(os.path.basename(video_path))[0]
    rtsp_url = f"rtsp://localhost:8554/{stream_name}"
    
    logger.info(f"Stream will be available at: rtsp://localhost:8554/{stream_name}")
    
    def start_ffmpeg_stream():
        """Start FFmpeg streaming in a separate thread"""
        try:
            # Wait a moment for RTSP server to be fully ready
            time.sleep(3)
            
            # Test if RTSP server is accessible
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 8554))
            sock.close()
            if result != 0:
                logger.error("RTSP server is not accessible on port 8554")
                return False
            
            logger.info(f"Starting FFmpeg stream to {rtsp_url}")
            
            # Try to start FFmpeg streaming
            cmd = [
                'ffmpeg', '-re', '-stream_loop', '-1', '-i', video_path,
                '-c', 'copy', '-f', 'rtsp', rtsp_url
            ]
            
            logger.info(f"FFmpeg command: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Monitor the process
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                logger.info("FFmpeg streaming completed successfully")
            else:
                logger.warning(f"FFmpeg streaming ended with code {process.returncode}")
                if stderr:
                    logger.error(f"FFmpeg stderr: {stderr}")
                else:
                    logger.error("No stderr output from FFmpeg")
                if stdout:
                    logger.info(f"FFmpeg stdout: {stdout}")
                else:
                    logger.info("No stdout output from FFmpeg")
                    
        except FileNotFoundError:
            logger.warning("FFmpeg not found or not working. Stream setup completed without auto-streaming.")
            logger.info("You can manually stream using:")
            logger.info(f"  VLC: Stream to {rtsp_url}")
            logger.info(f"  FFmpeg: ffmpeg -re -i {video_path} -c copy -f rtsp {rtsp_url}")
        except Exception as e:
            logger.error(f"Error starting FFmpeg stream: {e}")
            # Try a simpler approach
            logger.info("Trying simpler FFmpeg command...")
            try:
                simple_cmd = [
                    'ffmpeg', '-re', '-i', video_path,
                    '-c', 'copy', '-f', 'rtsp', rtsp_url
                ]
                logger.info(f"Simple FFmpeg command: {' '.join(simple_cmd)}")
                simple_process = subprocess.Popen(
                    simple_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                simple_stdout, simple_stderr = simple_process.communicate()
                if simple_process.returncode != 0:
                    logger.error(f"Simple FFmpeg also failed with code {simple_process.returncode}")
                    if simple_stderr:
                        logger.error(f"Simple FFmpeg stderr: {simple_stderr}")
            except Exception as simple_e:
                logger.error(f"Simple FFmpeg also failed: {simple_e}")
    
    # Start FFmpeg in background thread
    stream_thread = threading.Thread(target=start_ffmpeg_stream, daemon=True)
    stream_thread.start()
    
    logger.info("Video streaming setup completed")
    return True


def start_video_analysis(video_path):
    """Start secure video analysis using API proxy"""
    import threading
    
    def run_analysis():
        try:
            # Wait for streaming to be established
            time.sleep(12)  # Increased wait time for stream establishment
            
            # Create stream name from filename
            stream_name = os.path.splitext(os.path.basename(video_path))[0]
            rtsp_url = f"rtsp://localhost:8554/{stream_name}"
            
            logger.info(f"Starting secure video analysis for stream: {rtsp_url}")
            
            # Import and run the secure video analyzer
            from vigint.app import SecureVideoAnalyzer
            
            # Create and start secure analyzer
            analyzer = SecureVideoAnalyzer(
                api_base_url='http://localhost:5002',  # Use correct port (API proxy runs on 5002)
                api_key=os.getenv('VIGINT_API_KEY')
            )
            analyzer.analysis_interval = 30  # Reduce frequency to avoid quota issues
            
            logger.info("🎯 Secure video analysis started - monitoring for security events...")
            logger.info("🔒 All AI processing and credentials handled server-side via API proxy")
            
            # Start processing the video stream
            analyzer.process_video_stream(rtsp_url)
            
        except Exception as e:
            logger.error(f"Error starting video analysis: {e}")
            logger.info("Video analysis failed to start, but streaming continues...")
    
    # Start analysis in background thread
    analysis_thread = threading.Thread(target=run_analysis, daemon=True)
    analysis_thread.start()
    
    logger.info("Secure video analysis thread started")


def check_api_proxy_running():
    """Check if API proxy is already running on port 5002"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5002))
        sock.close()
        return result == 0
    except Exception:
        return False


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    stop_rtsp_server()
    sys.exit(0)


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description='Vigint Application')
    parser.add_argument('--mode', choices=['api', 'rtsp', 'full'], default='full',
                       help='Run mode: api only, rtsp only, or full stack')
    parser.add_argument('--init-db', action='store_true',
                       help='Initialize database and exit')
    parser.add_argument('--no-rtsp', action='store_true',
                       help='Skip RTSP server startup')
    parser.add_argument('--video-input', type=str,
                       help='Video file to stream (e.g., /path/to/video.mp4)')
    
    args = parser.parse_args()
    logger.info(f"Starting Vigint application with args: {args}")
    
    # Create Flask app
    app = create_app()
    
    # Initialize database if requested
    if args.init_db:
        logger.info("Initializing database...")
        if initialize_database(app):
            logger.info("Database initialization completed")
            return 0
        else:
            logger.error("Database initialization failed")
            return 1
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize database
        if not initialize_database(app):
            return 1
        
        # Check if API proxy is already running
        api_proxy_running = check_api_proxy_running()
        if api_proxy_running:
            logger.info("✅ API proxy already running on port 5002")
        
        # Import API proxy early but don't start it yet
        proxy_app = None
        if args.mode in ['api', 'full'] and not api_proxy_running:
            logger.info("Importing API proxy...")
            from api_proxy import app as proxy_app
        elif args.mode in ['api', 'full'] and api_proxy_running:
            logger.info("Skipping API proxy startup - already running")
        
        # Start RTSP server if needed
        if args.mode in ['rtsp', 'full'] and not args.no_rtsp:
            logger.info(f"Mode: {args.mode}, no_rtsp: {args.no_rtsp}")
            logger.info("Attempting to start RTSP server...")
            if not start_rtsp_server():
                logger.error("RTSP server startup failed, exiting")
                return 1
            
            # If video input is provided, configure streaming
            if args.video_input:
                logger.info(f"Video input provided: {args.video_input}")
                setup_video_streaming(args.video_input)
                
                # Start video analysis after streaming is set up
                logger.info("Starting video analysis with Gemini AI...")
                start_video_analysis(args.video_input)
            else:
                logger.info("No video input provided")
        
        # Start API server if needed (after RTSP server is running)
        if args.mode in ['api', 'full'] and proxy_app and not api_proxy_running:
            logger.info("Starting API server...")
            
            # Run the application
            proxy_app.run(
                host=config.host,
                port=config.port,
                debug=config.debug,
                use_reloader=False  # Disable reloader to avoid issues with RTSP server
            )
        elif args.mode in ['api', 'full'] and api_proxy_running:
            logger.info("API proxy already running, skipping startup")
        else:
            # If only RTSP mode, just keep the process alive
            logger.info("RTSP-only mode, keeping process alive...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
    
    except Exception as e:
        logger.error(f"Application error: {e}")
        return 1
    
    finally:
        # Cleanup
        stop_rtsp_server()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())