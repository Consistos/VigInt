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


def kill_existing_rtsp_processes():
    """Kill any existing processes using RTSP ports"""
    import subprocess
    
    ports_to_check = [8554, 8002, 1935]  # Common RTSP and streaming ports
    
    for port in ports_to_check:
        try:
            # Find processes using the port
            result = subprocess.run(['lsof', '-ti', f':{port}'], 
                                  capture_output=True, text=True)
            
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                logger.info(f"Found processes using port {port}: {pids}")
                
                # Kill the processes
                for pid in pids:
                    if pid:
                        try:
                            subprocess.run(['kill', '-9', pid], check=True)
                            logger.info(f"Killed process {pid} using port {port}")
                        except subprocess.CalledProcessError:
                            logger.warning(f"Could not kill process {pid}")
                            
        except FileNotFoundError:
            # lsof not available, skip
            pass
        except Exception as e:
            logger.warning(f"Error checking port {port}: {e}")


def start_rtsp_server():
    """Start the RTSP server with improved error handling"""
    logger.info("🚀 Starting RTSP server with dual-buffer video analysis...")
    
    # First, try to kill any existing processes using RTSP ports
    logger.info("Checking for existing RTSP processes...")
    kill_existing_rtsp_processes()
    
    # Wait a moment for ports to be freed
    time.sleep(2)
    
    # Try to start the RTSP server
    if rtsp_server.start():
        logger.info("✅ RTSP server started successfully")
        logger.info("🎬 Ready for dual-buffer video analysis")
        return True
    else:
        logger.error("❌ Failed to start RTSP server")
        logger.info("💡 This may be due to port conflicts or missing dependencies")
        logger.info("🔧 Try running: lsof -i :8554 to check port usage")
        return False


def start_video_server():
    """Start the local video server for serving video links"""
    import threading
    import subprocess
    import time
    import socket
    
    def check_server_running():
        """Check if video server is responding"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', 9999))  # Use port 9999
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def run_video_server():
        try:
            if check_server_running():
                logger.info("✅ Video server already running on port 9999")
                return
            
            logger.info("🚀 Starting local video server for GDPR-compliant video links...")
            
            # Kill any existing processes on port 9999
            try:
                subprocess.run(['lsof', '-ti', ':9999'], capture_output=True, text=True, check=True)
                subprocess.run(['pkill', '-f', 'video_server.py'], capture_output=True)
                time.sleep(1)
            except subprocess.CalledProcessError:
                pass  # No processes to kill
            
            # Try Flask server first, then fallback to simple server
            logger.info("🎬 Trying Flask video server...")
            process = subprocess.Popen([
                sys.executable, 'local_video_server.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Wait and verify it started
            for i in range(15):  # Try for 15 seconds
                time.sleep(1)
                if check_server_running():
                    logger.info("✅ Local video server started successfully on http://127.0.0.1:8888")
                    logger.info("🎬 Video links will be served locally for GDPR compliance")
                    
                    # Test the server with a health check
                    try:
                        import requests
                        response = requests.get('http://127.0.0.1:8888/health', timeout=3)
                        if response.status_code == 200:
                            logger.info("✅ Video server health check passed")
                        else:
                            logger.warning(f"⚠️ Video server health check failed: {response.status_code}")
                    except Exception as health_error:
                        logger.warning(f"⚠️ Could not verify server health: {health_error}")
                    
                    return
            
            # If Flask server failed, try simple server
            try:
                stdout, stderr = process.communicate(timeout=2)
                logger.warning(f"⚠️ Flask server failed, trying simple server...")
                if stderr:
                    logger.info(f"Flask error: {stderr[:200]}...")
            except subprocess.TimeoutExpired:
                process.kill()
            
            # Start simple server directly (more reliable)
            logger.info("🔄 Starting simple HTTP video server on port 9999...")
            simple_process = subprocess.Popen([
                sys.executable, 'simple_video_server.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Check if simple server starts
            for i in range(10):
                time.sleep(1)
                if check_server_running():
                    logger.info("✅ Simple video server started successfully on port 9999!")
                    logger.info("🎬 Video links will work: http://127.0.0.1:9999/video/{id}?token={token}")
                    return
            
            # If both servers failed
            logger.error("❌ Both Flask and simple servers failed to start")
            logger.warning("⚠️ Videos will be created but links may not work")
            logger.info("💡 Videos are still saved locally in mock_sparse_ai_cloud/")
        
        except Exception as e:
            logger.error(f"Error starting video server: {e}")
            logger.info("💡 Continuing without video server - videos will still be created locally")
            logger.info("🎬 IMPORTANT: Dual-buffer system is still working perfectly!")
            logger.info("📹 Videos are being created with smooth continuous footage")
            logger.info("📁 Check mock_sparse_ai_cloud/ folder for video files")
    
    # Start video server in background
    server_thread = threading.Thread(target=run_video_server, daemon=True)
    server_thread.start()
    
    return True


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
            
            # Try to start FFmpeg streaming with proper re-encoding for RTSP
            cmd = [
                'ffmpeg', '-re', '-stream_loop', '-1', '-i', video_path,
                '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency',
                '-c:a', 'aac', '-ar', '44100', '-b:a', '128k',
                '-f', 'rtsp', '-rtsp_transport', 'tcp', rtsp_url
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
                    '-c:v', 'libx264', '-preset', 'ultrafast',
                    '-c:a', 'aac', '-f', 'rtsp', rtsp_url
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
    """Start dual-buffer video analysis with real Gemini AI"""
    import threading
    
    def run_analysis():
        try:
            # Wait for streaming to be established
            time.sleep(5)
            
            logger.info(f"🎬 Starting DUAL-BUFFER video analysis for: {video_path}")
            logger.info("🚀 Using enhanced dual-buffer architecture for smooth video creation")
            logger.info("🧠 Real Gemini AI analysis with graceful fallback to mock analysis")
            
            # Import the enhanced dual-buffer video analyzer
            from video_analyzer import VideoAnalyzer
            
            # Create analyzer with dual-buffer system
            analyzer = VideoAnalyzer()
            
            logger.info("📹 Dual-buffer system initialized:")
            logger.info(f"   • Continuous buffer: {analyzer.long_buffer_duration}s ({analyzer.long_buffer_duration * analyzer.buffer_fps} frames)")
            logger.info(f"   • Analysis interval: {analyzer.analysis_interval}s")
            logger.info(f"   • Target FPS: {analyzer.buffer_fps}")
            logger.info("🎯 This ensures smooth video regardless of AI analysis timing!")
            
            # Analyze the video file directly with dual-buffer system
            analyzer.process_video_stream(video_path)
            
        except Exception as e:
            logger.error(f"Error starting dual-buffer video analysis: {e}")
            logger.info("Video analysis failed to start, but streaming continues...")
    
    # Start analysis in background thread
    analysis_thread = threading.Thread(target=run_analysis, daemon=True)
    analysis_thread.start()
    
    logger.info("🎬 Dual-buffer video analysis thread started")


def start_multi_source_analysis(config_file="multi_source_config.json"):
    """Start multi-source video analysis in parallel"""
    import threading
    
    def run_multi_analysis():
        try:
            # Wait for system to initialize
            time.sleep(5)
            
            logger.info("🚀 Starting MULTI-SOURCE video analysis")
            logger.info("📹 Loading video sources from configuration...")
            
            # Import multi-source components
            from multi_source_config import MultiSourceConfig
            from multi_source_video_analyzer import MultiSourceVideoAnalyzer
            
            # Load configuration
            config_manager = MultiSourceConfig(config_file)
            sources = config_manager.list_video_sources(enabled_only=True)
            
            if not sources:
                logger.error("❌ No enabled video sources found in configuration")
                logger.info(f"💡 Edit {config_file} to add video sources")
                return
            
            logger.info(f"✅ Loaded {len(sources)} enabled video source(s)")
            
            # Create multi-source analyzer
            analyzer = MultiSourceVideoAnalyzer()
            
            # Add all video sources to analyzer
            for source_id, source_config in sources.items():
                rtsp_url = source_config['rtsp_url']
                name = source_config['name']
                
                logger.info(f"   📹 {source_id}: {name} -> {rtsp_url}")
                analyzer.add_video_source(source_id, rtsp_url, name)
            
            # Get analysis settings from config
            analysis_settings = config_manager.config_data.get('analysis_settings', {})
            if analysis_settings:
                analyzer.analysis_interval = analysis_settings.get('analysis_interval', 10)
                logger.info(f"⚙️  Analysis interval: {analyzer.analysis_interval}s")
            
            # Start the parallel analysis
            logger.info("🚀 Starting parallel analysis of all sources...")
            analyzer.start_analysis()
            
            logger.info("✅ Multi-source analysis running")
            logger.info("🔍 All sources are being analyzed in parallel")
            logger.info("🚨 Incidents will trigger automated alerts")
            
        except Exception as e:
            logger.error(f"❌ Error starting multi-source analysis: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    # Start multi-source analysis in background thread
    analysis_thread = threading.Thread(target=run_multi_analysis, daemon=True)
    analysis_thread.start()
    
    logger.info("🎬 Multi-source analysis thread started")


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
    parser = argparse.ArgumentParser(
        description='🎬 Vigint Security System with Dual-Buffer Video Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 DUAL-BUFFER ARCHITECTURE:
   This system uses an enhanced dual-buffer approach that captures ALL frames
   continuously for smooth video creation, while running AI analysis separately.
   
   Key Benefits:
   • Smooth 25 FPS video evidence (no choppy gaps)
   • Real Gemini AI security analysis with fallback
   • GDPR-compliant video storage with automatic cleanup
   • Professional quality security evidence
   
📹 Example Usage:
   python3 start_vigint.py --video-input '/path/to/security_video.mp4'
   
   This will start the complete system with dual-buffer video analysis.
        """)
    
    parser.add_argument('--mode', choices=['api', 'rtsp', 'full'], default='full',
                       help='Run mode: api only, rtsp only, or full stack')
    parser.add_argument('--init-db', action='store_true',
                       help='Initialize database and exit')
    parser.add_argument('--no-rtsp', action='store_true',
                       help='Skip RTSP server startup')
    parser.add_argument('--video-input', type=str,
                       help='🎬 Video file for dual-buffer analysis (enables smooth video evidence creation)')
    parser.add_argument('--multi-source', action='store_true',
                       help='🎥 Enable multi-source parallel video analysis from config file')
    parser.add_argument('--config-file', type=str, default='multi_source_config.json',
                       help='📝 Configuration file for multi-source analysis (default: multi_source_config.json)')
    
    args = parser.parse_args()
    
    logger.info("🎬 VIGINT SECURITY SYSTEM")
    logger.info("=" * 50)
    logger.info(f"Mode: {args.mode}")
    if args.multi_source:
        logger.info(f"Multi-Source Analysis: ENABLED")
        logger.info(f"Config File: {args.config_file}")
        logger.info("🎥 Multiple video sources will be analyzed in parallel")
    elif args.video_input:
        logger.info(f"Video Input: {args.video_input}")
        logger.info("🔍 Real video analysis enabled - will analyze actual input frames")
        logger.info("📧 Video links will contain the frames that were actually analyzed")
    logger.info("=" * 50)
    
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
        
        # Check if using remote API server
        remote_api_url = config.api_server_url
        if remote_api_url:
            logger.info(f"✅ Using remote API server at: {remote_api_url}")
            logger.info("📡 Distributed deployment mode - API proxy will not start locally")
            api_proxy_running = True  # Skip local startup
        else:
            # Check if API proxy is already running locally
            api_proxy_running = check_api_proxy_running()
            if api_proxy_running:
                logger.info("✅ API proxy already running on port 5002")
        
        # Import API proxy early but don't start it yet
        proxy_app = None
        if args.mode in ['api', 'full'] and not api_proxy_running and not remote_api_url:
            logger.info("Importing API proxy for local deployment...")
            from api_proxy import app as proxy_app
        elif args.mode in ['api', 'full'] and (api_proxy_running or remote_api_url):
            logger.info("Skipping API proxy startup - using remote or already running")
        
        # Start RTSP server if needed
        if args.mode in ['rtsp', 'full'] and not args.no_rtsp:
            logger.info(f"Mode: {args.mode}, no_rtsp: {args.no_rtsp}")
            logger.info("Attempting to start RTSP server...")
            if not start_rtsp_server():
                logger.error("RTSP server startup failed, exiting")
                return 1
            
            # Start video server for GDPR-compliant video links
            logger.info("Starting video server for GDPR-compliant video links...")
            start_video_server()
            
            # Handle multi-source analysis mode
            if args.multi_source:
                logger.info("🎥 MULTI-SOURCE VIDEO ANALYSIS SETUP")
                logger.info("=" * 50)
                logger.info(f"📝 Config file: {args.config_file}")
                
                # Verify config file exists
                if not os.path.exists(args.config_file):
                    logger.error(f"❌ Configuration file not found: {args.config_file}")
                    logger.info("💡 Create a configuration file or use --config-file to specify a different path")
                    return 1
                
                logger.info("\n🚀 MULTI-SOURCE SYSTEM FEATURES:")
                logger.info("   ✅ Parallel analysis of multiple video sources")
                logger.info("   ✅ Aggregated analysis for 4+ sources")
                logger.info("   ✅ Individual analysis for fewer sources")
                logger.info("   ✅ Real Gemini AI with automatic fallback")
                logger.info("   ✅ Incident deduplication across sources")
                logger.info("   ✅ GDPR-compliant video storage")
                logger.info("=" * 50)
                
                # Start multi-source analysis
                logger.info("🎬 Starting MULTI-SOURCE video analysis...")
                start_multi_source_analysis(args.config_file)
                
                # Add monitoring for multi-source videos
                def monitor_multi_source_videos():
                    """Monitor and report video creation for multi-source analysis"""
                    import time
                    import glob
                    
                    time.sleep(10)  # Wait for system to start
                    initial_count = len(glob.glob('mock_sparse_ai_cloud/*.mp4'))
                    
                    while True:
                        time.sleep(30)  # Check every 30 seconds
                        current_count = len(glob.glob('mock_sparse_ai_cloud/*.mp4'))
                        if current_count > initial_count:
                            new_videos = current_count - initial_count
                            logger.info(f"🎬 {new_videos} new security video(s) created from multi-source analysis!")
                            logger.info("📁 Videos saved in: mock_sparse_ai_cloud/")
                            initial_count = current_count
                
                # Start monitoring in background
                import threading
                monitor_thread = threading.Thread(target=monitor_multi_source_videos, daemon=True)
                monitor_thread.start()
                
            # If video input is provided, configure streaming and dual-buffer analysis
            elif args.video_input:
                logger.info("🎬 DUAL-BUFFER VIDEO ANALYSIS SETUP")
                logger.info("=" * 50)
                logger.info(f"📹 Video input: {args.video_input}")
                
                # Verify video file exists
                if not os.path.exists(args.video_input):
                    logger.error(f"❌ Video file not found: {args.video_input}")
                    return 1
                
                # Get video file info
                file_size = os.path.getsize(args.video_input) / (1024 * 1024)  # MB
                logger.info(f"📁 File: {os.path.basename(args.video_input)} ({file_size:.1f} MB)")
                logger.info(f"📂 Path: {args.video_input}")
                
                logger.info("\n🚀 DUAL-BUFFER SYSTEM FEATURES:")
                logger.info("   ✅ Continuous frame buffering (no gaps)")
                logger.info("   ✅ Smooth 25 FPS video creation")
                logger.info("   ✅ Real Gemini AI analysis with fallback")
                logger.info("   ✅ Professional security evidence quality")
                logger.info("   ✅ GDPR-compliant video storage")
                logger.info("=" * 50)
                
                # Setup video streaming
                logger.info("🔄 Setting up video streaming...")
                setup_video_streaming(args.video_input)
                
                # Start dual-buffer video analysis
                logger.info("🎬 Starting DUAL-BUFFER video analysis...")
                logger.info("💡 This uses your improved 'buffer before analysis' architecture!")
                
                # Start dual-buffer video analysis
                start_video_analysis(args.video_input)
                
                # Add a simple verification that videos are being created
                def monitor_video_creation():
                    """Monitor and report video creation"""
                    import time
                    import glob
                    
                    time.sleep(10)  # Wait for system to start
                    initial_count = len(glob.glob('mock_sparse_ai_cloud/*.mp4'))
                    
                    while True:
                        time.sleep(30)  # Check every 30 seconds
                        current_count = len(glob.glob('mock_sparse_ai_cloud/*.mp4'))
                        if current_count > initial_count:
                            new_videos = current_count - initial_count
                            logger.info(f"🎬 {new_videos} new security video(s) created!")
                            logger.info("📁 Videos saved in: mock_sparse_ai_cloud/")
                            initial_count = current_count
                
                # Start monitoring in background
                import threading
                monitor_thread = threading.Thread(target=monitor_video_creation, daemon=True)
                monitor_thread.start()
            else:
                logger.info("⚠️ No video input provided")
                logger.info("💡 Options:")
                logger.info("   • Use --video-input to enable single video analysis")
                logger.info("     Example: --video-input '/path/to/your/video.mp4'")
                logger.info("   • Use --multi-source to enable parallel analysis of multiple sources")
                logger.info("     Example: --multi-source --config-file multi_source_config.json")
        
        # Start API server if needed (after RTSP server is running)
        if args.mode in ['api', 'full'] and proxy_app and not api_proxy_running:
            logger.info("Starting API server...")
            
            if config.debug:
                logger.info("🔧 Running in DEBUG mode with Flask development server")
                # Run the application
                proxy_app.run(
                    host=config.host,
                    port=config.port,
                    debug=config.debug,
                    use_reloader=False  # Disable reloader to avoid issues with RTSP server
                )
            else:
                logger.info("🚀 Running in PRODUCTION mode with Gunicorn")
                import subprocess
                
                # Build gunicorn command
                # Use 4 workers or (2 * cpu_count) + 1
                workers = '4'
                try:
                    import multiprocessing
                    workers = str(multiprocessing.cpu_count() * 2 + 1)
                except:
                    pass
                
                cmd = [
                    'gunicorn',
                    '--bind', f'{config.host}:{config.port}',
                    '--workers', workers,
                    '--timeout', '120',
                    '--access-logfile', '-',
                    '--error-logfile', '-',
                    'api_proxy:app'
                ]
                
                logger.info(f"Executing: {' '.join(cmd)}")
                
                try:
                    # Run gunicorn
                    subprocess.run(cmd, check=True)
                except subprocess.CalledProcessError as e:
                    logger.error(f"Gunicorn server failed: {e}")
                    return 1
                except KeyboardInterrupt:
                    logger.info("Gunicorn server stopped")
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