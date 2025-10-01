"""
Simple Video Analyzer using OpenCV and Gemini AI
Processes RTSP video streams and analyzes frames for security incidents
"""

import os
import sys
import cv2
import base64
import logging
import threading
from datetime import datetime
from pathlib import Path
import time
import hashlib
import json
from config import config

# Optional Gemini AI import (guarded)
try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except Exception:
    genai = None  # type: ignore
    _GENAI_AVAILABLE = False

_GLOBAL_INCIDENT_CACHE = {}
_CACHE_FILE = os.path.join(os.getcwd(), '.incident_cache.json')

# Import email modules with fallback
EMAIL_AVAILABLE = False
try:
    import smtplib
    from email.mime.text import MIMEText as MimeText
    from email.mime.multipart import MIMEMultipart as MimeMultipart
    EMAIL_AVAILABLE = True
    print("✅ Email functionality loaded successfully")
except Exception as e:
    print(f"❌ Email functionality not available: {e}")
    # Create dummy classes for fallback
    class MimeText:
        def __init__(self, *args, **kwargs): pass
    class MimeMultipart:
        def __init__(self, *args, **kwargs): pass
        def attach(self, *args): pass
        def __setitem__(self, key, value): pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _load_incident_cache():
    """Load incident cache from disk to persist across restarts"""
    global _GLOBAL_INCIDENT_CACHE
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                # Clean up expired entries (older than 24 hours)
                current_time = time.time()
                _GLOBAL_INCIDENT_CACHE = {
                    k: v for k, v in cache_data.items()
                    if current_time - v.get('timestamp', 0) < 86400  # 24 hours
                }
                logger.info(f"Loaded {len(_GLOBAL_INCIDENT_CACHE)} cached incidents")
    except Exception as e:
        logger.warning(f"Could not load incident cache: {e}")
        _GLOBAL_INCIDENT_CACHE = {}


def _save_incident_cache():
    """Save incident cache to disk"""
    try:
        with open(_CACHE_FILE, 'w') as f:
            json.dump(_GLOBAL_INCIDENT_CACHE, f)
    except Exception as e:
        logger.warning(f"Could not save incident cache: {e}")


def _get_frame_hash(frame):
    """
    Create perceptual hash of frame for visual similarity matching
    Uses very low resolution (4x4) to group similar scenes together
    This tolerates movement, lighting changes, and timing differences
    """
    try:
        import cv2
        import numpy as np
        
        # Validate frame
        if frame is None or not isinstance(frame, np.ndarray):
            logger.error(f"Invalid frame for hashing: type={type(frame)}")
            raise ValueError("Invalid frame")
        
        # VERY low resolution to group similar scenes (4x4 = 16 pixels total)
        # This makes hash very tolerant of movement, position changes, etc.
        small = cv2.resize(frame, (4, 4), interpolation=cv2.INTER_AREA)
        
        # Convert to grayscale
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        
        # Compute average
        avg = gray.mean()
        
        # Create hash based on whether each pixel is above/below average
        # With only 16 pixels, this groups very similar scenes together
        hash_bits = (gray > avg).flatten()
        
        # Convert to hex string
        hash_bytes = np.packbits(hash_bits).tobytes()
        frame_hash = hashlib.md5(hash_bytes).hexdigest()
        
        logger.debug(f"Generated frame hash: {frame_hash[:8]}... (frame shape: {frame.shape}, 4x4 grid)")
        return frame_hash
        
    except Exception as e:
        logger.error(f"Failed to hash frame: {e}", exc_info=True)
        # Fallback to timestamp-based hash if frame processing fails
        fallback = hashlib.md5(str(time.time()).encode()).hexdigest()
        logger.warning(f"Using timestamp fallback hash: {fallback[:8]}...")
        return fallback


def _get_incident_hash(analysis_text, frame=None):
    """
    Create a unique hash for an incident
    Prioritizes visual frame hash over text to handle varying AI descriptions
    """
    if frame is not None:
        # Use visual frame hash (more reliable for same scene)
        return _get_frame_hash(frame)
    else:
        # Fallback to text-based hash
        content = analysis_text[:100].lower().strip()
        return hashlib.md5(content.encode()).hexdigest()


def _check_duplicate_global(incident_hash, cooldown_seconds=300):
    """
    Check if incident is duplicate using global cache
    Returns: (is_duplicate, time_since_last)
    """
    global _GLOBAL_INCIDENT_CACHE
    current_time = time.time()
    
    if incident_hash in _GLOBAL_INCIDENT_CACHE:
        last_time = _GLOBAL_INCIDENT_CACHE[incident_hash]['timestamp']
        time_since = current_time - last_time
        
        if time_since < cooldown_seconds:
            return True, time_since
    
    return False, None


def _register_incident_global(incident_hash, incident_type):
    """Register an incident in the global cache"""
    global _GLOBAL_INCIDENT_CACHE
    _GLOBAL_INCIDENT_CACHE[incident_hash] = {
        'timestamp': time.time(),
        'incident_type': incident_type
    }
    _save_incident_cache()


# Load cache on module import
_load_incident_cache()


class VideoAnalyzer:
    """Handles video stream processing and AI analysis"""
    
    def __init__(self):
        # Configure Gemini AI with fallback models
        self.gemini_api_key = os.getenv('GOOGLE_API_KEY')
        if self.gemini_api_key and _GENAI_AVAILABLE:
            genai.configure(
                api_key=self.gemini_api_key,
                transport='rest'
            )
            
            # Try different model versions with fallback (updated for 2025)
            model_versions = [
                'gemini-2.5-flash',
                'gemini-2.0-flash',
                'gemini-flash-latest',
                'gemini-pro-latest',
                'gemini-2.5-pro'
            ]
            
            self.model = None
            for model_name in model_versions:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    logger.info(f"Gemini AI configured successfully with model: {model_name}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to load model {model_name}: {e}")
                    continue
            
            if not self.model:
                logger.error("Failed to load any Gemini model")
        elif self.gemini_api_key and not _GENAI_AVAILABLE:
            logger.warning("Google Generative AI SDK not available; falling back to mock analysis")
            self.model = None
        else:
            logger.error("Gemini API key not found in environment variables")
            self.model = None
        
        # Email configuration
        self.email_config = {
            'smtp_server': config.get('Email', 'smtp_server', 'smtp.gmail.com'),
            'smtp_port': config.getint('Email', 'smtp_port', 587),
            'username': config.get('Email', 'username', ''),
            'password': config.get('Email', 'password', ''),
            'from_email': config.get('Email', 'from_email', ''),
            'to_email': config.get('Email', 'to_email', '')
        }
        
        self.frame_count = 0
        self.last_analysis_time = 0
        self.analysis_interval = 5  # Analyze every 5 seconds
        self.running = False
        
        # Incident deduplication tracking
        self.last_incident_time = 0
        self.incident_cooldown = 60  # Don't re-alert for 60 seconds after an incident
        self.last_incident_hash = None
        
        # Dual buffer system for smooth video creation
        from collections import deque
        
        # Configuration for buffer durations
        self.short_buffer_duration = 5   # seconds for monitoring
        self.long_buffer_duration = 15   # seconds for video evidence
        self.buffer_fps = 25             # target FPS for smooth video
        
        # Calculate buffer sizes
        max_frames = self.long_buffer_duration * self.buffer_fps  # 375 frames for 15 seconds
        
        # Continuous frame buffer - captures ALL frames for smooth video
        self.frame_buffer = deque(maxlen=max_frames)
        
        logger.info(f"📹 Dual buffer initialized:")
        logger.info(f"   - Continuous buffer: {self.long_buffer_duration}s ({max_frames} frames)")
        logger.info(f"   - Analysis interval: {self.analysis_interval}s")
        logger.info(f"   - Target FPS: {self.buffer_fps}")
        logger.info(f"🎬 This ensures smooth video regardless of analysis timing!")
    
    def analyze_frame(self, frame):
        """Analyze a video frame using Gemini AI with fallback"""
        if not self.model:
            return self._mock_analysis(frame)
        
        try:
            # Convert frame to base64 for Gemini API
            _, buffer_img = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer_img).decode('utf-8')
            
            # Prepare the prompt
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
            "incident_type": string,     // Describe the type of incident (e.g.: shoplifting, theft, vandalism)
            "confidence": float,         // confidence level between 0.0 and 1.0
            "description": string,       // brief description of what you see
            "analysis": string,          // detailed analysis of the video content}}
            
            Answer in French.
            """
            
            # Send to Gemini for analysis
            response = self.model.generate_content([
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
                incident_detected = analysis_json.get('incident_detected', False)
                incident_type = analysis_json.get('incident_type', '')
                analysis_text = analysis_json.get('analysis', response.text)
            except (json.JSONDecodeError, KeyError):
                # Fallback to text parsing
                analysis_text = response.text
                response_text_lower = response.text.lower()
                incident_detected = 'incident_detected": true' in response_text_lower
                
                # Try to extract incident_type from text
                incident_type = ''
                if '"incident_type":' in response_text_lower:
                    try:
                        import re
                        match = re.search(r'"incident_type":\s*"([^"]*)"', response.text)
                        if match:
                            incident_type = match.group(1)
                    except Exception:
                        pass
            
            analysis_result = {
                'timestamp': datetime.now().isoformat(),
                'frame_count': self.frame_count,
                'analysis': analysis_text,
                'incident_detected': incident_detected,
                'incident_type': incident_type,
                'frame_shape': frame.shape
            }
            
            logger.info(f"Frame {self.frame_count} analyzed")
            logger.info(f"Analysis: {response.text[:200]}...")
            
            return analysis_result
            
        except Exception as e:
            # Only log the first few API errors to avoid spam
            if not hasattr(self, '_api_error_count'):
                self._api_error_count = 0
            
            self._api_error_count += 1
            if self._api_error_count <= 3:
                logger.error(f"Error analyzing frame {self.frame_count}: {e}")
                if self._api_error_count == 3:
                    logger.info("🎭 Switching to mock analysis mode due to API issues")
            
            return self._mock_analysis(frame)
    
    def _mock_analysis(self, frame):
        """Mock analysis for when Gemini API is unavailable"""
        import random
        from datetime import datetime
        
        # Simulate incident detection occasionally (10% chance)
        incident_detected = random.random() < 0.1
        
        if incident_detected:
            incident_types = ['shoplifting', 'suspicious_behavior', 'unauthorized_access']
            incident_type = random.choice(incident_types)
        else:
            incident_type = ''
        
        return {
            'timestamp': datetime.now().isoformat(),
            'frame_count': self.frame_count,
            'analysis': f"Mock analysis of frame {self.frame_count} - {'Incident detected' if incident_detected else 'Normal activity'}",
            'incident_detected': incident_detected,
            'incident_type': incident_type,
            'confidence': random.uniform(0.7, 0.95) if incident_detected else random.uniform(0.1, 0.3),
            'frame_shape': frame.shape if frame is not None else (480, 640, 3)
        }
    
    def send_alert_email(self, analysis_result, video_frames=None):
        """Send email alert with analysis results and optional video"""
        if not EMAIL_AVAILABLE:
            logger.warning("Email functionality not available, logging alert instead")
            logger.warning(f"🚨 ALERTE SÉCURITÉ: {analysis_result['analysis']}")
            return False
            
        if not self.email_config['username'] or not self.email_config['to_email']:
            logger.warning("Email configuration incomplete, logging alert instead")
            logger.warning(f"🚨 ALERTE SÉCURITÉ: {analysis_result['analysis']}")
            return False
        
        try:
            # Import alerts module for video functionality
            from alerts import send_security_alert_with_video
            
            # Prepare incident data
            incident_data = {
                'risk_level': 'HIGH' if analysis_result.get('incident_detected', False) else 'MEDIUM',
                'frame_count': analysis_result.get('frame_count', 0),
                'confidence': analysis_result.get('confidence', 0.0),
                'analysis': analysis_result.get('analysis', ''),
                'incident_type': analysis_result.get('incident_type', '')
            }
            
            # Create alert message in French
            message = f"""
INCIDENT DE SÉCURITÉ DÉTECTÉ

Heure: {analysis_result['timestamp']}
Image: {analysis_result['frame_count']}
Incident détecté: {analysis_result.get('incident_detected', False)}
Type d'incident: {analysis_result.get('incident_type', 'Non spécifié')}

Ceci est une alerte automatique du système de sécurité Vigint.
Veuillez examiner immédiatement les preuves vidéo ci-jointes.
"""
            
            # Send alert with video if frames are available
            if video_frames:
                result = send_security_alert_with_video(message, video_frames, incident_data)
                logger.info("🚨 EMAIL D'ALERTE SÉCURITÉ AVEC VIDÉO ENVOYÉ!")
            else:
                # Fallback to basic email alert
                from alerts import AlertManager
                alert_manager = AlertManager()
                result = alert_manager.send_email_alert(message, "security", incident_data=incident_data)
                logger.info("🚨 EMAIL D'ALERTE SÉCURITÉ ENVOYÉ (sans vidéo)!")
            
            return result.get('success', False)
            
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            logger.warning(f"🚨 SECURITY ALERT (email failed): {analysis_result['analysis']}")
            return False
    
    def process_video_stream(self, rtsp_url):
        """Process video stream with dual buffer system - buffer BEFORE analysis"""
        logger.info(f"Connecting to RTSP stream: {rtsp_url}")
        
        # Open video capture
        cap = cv2.VideoCapture(rtsp_url)
        
        if not cap.isOpened():
            logger.error(f"Failed to open RTSP stream: {rtsp_url}")
            return False
        
        logger.info("Successfully connected to RTSP stream")
        logger.info("Starting dual-buffer video analysis...")
        logger.info(f"📹 Buffering ALL frames continuously for smooth video")
        logger.info(f"🔍 Analyzing frames every {self.analysis_interval} seconds")
        
        self.running = True
        
        try:
            while self.running:
                ret, frame = cap.read()
                
                if not ret:
                    # Check if this is a video file that has ended
                    if hasattr(cap, 'get') and cap.get(cv2.CAP_PROP_FRAME_COUNT) > 0:
                        # Video file ended, restart from beginning
                        logger.info("Video file ended, restarting from beginning...")
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        logger.warning("Failed to read frame from stream")
                        time.sleep(1)
                        continue
                
                self.frame_count += 1
                current_time = time.time()
                
                # CRITICAL: Add EVERY frame to buffer BEFORE analysis
                # This ensures smooth video regardless of analysis results
                self._add_frame_to_buffer(frame.copy())
                
                # Analyze frames periodically (not every frame)
                if current_time - self.last_analysis_time >= self.analysis_interval:
                    self.last_analysis_time = current_time
                    
                    # Analyze recent frames from buffer in separate thread
                    threading.Thread(
                        target=self._analyze_frames_async,
                        args=(),  # No frame argument - use buffer instead
                        daemon=True
                    ).start()
                
                # Small delay to prevent overwhelming the system
                time.sleep(0.04)  # ~25 FPS capture rate
        
        except KeyboardInterrupt:
            logger.info("Video analysis stopped by user")
        except Exception as e:
            logger.error(f"Error in video processing: {e}")
        finally:
            cap.release()
            self.running = False
            logger.info("Video capture released")
    
    def _add_frame_to_buffer(self, frame):
        """Add frame to buffer for video creation"""
        try:
            # Convert frame to base64 for storage
            _, buffer_img = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer_img).decode('utf-8')
            
            frame_info = {
                'frame_data': frame_base64,
                'frame_count': self.frame_count,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.frame_buffer.append(frame_info)
            
        except Exception as e:
            logger.error(f"Error adding frame to buffer: {e}")
    
    def _get_recent_frames(self, duration_seconds=5):
        """Get recent frames from buffer for video creation"""
        try:
            # Calculate number of frames needed
            frames_needed = duration_seconds * self.buffer_fps
            
            # Get the most recent frames
            if len(self.frame_buffer) >= frames_needed:
                return list(self.frame_buffer)[-frames_needed:]
            else:
                return list(self.frame_buffer)
                
        except Exception as e:
            logger.error(f"Error getting recent frames: {e}")
            return []
    
    def _analyze_frames_async(self):
        """Analyze recent frames from buffer in a separate thread"""
        try:
            logger.warning("⚡ Starting async frame analysis...")
            
            # Get the most recent frame for analysis
            if len(self.frame_buffer) == 0:
                logger.warning("No frames in buffer for analysis")
                return
            
            # Get the latest frame for AI analysis
            latest_frame_info = self.frame_buffer[-1]
            
            # Decode frame from base64
            import base64
            frame_data = base64.b64decode(latest_frame_info['frame_data'])
            import numpy as np
            frame_array = cv2.imdecode(
                np.frombuffer(frame_data, dtype=np.uint8), 
                cv2.IMREAD_COLOR
            )
            
            # Analyze the frame
            result = self.analyze_frame(frame_array)
            
            if result:
                # Check if alert should be sent based on incident detection
                if result.get('incident_detected', False):
                    logger.warning("🚨 POTENTIAL SECURITY EVENT DETECTED!")
                    logger.warning(f"Analysis: {result['analysis']}")
                    
                    try:
                        # GLOBAL deduplication using persistent cache with VISUAL frame hashing
                        # This prevents duplicates even if AI describes the scene differently
                        analysis_text = result.get('analysis', '')
                        incident_type = result.get('incident_type', 'unknown')
                        
                        logger.warning(f"🔍 Checking deduplication for incident type: {incident_type}")
                        
                        # Use VISUAL frame hash (not text) - same scene = same hash
                        incident_hash = _get_incident_hash(analysis_text, frame=frame_array)
                        logger.warning(f"   Generated visual hash: {incident_hash[:8]}...")
                        
                        # Use 5-minute cooldown for global cache (longer than local cooldown)
                        is_duplicate, time_since = _check_duplicate_global(incident_hash, cooldown_seconds=300)
                        logger.warning(f"   Duplicate check result: is_duplicate={is_duplicate}, time_since={time_since}")
                    except Exception as dedup_error:
                        logger.error(f"❌ Deduplication failed: {dedup_error}", exc_info=True)
                        # Continue without deduplication on error
                        is_duplicate = False
                        time_since = None
                    
                    if is_duplicate:
                        logger.warning(f"⏭️  Skipping GLOBAL duplicate incident (seen {time_since:.1f}s ago)")
                        logger.warning(f"   Visual Hash: {incident_hash[:8]}... | Type: {incident_type}")
                        logger.warning(f"   Same scene detected (AI may describe differently but visually identical)")
                        return
                    
                    # Also check local instance deduplication (backup check)
                    current_time = time.time()
                    incident_signature = f"{incident_type}_{analysis_text[:50]}"
                    
                    if (current_time - self.last_incident_time < self.incident_cooldown and 
                        self.last_incident_hash == incident_signature):
                        logger.info(f"⏭️  Skipping local duplicate incident alert (cooldown: {self.incident_cooldown}s)")
                        logger.info(f"   Time since last alert: {current_time - self.last_incident_time:.1f}s")
                        return
                    
                    # Register incident in global cache
                    _register_incident_global(incident_hash, incident_type)
                    
                    # Update local instance tracking
                    self.last_incident_time = current_time
                    self.last_incident_hash = incident_signature
                    
                    # Get ALL recent frames for smooth video evidence
                    video_frames = self._get_recent_frames(duration_seconds=10)
                    
                    logger.warning(f"📹 Creating video from {len(video_frames)} buffered frames")
                    logger.warning("🎬 Video will show continuous footage, not just analyzed frames")
                    logger.warning(f"📧 Sending NEW incident alert (visual hash cached: {incident_hash[:8]}...)")
                    logger.warning(f"   Cooldowns: Local {self.incident_cooldown}s | Global 300s (visual deduplication)")
                    
                    # Send alert email with video
                    self.send_alert_email(result, video_frames)
        
        except Exception as e:
            logger.error(f"Error in async frame analysis: {e}")
    
    def stop(self):
        """Stop video analysis"""
        self.running = False


def main():
    """Main function to start video analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Vigint Video Analyzer')
    parser.add_argument('--rtsp-url', type=str, required=True,
                       help='RTSP stream URL')
    parser.add_argument('--interval', type=int, default=5,
                       help='Analysis interval in seconds (default: 5)')
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = VideoAnalyzer()
    analyzer.analysis_interval = args.interval
    
    try:
        # Start video analysis
        analyzer.process_video_stream(args.rtsp_url)
    except KeyboardInterrupt:
        logger.info("Shutting down video analyzer...")
    finally:
        analyzer.stop()


if __name__ == '__main__':
    main()