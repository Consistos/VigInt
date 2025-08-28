"""API Proxy for Vigint services - handles routing and load balancing"""

import requests
import logging
import time
from flask import Flask, request, jsonify, Response
from urllib.parse import urljoin
from auth import require_api_key, require_api_key_flexible
from vigint.models import db, APIUsage
from config import config
import google.generativeai as genai
import base64
import cv2
import numpy as np
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import tempfile
import os
import shutil
import threading
import atexit
from collections import deque


app = Flask(__name__)
app.config['SECRET_KEY'] = config.secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = config.database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database with app
db.init_app(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reduce werkzeug (Flask) logging verbosity
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.WARNING)

# Configure Gemini AI (server-side only)
gemini_api_key = config.gemini_api_key
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    logger.info("Gemini AI configured on server")
else:
    gemini_model = None
    logger.warning("Gemini API key not configured")

# Email configuration (server-side only)
email_config = {
    'smtp_server': config.get('Email', 'smtp_server', 'smtp.gmail.com'),
    'smtp_port': config.getint('Email', 'smtp_port', 587),
    'username': config.get('Email', 'username', ''),
    'password': config.get('Email', 'password', ''),
    'from_email': config.get('Email', 'from_email', ''),
    'to_email': config.get('Email', 'to_email', '')
}

# Video analysis configuration (server-side only)
video_config = {
    'short_buffer_duration': config.getint('VideoAnalysis', 'short_buffer_duration', 3),
    'long_buffer_duration': config.getint('VideoAnalysis', 'long_buffer_duration', 10),
    'analysis_fps': config.getint('VideoAnalysis', 'analysis_fps', 25),
    'video_format': config.get('VideoAnalysis', 'video_format', 'mp4'),
    'compression_quality': config.getfloat('VideoAnalysis', 'compression_quality', 0.85),
    'max_email_size_mb': config.getint('VideoAnalysis', 'max_email_size_mb', 20),
    'preferred_codec': config.get('VideoAnalysis', 'preferred_codec', 'H264')
}

# Global frame buffers for each client (keyed by client ID)
client_frame_buffers = {}

# Temporary file management
temp_video_files = set()  # Track temporary video files for cleanup
temp_file_lock = threading.Lock()  # Thread-safe access to temp files set


def check_disk_space(path=None, min_free_gb=1.0):
    """
    Check available disk space
    
    Args:
        path: Path to check (defaults to temp directory)
        min_free_gb: Minimum free space required in GB
    
    Returns:
        dict: Disk space information and availability status
    """
    if path is None:
        path = tempfile.gettempdir()
    
    try:
        total, used, free = shutil.disk_usage(path)
        free_gb = free / (1024**3)  # Convert to GB
        total_gb = total / (1024**3)
        used_gb = used / (1024**3)
        
        return {
            'available': free_gb >= min_free_gb,
            'free_gb': free_gb,
            'total_gb': total_gb,
            'used_gb': used_gb,
            'path': path
        }
    except Exception as e:
        logger.error(f"Error checking disk space: {e}")
        return {
            'available': False,
            'error': str(e),
            'path': path
        }


def create_secure_temp_file(suffix='.mp4', prefix='vigint_incident_'):
    """
    Create a secure temporary file for incident videos
    
    Args:
        suffix: File extension
        prefix: Filename prefix
    
    Returns:
        dict: Temporary file information
    """
    try:
        # Check disk space first
        disk_info = check_disk_space()
        if not disk_info['available']:
            return {
                'success': False,
                'error': f"Insufficient disk space: {disk_info.get('free_gb', 0):.2f} GB available",
                'disk_info': disk_info
            }
        
        # Create secure temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        os.close(temp_fd)  # Close file descriptor, we'll use the path
        
        # Track the temporary file for cleanup
        with temp_file_lock:
            temp_video_files.add(temp_path)
        
        logger.info(f"Created secure temporary file: {temp_path}")
        
        return {
            'success': True,
            'path': temp_path,
            'disk_info': disk_info
        }
        
    except Exception as e:
        logger.error(f"Error creating secure temporary file: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def cleanup_temp_file(file_path):
    """
    Clean up a specific temporary file
    
    Args:
        file_path: Path to the temporary file to clean up
    
    Returns:
        bool: True if cleanup successful
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")
        
        # Remove from tracking set
        with temp_file_lock:
            temp_video_files.discard(file_path)
        
        return True
        
    except Exception as e:
        logger.error(f"Error cleaning up temporary file {file_path}: {e}")
        return False


def cleanup_all_temp_files():
    """
    Clean up all tracked temporary video files
    
    Returns:
        dict: Cleanup statistics
    """
    cleaned_count = 0
    failed_count = 0
    
    with temp_file_lock:
        temp_files_copy = temp_video_files.copy()
        temp_video_files.clear()
    
    for file_path in temp_files_copy:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                cleaned_count += 1
                logger.debug(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            failed_count += 1
            logger.warning(f"Failed to clean up temporary file {file_path}: {e}")
    
    if cleaned_count > 0 or failed_count > 0:
        logger.info(f"Temporary file cleanup: {cleaned_count} cleaned, {failed_count} failed")
    
    return {
        'cleaned': cleaned_count,
        'failed': failed_count,
        'total': cleaned_count + failed_count
    }


def cleanup_old_temp_files(max_age_hours=24):
    """
    Clean up old temporary files based on age
    
    Args:
        max_age_hours: Maximum age in hours before cleanup
    
    Returns:
        dict: Cleanup statistics
    """
    import time
    
    cleaned_count = 0
    failed_count = 0
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    
    temp_dir = tempfile.gettempdir()
    
    try:
        for filename in os.listdir(temp_dir):
            if filename.startswith('vigint_incident_') and filename.endswith('.mp4'):
                file_path = os.path.join(temp_dir, filename)
                try:
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > max_age_seconds:
                        os.unlink(file_path)
                        cleaned_count += 1
                        logger.debug(f"Cleaned up old temporary file: {file_path}")
                        
                        # Remove from tracking set if present
                        with temp_file_lock:
                            temp_video_files.discard(file_path)
                            
                except Exception as e:
                    failed_count += 1
                    logger.warning(f"Failed to clean up old file {file_path}: {e}")
    
    except Exception as e:
        logger.error(f"Error during old file cleanup: {e}")
        return {'error': str(e)}
    
    if cleaned_count > 0 or failed_count > 0:
        logger.info(f"Old file cleanup: {cleaned_count} cleaned, {failed_count} failed")
    
    return {
        'cleaned': cleaned_count,
        'failed': failed_count,
        'total': cleaned_count + failed_count
    }


def monitor_storage_usage():
    """
    Monitor storage usage and perform cleanup if needed
    
    Returns:
        dict: Storage monitoring results
    """
    disk_info = check_disk_space(min_free_gb=0.5)  # Warning threshold
    
    if disk_info['available']:
        return {
            'status': 'ok',
            'disk_info': disk_info
        }
    
    # Perform emergency cleanup
    logger.warning(f"Low disk space detected: {disk_info.get('free_gb', 0):.2f} GB available")
    
    # Clean up old files first
    old_cleanup = cleanup_old_temp_files(max_age_hours=1)  # More aggressive cleanup
    
    # Clean up all tracked files if still low on space
    disk_info_after_old = check_disk_space(min_free_gb=0.5)
    if not disk_info_after_old['available']:
        all_cleanup = cleanup_all_temp_files()
        disk_info_final = check_disk_space(min_free_gb=0.5)
        
        return {
            'status': 'emergency_cleanup',
            'old_cleanup': old_cleanup,
            'all_cleanup': all_cleanup,
            'disk_info_initial': disk_info,
            'disk_info_final': disk_info_final
        }
    
    return {
        'status': 'cleanup_performed',
        'old_cleanup': old_cleanup,
        'disk_info_initial': disk_info,
        'disk_info_after': disk_info_after_old
    }


# Register cleanup function to run on exit
atexit.register(cleanup_all_temp_files)


def get_client_buffer(client_id):
    """Get or create frame buffer for a client"""
    if client_id not in client_frame_buffers:
        max_frames = video_config['long_buffer_duration'] * video_config['analysis_fps']
        client_frame_buffers[client_id] = deque(maxlen=max_frames)
    return client_frame_buffers[client_id]


def validate_video_format(video_format):
    """Validate video format and return appropriate codec"""
    format_codecs = {
        'mp4': 'mp4v',
        'avi': 'XVID',
        'mov': 'mp4v',
        'mkv': 'XVID'
    }
    
    if video_format.lower() not in format_codecs:
        logger.warning(f"Unsupported video format: {video_format}, defaulting to mp4")
        return 'mp4', 'mp4v'
    
    return video_format.lower(), format_codecs[video_format.lower()]


def create_video_from_frames(frames, output_path, fps=None, video_format=None, quality_optimization=True):
    """
    Create a video file from a list of frames with configurable settings
    
    Args:
        frames: List of frame dictionaries with 'frame_data' key
        output_path: Path where video will be saved
        fps: Frames per second (defaults to config value)
        video_format: Video format (defaults to config value)
        quality_optimization: Whether to optimize video quality
    
    Returns:
        dict: Result with success status and metadata
    """
    if not frames:
        return {'success': False, 'error': 'No frames provided', 'frames_processed': 0}
    
    # Use configuration defaults if not specified
    if fps is None:
        fps = video_config['analysis_fps']
    if video_format is None:
        video_format = video_config['video_format']
    
    # Validate format and get codec
    validated_format, codec = validate_video_format(video_format)
    
    try:
        # Decode and validate first frame
        first_frame_data = base64.b64decode(frames[0]['frame_data'])
        first_frame = cv2.imdecode(np.frombuffer(first_frame_data, np.uint8), cv2.IMREAD_COLOR)
        
        if first_frame is None:
            return {'success': False, 'error': 'Failed to decode first frame', 'frames_processed': 0}
        
        height, width, channels = first_frame.shape
        
        # Quality optimization settings
        if quality_optimization:
            # Ensure dimensions are even (required by some codecs)
            if width % 2 != 0:
                width -= 1
            if height % 2 != 0:
                height -= 1
        
        # Create video writer with high-quality codec options
        codec_options = [
            ('H264', cv2.VideoWriter_fourcc(*'H264')),
            ('avc1', cv2.VideoWriter_fourcc(*'avc1')),
            ('X264', cv2.VideoWriter_fourcc(*'X264')),
            (codec, cv2.VideoWriter_fourcc(*codec))  # Original codec as fallback
        ]
        
        video_writer = None
        used_codec = None
        
        for codec_name, fourcc in codec_options:
            video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            if video_writer.isOpened():
                used_codec = codec_name
                logger.info(f"Using {codec_name} codec for video creation")
                break
            else:
                video_writer.release()
        
        if not video_writer or not video_writer.isOpened():
            return {'success': False, 'error': 'Failed to initialize video writer with any codec', 'frames_processed': 0}
        
        frames_processed = 0
        failed_frames = 0
        
        # Write frames to video
        for i, frame_info in enumerate(frames):
            try:
                frame_data = base64.b64decode(frame_info['frame_data'])
                frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
                
                if frame is None:
                    failed_frames += 1
                    logger.warning(f"Failed to decode frame {i}")
                    continue
                
                # Resize frame if dimensions don't match (quality optimization)
                if quality_optimization and (frame.shape[1] != width or frame.shape[0] != height):
                    frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_LANCZOS4)
                
                # Add timestamp overlay if frame has timestamp
                if 'timestamp' in frame_info:
                    timestamp_text = frame_info['timestamp']
                    cv2.putText(frame, timestamp_text, (10, 30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                video_writer.write(frame)
                frames_processed += 1
                
            except Exception as e:
                failed_frames += 1
                logger.warning(f"Error processing frame {i}: {e}")
                continue
        
        video_writer.release()
        
        # Verify video was created successfully
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            return {'success': False, 'error': 'Video file not created or empty', 'frames_processed': frames_processed}
        
        return {
            'success': True,
            'frames_processed': frames_processed,
            'failed_frames': failed_frames,
            'video_path': output_path,
            'duration_seconds': frames_processed / fps,
            'fps': fps,
            'format': validated_format,
            'resolution': f"{width}x{height}",
            'codec_used': used_codec,
            'quality_optimized': quality_optimization
        }
        
    except Exception as e:
        logger.error(f"Error creating video: {e}")
        return {'success': False, 'error': str(e), 'frames_processed': 0}


def generate_incident_video(client_id, incident_analysis=None, buffer_type='long'):
    """
    Generate a video specifically for security incidents with enhanced metadata
    
    Args:
        client_id: ID of the client
        incident_analysis: Analysis result containing incident details
        buffer_type: Type of buffer to use ('short' or 'long')
    
    Returns:
        dict: Result with video path and metadata
    """
    try:
        # Get client's frame buffer
        client_buffer = get_client_buffer(client_id)
        
        if len(client_buffer) == 0:
            return {'success': False, 'error': 'No frames in buffer'}
        
        # Determine buffer duration and frames to use
        if buffer_type == 'short':
            buffer_duration = video_config['short_buffer_duration']
        else:
            buffer_duration = video_config['long_buffer_duration']
        
        required_frames = buffer_duration * video_config['analysis_fps']
        incident_frames = list(client_buffer)[-required_frames:] if len(client_buffer) >= required_frames else list(client_buffer)
        
        if not incident_frames:
            return {'success': False, 'error': 'Insufficient frames for video generation'}
        
        # Create secure temporary video file with incident-specific naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        risk_level = incident_analysis.get('risk_level', 'UNKNOWN') if incident_analysis else 'UNKNOWN'
        
        temp_prefix = f"vigint_incident_{client_id}_{risk_level}_{timestamp}_"
        temp_suffix = f".{video_config['video_format']}"
        
        # Check storage and create secure temp file
        storage_status = monitor_storage_usage()
        if storage_status['status'] == 'emergency_cleanup':
            logger.warning("Emergency storage cleanup performed before video generation")
        
        temp_result = create_secure_temp_file(suffix=temp_suffix, prefix=temp_prefix)
        if not temp_result['success']:
            return temp_result
        
        video_path = temp_result['path']
        
        # Generate video with quality optimization
        result = create_video_from_frames(
            incident_frames, 
            video_path, 
            fps=video_config['analysis_fps'],
            video_format=video_config['video_format'],
            quality_optimization=True
        )
        
        if not result['success']:
            return result
        
        # Add incident-specific metadata
        result.update({
            'incident_type': 'security_incident',
            'client_id': client_id,
            'risk_level': risk_level,
            'buffer_type': buffer_type,
            'buffer_duration': buffer_duration,
            'incident_timestamp': timestamp,
            'analysis_summary': incident_analysis.get('analysis', '') if incident_analysis else ''
        })
        
        logger.info(f"Generated incident video for client {client_id}: {video_path}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating incident video: {e}")
        return {'success': False, 'error': str(e)}


def analyze_frame_for_security(frame_base64, frame_count, buffer_type="short"):
    """Analyze frame for security incidents using Gemini AI"""
    if not gemini_model:
        return None
    
    # Temporary quota check - return mock analysis if quota exceeded
    import time
    current_hour = int(time.time() / 3600)
    if hasattr(analyze_frame_for_security, 'quota_exceeded_hour') and \
       analyze_frame_for_security.quota_exceeded_hour == current_hour:
        return {
            'analysis': 'Analysis temporarily disabled due to API quota limits',
            'has_security_incident': False,
            'risk_level': "LOW",
            'timestamp': datetime.now().isoformat(),
            'frame_count': frame_count
        }
    
    try:
        prompt = f"""
        Analyze the provided video carefully for security incidents in a retail environment, with special focus on shoplifting behavior. Pay particular attention to:
        1. Customers taking items and concealing them (in pockets, bags, clothing)
        2. Unusual handling of merchandise (checking for security tags, looking around suspiciously)
        3. Taking items without paying
        4. Groups working together to distract staff while items are taken
        5. Removing packaging or security devices
        6. Unusual movements around high-value items
        7. Signs of nervousness or anxiety while handling merchandise
        
        Your analysis must be thorough and should err on the side of detecting potential security incidents rather than missing them.
        
        Return ONLY the JSON object without markdown formatting, code blocks, or additional text.
        If no incidents are detected, return the JSON with incident_detected set to false.
        
        Your response must be a valid JSON object with the following structure:
        {{"incident_detected": boolean,  // true if an incident is detected, false otherwise
        "incident_type": string      // Describe the type of incident (e.g.: shoplifting)
        "confidence": float,         // confidence level between 0.0 and 1.0
        "description": string,       // description of what you see
        "analysis": string,          // detailed analysis of the video content}}
        
        Answer in French.
        """
        
        response = gemini_model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": frame_base64}
        ])
        
        # Parse JSON response
        try:
            import json
            analysis_json = json.loads(response.text.strip())
            
            has_security_incident = analysis_json.get('incident_detected', False)
            confidence = analysis_json.get('confidence', 0.0)
            description = analysis_json.get('description', '')
            analysis_text = analysis_json.get('analysis', '')
            
            # Map confidence to risk level
            if confidence >= 0.8:
                risk_level = "HIGH"
            elif confidence >= 0.5:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
                
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse JSON response, falling back to text analysis: {e}")
            analysis_text = response.text
            has_security_incident = 'incident_detected": true' in analysis_text.lower()
            risk_level = "MEDIUM"  # Default risk level
        
        return {
            'analysis': analysis_text,
            'has_security_incident': has_security_incident,
            'risk_level': risk_level,
            'timestamp': datetime.now().isoformat(),
            'frame_count': frame_count
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in security analysis: {e}")
        
        # Check if it's a quota error and mark it
        if "429" in error_msg or "quota" in error_msg.lower():
            analyze_frame_for_security.quota_exceeded_hour = int(time.time() / 3600)
            logger.warning("API quota exceeded, disabling analysis for this hour")
        
        return None

# Backend service configurations
BACKEND_SERVICES = {
    'rtsp': {
        'base_url': 'http://localhost:9997',  # MediaMTX API
        'timeout': 30
    },
    'billing': {
        'base_url': 'http://localhost:5001',  # Billing service
        'timeout': 30
    }
}


def log_api_usage(api_key_id, endpoint, method, status_code, cost=0.001):
    """Log API usage for billing purposes"""
    try:
        usage = APIUsage(
            api_key_id=api_key_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            cost=cost
        )
        db.session.add(usage)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log API usage: {e}")


def proxy_request(service_name, path, method='GET', **kwargs):
    """Proxy a request to a backend service"""
    if service_name not in BACKEND_SERVICES:
        return None, 404
    
    service_config = BACKEND_SERVICES[service_name]
    url = urljoin(service_config['base_url'], path)
    timeout = service_config['timeout']
    
    try:
        # Prepare request parameters
        req_kwargs = {
            'timeout': timeout,
            'headers': dict(request.headers),
            'params': dict(request.args)
        }
        
        # Add request body for POST/PUT requests
        if method.upper() in ['POST', 'PUT', 'PATCH']:
            if request.is_json:
                req_kwargs['json'] = request.get_json()
            else:
                req_kwargs['data'] = request.get_data()
        
        # Make the request
        response = requests.request(method, url, **req_kwargs)
        
        return response, response.status_code
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout when proxying to {service_name}: {url}")
        return None, 504
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error when proxying to {service_name}: {url}")
        return None, 503
    except Exception as e:
        logger.error(f"Error proxying to {service_name}: {e}")
        return None, 500


@app.route('/api/rtsp/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@require_api_key
def rtsp_proxy(path):
    """Proxy RTSP API requests"""
    start_time = time.time()
    
    response, status_code = proxy_request('rtsp', f'/v1/{path}', request.method)
    
    # Calculate cost based on request type and processing time
    processing_time = time.time() - start_time
    cost = 0.001 + (processing_time * 0.0001)  # Base cost + time-based cost
    
    # Log usage
    log_api_usage(
        api_key_id=request.current_api_key.id,
        endpoint=f'/api/rtsp/{path}',
        method=request.method,
        status_code=status_code,
        cost=cost
    )
    
    if response is None:
        return jsonify({'error': 'Service unavailable'}), status_code
    
    # Return the response
    return Response(
        response.content,
        status=response.status_code,
        headers=dict(response.headers)
    )


@app.route('/api/billing/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@require_api_key
def billing_proxy(path):
    """Proxy billing API requests"""
    start_time = time.time()
    
    response, status_code = proxy_request('billing', f'/api/{path}', request.method)
    
    # Calculate cost
    processing_time = time.time() - start_time
    cost = 0.002 + (processing_time * 0.0001)  # Higher base cost for billing operations
    
    # Log usage
    log_api_usage(
        api_key_id=request.current_api_key.id,
        endpoint=f'/api/billing/{path}',
        method=request.method,
        status_code=status_code,
        cost=cost
    )
    
    if response is None:
        return jsonify({'error': 'Service unavailable'}), status_code
    
    return Response(
        response.content,
        status=response.status_code,
        headers=dict(response.headers)
    )


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'services': {
            service: 'unknown' for service in BACKEND_SERVICES.keys()
        }
    })





@app.route('/api/video/buffer', methods=['POST'])
@require_api_key_flexible
def add_frame_to_buffer():
    """Add frame to client's buffer for continuous monitoring"""
    try:
        # Get frame data from request
        data = request.get_json()
        if not data or 'frame_data' not in data:
            return jsonify({'error': 'Missing frame data'}), 400
        
        frame_base64 = data['frame_data']
        frame_count = data.get('frame_count', 0)
        timestamp = datetime.now().isoformat()
        
        # Get client's frame buffer
        client_buffer = get_client_buffer(request.current_client.id)
        
        # Add frame to buffer
        frame_info = {
            'frame_data': frame_base64,
            'frame_count': frame_count,
            'timestamp': timestamp
        }
        client_buffer.append(frame_info)
        
        return jsonify({
            'status': 'buffered',
            'frame_count': frame_count,
            'buffer_size': len(client_buffer),
            'timestamp': timestamp
        })
        
    except Exception as e:
        logger.error(f"Error buffering frame: {e}")
        return jsonify({'error': 'Failed to buffer frame'}), 500


@app.route('/api/video/analyze', methods=['POST'])
@require_api_key_flexible
def analyze_frame():
    """Analyze recent frames for security incidents using dual buffer system"""
    start_time = time.time()
    
    try:
        if not gemini_model:
            return jsonify({'error': 'AI analysis not available'}), 503
        
        # Get client's frame buffer
        client_buffer = get_client_buffer(request.current_client.id)
        
        if len(client_buffer) == 0:
            return jsonify({'error': 'No frames in buffer'}), 400
        
        # Get short buffer (last 3 seconds) for initial analysis
        short_buffer_frames = video_config['short_buffer_duration'] * video_config['analysis_fps']
        recent_frames = list(client_buffer)[-short_buffer_frames:] if len(client_buffer) >= short_buffer_frames else list(client_buffer)
        
        if not recent_frames:
            return jsonify({'error': 'Insufficient frames for analysis'}), 400
        
        # Analyze the most recent frame for security incidents
        latest_frame = recent_frames[-1]
        analysis_result = analyze_frame_for_security(
            latest_frame['frame_data'], 
            latest_frame['frame_count'], 
            "short"
        )
        
        if not analysis_result:
            return jsonify({'error': 'Analysis failed'}), 500
        
        # Calculate cost
        processing_time = time.time() - start_time
        cost = 0.01 + (processing_time * 0.001)
        
        # Log usage
        log_api_usage(
            api_key_id=request.current_api_key.id,
            endpoint='/api/video/analyze',
            method='POST',
            status_code=200,
            cost=cost
        )
        
        logger.info(f"Frame {latest_frame['frame_count']} analyzed for client {request.current_client.name}")
        
        # If security incident detected, trigger detailed analysis
        if analysis_result['has_security_incident']:
            logger.warning(f"🚨 SECURITY INCIDENT DETECTED for client {request.current_client.name}")
            
            # Get long buffer (last 10 seconds) for detailed analysis
            long_buffer_frames = video_config['long_buffer_duration'] * video_config['analysis_fps']
            incident_frames = list(client_buffer)[-long_buffer_frames:] if len(client_buffer) >= long_buffer_frames else list(client_buffer)
            
            # Perform detailed analysis on the incident context
            detailed_analysis = analyze_incident_context(incident_frames)
            analysis_result['detailed_analysis'] = detailed_analysis
            analysis_result['incident_frames_count'] = len(incident_frames)
        
        return jsonify(analysis_result)
        
    except Exception as e:
        logger.error(f"Error analyzing frame: {e}")
        return jsonify({'error': 'Analysis failed'}), 500


def send_email_with_retry(msg, video_attached, attachment_error, max_retries=3, retry_delay=2):
    """
    Send email with robust error handling, retry mechanisms, and fallback options
    
    Args:
        msg: Email message object
        video_attached: Whether video was successfully attached
        attachment_error: Any error from video attachment
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        dict: Email delivery result with status and metadata
    """
    import time
    import socket
    from email.mime.text import MIMEText
    
    delivery_attempts = []
    
    for attempt in range(max_retries + 1):
        attempt_start = time.time()
        attempt_info = {
            'attempt': attempt + 1,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'error': None,
            'duration': 0,
            'fallback_used': False
        }
        
        try:
            logger.info(f"Email delivery attempt {attempt + 1}/{max_retries + 1}")
            
            # Create SMTP connection with timeout
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'], timeout=30)
            server.set_debuglevel(0)  # Disable debug output for production
            
            # Start TLS with error handling
            try:
                server.starttls()
            except smtplib.SMTPException as e:
                raise Exception(f"TLS negotiation failed: {e}")
            
            # Login with credential validation
            try:
                server.login(email_config['username'], email_config['password'])
            except smtplib.SMTPAuthenticationError as e:
                raise Exception(f"Authentication failed: {e}")
            except smtplib.SMTPException as e:
                raise Exception(f"Login failed: {e}")
            
            # Send message with size validation
            try:
                # Check message size (most servers limit to 25MB)
                msg_string = msg.as_string()
                msg_size_mb = len(msg_string.encode('utf-8')) / (1024 * 1024)
                
                if msg_size_mb > 25:
                    logger.warning(f"Email size ({msg_size_mb:.1f} MB) exceeds typical limits")
                    
                    # If this is the first attempt and we have a video attachment, try without it
                    if attempt == 0 and video_attached:
                        logger.info("Attempting fallback to text-only email due to size")
                        fallback_msg = create_text_only_fallback_email(msg, attachment_error or "Email size too large")
                        server.send_message(fallback_msg)
                        attempt_info['fallback_used'] = True
                        logger.info("Successfully sent text-only fallback email")
                    else:
                        raise Exception(f"Email too large ({msg_size_mb:.1f} MB)")
                else:
                    server.send_message(msg)
                
                server.quit()
                
                # Success!
                attempt_info['success'] = True
                attempt_info['duration'] = time.time() - attempt_start
                delivery_attempts.append(attempt_info)
                
                logger.info(f"Email sent successfully on attempt {attempt + 1}")
                
                return {
                    'success': True,
                    'attempts': delivery_attempts,
                    'total_attempts': attempt + 1,
                    'final_status': 'delivered',
                    'fallback_used': attempt_info['fallback_used'],
                    'delivery_time': attempt_info['duration']
                }
                
            except smtplib.SMTPRecipientsRefused as e:
                raise Exception(f"Recipient refused: {e}")
            except smtplib.SMTPDataError as e:
                raise Exception(f"SMTP data error: {e}")
            except smtplib.SMTPException as e:
                raise Exception(f"SMTP error during send: {e}")
            
        except Exception as e:
            attempt_info['error'] = str(e)
            attempt_info['duration'] = time.time() - attempt_start
            delivery_attempts.append(attempt_info)
            
            logger.warning(f"Email delivery attempt {attempt + 1} failed: {e}")
            
            # Close server connection if it exists
            try:
                if 'server' in locals():
                    server.quit()
            except:
                pass
            
            # If this is not the last attempt, wait before retrying
            if attempt < max_retries:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                # Final attempt failed, try text-only fallback if we haven't already
                if not any(a.get('fallback_used', False) for a in delivery_attempts):
                    logger.info("All attempts failed, trying final text-only fallback")
                    try:
                        fallback_result = send_text_only_fallback(msg, str(e))
                        if fallback_result['success']:
                            return {
                                'success': True,
                                'attempts': delivery_attempts + [fallback_result],
                                'total_attempts': attempt + 2,
                                'final_status': 'delivered_fallback',
                                'fallback_used': True,
                                'delivery_time': fallback_result['duration']
                            }
                    except Exception as fallback_error:
                        logger.error(f"Text-only fallback also failed: {fallback_error}")
    
    # All attempts failed
    logger.error(f"Email delivery failed after {max_retries + 1} attempts")
    
    return {
        'success': False,
        'attempts': delivery_attempts,
        'total_attempts': len(delivery_attempts),
        'final_status': 'failed',
        'fallback_used': False,
        'last_error': delivery_attempts[-1]['error'] if delivery_attempts else 'Unknown error'
    }


def create_text_only_fallback_email(original_msg, reason):
    """
    Create a text-only fallback email when video attachment fails
    
    Args:
        original_msg: Original email message
        reason: Reason for fallback
    
    Returns:
        MIMEText: Text-only email message
    """
    # Extract basic information from original message
    subject = original_msg['Subject']
    to_email = original_msg['To']
    from_email = original_msg['From']
    
    # Create simplified text-only body
    fallback_body = f"""
🚨 VIGINT SECURITY ALERT - VIDEO ATTACHMENT UNAVAILABLE

This is a text-only security alert. The video evidence could not be attached.
Reason: {reason}

{'-' * 60}
ALERT DETAILS
{'-' * 60}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
Status: Security incident detected
Video: Attachment failed - contact administrator

{'-' * 60}
IMMEDIATE ACTIONS REQUIRED
{'-' * 60}
1. Check security monitoring system directly
2. Contact system administrator about video attachment issue
3. Review incident through alternative monitoring methods
4. Document this delivery issue for technical support

{'-' * 60}
TECHNICAL INFORMATION
{'-' * 60}
This alert was automatically converted to text-only format due to delivery issues.
Original alert contained video evidence and detailed analysis.
Contact technical support with timestamp: {datetime.now().isoformat()}

For immediate assistance, access the monitoring system directly or contact security personnel.
"""
    
    # Create new text-only message
    fallback_msg = MIMEText(fallback_body, 'plain')
    fallback_msg['Subject'] = f"[TEXT-ONLY] {subject}"
    fallback_msg['From'] = from_email
    fallback_msg['To'] = to_email
    fallback_msg['X-Vigint-Fallback'] = 'true'
    fallback_msg['X-Vigint-Original-Failure'] = reason
    
    return fallback_msg


def compress_video_for_email(video_path, max_size_mb=20, quality_reduction=0.85):
    """
    Compress video file to meet email attachment size limits with improved quality
    
    Args:
        video_path: Path to original video file
        max_size_mb: Maximum size in MB for email attachment
        quality_reduction: Quality reduction factor (0.1 = very compressed, 0.9 = minimal compression)
    
    Returns:
        dict: Compression result with new file path or error
    """
    try:
        import tempfile
        
        # Check if compression is needed
        original_size = os.path.getsize(video_path) / (1024 * 1024)  # Size in MB
        if original_size <= max_size_mb:
            return {
                'success': True,
                'compressed': False,
                'original_path': video_path,
                'compressed_path': video_path,
                'original_size_mb': original_size,
                'final_size_mb': original_size,
                'compression_ratio': 1.0
            }
        
        logger.info(f"Compressing video: {original_size:.1f} MB > {max_size_mb} MB limit")
        
        # Create compressed video file
        compressed_fd, compressed_path = tempfile.mkstemp(suffix='_compressed.mp4', prefix='vigint_compressed_')
        os.close(compressed_fd)
        
        # Track compressed file for cleanup
        with temp_file_lock:
            temp_video_files.add(compressed_path)
        
        # Read original video to get properties
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {'success': False, 'error': 'Cannot open original video for compression'}
        
        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Improved compression strategy - preserve quality better
        # Only reduce resolution if absolutely necessary
        compression_ratio_needed = max_size_mb / original_size
        
        if compression_ratio_needed > 0.7:
            # Light compression - maintain original resolution, reduce FPS slightly
            new_width = width
            new_height = height
            new_fps = max(15, int(fps * 0.8))  # Reduce FPS by 20% max
        elif compression_ratio_needed > 0.4:
            # Medium compression - slight resolution reduction
            new_width = int(width * 0.9)
            new_height = int(height * 0.9)
            new_fps = max(12, int(fps * 0.7))
        else:
            # Heavy compression - use quality_reduction factor
            new_width = int(width * quality_reduction)
            new_height = int(height * quality_reduction)
            new_fps = max(10, int(fps * quality_reduction))
        
        # Ensure dimensions are even (required by H.264)
        if new_width % 2 != 0:
            new_width -= 1
        if new_height % 2 != 0:
            new_height -= 1
        
        # Use H.264 codec for better quality and compression
        # Try multiple codec options for better compatibility
        codec_options = [
            ('H264', cv2.VideoWriter_fourcc(*'H264')),
            ('avc1', cv2.VideoWriter_fourcc(*'avc1')),
            ('X264', cv2.VideoWriter_fourcc(*'X264')),
            ('mp4v', cv2.VideoWriter_fourcc(*'mp4v'))  # Fallback
        ]
        
        out = None
        used_codec = None
        
        for codec_name, fourcc in codec_options:
            out = cv2.VideoWriter(compressed_path, fourcc, new_fps, (new_width, new_height))
            if out.isOpened():
                used_codec = codec_name
                logger.info(f"Using {codec_name} codec for compression")
                break
            else:
                out.release()
        
        if not out or not out.isOpened():
            cap.release()
            return {'success': False, 'error': 'Cannot create compressed video writer with any codec'}
        
        # Process frames with improved quality preservation
        frame_count = 0
        processed_frames = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Calculate frame skip for FPS reduction
        original_fps = fps
        frame_skip = max(1, int(original_fps / new_fps))
        
        logger.info(f"Compressing: {width}x{height}@{fps}fps → {new_width}x{new_height}@{new_fps}fps")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process every nth frame based on FPS reduction
            if frame_count % frame_skip == 0:
                # Use high-quality interpolation for resizing
                if new_width != width or new_height != height:
                    resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
                else:
                    resized_frame = frame
                
                out.write(resized_frame)
                processed_frames += 1
            
            frame_count += 1
        
        cap.release()
        out.release()
        
        # Check compressed file size
        if not os.path.exists(compressed_path):
            return {'success': False, 'error': 'Compressed video file not created'}
        
        compressed_size = os.path.getsize(compressed_path) / (1024 * 1024)
        compression_ratio = compressed_size / original_size
        
        logger.info(f"Video compressed with {used_codec}: {original_size:.1f} MB → {compressed_size:.1f} MB (ratio: {compression_ratio:.2f})")
        
        return {
            'success': True,
            'compressed': True,
            'original_path': video_path,
            'compressed_path': compressed_path,
            'original_size_mb': original_size,
            'final_size_mb': compressed_size,
            'compression_ratio': compression_ratio,
            'new_dimensions': f"{new_width}x{new_height}",
            'new_fps': new_fps,
            'frames_processed': processed_frames,
            'codec_used': used_codec,
            'quality_preserved': compression_ratio > 0.3
        }
        
    except Exception as e:
        logger.error(f"Video compression failed: {e}")
        return {'success': False, 'error': str(e)}


def send_text_only_fallback(original_msg, error_reason):
    """
    Send a text-only fallback email as last resort
    
    Args:
        original_msg: Original email message
        error_reason: Reason for fallback
    
    Returns:
        dict: Delivery result
    """
    start_time = time.time()
    
    try:
        fallback_msg = create_text_only_fallback_email(original_msg, error_reason)
        
        # Simple, direct SMTP send for fallback
        server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'], timeout=15)
        server.starttls()
        server.login(email_config['username'], email_config['password'])
        server.send_message(fallback_msg)
        server.quit()
        
        duration = time.time() - start_time
        logger.info(f"Text-only fallback email sent successfully in {duration:.2f}s")
        
        return {
            'success': True,
            'fallback_used': True,
            'duration': duration,
            'method': 'text_only_fallback',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Text-only fallback failed: {e}")
        
        return {
            'success': False,
            'fallback_used': True,
            'duration': duration,
            'error': str(e),
            'method': 'text_only_fallback',
            'timestamp': datetime.now().isoformat()
        }


def generate_incident_summary(analysis_text, risk_level, detailed_analysis, total_frames, incident_frames_count):
    """
    Generate a comprehensive executive summary of the security incident
    
    Args:
        analysis_text: Initial detection analysis
        risk_level: Risk level (LOW, MEDIUM, HIGH)
        detailed_analysis: List of detailed frame analyses
        total_frames: Total frames in buffer
        incident_frames_count: Number of frames analyzed for incident
    
    Returns:
        str: Formatted incident summary
    """
    try:
        # Extract key information from analysis
        analysis_lower = analysis_text.lower()
        
        # Identify incident type based on keywords
        incident_types = []
        if any(word in analysis_lower for word in ['person', 'people', 'individual', 'human']):
            incident_types.append('Human Activity')
        if any(word in analysis_lower for word in ['vehicle', 'car', 'truck', 'van']):
            incident_types.append('Vehicle Activity')
        if any(word in analysis_lower for word in ['suspicious', 'unusual', 'concerning']):
            incident_types.append('Suspicious Behavior')
        if any(word in analysis_lower for word in ['unauthorized', 'trespassing', 'intrusion']):
            incident_types.append('Unauthorized Access')
        if any(word in analysis_lower for word in ['theft', 'stealing', 'taking']):
            incident_types.append('Theft Activity')
        if any(word in analysis_lower for word in ['loitering', 'lingering', 'waiting']):
            incident_types.append('Loitering')
        
        if not incident_types:
            incident_types = ['General Security Event']
        
        # Generate summary based on risk level and incident types
        summary_parts = []
        
        # Risk-based opening statement
        risk_statements = {
            'HIGH': '🔴 CRITICAL SECURITY INCIDENT requiring immediate attention.',
            'MEDIUM': '🟡 SIGNIFICANT SECURITY EVENT requiring prompt review.',
            'LOW': '🟢 ROUTINE SECURITY ALERT for monitoring purposes.'
        }
        summary_parts.append(risk_statements.get(risk_level, risk_statements['MEDIUM']))
        
        # Incident type summary
        if len(incident_types) == 1:
            summary_parts.append(f"Detected: {incident_types[0]}")
        else:
            summary_parts.append(f"Detected: {', '.join(incident_types[:-1])} and {incident_types[-1]}")
        
        # Context information
        if detailed_analysis and len(detailed_analysis) > 0:
            context_info = f"Detailed analysis of {len(detailed_analysis)} key frames reveals progression of events."
            summary_parts.append(context_info)
        
        # Coverage information
        coverage_info = f"Analysis covers {incident_frames_count} frames from {total_frames} total buffer frames."
        summary_parts.append(coverage_info)
        
        # Action recommendation based on risk level
        action_recommendations = {
            'HIGH': 'IMMEDIATE security response recommended.',
            'MEDIUM': 'Prompt security review advised within 30 minutes.',
            'LOW': 'Routine review suggested when convenient.'
        }
        summary_parts.append(action_recommendations.get(risk_level, action_recommendations['MEDIUM']))
        
        return ' '.join(summary_parts)
        
    except Exception as e:
        logger.error(f"Error generating incident summary: {e}")
        return f"Security incident detected with {risk_level} risk level. Review video evidence and analysis details below."


def analyze_incident_context(frames):
    """Analyze longer buffer for detailed incident context"""
    if not frames or not gemini_model:
        return None
    
    try:
        # Analyze first, middle, and last frames for context
        key_frames = []
        if len(frames) >= 3:
            key_frames = [frames[0], frames[len(frames)//2], frames[-1]]
        else:
            key_frames = frames
        
        context_analysis = []
        for i, frame_info in enumerate(key_frames):
            prompt = f"""
            Analyze this frame for retail security incidents, focusing on shoplifting behavior.
            Frame position: {'Start' if i == 0 else 'Middle' if i == 1 else 'End'} of incident sequence
            
            Look for:
            1. Customers concealing merchandise
            2. Suspicious handling of items
            3. Groups working together
            4. Removing security tags or packaging
            
            Return ONLY a JSON object:
            {{"incident_detected": boolean, "confidence": float, "description": string, "analysis": string}}
            
            Answer in French.
            """
            
            response = gemini_model.generate_content([
                prompt,
                {"mime_type": "image/jpeg", "data": frame_info['frame_data']}
            ])
            
            # Parse JSON response
            try:
                import json
                analysis_json = json.loads(response.text.strip())
                analysis_text = analysis_json.get('analysis', response.text)
            except (json.JSONDecodeError, KeyError):
                analysis_text = response.text
            
            context_analysis.append({
                'frame_position': 'Start' if i == 0 else 'Middle' if i == 1 else 'End',
                'frame_count': frame_info['frame_count'],
                'analysis': analysis_text
            })
        
        return context_analysis
        
    except Exception as e:
        logger.error(f"Error in detailed incident analysis: {e}")
        return None


@app.route('/api/video/alert', methods=['POST'])
@require_api_key_flexible
def send_security_alert():
    """Send security alert email with video attachment (server-side processing)"""
    start_time = time.time()
    
    try:
        # Check email configuration
        if not email_config['username'] or not email_config['to_email']:
            return jsonify({'error': 'Email not configured'}), 503
        
        # Get alert data from request
        data = request.get_json()
        if not data or 'analysis' not in data:
            return jsonify({'error': 'Missing analysis data'}), 400
        
        analysis_text = data['analysis']
        frame_count = data.get('frame_count', 0)
        risk_level = data.get('risk_level', 'MEDIUM')
        detailed_analysis = data.get('detailed_analysis', None)
        incident_frames_count = data.get('incident_frames_count', 0)
        
        # Get client's frame buffer for video creation
        client_buffer = get_client_buffer(request.current_client.id)
        
        # Create video from long buffer using enhanced video generation
        video_path = None
        video_metadata = None
        if len(client_buffer) > 0:
            # Use the enhanced incident video generation
            video_result = generate_incident_video(
                request.current_client.id, 
                {
                    'risk_level': risk_level,
                    'analysis': analysis_text,
                    'frame_count': frame_count
                },
                buffer_type='long'
            )
            
            if video_result['success']:
                video_path = video_result['video_path']
                video_metadata = video_result
                logger.info(f"Created incident video: {video_path} ({video_result['frames_processed']} frames)")
            else:
                logger.warning(f"Failed to create incident video: {video_result.get('error', 'Unknown error')}")
                video_path = None
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = email_config['from_email'] or email_config['username']
        msg['To'] = email_config['to_email']
        msg['Subject'] = f"🚨 Vigint Security Alert [{risk_level}] - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Create simplified email body
        incident_timestamp = datetime.now()
        
        body = f"""
🚨 VIGINT SECURITY ALERT - {risk_level} RISK

Client: {request.current_client.name}
Time: {incident_timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC
Risk Level: {risk_level}

ANALYSIS:
{analysis_text}

This is an automated alert from the Vigint security system.
Please review the attached video footage immediately.
        """
        

        
        # Add simple video status
        if video_metadata:
            body += f"\n\nVideo evidence attached ({video_metadata.get('duration_seconds', 0):.1f} seconds)"
        else:
            body += "\n\nVideo evidence not available"
        

        
        msg.attach(MIMEText(body, 'plain'))
        
        # Enhanced video attachment with compression and proper MIME handling
        video_attached = False
        attachment_error = None
        compression_info = None
        final_video_path = video_path
        
        if video_path and os.path.exists(video_path):
            try:
                # Check file size and compress if needed
                file_size = os.path.getsize(video_path)
                max_attachment_size = 20 * 1024 * 1024  # 20MB limit (conservative)
                
                if file_size > max_attachment_size:
                    logger.info(f"Video file ({file_size / (1024*1024):.1f} MB) exceeds limit, attempting compression")
                    
                    # Attempt video compression with configured settings
                    compression_result = compress_video_for_email(
                        video_path, 
                        max_size_mb=video_config['max_email_size_mb'],
                        quality_reduction=video_config['compression_quality']
                    )
                    
                    if compression_result['success']:
                        final_video_path = compression_result['compressed_path']
                        compression_info = compression_result
                        logger.info(f"Video compressed successfully: {compression_result['original_size_mb']:.1f} MB → {compression_result['final_size_mb']:.1f} MB")
                        
                        # Check if compressed video is still too large
                        max_size = video_config['max_email_size_mb']
                        if compression_result['final_size_mb'] > max_size:
                            attachment_error = f"Video still too large after compression ({compression_result['final_size_mb']:.1f} MB > {max_size} MB limit)"
                            final_video_path = None
                    else:
                        attachment_error = f"Video compression failed: {compression_result.get('error', 'Unknown error')}"
                        final_video_path = None
                
                if final_video_path and os.path.exists(final_video_path):
                    with open(final_video_path, 'rb') as video_file:
                        # Use proper MIME type for video
                        video_format = video_config['video_format'].lower()
                        mime_types = {
                            'mp4': ('video', 'mp4'),
                            'avi': ('video', 'x-msvideo'),
                            'mov': ('video', 'quicktime'),
                            'mkv': ('video', 'x-matroska')
                        }
                        
                        main_type, sub_type = mime_types.get(video_format, ('application', 'octet-stream'))
                        video_attachment = MIMEBase(main_type, sub_type)
                        video_attachment.set_payload(video_file.read())
                        encoders.encode_base64(video_attachment)
                        
                        # Create descriptive filename with incident details
                        incident_id = f"VIG-{incident_timestamp.strftime('%Y%m%d')}-{frame_count}-{risk_level}"
                        filename = f"security_incident_{incident_id}.{video_format}"
                        
                        video_attachment.add_header(
                            'Content-Disposition',
                            f'attachment; filename="{filename}"'
                        )
                        video_attachment.add_header(
                            'Content-Description', 
                            f'Vigint Security Incident Video - {risk_level} Risk'
                        )
                        
                        msg.attach(video_attachment)
                        video_attached = True
                        
                        final_file_size = os.path.getsize(final_video_path) / (1024*1024)
                        compression_note = f" (compressed from {compression_info['original_size_mb']:.1f} MB)" if compression_info and compression_info['compressed'] else ""
                        logger.info(f"Video attachment added to email: {filename} ({final_file_size:.1f} MB{compression_note})")
                        
            except Exception as e:
                attachment_error = str(e)
                logger.error(f"Failed to attach video: {e}")
                
                # Update email body to indicate attachment failure
                body += f"\n\n⚠️ Video attachment failed: {attachment_error}"
        
        # Send email with robust error handling and retry mechanisms
        email_result = send_email_with_retry(msg, video_attached, attachment_error)
        
        # Handle email delivery results
        if email_result['success']:
            if email_result.get('fallback_used', False):
                logger.warning(f"Security alert sent using fallback method for client {request.current_client.name}")
            else:
                logger.info(f"Security alert sent successfully for client {request.current_client.name}")
        else:
            logger.error(f"Failed to send security alert for client {request.current_client.name}: {email_result.get('last_error', 'Unknown error')}")
        
        # Clean up temporary video files using secure cleanup
        cleanup_results = []
        
        # Clean up original video file
        if video_path:
            cleanup_success = cleanup_temp_file(video_path)
            cleanup_results.append(('original', cleanup_success))
            if cleanup_success:
                logger.info("Original temporary video file cleaned up securely")
            else:
                logger.warning("Failed to clean up original video file securely")
        
        # Clean up compressed video file if it was created
        if compression_info and compression_info.get('compressed', False) and compression_info.get('compressed_path'):
            compressed_cleanup = cleanup_temp_file(compression_info['compressed_path'])
            cleanup_results.append(('compressed', compressed_cleanup))
            if compressed_cleanup:
                logger.info("Compressed temporary video file cleaned up securely")
            else:
                logger.warning("Failed to clean up compressed video file securely")
        
        # Calculate cost (include retry overhead if applicable)
        processing_time = time.time() - start_time
        retry_overhead = max(0, email_result.get('total_attempts', 1) - 1) * 0.001  # Additional cost for retries
        cost = 0.005 + (processing_time * 0.0001) + retry_overhead
        
        # Determine HTTP status code based on email delivery
        http_status = 200 if email_result['success'] else 207  # 207 = Multi-Status (partial success)
        
        # Log usage with appropriate status
        log_api_usage(
            api_key_id=request.current_api_key.id,
            endpoint='/api/video/alert',
            method='POST',
            status_code=http_status,
            cost=cost
        )
        
        # Create comprehensive response with enhanced email and video details
        alert_id = f"VIG-{incident_timestamp.strftime('%Y%m%d')}-{frame_count}-{risk_level}"
        
        response_data = {
            'status': email_result['final_status'] if email_result['success'] else 'failed',
            'timestamp': incident_timestamp.isoformat(),
            'alert_id': alert_id,
            'to': email_config['to_email'],
            'client_name': request.current_client.name,
            'risk_level': risk_level,
            'frame_count': frame_count,
            'incident_summary': generate_incident_summary(
                analysis_text, risk_level, detailed_analysis, 
                len(client_buffer), incident_frames_count
            ),
            'buffer_metadata': {
                'total_frames': len(client_buffer),
                'short_buffer_duration': video_config['short_buffer_duration'],
                'long_buffer_duration': video_config['long_buffer_duration'],
                'incident_frames_count': incident_frames_count,
                'analysis_fps': video_config['analysis_fps'],
                'buffer_utilization': (len(client_buffer) / (video_config['long_buffer_duration'] * video_config['analysis_fps']) * 100) if len(client_buffer) > 0 else 0
            },
            'video_attachment': {
                'attached': video_attached,
                'error': attachment_error,
                'metadata': video_metadata if video_attached else None,
                'quality_rating': "High" if video_metadata and video_metadata.get('failed_frames', 0) == 0 else "Good" if video_metadata and video_metadata.get('failed_frames', 0) < 5 else "Fair",
                'compression': compression_info if compression_info else None,
                'final_size_mb': compression_info['final_size_mb'] if compression_info else (os.path.getsize(video_path) / (1024*1024) if video_path and os.path.exists(video_path) else 0)
            },
            'email_delivery': {
                'success': email_result['success'],
                'delivery_status': email_result['final_status'],
                'attempts': email_result['total_attempts'],
                'fallback_used': email_result.get('fallback_used', False),
                'delivery_time': email_result.get('delivery_time', 0),
                'retry_count': max(0, email_result['total_attempts'] - 1),
                'error': email_result.get('last_error') if not email_result['success'] else None,
                'delivery_method': 'fallback' if email_result.get('fallback_used', False) else 'standard'
            },
            'email_details': {
                'subject': msg['Subject'],
                'body_length': len(body),
                'has_detailed_analysis': detailed_analysis is not None,
                'detailed_analysis_frames': len(detailed_analysis) if detailed_analysis else 0,
                'has_incident_summary': True,
                'sections_included': [
                    'executive_summary',
                    'incident_details', 
                    'initial_analysis',
                    'timeline_context',
                    'detailed_analysis' if detailed_analysis else None,
                    'video_evidence',
                    'recommended_actions',
                    'system_metadata'
                ]
            },
            'analysis_metadata': {
                'detection_method': 'multi_frame_contextual' if detailed_analysis else 'single_frame',
                'analysis_confidence': 'high' if detailed_analysis and len(detailed_analysis) >= 3 else 'medium',
                'ai_model': 'gemini_1_5_flash',
                'processing_time_estimate': f'{processing_time:.2f}_seconds'
            },
            'system_performance': {
                'total_processing_time': processing_time,
                'video_generation_time': video_metadata.get('duration_seconds', 0) if video_metadata else 0,
                'email_delivery_time': email_result.get('delivery_time', 0),
                'cost_breakdown': {
                    'base_cost': 0.005,
                    'processing_cost': processing_time * 0.0001,
                    'retry_overhead': retry_overhead,
                    'total_cost': cost
                }
            }
        }
        
        return jsonify(response_data), http_status
        
    except Exception as e:
        logger.error(f"Error sending alert: {e}")
        return jsonify({'error': 'Failed to send alert'}), 500


@app.route('/api/storage/status')
@require_api_key_flexible
def get_storage_status():
    """Get storage status and temporary file information"""
    try:
        disk_info = check_disk_space()
        
        # Count tracked temporary files
        with temp_file_lock:
            tracked_files = len(temp_video_files)
            tracked_files_list = list(temp_video_files)
        
        # Calculate total size of tracked files
        total_size = 0
        existing_files = 0
        for file_path in tracked_files_list:
            try:
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
                    existing_files += 1
            except Exception:
                continue
        
        return jsonify({
            'disk_info': disk_info,
            'temp_files': {
                'tracked': tracked_files,
                'existing': existing_files,
                'total_size_mb': total_size / (1024 * 1024)
            },
            'status': 'healthy' if disk_info['available'] else 'low_space'
        })
        
    except Exception as e:
        logger.error(f"Error getting storage status: {e}")
        return jsonify({'error': 'Failed to get storage status'}), 500


@app.route('/api/storage/cleanup', methods=['POST'])
@require_api_key_flexible
def manual_cleanup():
    """Manually trigger cleanup of temporary files"""
    try:
        data = request.get_json() or {}
        cleanup_type = data.get('type', 'old')  # 'old', 'all', or 'monitor'
        
        if cleanup_type == 'all':
            result = cleanup_all_temp_files()
        elif cleanup_type == 'monitor':
            result = monitor_storage_usage()
        else:  # 'old'
            max_age_hours = data.get('max_age_hours', 24)
            result = cleanup_old_temp_files(max_age_hours)
        
        # Get updated storage status
        disk_info = check_disk_space()
        
        return jsonify({
            'cleanup_result': result,
            'disk_info_after': disk_info,
            'cleanup_type': cleanup_type
        })
        
    except Exception as e:
        logger.error(f"Error during manual cleanup: {e}")
        return jsonify({'error': 'Cleanup failed'}), 500


@app.route('/api/usage')
@require_api_key_flexible
def get_usage():
    """Get API usage statistics for the current client"""
    try:
        # Get recent usage for this API key
        recent_usage = APIUsage.query.filter_by(
            api_key_id=request.current_api_key.id
        ).order_by(APIUsage.timestamp.desc()).limit(100).all()
        
        usage_data = []
        for usage in recent_usage:
            usage_data.append({
                'timestamp': usage.timestamp.isoformat(),
                'endpoint': usage.endpoint,
                'method': usage.method,
                'status_code': usage.status_code,
                'cost': float(usage.cost)
            })
        
        return jsonify({
            'api_key_id': request.current_api_key.id,
            'client_name': request.current_client.name,
            'usage_count': len(usage_data),
            'usage': usage_data
        })
        
    except Exception as e:
        logger.error(f"Error getting usage data: {e}")
        return jsonify({'error': 'Internal server error'}), 500


def initialize_database():
    """Initialize database tables"""
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")


if __name__ == '__main__':
    # Initialize database
    initialize_database()
    
    app.run(
        host=config.host,
        port=config.port,
        debug=config.debug
    )