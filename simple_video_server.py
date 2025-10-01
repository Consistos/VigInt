#!/usr/bin/env python3
"""
Simple HTTP server for serving video files
Fallback option when Flask server has issues
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import mimetypes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
VIDEO_STORAGE_DIR = Path('mock_sparse_ai_cloud')
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 9999  # Use port 9999 to avoid all conflicts

class VideoHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for video files"""
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"{self.address_string()} - {format % args}")
    
    def do_GET(self):
        """Handle GET requests"""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            query_params = parse_qs(parsed_path.query)
            
            if path == '/health':
                self.send_health_response()
            elif path.startswith('/video/'):
                self.serve_video(path, query_params)
            elif path == '/videos':
                self.list_videos()
            else:
                self.send_error(404, "Not Found")
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            self.send_error(500, "Internal Server Error")
    
    def send_health_response(self):
        """Send health check response"""
        response = {
            'status': 'healthy',
            'service': 'simple_video_server',
            'storage_dir': str(VIDEO_STORAGE_DIR.absolute())
        }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def list_videos(self):
        """List available videos"""
        videos = []
        
        try:
            for metadata_file in VIDEO_STORAGE_DIR.glob("*.json"):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                video_path = Path(metadata['cloud_path'])
                if video_path.exists():
                    videos.append({
                        'video_id': metadata['video_id'],
                        'filename': video_path.name,
                        'size_mb': round(video_path.stat().st_size / (1024 * 1024), 1),
                        'upload_time': metadata['upload_timestamp']
                    })
        except Exception as e:
            logger.error(f"Error listing videos: {e}")
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(videos).encode())
    
    def serve_video(self, path, query_params):
        """Serve video file"""
        try:
            # Extract video ID from path
            video_id = path.split('/')[-1]
            token = query_params.get('token', [''])[0]
            
            if not token:
                self.send_error(401, "Access token required")
                return
            
            # Find video metadata
            video_found = False
            for metadata_file in VIDEO_STORAGE_DIR.glob("*.json"):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    if metadata['video_id'] == video_id:
                        # Verify token
                        expected_token = hashlib.sha256(
                            f"{video_id}:{metadata['expiration_time']}:mock-key".encode()
                        ).hexdigest()[:32]
                        
                        if token != expected_token:
                            self.send_error(403, "Invalid token")
                            return
                        
                        # Check expiration
                        expiration_time = datetime.fromisoformat(metadata['expiration_time'])
                        if datetime.now() > expiration_time:
                            self.send_error(403, "Video link has expired")
                            return
                        
                        # Serve video file
                        video_path = Path(metadata['cloud_path'])
                        if video_path.exists():
                            self.serve_file(video_path)
                            video_found = True
                            break
                        else:
                            self.send_error(404, "Video file not found")
                            return
                            
                except Exception as e:
                    logger.error(f"Error processing metadata file {metadata_file}: {e}")
                    continue
            
            if not video_found:
                self.send_error(404, "Video not found")
                
        except Exception as e:
            logger.error(f"Error serving video: {e}")
            self.send_error(500, "Internal server error")
    
    def serve_file(self, file_path):
        """Serve a file with proper headers"""
        try:
            file_size = file_path.stat().st_size
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # Send headers
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(file_size))
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()
            
            # Send file content
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
            
            logger.info(f"Served video: {file_path.name} ({file_size} bytes)")
            
        except Exception as e:
            logger.error(f"Error serving file {file_path}: {e}")
            self.send_error(500, "Error serving file")

def start_simple_server():
    """Start the simple HTTP server"""
    # Ensure storage directory exists
    VIDEO_STORAGE_DIR.mkdir(exist_ok=True)
    
    logger.info(f"🚀 Starting simple video server...")
    logger.info(f"📁 Storage directory: {VIDEO_STORAGE_DIR.absolute()}")
    logger.info(f"🌐 Server URL: http://{SERVER_HOST}:{SERVER_PORT}")
    
    # Kill existing processes
    import subprocess
    try:
        result = subprocess.run(['lsof', '-ti', f':{SERVER_PORT}'], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    subprocess.run(['kill', '-9', pid], capture_output=True)
                    logger.info(f"Killed existing process {pid}")
    except Exception:
        pass
    
    # Start server
    try:
        server = HTTPServer((SERVER_HOST, SERVER_PORT), VideoHandler)
        logger.info(f"✅ Simple video server started on http://{SERVER_HOST}:{SERVER_PORT}")
        logger.info("🎬 Ready to serve video links!")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Failed to start simple server: {e}")
        raise

if __name__ == '__main__':
    start_simple_server()