#!/usr/bin/env python3
"""
Local Video Server for GDPR-compliant video hosting
Serves videos locally with secure token-based access
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, request, send_file, jsonify, abort
from urllib.parse import unquote

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
VIDEO_STORAGE_DIR = Path('mock_sparse_ai_cloud')
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8888
BASE_URL = f'http://{SERVER_HOST}:{SERVER_PORT}'


def verify_token(video_id, token):
    """Verify if a token is valid for a video"""
    try:
        # Find video metadata
        for metadata_file in VIDEO_STORAGE_DIR.glob("*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                if metadata['video_id'] == video_id:
                    # Check if video has expired
                    expiration_time = datetime.fromisoformat(metadata['expiration_time'])
                    if datetime.now() > expiration_time:
                        return False, "Video link has expired"
                    
                    # Verify token (consistent with mock service)
                    expected_token = hashlib.sha256(
                        f"{video_id}:{metadata['expiration_time']}:mock-key".encode()
                    ).hexdigest()[:32]
                    
                    if token == expected_token:
                        return True, metadata
                    else:
                        return False, "Invalid token"
            
            except Exception as e:
                logger.warning(f"Error reading metadata {metadata_file}: {e}")
                continue
        
        return False, "Video not found"
    
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return False, "Verification error"


@app.route('/video/<video_id>')
def serve_video(video_id):
    """Serve video with token verification"""
    try:
        # Get token from query parameters
        token = request.args.get('token')
        if not token:
            abort(401, description="Access token required")
        
        # Verify token
        is_valid, result = verify_token(video_id, token)
        if not is_valid:
            abort(403, description=f"Access denied: {result}")
        
        # Get video metadata
        metadata = result
        video_path = Path(metadata['cloud_path'])
        
        if not video_path.exists():
            abort(404, description="Video file not found")
        
        # Log access
        logger.info(f"Serving video: {video_id} ({video_path.name})")
        
        # Serve video file
        return send_file(
            video_path,
            as_attachment=False,
            download_name=f"incident_{metadata.get('risk_level', 'UNKNOWN')}_{video_id[:8]}.mp4",
            mimetype='video/mp4'
        )
    
    except Exception as e:
        logger.error(f"Error serving video {video_id}: {e}")
        abort(500, description="Internal server error")


@app.route('/video/<video_id>/info')
def video_info(video_id):
    """Get video information"""
    try:
        token = request.args.get('token')
        if not token:
            abort(401, description="Access token required")
        
        is_valid, result = verify_token(video_id, token)
        if not is_valid:
            abort(403, description=f"Access denied: {result}")
        
        metadata = result
        video_path = Path(metadata['cloud_path'])
        
        info = {
            'video_id': video_id,
            'filename': video_path.name,
            'size_mb': round(video_path.stat().st_size / (1024 * 1024), 1) if video_path.exists() else 0,
            'upload_time': metadata['upload_timestamp'],
            'expiration_time': metadata['expiration_time'],
            'incident_type': metadata.get('incident_type', 'unknown'),
            'risk_level': metadata.get('risk_level', 'unknown'),
            'gdpr_compliant': metadata.get('gdpr_compliant', True),
            'available': video_path.exists()
        }
        
        return jsonify(info)
    
    except Exception as e:
        logger.error(f"Error getting video info {video_id}: {e}")
        abort(500, description="Internal server error")


@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'local_video_server',
        'storage_dir': str(VIDEO_STORAGE_DIR.absolute()),
        'base_url': BASE_URL
    })


@app.route('/videos')
def list_videos():
    """List all available videos (for admin)"""
    try:
        videos = []
        
        for metadata_file in VIDEO_STORAGE_DIR.glob("*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                video_path = Path(metadata['cloud_path'])
                if video_path.exists():
                    videos.append({
                        'video_id': metadata['video_id'],
                        'filename': video_path.name,
                        'size_mb': round(video_path.stat().st_size / (1024 * 1024), 1),
                        'upload_time': metadata['upload_timestamp'],
                        'expiration_time': metadata['expiration_time'],
                        'incident_type': metadata.get('incident_type', 'unknown'),
                        'risk_level': metadata.get('risk_level', 'unknown'),
                        'expired': datetime.now() > datetime.fromisoformat(metadata['expiration_time'])
                    })
            
            except Exception as e:
                logger.warning(f"Error reading metadata {metadata_file}: {e}")
        
        return jsonify({
            'total_videos': len(videos),
            'videos': videos
        })
    
    except Exception as e:
        logger.error(f"Error listing videos: {e}")
        abort(500, description="Internal server error")


@app.errorhandler(404)
def not_found(error):
    """Custom 404 handler"""
    return jsonify({
        'error': 'Video not found',
        'message': 'The requested video does not exist or the link has expired',
        'code': 404
    }), 404


@app.errorhandler(403)
def forbidden(error):
    """Custom 403 handler"""
    return jsonify({
        'error': 'Access denied',
        'message': str(error.description),
        'code': 403
    }), 403


@app.errorhandler(401)
def unauthorized(error):
    """Custom 401 handler"""
    return jsonify({
        'error': 'Unauthorized',
        'message': 'Access token required',
        'code': 401
    }), 401


def start_server():
    """Start the local video server with robust error handling"""
    import socket
    import subprocess
    import time
    
    # Ensure storage directory exists
    VIDEO_STORAGE_DIR.mkdir(exist_ok=True)
    
    logger.info(f"🚀 Starting local video server...")
    logger.info(f"📁 Storage directory: {VIDEO_STORAGE_DIR.absolute()}")
    logger.info(f"🌐 Server URL: {BASE_URL}")
    
    # Kill any existing processes on the port
    try:
        result = subprocess.run(['lsof', '-ti', f':{SERVER_PORT}'], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    subprocess.run(['kill', '-9', pid], capture_output=True)
                    logger.info(f"Killed existing process {pid}")
            time.sleep(2)
    except Exception:
        pass  # Ignore errors in cleanup
    
    # Try different approaches to start the server
    for attempt in range(3):
        try:
            logger.info(f"🎬 Starting Flask server (attempt {attempt + 1})...")
            
            # Configure Flask app for better reliability
            app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
            app.config['TEMPLATES_AUTO_RELOAD'] = False
            
            # Start server with minimal configuration
            from werkzeug.serving import run_simple
            
            logger.info(f"✅ Starting server on {SERVER_HOST}:{SERVER_PORT}")
            run_simple(
                hostname=SERVER_HOST,
                port=SERVER_PORT,
                application=app,
                threaded=True,
                use_reloader=False,
                use_debugger=False
            )
            break
            
        except OSError as e:
            if "Address already in use" in str(e):
                logger.warning(f"Port {SERVER_PORT} still in use, waiting...")
                time.sleep(3)
                continue
            else:
                logger.error(f"❌ Server startup failed: {e}")
                if attempt == 2:  # Last attempt
                    raise
        except Exception as e:
            logger.error(f"❌ Unexpected error starting server: {e}")
            if attempt == 2:  # Last attempt
                raise
            time.sleep(2)


if __name__ == '__main__':
    start_server()