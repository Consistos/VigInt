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
from datetime import datetime, timedelta
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
import uuid


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
gemini_model_short = None
gemini_model_long = None

def initialize_gemini_models():
    """Initialize Gemini models with fallback - called lazily to avoid startup crashes"""
    global gemini_model_short, gemini_model_long
    
    if not gemini_api_key:
        logger.warning("Gemini API key not configured")
        return False
    
    try:
        genai.configure(
            api_key=gemini_api_key,
            transport='rest'
        )
        
        # Try different model versions with fallback
        # Using gemini-2.5-flash as requested
        short_model_versions = [
            'gemini-2.5-flash',
            'gemini-pro'
        ]
        
        long_model_versions = [
            'gemini-2.5-flash',
            'gemini-pro'
        ]
        
        # Initialize short buffer model
        for model_name in short_model_versions:
            try:
                gemini_model_short = genai.GenerativeModel(model_name)
                logger.info(f"✅ Gemini short buffer model initialized: {model_name}")
                break
            except Exception as e:
                logger.warning(f"Failed to load short buffer model {model_name}: {e}")
                continue
        
        # Initialize long buffer model
        for model_name in long_model_versions:
            try:
                gemini_model_long = genai.GenerativeModel(model_name)
                logger.info(f"✅ Gemini long buffer model initialized: {model_name}")
                break
            except Exception as e:
                logger.warning(f"Failed to load long buffer model {model_name}: {e}")
                continue
        
        if not gemini_model_short or not gemini_model_long:
            logger.error("❌ Failed to initialize Gemini models")
            return False
        else:
            logger.info("✅ Gemini AI configured successfully on server")
            return True
            
    except Exception as e:
        logger.error(f"❌ Critical error during Gemini initialization: {e}")
        return False

# Try to initialize but don't crash if it fails
try:
    initialize_gemini_models()
except Exception as e:
    logger.error(f"❌ Gemini initialization failed but server will continue: {e}")

# Email configuration (server-side only)
# Read from environment variables first (for Render), then fallback to config file
email_config = {
    'smtp_server': config.email_smtp_server,
    'smtp_port': config.email_smtp_port,
    'username': config.email_username,
    'password': config.email_password,
    'from_email': config.email_from,
    'to_email': config.email_to
}

# Log email configuration status (without exposing sensitive data)
logger.info(f"📧 Email config loaded - Username: {'✅ SET' if email_config['username'] else '❌ NOT SET'}, To: {'✅ SET' if email_config['to_email'] else '❌ NOT SET'}")

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

# Multi-source frame buffers (keyed by client_id -> source_id -> deque)
multi_source_buffers = {}
multi_source_buffer_lock = threading.Lock()

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


def get_multi_source_buffer(client_id, source_id):
    """Get or create frame buffer for a specific video source"""
    with multi_source_buffer_lock:
        if client_id not in multi_source_buffers:
            multi_source_buffers[client_id] = {}
        
        if source_id not in multi_source_buffers[client_id]:
            max_frames = video_config['long_buffer_duration'] * video_config['analysis_fps']
            multi_source_buffers[client_id][source_id] = deque(maxlen=max_frames)
        
        return multi_source_buffers[client_id][source_id]


def get_all_client_sources(client_id):
    """Get all video sources for a client"""
    with multi_source_buffer_lock:
        if client_id not in multi_source_buffers:
            return []
        return list(multi_source_buffers[client_id].keys())


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
        
        # Create video writer with codec options ordered by compatibility
        # Try most compatible codecs first (work without external encoders)
        codec_options = [
            ('mp4v', cv2.VideoWriter_fourcc(*'mp4v')),  # MPEG-4, most compatible
            ('MJPG', cv2.VideoWriter_fourcc(*'MJPG')),  # Motion JPEG, very compatible
            ('XVID', cv2.VideoWriter_fourcc(*'XVID')),  # Xvid codec
            ('avc1', cv2.VideoWriter_fourcc(*'avc1')),  # H264 variant
            ('X264', cv2.VideoWriter_fourcc(*'X264')),  # x264 codec
            (codec, cv2.VideoWriter_fourcc(*codec))     # Original codec as fallback
        ]
        
        video_writer = None
        used_codec = None
        
        for codec_name, fourcc in codec_options:
            try:
                video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
                if video_writer.isOpened():
                    used_codec = codec_name
                    logger.info(f"✅ Using {codec_name} codec for video creation")
                    break
                else:
                    video_writer.release()
                    logger.debug(f"❌ {codec_name} codec not available")
            except Exception as e:
                logger.debug(f"❌ {codec_name} codec failed: {e}")
                continue
        
        if not video_writer or not video_writer.isOpened():
            logger.error(f"❌ Failed to initialize video writer - tried codecs: {[c[0] for c in codec_options]}")
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


def generate_incident_video(client_id, incident_analysis, buffer_type='long'):
    """
    Generate video for incident documentation (use uploaded video directly)
    
    Args:
        client_id: ID of the client
        incident_analysis: Analysis result containing incident details
        buffer_type: Type of buffer to use ('short' or 'long')
    
    Returns:
        dict: Result with video path and metadata
    """
    try:
        # Get client's video metadata
        if client_id not in client_frame_buffers:
            return {'success': False, 'error': 'No video uploaded'}
        
        video_meta = client_frame_buffers[client_id]
        if not video_meta or video_meta.get('type') != 'video':
            return {'success': False, 'error': 'No video in buffer'}
        
        source_video_path = video_meta.get('video_path')
        if not source_video_path or not os.path.exists(source_video_path):
            return {'success': False, 'error': 'Video file not found'}
        
        # Use uploaded video directly for email (no need to regenerate)
        # Just copy to a new temp file with incident-specific naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        risk_level = incident_analysis.get('risk_level', 'UNKNOWN') if incident_analysis else 'UNKNOWN'
        
        temp_prefix = f"vigint_incident_{client_id}_{risk_level}_{timestamp}_"
        temp_suffix = '.mp4'
        
        # Check storage and create secure temp file
        storage_status = monitor_storage_usage()
        if storage_status['status'] == 'emergency_cleanup':
            logger.warning("Emergency storage cleanup performed before video generation")
        
        temp_result = create_secure_temp_file(suffix=temp_suffix, prefix=temp_prefix)
        if not temp_result['success']:
            return temp_result
        
        video_path = temp_result['path']
        
        # Copy uploaded video to incident video path
        import shutil
        shutil.copy2(source_video_path, video_path)
        
        logger.info(f"📹 Using uploaded video for incident ({video_meta.get('video_size_mb', 0):.2f} MB)")
        
        # Return success with video metadata
        result = {
            'success': True,
            'video_path': video_path,
            'frames_processed': video_meta.get('frame_count', 0),
            'fps': video_meta.get('fps', 25),
            'duration': video_meta.get('duration', 0),
            'file_size_mb': video_meta.get('video_size_mb', 0)
        }
        
        result.update({
            'incident_type': incident_analysis.get('incident_type', 'security_incident') if incident_analysis else 'security_incident',
            'client_id': client_id,
            'risk_level': risk_level,
            'buffer_type': buffer_type,
            'buffer_duration': result['duration'],
            'incident_timestamp': timestamp,
            'analysis_summary': incident_analysis.get('analysis', '') if incident_analysis else ''
        })
        
        logger.info(f"Generated incident video for client {client_id}: {video_path}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating incident video: {e}")
        return {'success': False, 'error': str(e)}


def analyze_video_with_gemini(video_path, model, analyze_duration=None, buffer_type="short"):
    """Analyze video file directly with Gemini using File API (NEW APPROACH)"""
    if not model or not video_path or not os.path.exists(video_path):
        return None
    
    try:
        # Upload video to Gemini File API
        logger.info(f"📤 Uploading video to Gemini File API...")
        uploaded_video = genai.upload_file(video_path)
        logger.info(f"✅ Video uploaded to Gemini: {uploaded_video.name}")
        
        # Wait for processing
        import time as time_module
        while uploaded_video.state.name == "PROCESSING":
            time_module.sleep(1)
            uploaded_video = genai.get_file(uploaded_video.name)
        
        if uploaded_video.state.name == "FAILED":
            logger.error("❌ Video processing failed in Gemini")
            return None
        
        # Build prompt based on duration
        duration_text = f"first {analyze_duration} seconds" if analyze_duration else "entire video"
        
        prompt = f"""
        Analyze the {duration_text} of this security video for shoplifting incidents in a retail environment.
        
        IMPORTANT: This is a VIDEO showing behavior over time. Look for MOVEMENT and BEHAVIOR PATTERNS.
        
        Focus on:
        1. Customers concealing merchandise (watch their MOVEMENTS)
        2. Suspicious handling of items (track HOW they interact over time)
        3. Taking items without paying (follow the PROGRESSION)
        4. Removing security tags or packaging (watch the SEQUENCE)
        
        Analyze the video to understand the complete context. A single suspicious moment is not enough - look for patterns.
        
        Return ONLY a JSON object without markdown formatting:
        {{"incident_detected": boolean, "incident_type": string, "description": string, "analysis": string}}
        
        Answer in French.
        """
        
        # Generate content with video
        logger.info(f"🎬 Sending video to Gemini {model._model_name} for analysis...")
        response = model.generate_content([uploaded_video, prompt])
        
        # Cleanup uploaded file
        try:
            genai.delete_file(uploaded_video.name)
            logger.info(f"🗑️  Deleted uploaded video from Gemini")
        except:
            pass
        
        # Parse JSON response
        try:
            import json
            response_text = response.text.strip()
            
            # Handle JSON wrapped in markdown code blocks
            if response_text.startswith('```json'):
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    response_text = response_text[start_idx:end_idx]
            
            analysis_json = json.loads(response_text)
            has_security_incident = analysis_json.get('incident_detected', False)
            description = analysis_json.get('description', '')
            analysis_text = analysis_json.get('analysis', '')
            incident_type = analysis_json.get('incident_type', '')
                
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            analysis_text = response.text
            has_security_incident = 'incident_detected": true' in analysis_text.lower()
            incident_type = ""
        
        risk_level = "HIGH" if has_security_incident else "LOW"
        
        logger.info(f"✅ VIDEO analysis: incident_detected={has_security_incident}")
        
        return {
            'has_security_incident': has_security_incident,
            'incident_detected': has_security_incident,
            'incident_type': incident_type,
            'analysis': analysis_text,
            'risk_level': risk_level,
            'description': description
        }
        
    except Exception as e:
        logger.error(f"Error analyzing video with Gemini: {e}")
        return None


def analyze_short_video_for_security(frames, buffer_type="short"):
    """Analyze SHORT VIDEO sequence for security incidents using Gemini AI"""
    # Select appropriate model based on buffer type
    if buffer_type == "short":
        model = gemini_model_short
    else:
        model = gemini_model_long
    
    if not model or not frames:
        return None
    
    frame_count = frames[-1]['frame_count'] if frames else 0
    
    try:
        prompt = f"""
        Analyze this COMPLETE SHORT VIDEO SEQUENCE ({len(frames)} frames over ~{len(frames)/25:.1f} seconds) for security incidents in a retail environment.
        
        IMPORTANT: This is a VIDEO showing {len(frames)/25:.1f} seconds of footage. Look for MOVEMENT and BEHAVIOR throughout the ENTIRE duration.
        
        Focus on shoplifting behavior:
        1. Customers concealing merchandise (watch their MOVEMENTS throughout the video)
        2. Suspicious handling of items (track HOW they interact over time)
        3. Taking items without paying (follow the COMPLETE PROGRESSION)
        4. Removing security tags or packaging (watch the ENTIRE SEQUENCE)
        
        Analyze the FULL video to understand the complete context. A single suspicious moment is not enough - look for patterns over time.
        
        Return ONLY a JSON object without markdown formatting:
        {{"incident_detected": boolean, "incident_type": string, "description": string, "analysis": string}}
        
        Answer in French.
        """
        
        # Prepare video sequence
        video_parts = [prompt]
        for frame_info in frames:
            video_parts.append({"mime_type": "image/jpeg", "data": frame_info['frame_data']})
        
        logger.info(f"🎬 Sending {len(frames)} frames to Flash-Lite for SHORT VIDEO analysis...")
        response = model.generate_content(video_parts)
        
        # Parse JSON response
        try:
            import json
            response_text = response.text.strip()
            
            # Handle JSON wrapped in markdown code blocks
            if response_text.startswith('```json'):
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    response_text = response_text[start_idx:end_idx]
            
            analysis_json = json.loads(response_text)
            has_security_incident = analysis_json.get('incident_detected', False)
            description = analysis_json.get('description', '')
            analysis_text = analysis_json.get('analysis', '')
            incident_type = analysis_json.get('incident_type', '')
                
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse JSON response, falling back to text analysis: {e}")
            analysis_text = response.text
            analysis_text_lower = analysis_text.lower()
            has_security_incident = 'incident_detected": true' in analysis_text_lower
            
            # Try to extract incident_type from text
            incident_type = ""
            if '"incident_type":' in analysis_text_lower:
                try:
                    import re
                    match = re.search(r'"incident_type":\s*"([^"]*)"', analysis_text)
                    if match:
                        incident_type = match.group(1)
                except Exception:
                    pass
        
        # Determine risk level
        risk_level = "HIGH" if has_security_incident else "LOW"
        
        logger.info(f"✅ SHORT VIDEO analysis: incident_detected={has_security_incident}")
        
        return {
            'analysis': analysis_text,
            'has_security_incident': has_security_incident,
            'risk_level': risk_level,
            'timestamp': datetime.now().isoformat(),
            'frame_count': frame_count,
            'incident_type': incident_type,
            'video_analysis': True,
            'frames_analyzed': len(frames)
        }
        
    except Exception as e:
        logger.error(f"Error in short video analysis: {e}")
        return None


def analyze_frame_for_security(frame_base64, frame_count, buffer_type="short"):
    """DEPRECATED: Analyze single frame for security incidents using Gemini AI - use analyze_short_video_for_security instead"""
    # Select appropriate model based on buffer type
    if buffer_type == "short":
        model = gemini_model_short
    else:
        model = gemini_model_long
    
    if not model:
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
        2. Unusual handling of merchandise (checking for security tags)
        3. Taking items without paying
        4. Removing packaging or security devices
        
        Return ONLY the JSON object without markdown formatting, code blocks, or additional text.
        If no incidents are detected, return the JSON with incident_detected set to false.
        
        Your response must be a valid JSON object with the following structure:
        {{"incident_detected": boolean,  // true if an incident is detected, false otherwise
        "incident_type": string      // Describe the type of incident (e.g.: shoplifting)
        "description": string,       // description of what you see
        "analysis": string,          // detailed analysis of the video content}}
        
        Answer in French.
        """
        
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": frame_base64}
        ])
        
        # Parse JSON response
        try:
            import json
            response_text = response.text.strip()
            
            # Handle JSON wrapped in markdown code blocks
            if response_text.startswith('```json'):
                # Extract JSON from markdown code block
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    response_text = response_text[start_idx:end_idx]
            
            analysis_json = json.loads(response_text)
            
            has_security_incident = analysis_json.get('incident_detected', False)
            description = analysis_json.get('description', '')
            analysis_text = analysis_json.get('analysis', '')
            incident_type = analysis_json.get('incident_type', '')
                
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse JSON response, falling back to text analysis: {e}")
            analysis_text = response.text
            analysis_text_lower = analysis_text.lower()
            has_security_incident = 'incident_detected": true' in analysis_text_lower
            
            # Try to extract incident_type from text
            incident_type = ""
            if '"incident_type":' in analysis_text_lower:
                try:
                    import re
                    match = re.search(r'"incident_type":\s*"([^"]*)"', analysis_text)
                    if match:
                        incident_type = match.group(1)
                except Exception:
                    pass
        
        # Determine risk level based on incident detection
        risk_level = "HIGH" if has_security_incident else "LOW"
        
        return {
            'analysis': analysis_text,
            'has_security_incident': has_security_incident,
            'risk_level': risk_level,
            'timestamp': datetime.now().isoformat(),
            'frame_count': frame_count,
            'incident_type': incident_type
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


@app.route('/api/video/buffer/batch', methods=['POST'])
@require_api_key_flexible
def add_frames_batch():
    """Add multiple frames to client's buffer in one request"""
    try:
        # Get frames array from request
        data = request.get_json()
        if not data or 'frames' not in data:
            return jsonify({'error': 'Missing frames array'}), 400
        
        frames = data['frames']
        if not isinstance(frames, list):
            return jsonify({'error': 'frames must be an array'}), 400
        
        # Get client's frame buffer
        client_buffer = get_client_buffer(request.current_client.id)
        
        # Add all frames to buffer
        added_count = 0
        for frame_data in frames:
            if 'frame_data' not in frame_data:
                continue
            
            frame_info = {
                'frame_data': frame_data['frame_data'],
                'frame_count': frame_data.get('frame_count', 0),
                'timestamp': frame_data.get('timestamp', datetime.now().isoformat())
            }
            client_buffer.append(frame_info)
            added_count += 1
        
        logger.info(f"📥 Batch added {added_count} frames to buffer for client {request.current_client.name}")
        
        return jsonify({
            'status': 'buffered',
            'frames_added': added_count,
            'buffer_size': len(client_buffer)
        })
        
    except Exception as e:
        logger.error(f"Error buffering frame batch: {e}")
        return jsonify({'error': 'Failed to buffer frames'}), 500


@app.route('/api/video/upload', methods=['POST'])
@require_api_key_flexible
def upload_video():
    """Upload video file - store for direct Gemini analysis"""
    try:
        data = request.get_json()
        if not data or 'video_data' not in data:
            return jsonify({'error': 'Missing video data'}), 400
        
        video_base64 = data['video_data']
        video_filename = data.get('video_filename', 'uploaded.mp4')
        
        # Decode video
        import base64
        video_bytes = base64.b64decode(video_base64)
        
        # Save video file (Gemini will analyze it directly)
        temp_result = create_secure_temp_file(suffix='.mp4', prefix='vigint_uploaded_')
        if not temp_result['success']:
            return jsonify({'error': 'Failed to create temp file'}), 500
        
        video_path = temp_result['path']
        
        with open(video_path, 'wb') as f:
            f.write(video_bytes)
        
        video_size_mb = len(video_bytes) / (1024 * 1024)
        
        # Get video metadata
        import cv2
        cap = cv2.VideoCapture(video_path)
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_seconds = frame_count / video_fps if video_fps > 0 else 0
        cap.release()
        
        # Store video metadata in client buffer (NOT individual frames!)
        client_id = request.current_client.id
        if client_id not in client_frame_buffers:
            client_frame_buffers[client_id] = {}
        
        client_frame_buffers[client_id] = {
            'type': 'video',
            'video_path': video_path,
            'video_size_mb': video_size_mb,
            'fps': video_fps,
            'frame_count': frame_count,
            'duration': duration_seconds,
            'upload_time': datetime.now().isoformat(),
            'filename': video_filename
        }
        
        logger.info(f"📹 Stored video for analysis: {video_size_mb:.2f} MB, {frame_count} frames, {duration_seconds:.1f}s @ {video_fps:.1f} FPS for client {request.current_client.name}")
        
        return jsonify({
            'status': 'uploaded',
            'video_size_mb': video_size_mb,
            'frame_count': frame_count,
            'duration': duration_seconds,
            'ready_for_analysis': True
        })
        
    except Exception as e:
        logger.error(f"Error uploading video: {e}")
        return jsonify({'error': 'Failed to process video'}), 500


@app.route('/api/video/analyze', methods=['POST'])
@require_api_key_flexible
def analyze_frame():
    """Analyze uploaded video for security incidents using Gemini video API"""
    start_time = time.time()
    
    try:
        if not gemini_model_short:
            return jsonify({'error': 'AI analysis not available'}), 503
        
        # Get client's video metadata
        client_id = request.current_client.id
        if client_id not in client_frame_buffers:
            return jsonify({'error': 'No video uploaded'}), 400
        
        video_meta = client_frame_buffers[client_id]
        if not video_meta or video_meta.get('type') != 'video':
            return jsonify({'error': 'No video in buffer'}), 400
        
        video_path = video_meta.get('video_path')
        if not video_path or not os.path.exists(video_path):
            return jsonify({'error': 'Video file not found'}), 404
        
        duration = video_meta.get('duration', 0)
        
        # Analyze video directly with Flash-Lite (first 3 seconds)
        logger.info(f"🎥 Flash-Lite analyzing video ({duration:.1f}s) using Gemini video API")
        
        analysis_result = analyze_video_with_gemini(
            video_path,
            gemini_model_short,
            analyze_duration=3,  # Analyze first 3 seconds for quick detection
            buffer_type="short"
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
        
        # Log video analysis
        frame_count = video_meta.get('frame_count', 0)
        logger.info(f"Video analyzed for client {request.current_client.name}: {frame_count} frames, {duration:.1f}s")
        
        # If security incident detected by short buffer, trigger detailed analysis with long buffer
        if analysis_result['has_security_incident']:
            logger.warning(f"🚨 SECURITY INCIDENT DETECTED by Flash-Lite for client {request.current_client.name}")
            logger.warning(f"   Triggering Gemini 2.5 Flash (long buffer) for confirmation...")
            
            # Analyze FULL video (10 seconds) with Flash 2.5 for detailed confirmation
            logger.info(f"🎥 Flash 2.5 analyzing full video ({duration:.1f}s) for confirmation")
            
            # Perform detailed analysis on the complete video
            detailed_analysis = analyze_video_with_gemini(
                video_path,
                gemini_model_long,
                analyze_duration=None,  # Analyze full video (10 seconds)
                buffer_type="long"
            )
            
            if detailed_analysis:
                # Check if Flash (long buffer) confirms the incident
                incident_confirmed = detailed_analysis.get('has_security_incident', False)
                
                if incident_confirmed:
                    logger.warning(f"✅ INCIDENT CONFIRMED by Gemini 2.5 Flash (full video)")
                    logger.warning(f"   Flash 2.5 confirmed the incident detected by Flash-Lite")
                    analysis_result['detailed_analysis'] = detailed_analysis.get('analysis', '')
                    analysis_result['flash_confirmation'] = True
                else:
                    logger.warning(f"❌ INCIDENT REJECTED by Gemini 2.5 Flash (full video)")
                    logger.warning(f"   Flash-Lite detected incident, but Flash 2.5 found no issues")
                    logger.warning(f"   Email alert will NOT be sent (Flash 2.5 has final decision)")
                    # Override the short buffer decision - Flash 2.5 has veto power
                    analysis_result['has_security_incident'] = False
                    analysis_result['detailed_analysis'] = detailed_analysis.get('analysis', '')
                    analysis_result['flash_confirmation'] = False
                    analysis_result['flash_veto'] = True
                    analysis_result['veto_reason'] = 'Gemini 2.5 Flash did not confirm incident detected by Flash-Lite'
            else:
                # If detailed analysis failed, fall back to short buffer decision
                logger.warning(f"⚠️  Flash 2.5 analysis failed, using Flash-Lite decision as fallback")
                analysis_result['detailed_analysis'] = None
                analysis_result['flash_confirmation'] = None
        
        return jsonify(analysis_result)
        
    except Exception as e:
        logger.error(f"Error analyzing frame: {e}")
        return jsonify({'error': 'Analysis failed'}), 500


@app.route('/api/video/multi-source/buffer', methods=['POST'])
@require_api_key_flexible
def add_frame_to_multi_source_buffer():
    """Add frame to a specific video source buffer for multi-source analysis"""
    try:
        data = request.get_json()
        
        if not data or 'frame_data' not in data or 'source_id' not in data:
            return jsonify({'error': 'Missing required fields: frame_data, source_id'}), 400
        
        source_id = data['source_id']
        frame_data = data['frame_data']
        frame_count = data.get('frame_count', 0)
        source_name = data.get('source_name', source_id)
        
        # Get or create buffer for this source
        source_buffer = get_multi_source_buffer(request.current_client.id, source_id)
        
        # Add frame to buffer with metadata
        frame_info = {
            'frame_data': frame_data,
            'frame_count': frame_count,
            'timestamp': datetime.now().isoformat(),
            'source_id': source_id,
            'source_name': source_name
        }
        
        source_buffer.append(frame_info)
        
        return jsonify({
            'success': True,
            'source_id': source_id,
            'buffer_size': len(source_buffer),
            'frame_count': frame_count
        })
        
    except Exception as e:
        logger.error(f"Error buffering multi-source frame: {e}")
        return jsonify({'error': 'Failed to buffer frame'}), 500


@app.route('/api/video/multi-source/analyze', methods=['POST'])
@require_api_key_flexible
def analyze_multi_source():
    """Analyze multiple video sources using dual buffer system (Flash-Lite → Flash)"""
    start_time = time.time()
    
    try:
        if not gemini_model_short:
            return jsonify({'error': 'AI analysis not available'}), 503
        
        data = request.get_json()
        source_ids = data.get('source_ids', [])
        
        if not source_ids:
            # Analyze all sources for this client
            source_ids = get_all_client_sources(request.current_client.id)
        
        if not source_ids:
            return jsonify({'error': 'No video sources found'}), 400
        
        results = {
            'client_name': request.current_client.name,
            'timestamp': datetime.now().isoformat(),
            'sources_analyzed': len(source_ids),
            'sources': {}
        }
        
        total_incidents_detected = 0
        total_incidents_confirmed = 0
        
        # Analyze each source independently using dual-buffer logic
        for source_id in source_ids:
            source_buffer = get_multi_source_buffer(request.current_client.id, source_id)
            
            if len(source_buffer) == 0:
                results['sources'][source_id] = {
                    'error': 'No frames in buffer',
                    'has_security_incident': False
                }
                continue
            
            # Stage 1: Analyze short buffer with Flash-Lite
            short_buffer_frames = video_config['short_buffer_duration'] * video_config['analysis_fps']
            recent_frames = list(source_buffer)[-short_buffer_frames:] if len(source_buffer) >= short_buffer_frames else list(source_buffer)
            
            if not recent_frames:
                results['sources'][source_id] = {
                    'error': 'Insufficient frames',
                    'has_security_incident': False
                }
                continue
            
            # Sample frames for Gemini to avoid API limits (25 frames)
            # Full buffer will still be used for video creation
            frames_for_analysis = recent_frames[-25:] if len(recent_frames) > 25 else recent_frames
            source_name = recent_frames[-1].get('source_name', source_id)
            
            logger.info(f"🎥 Flash-Lite analyzing {len(frames_for_analysis)} frames as SHORT VIDEO for source '{source_name}'")
            
            analysis_result = analyze_short_video_for_security(
                frames_for_analysis,
                "short"
            )
            
            if not analysis_result:
                results['sources'][source_id] = {
                    'error': 'Analysis failed',
                    'has_security_incident': False
                }
                continue
            
            # Add source metadata
            analysis_result['source_name'] = source_name
            analysis_result['buffer_size'] = len(source_buffer)
            
            # Stage 2: If incident detected, confirm with Flash (long buffer)
            if analysis_result['has_security_incident']:
                total_incidents_detected += 1
                logger.warning(f"🚨 INCIDENT DETECTED by Flash-Lite for source '{source_name}' (client: {request.current_client.name})")
                logger.warning(f"   Triggering Gemini 2.5 Flash (long buffer) for confirmation...")
                
                # Get long buffer for detailed analysis
                long_buffer_frames = video_config['long_buffer_duration'] * video_config['analysis_fps']
                incident_frames = list(source_buffer)[-long_buffer_frames:] if len(source_buffer) >= long_buffer_frames else list(source_buffer)
                
                # Perform detailed analysis with Flash
                detailed_analysis = analyze_incident_context(incident_frames)
                
                if detailed_analysis:
                    incident_confirmed = detailed_analysis.get('incident_confirmed', False)
                    
                    if incident_confirmed:
                        total_incidents_confirmed += 1
                        logger.warning(f"✅ INCIDENT CONFIRMED by Flash for source '{source_name}'")
                        logger.warning(f"   Confirmation: {detailed_analysis['confirmation_count']}/{detailed_analysis['total_frames_analyzed']} frames")
                        analysis_result['detailed_analysis'] = detailed_analysis['frames']
                        analysis_result['incident_frames_count'] = len(incident_frames)
                        analysis_result['flash_confirmation'] = True
                        analysis_result['incident_frames'] = incident_frames  # Include frames for video creation
                    else:
                        logger.warning(f"❌ INCIDENT REJECTED by Flash for source '{source_name}'")
                        logger.warning(f"   Flash found no issues (0/{detailed_analysis['total_frames_analyzed']} frames)")
                        # Flash vetoes the incident
                        analysis_result['has_security_incident'] = False
                        analysis_result['detailed_analysis'] = detailed_analysis['frames']
                        analysis_result['incident_frames_count'] = len(incident_frames)
                        analysis_result['flash_confirmation'] = False
                        analysis_result['flash_veto'] = True
                        analysis_result['veto_reason'] = 'Gemini 2.5 Flash did not confirm incident'
                else:
                    # Fallback to Flash-Lite decision if Flash analysis fails
                    logger.warning(f"⚠️  Long buffer analysis failed for source '{source_name}', using Flash-Lite decision")
                    analysis_result['detailed_analysis'] = None
                    analysis_result['incident_frames_count'] = len(incident_frames)
                    analysis_result['flash_confirmation'] = None
                    analysis_result['incident_frames'] = incident_frames
            
            results['sources'][source_id] = analysis_result
        
        # Add summary
        results['summary'] = {
            'total_incidents_detected_by_flash_lite': total_incidents_detected,
            'total_incidents_confirmed_by_flash': total_incidents_confirmed,
            'total_incidents_vetoed': total_incidents_detected - total_incidents_confirmed,
            'has_any_confirmed_incident': total_incidents_confirmed > 0
        }
        
        # Calculate cost and log usage
        processing_time = time.time() - start_time
        cost = 0.01 * len(source_ids) + (processing_time * 0.001)
        
        log_api_usage(
            api_key_id=request.current_api_key.id,
            endpoint='/api/video/multi-source/analyze',
            method='POST',
            status_code=200,
            cost=cost
        )
        
        logger.info(f"Multi-source analysis completed for {len(source_ids)} sources")
        logger.info(f"   Detected: {total_incidents_detected}, Confirmed: {total_incidents_confirmed}")
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error in multi-source analysis: {e}")
        return jsonify({'error': 'Multi-source analysis failed'}), 500


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
    """Analyze longer buffer for detailed incident context and confirm/reject incident using VIDEO analysis"""
    if not frames or not gemini_model_long:
        return None
    
    try:
        # Analyze FULL 10-second video for detailed confirmation
        # This is the LONG BUFFER analysis with complete temporal context
        duration_seconds = len(frames) / 25.0
        logger.info(f"📹 Flash 2.5 analyzing {len(frames)} frames as LONG VIDEO sequence (~{duration_seconds:.1f}s)")
        
        # Build prompt for VIDEO analysis
        prompt = f"""
        Analyze this COMPLETE VIDEO SEQUENCE ({len(frames)} frames, ~{duration_seconds:.1f} seconds from security video) for retail security incidents.
        
        IMPORTANT: This is a VIDEO showing behavior over time. Look for MOVEMENT and BEHAVIOR PATTERNS.
        
        Focus on:
        1. Customers concealing merchandise (watch their MOVEMENTS throughout the sequence)
        2. Suspicious handling of items (track HOW they interact over time)
        3. Groups working together (observe COORDINATION)
        4. Removing security tags or packaging (watch the SEQUENCE of actions)
        5. Taking items and leaving without payment (follow the PROGRESSION)
        
        Analyze the entire sequence to understand the full context and behavior patterns.
        A single suspicious pose is NOT enough - you must see SUSPICIOUS BEHAVIOR OVER TIME.
        
        Return ONLY a JSON object:
        {{"incident_detected": boolean, "incident_type": string, "description": string, "analysis": string}}
        
        Answer in French.
        """
        
        # Prepare video frames for Gemini
        video_parts = [prompt]
        for frame_info in frames:
            video_parts.append({"mime_type": "image/jpeg", "data": frame_info['frame_data']})
        
        logger.info(f"🎬 Sending {len(frames)} frames to Gemini Flash for VIDEO analysis...")
        response = gemini_model_long.generate_content(video_parts)
        
        # Parse JSON response
        incident_detected = False
        try:
            import json
            response_text = response.text.strip()
            
            # Handle JSON wrapped in markdown code blocks
            if response_text.startswith('```json'):
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    response_text = response_text[start_idx:end_idx]
            
            analysis_json = json.loads(response_text)
            analysis_text = analysis_json.get('analysis', response.text)
            incident_type = analysis_json.get('incident_type', '')
            incident_detected = analysis_json.get('incident_detected', False)
        except (json.JSONDecodeError, KeyError):
            analysis_text = response.text
            incident_type = ''
            
            # Try to extract incident_type and incident_detected from text
            if '"incident_type":' in response.text.lower():
                import re
                match = re.search(r'"incident_type":\s*"([^"]*)"', response.text)
                if match:
                    incident_type = match.group(1)
            
            # Check for incident_detected in text
            if 'incident_detected": true' in response.text.lower():
                incident_detected = True
        
        # Build analysis summary for the entire video
        context_analysis = [{
            'frame_position': 'Complete Video Sequence',
            'frame_count': len(frames),
            'analysis': analysis_text,
            'incident_type': incident_type,
            'incident_detected': incident_detected
        }]
        
        logger.info(f"✅ COMPLETE VIDEO analysis ({len(frames)} frames, ~{len(frames)/25:.1f}s): incident_detected={incident_detected}")
        
        # Return analysis with confirmation status
        return {
            'frames': context_analysis,
            'incident_confirmed': incident_detected,
            'confirmation_count': 1 if incident_detected else 0,
            'total_frames_analyzed': len(frames),
            'video_duration_seconds': len(frames) / 25,
            'video_analysis': True
        }
        
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
            missing = []
            if not email_config['username']:
                missing.append('EMAIL_USERNAME')
            if not email_config['to_email']:
                missing.append('EMAIL_TO')
            error_msg = f"Email not configured - Missing: {', '.join(missing)}"
            logger.error(f"❌ {error_msg}")
            return jsonify({'error': error_msg}), 503
        
        # Get alert data from request
        data = request.get_json()
        if not data or 'analysis' not in data:
            return jsonify({'error': 'Missing analysis data'}), 400
        
        analysis_text = data['analysis']
        frame_count = data.get('frame_count', 0)
        risk_level = data.get('risk_level', 'MEDIUM')
        detailed_analysis = data.get('detailed_analysis', None)
        incident_frames_count = data.get('incident_frames_count', 0)
        incident_type = data.get('incident_type', '')
        
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
                    'frame_count': frame_count,
                    'incident_type': incident_type
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
        
        # Create subject with incident type if available (in French)
        subject = f"🚨 Alerte Sécurité Vigint [{risk_level}]"
        if incident_type:
            subject = f"🚨 Alerte Vigint - {incident_type} - [{risk_level}]"
        subject += f" - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        msg['Subject'] = subject
        
        # Create simplified email body in French (will be finalized after video attachment)
        incident_timestamp = datetime.now()
        
        # Build email body
        body = f"""
🚨 ALERTE SÉCURITÉ VIGINT

Client: {request.current_client.name}
Heure: {incident_timestamp.strftime('%H:%M:%S - %d/%m/%Y')} UTC
Type d'incident: {incident_type if incident_type else 'Non spécifié'}

ANALYSE:
{analysis_text}

Ceci est une alerte automatique du système de sécurité Vigint.
"""
        
        # Store video and generate shareable link using existing video system
        video_link_info = None
        video_link_error = None
        
        if video_path and os.path.exists(video_path):
            try:
                import hashlib
                import json
                
                # Generate unique video ID
                video_id = str(uuid.uuid4())
                
                # Set expiration (48 hours for security incidents)
                expiration_time = datetime.now() + timedelta(hours=48)
                
                # Re-encode video to H264 for browser compatibility using ffmpeg
                video_filename = f"video_{video_id}.mp4"
                permanent_path = os.path.join(VIDEO_STORAGE_DIR, video_filename)
                
                # Try to re-encode with ffmpeg for browser compatibility
                try:
                    import subprocess
                    
                    # Get ffmpeg binary from imageio-ffmpeg package
                    try:
                        from imageio_ffmpeg import get_ffmpeg_exe
                        ffmpeg_bin = get_ffmpeg_exe()
                        logger.info(f"Using imageio-ffmpeg binary: {ffmpeg_bin}")
                    except ImportError:
                        # Fall back to system ffmpeg
                        ffmpeg_bin = 'ffmpeg'
                        logger.info("Using system ffmpeg")
                    
                    # Use ffmpeg to convert mp4v to H264 (browser-compatible)
                    result = subprocess.run([
                        ffmpeg_bin, '-i', video_path,
                        '-c:v', 'libx264',  # H264 codec
                        '-preset', 'fast',   # Fast encoding
                        '-crf', '23',        # Good quality
                        '-c:a', 'aac',       # Audio codec (if any)
                        '-y',                # Overwrite output
                        permanent_path
                    ], capture_output=True, timeout=30)
                    
                    if result.returncode == 0:
                        logger.info(f"Video re-encoded to H264 using ffmpeg for browser compatibility")
                    else:
                        # Ffmpeg failed, fall back to direct copy
                        logger.warning(f"FFmpeg encoding failed, using original mp4v: {result.stderr.decode()[:200]}")
                        shutil.copy2(video_path, permanent_path)
                except (FileNotFoundError, subprocess.TimeoutExpired) as e:
                    # Ffmpeg not available or timeout, fall back to direct copy
                    logger.warning(f"FFmpeg not available ({e}), using original video format")
                    shutil.copy2(video_path, permanent_path)
                
                # Save metadata
                metadata = {
                    'video_id': video_id,
                    'client_id': request.current_client.id,
                    'client_name': request.current_client.name,
                    'incident_type': incident_type,
                    'risk_level': risk_level,
                    'created': datetime.now().isoformat(),
                    'expiration_time': expiration_time.isoformat(),
                    'size_mb': os.path.getsize(permanent_path) / (1024 * 1024)
                }
                
                metadata_filename = f"video_{video_id}.json"
                metadata_path = os.path.join(VIDEO_STORAGE_DIR, metadata_filename)
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                # Generate token for secure access
                token_key = os.environ.get('SPARSE_AI_API_KEY') or config.secret_key
                token_data = f"{video_id}:{expiration_time.isoformat()}:{token_key}"
                token = hashlib.sha256(token_data.encode()).hexdigest()[:32]
                
                # Generate public link
                server_url = os.getenv('RENDER_EXTERNAL_URL', 'https://vigint.onrender.com')
                video_url = f"{server_url}/video/{video_id}?token={token}"
                
                video_size = os.path.getsize(permanent_path) / (1024 * 1024)  # Size in MB
                
                # Add video link to email body
                body += f"""

📹 PREUVES VIDÉO DISPONIBLES
Lien vidéo sécurisé: {video_url}
Taille du fichier: {video_size:.1f} MB
Expiration: {expiration_time.strftime('%Y-%m-%d %H:%M:%S')} UTC (48 heures)
ID Vidéo: {video_id}

⚠️ IMPORTANT: Ce lien est sécurisé et expirera automatiquement dans 48 heures.
Cliquez sur le lien pour visualiser la vidéo de l'incident dans votre navigateur.
"""
                
                video_link_info = {
                    'success': True,
                    'video_id': video_id,
                    'video_url': video_url,
                    'expiration_time': expiration_time.isoformat(),
                    'size_mb': video_size
                }
                
                logger.info(f"Video stored and link generated: {video_id} ({video_size:.1f} MB)")
                    
            except Exception as e:
                video_link_error = str(e)
                logger.error(f"Error storing video: {e}")
                body += f"""

⚠️ Erreur lors de la création du lien vidéo
Erreur technique: {video_link_error}
La vidéo n'est pas disponible en ligne.
"""
        else:
            # Video path doesn't exist - already handled in body above
            pass
        
        # Attach the final body text to the message
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email with robust error handling and retry mechanisms
        email_result = send_email_with_retry(msg, video_link_info is not None, video_link_error)
        
        # Handle email delivery results
        if email_result['success']:
            if email_result.get('fallback_used', False):
                logger.warning(f"Security alert sent using fallback method for client {request.current_client.name}")
            else:
                logger.info(f"Security alert sent successfully for client {request.current_client.name}")
        else:
            logger.error(f"Failed to send security alert for client {request.current_client.name}: {email_result.get('last_error', 'Unknown error')}")
        
        # Clean up temporary video file after upload
        if video_path:
            cleanup_success = cleanup_temp_file(video_path)
            if cleanup_success:
                logger.info("Temporary video file cleaned up securely after upload")
            else:
                logger.warning("Failed to clean up temporary video file after upload")
        
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
            'success': email_result['success'],  # Add success field for client compatibility
            'error': email_result.get('last_error') if not email_result['success'] else None,  # Add error field for client
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
            'video_link': {
                'available': video_link_info is not None,
                'video_url': video_link_info.get('video_url') if video_link_info else None,
                'video_id': video_link_info.get('video_id') if video_link_info else None,
                'expiration_time': video_link_info.get('expiration_time') if video_link_info else None,
                'error': video_link_error,
                'metadata': video_metadata,
                'quality_rating': "High" if video_metadata and video_metadata.get('failed_frames', 0) == 0 else "Good" if video_metadata and video_metadata.get('failed_frames', 0) < 5 else "Fair",
                'file_size_mb': os.path.getsize(video_path) / (1024*1024) if video_path and os.path.exists(video_path) else 0
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
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': f'Failed to send alert: {str(e)}'}), 500


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


@app.route('/api/video/compress', methods=['POST'])
@require_api_key_flexible
def compress_video_api():
    """API endpoint for video compression"""
    try:
        data = request.get_json()
        
        if not data or 'video_data' not in data:
            return jsonify({'error': 'Missing video_data'}), 400
        
        # Decode video data
        video_data = base64.b64decode(data['video_data'])
        filename = data.get('filename', 'video.mp4')
        max_size_mb = data.get('max_size_mb', 20)
        quality_reduction = data.get('quality_reduction', 0.85)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            tmp_file.write(video_data)
            input_path = tmp_file.name
        
        try:
            # Compress video
            result = compress_video_for_email(input_path, max_size_mb, quality_reduction)
            
            if result.get('success') and result.get('compressed_path'):
                # Read compressed video
                with open(result['compressed_path'], 'rb') as f:
                    compressed_data = base64.b64encode(f.read()).decode('utf-8')
                
                # Clean up
                os.unlink(result['compressed_path'])
                
                return jsonify({
                    'success': True,
                    'video_data': compressed_data,
                    'original_size': result.get('original_size'),
                    'compressed_size': result.get('compressed_size'),
                    'compression_ratio': result.get('compression_ratio')
                })
            else:
                return jsonify({'success': False, 'error': result.get('error')}), 500
                
        finally:
            # Clean up input file
            if os.path.exists(input_path):
                os.unlink(input_path)
        
    except Exception as e:
        logger.error(f"Error compressing video: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/video/create', methods=['POST'])
@require_api_key_flexible
def create_video_api():
    """API endpoint for creating video from frames"""
    try:
        data = request.get_json()
        
        if not data or 'frames' not in data:
            return jsonify({'error': 'Missing frames data'}), 400
        
        frames_data = data['frames']
        output_filename = data.get('output_filename', 'output.mp4')
        fps = data.get('fps')
        video_format = data.get('video_format')
        
        # Decode frames
        frames = []
        for frame_b64 in frames_data:
            frame_bytes = base64.b64decode(frame_b64)
            # Convert to numpy array
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is not None:
                frames.append(frame)
        
        if not frames:
            return jsonify({'error': 'No valid frames decoded'}), 400
        
        # Create temporary output path
        output_path = os.path.join(tempfile.gettempdir(), output_filename)
        
        # Create video
        result = create_video_from_frames(frames, output_path, fps, video_format)
        
        if result.get('success'):
            # Read created video
            with open(output_path, 'rb') as f:
                video_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Store video temporarily for download
            download_id = os.urandom(16).hex()
            download_path = os.path.join(tempfile.gettempdir(), f'download_{download_id}.mp4')
            os.rename(output_path, download_path)
            
            return jsonify({
                'success': True,
                'video_data': video_data,
                'download_url': f'/api/video/download/{download_id}',
                'frames_processed': result.get('frames_processed'),
                'duration': result.get('duration')
            })
        else:
            return jsonify({'success': False, 'error': result.get('error')}), 500
        
    except Exception as e:
        logger.error(f"Error creating video: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/video/download/<download_id>')
@require_api_key_flexible
def download_video(download_id):
    """Download a generated video"""
    try:
        download_path = os.path.join(tempfile.gettempdir(), f'download_{download_id}.mp4')
        
        if not os.path.exists(download_path):
            return jsonify({'error': 'Video not found or expired'}), 404
        
        # Send file and schedule deletion
        def cleanup_after_send():
            time.sleep(5)  # Give time for download to complete
            if os.path.exists(download_path):
                os.unlink(download_path)
        
        # Schedule cleanup in background
        threading.Thread(target=cleanup_after_send, daemon=True).start()
        
        return Response(
            open(download_path, 'rb').read(),
            mimetype='video/mp4',
            headers={'Content-Disposition': f'attachment; filename=video_{download_id}.mp4'}
        )
        
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return jsonify({'error': str(e)}), 500


def initialize_database():
    """Initialize database tables"""
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")


# ============================================================================
# VIDEO STORAGE SERVICE (Sparse AI integration)
# ============================================================================

# Video storage directory
VIDEO_STORAGE_DIR = os.environ.get('VIDEO_STORAGE_DIR', 
                                   os.path.join(tempfile.gettempdir(), 'video_uploads'))

if not os.path.exists(VIDEO_STORAGE_DIR):
    os.makedirs(VIDEO_STORAGE_DIR)
    logger.info(f"Created video storage directory: {VIDEO_STORAGE_DIR}")


def find_video_metadata(video_id):
    """Find the metadata file for a given video_id"""
    import json
    for filename in os.listdir(VIDEO_STORAGE_DIR):
        if filename.endswith('.json'):
            filepath = os.path.join(VIDEO_STORAGE_DIR, filename)
            try:
                with open(filepath, 'r') as f:
                    metadata = json.load(f)
                    if metadata.get('video_id') == video_id:
                        return metadata, os.path.splitext(filename)[0] + '.mp4'
            except (json.JSONDecodeError, IOError):
                continue
    return None, None


def validate_video_token(video_id, token):
    """Validate the access token for a video"""
    import hashlib
    from datetime import datetime
    
    metadata, video_filename = find_video_metadata(video_id)
    if not metadata:
        return False, "Video not found", None

    expiration_time_str = metadata.get('expiration_time')
    if not expiration_time_str:
        return False, "Expiration time not found", None

    expiration_time = datetime.fromisoformat(expiration_time_str)
    if datetime.now() > expiration_time:
        return False, "Link has expired", None

    # Recreate the token to validate it
    # Use either SPARSE_AI_API_KEY or SECRET_KEY for compatibility
    api_key = os.environ.get('SPARSE_AI_API_KEY') or config.secret_key
    token_data = f"{video_id}:{expiration_time.isoformat()}:{api_key}"
    expected_token = hashlib.sha256(token_data.encode()).hexdigest()[:32]

    if token == expected_token:
        return True, "Valid token", video_filename
    else:
        return False, "Invalid token", None


@app.route('/video/<video_id>')
def serve_video_with_token(video_id):
    """Serve a video file after validating the token (Sparse AI compatible)"""
    from flask import abort, send_file
    
    token = request.args.get('token')
    if not token:
        abort(401, description="Access token is missing.")

    is_valid, message, video_filename = validate_video_token(video_id, token)
    if not is_valid:
        abort(403, description=message)

    video_path = os.path.join(VIDEO_STORAGE_DIR, video_filename)
    if not os.path.exists(video_path):
        abort(404, description="Video file not found on server.")

    # Serve video with proper headers for browser playback
    return send_file(
        video_path,
        mimetype='video/mp4',
        as_attachment=False,
        download_name=video_filename,
        conditional=True  # Enable range requests for video seeking
    )


@app.route('/api/v1/videos/upload', methods=['POST'])
def upload_video_sparse_ai():
    """Handle video uploads (Sparse AI compatible endpoint)"""
    import json
    import hashlib
    from datetime import timedelta
    
    # Support both Bearer token and X-API-Key authentication
    auth_header = request.headers.get('Authorization')
    api_key = None
    
    if auth_header and auth_header.startswith('Bearer '):
        api_key = auth_header.split(' ')[1]
    elif request.headers.get('X-API-Key'):
        api_key = request.headers.get('X-API-Key')
    
    if not api_key:
        return jsonify({"error": "Authorization header missing"}), 401
    
    # Validate API key - accept either SPARSE_AI_API_KEY or SECRET_KEY
    valid_keys = [
        os.environ.get('SPARSE_AI_API_KEY'),
        config.secret_key
    ]
    
    if api_key not in [k for k in valid_keys if k]:
        return jsonify({"error": "Invalid API key"}), 403

    if 'video' not in request.files:
        return jsonify({"error": "No video file part"}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    metadata_str = request.form.get('metadata', '{}')
    try:
        metadata = json.loads(metadata_str)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid metadata"}), 400

    video_id = metadata.get('video_id')
    if not video_id:
        return jsonify({"error": "video_id missing from metadata"}), 400

    # Use expiration from request or default to 30 days
    expiration_hours = int(request.form.get('expiration_hours', 720))  # 30 days default
    expiration_time = datetime.now() + timedelta(hours=expiration_hours)
    metadata['expiration_time'] = expiration_time.isoformat()

    # Save the video file
    video_filename = f"video_{video_id}.mp4"
    video_path = os.path.join(VIDEO_STORAGE_DIR, video_filename)
    file.save(video_path)

    # Save the metadata file
    metadata_filename = f"video_{video_id}.json"
    metadata_path = os.path.join(VIDEO_STORAGE_DIR, metadata_filename)
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    # Generate the private link
    # Use SPARSE_AI_API_KEY if available for token generation, otherwise SECRET_KEY
    token_key = os.environ.get('SPARSE_AI_API_KEY') or config.secret_key
    token_data = f"{video_id}:{expiration_time.isoformat()}:{token_key}"
    token = hashlib.sha256(token_data.encode()).hexdigest()[:32]
    
    # Use HTTPS for production
    base_url = request.host_url
    if os.environ.get('RENDER'):
        base_url = base_url.replace('http://', 'https://')
    
    private_link = f"{base_url}video/{video_id}?token={token}"

    logger.info(f"Video uploaded successfully: {video_id}")
    
    return jsonify({
        "success": True,
        "video_id": video_id,
        "private_link": private_link,
        "expiration_time": expiration_time.isoformat(),
        "message": "Video uploaded successfully"
    }), 200


# ============================================================================
# ADMIN ENDPOINTS - For managing clients on server
# ============================================================================

def require_admin_key(f):
    """Decorator to require admin key authentication"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_key = request.headers.get('X-Admin-Key')
        if not admin_key:
            return jsonify({'error': 'Admin key required'}), 401
        
        # Admin key is the SECRET_KEY itself
        if admin_key != config.secret_key:
            return jsonify({'error': 'Invalid admin key'}), 401
        
        return f(*args, **kwargs)
    return decorated_function


@app.route('/admin/clients', methods=['GET'])
@require_admin_key
def admin_list_clients():
    """List all clients (admin only)"""
    try:
        from vigint.models import Client, APIKey
        clients = Client.query.all()
        
        result = []
        for client in clients:
            api_keys = APIKey.query.filter_by(client_id=client.id).all()
            result.append({
                'id': client.id,
                'name': client.name,
                'email': client.email,
                'created_at': client.created_at.isoformat(),
                'api_keys': [{
                    'id': key.id,
                    'is_active': key.is_active,
                    'name': key.name,
                    'created_at': key.created_at.isoformat()
                } for key in api_keys]
            })
        
        return jsonify({
            'clients': result,
            'count': len(result)
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to list clients: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/clients', methods=['POST'])
@require_admin_key
def admin_create_client():
    """Create a new client (admin only)"""
    try:
        from auth import create_client_with_api_key
        
        data = request.json
        if not data or 'name' not in data or 'email' not in data:
            return jsonify({'error': 'name and email required'}), 400
        
        client, api_key = create_client_with_api_key(
            name=data['name'],
            email=data['email']
        )
        
        return jsonify({
            'success': True,
            'client_id': client.id,
            'name': client.name,
            'email': client.email,
            'api_key': api_key,
            'warning': 'Save this API key! It cannot be retrieved later.'
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to create client: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/clients/<int:client_id>/revoke', methods=['POST'])
@require_admin_key
def admin_revoke_client(client_id):
    """Revoke all API keys for a client (admin only)"""
    try:
        from vigint.models import Client, APIKey
        from auth import revoke_api_key
        
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': f'Client {client_id} not found'}), 404
        
        api_keys = APIKey.query.filter_by(client_id=client_id, is_active=True).all()
        
        if not api_keys:
            return jsonify({
                'message': f'Client {client.name} has no active API keys',
                'revoked_count': 0
            }), 200
        
        revoked_count = 0
        for api_key in api_keys:
            if revoke_api_key(api_key.id):
                revoked_count += 1
        
        return jsonify({
            'success': True,
            'client_id': client_id,
            'client_name': client.name,
            'revoked_count': revoked_count,
            'message': f'Revoked {revoked_count} API key(s) for {client.name}'
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to revoke client: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/clients/<int:client_id>/reactivate', methods=['POST'])
@require_admin_key
def admin_reactivate_client(client_id):
    """Reactivate revoked API keys for a client (admin only)"""
    try:
        from vigint.models import Client, APIKey
        
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': f'Client {client_id} not found'}), 404
        
        revoked_keys = APIKey.query.filter_by(client_id=client_id, is_active=False).all()
        
        if not revoked_keys:
            return jsonify({
                'message': f'Client {client.name} has no revoked API keys',
                'reactivated_count': 0
            }), 200
        
        for key in revoked_keys:
            key.is_active = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'client_id': client_id,
            'client_name': client.name,
            'reactivated_count': len(revoked_keys),
            'message': f'Reactivated {len(revoked_keys)} API key(s) for {client.name}'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to reactivate client: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Initialize database
    initialize_database()
    
    # Use PORT environment variable for cloud deployments (Render, Heroku, etc.)
    port = int(os.environ.get('PORT', config.port))
    host = os.environ.get('HOST', config.host)
    
    app.run(
        host=host,
        port=port,
        debug=config.debug
    )