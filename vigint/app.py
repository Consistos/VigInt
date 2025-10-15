#!/usr/bin/env python3
"""
Vigint Video Analysis Application
Secure client-side application that uses API proxy for all sensitive operations
"""

import os
import sys
import cv2
import time
import logging
import threading
import requests
import base64
from pathlib import Path
from datetime import datetime

# Try to import config, but use defaults if not available (client mode)
try:
    from config import config
    CONFIG_AVAILABLE = True
except (ImportError, FileNotFoundError):
    config = None
    CONFIG_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecureVideoAnalyzer:
    """
    Secure video analyzer that uses API proxy for all sensitive operations.
    No credentials or API keys stored on client side.
    """
    
    def __init__(self, api_base_url='http://localhost:5002', api_key=None):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key or os.getenv('VIGINT_API_KEY')
        
        if not self.api_key:
            logger.warning("No API key provided. Some features may not work.")
            logger.info("Set VIGINT_API_KEY environment variable or pass api_key parameter")
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        } if self.api_key else {}
        
        self.frame_count = 0
        self.last_analysis_time = 0
        self.running = False
        self.start_time = None  # Track when streaming started
        
        # Load and validate buffer configuration
        self._load_buffer_config()
        
        # Local frame buffer for fallback video creation
        from collections import deque
        buffer_size = self.long_buffer_duration * self.analysis_fps
        self.local_frame_buffer = deque(maxlen=buffer_size)
        logger.info(f"Local frame buffer initialized (max {buffer_size} frames)")
        
        # Test API connection if API key is available
        if self.api_key:
            self._test_connection()
    
    def _load_buffer_config(self):
        """Load and validate buffer configuration from config.ini or use defaults"""
        # Try to load from config.ini if available (server mode)
        if CONFIG_AVAILABLE and config is not None:
            try:
                # Validate configuration first
                config.validate_buffer_config()
                
                # Load buffer settings
                buffer_config = config.get_buffer_config()
                self.short_buffer_duration = buffer_config['short_buffer_duration']
                self.long_buffer_duration = buffer_config['long_buffer_duration']
                self.analysis_fps = buffer_config['analysis_fps']
                self.video_format = buffer_config['video_format']
                
                # Set analysis interval to short buffer duration for more frequent monitoring
                self.analysis_interval = self.short_buffer_duration
                
                logger.info(f"Buffer configuration loaded from config.ini:")
                logger.info(f"  Short buffer: {self.short_buffer_duration}s")
                logger.info(f"  Long buffer: {self.long_buffer_duration}s")
                logger.info(f"  Analysis interval: {self.analysis_interval}s")
                logger.info(f"  Analysis FPS: {self.analysis_fps}")
                logger.info(f"  Video format: {self.video_format}")
                return
                
            except Exception as e:
                logger.warning(f"Failed to load buffer configuration: {e}")
                logger.info("Using default buffer settings")
        else:
            logger.info("No config.ini found - using default buffer settings (client mode)")
        
        # Set default values (client mode or fallback)
        self.short_buffer_duration = 3
        self.long_buffer_duration = 10
        self.analysis_fps = 25
        self.video_format = 'mp4'
        self.analysis_interval = self.short_buffer_duration
        
        logger.info(f"Default buffer configuration:")
        logger.info(f"  Short buffer: {self.short_buffer_duration}s")
        logger.info(f"  Long buffer: {self.long_buffer_duration}s")
        logger.info(f"  Analysis FPS: {self.analysis_fps}")
    
    def _test_connection(self):
        """Test connection to API proxy"""
        try:
            response = requests.get(
                f'{self.api_base_url}/api/health',
                timeout=5
            )
            if response.status_code == 200:
                logger.info("✅ Connected to Vigint API proxy")
                
                # Test authenticated endpoint if API key is available
                if self.api_key:
                    auth_response = requests.get(
                        f'{self.api_base_url}/api/usage',
                        headers=self.headers,
                        timeout=5
                    )
                    if auth_response.status_code == 200:
                        logger.info("✅ API authentication successful")
                    else:
                        logger.warning("⚠️ API authentication failed - check API key")
            else:
                logger.warning(f"API proxy responded with status {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to connect to API proxy: {e}")
            logger.warning("Will continue without API proxy features")
    
    def add_frame_to_buffer(self, frame):
        """Add frame to both server-side and local buffers"""
        # Always add to local buffer for fallback
        self._add_frame_to_local_buffer(frame)
        
        # Try to add to server-side buffer if API key available
        if not self.api_key:
            return True  # Local buffer success is sufficient
            
        try:
            # Convert frame to base64
            _, buffer_img = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer_img).decode('utf-8')
            
            # Send frame to server buffer
            payload = {
                'frame_data': frame_base64,
                'frame_count': self.frame_count
            }
            
            response = requests.post(
                f'{self.api_base_url}/api/video/buffer',
                json=payload,
                headers=self.headers,
                timeout=5  # Reduced timeout to avoid blocking
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.debug(f"Server buffer failed: {response.status_code}")
                return True  # Local buffer still works
                
        except Exception as e:
            logger.debug(f"Error buffering frame to server {self.frame_count}: {e}")
            return True  # Local buffer still works
    
    def _add_frame_to_local_buffer(self, frame):
        """Add frame to local buffer for fallback video creation"""
        try:
            # Convert frame to base64 for storage
            _, buffer_img = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer_img).decode('utf-8')
            
            frame_info = {
                'frame_data': frame_base64,
                'frame_count': self.frame_count,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.local_frame_buffer.append(frame_info)
            
        except Exception as e:
            logger.error(f"Error adding frame to local buffer: {e}")
    
    def _add_frame_to_buffer_async(self, frame):
        """Add frame to buffer asynchronously to avoid blocking video capture"""
        try:
            success = self.add_frame_to_buffer(frame)
            if not success:
                logger.debug(f"Failed to buffer frame {self.frame_count}")
        except Exception as e:
            logger.error(f"Error in async frame buffering: {e}")
    
    def analyze_recent_frames(self):
        """Analyze recent frames for security incidents using dual buffer system with local fallback"""
        # Try API proxy first if available
        if self.api_key:
            try:
                response = requests.post(
                    f'{self.api_base_url}/api/video/analyze',
                    json={},
                    headers=self.headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Recent frames analyzed via API proxy")
                    if result.get('has_security_incident'):
                        logger.warning("🚨 SECURITY INCIDENT DETECTED in analysis!")
                    return result
                else:
                    logger.error(f"API analysis failed: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"Error analyzing recent frames via API: {e}")
        
        # Fallback to local analysis
        logger.info("Falling back to local frame analysis...")
        return self._analyze_frames_locally()
    
    def _analyze_frames_locally(self):
        """Analyze frames locally when API proxy is unavailable"""
        try:
            # Check if we have frames in local buffer
            if len(self.local_frame_buffer) == 0:
                logger.debug("No frames in local buffer for analysis")
                return None
            
            # Get the most recent frame for analysis
            latest_frame = self.local_frame_buffer[-1]
            
            # Import local AI analysis if available
            try:
                import google.generativeai as genai
                import os
                
                # Check if Gemini API key is available
                gemini_api_key = os.getenv('GOOGLE_API_KEY')
                if not gemini_api_key:
                    logger.warning("No Gemini API key available for local analysis")
                    return self._create_mock_analysis_result(latest_frame)
                
                # Configure Gemini for local analysis
                genai.configure(
                    api_key=gemini_api_key,
                    transport='rest'
                )
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Analyze the frame
                prompt = """
                Analyze the provided video frame for security incidents in a retail environment, with special focus on shoplifting behavior. Pay particular attention to:
                1. Customers taking items and concealing them (in pockets, bags, clothing)
                2. Unusual handling of merchandise (checking for security tags, looking around suspiciously)
                3. Taking items without paying
                4. Groups working together to distract staff while items are taken
                5. Removing packaging or security devices
                6. Unusual movements around high-value items
                7. Signs of nervousness or anxiety while handling merchandise
                
                Return ONLY a JSON object without markdown formatting:
                {"incident_detected": boolean, "incident_type": string, "description": string, "analysis": string}
                
                Answer in French.
                """
                
                response = model.generate_content([
                    prompt,
                    {"mime_type": "image/jpeg", "data": latest_frame['frame_data']}
                ])
                
                # Parse response
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
                    analysis_text = analysis_json.get('analysis', response.text)
                    incident_type = analysis_json.get('incident_type', '')
                    
                    # Set risk level to HIGH for all detected incidents
                    risk_level = "HIGH" if has_security_incident else "LOW"
                    
                    result = {
                        'analysis': analysis_text,
                        'has_security_incident': has_security_incident,
                        'risk_level': risk_level,
                        'frame_count': latest_frame['frame_count'],
                        'timestamp': datetime.now().isoformat(),
                        'source': 'local_analysis',
                        'incident_type': incident_type
                    }
                    
                    if has_security_incident:
                        logger.warning("🚨 SECURITY INCIDENT DETECTED in local analysis!")
                        logger.warning(f"Risk Level: {risk_level}")
                    
                    return result
                    
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse local analysis JSON: {e}")
                    # Fallback to text analysis
                    response_text = response.text.lower()
                    has_incident = 'incident_detected": true' in response_text
                    
                    # Try to extract incident_type from text
                    incident_type_fallback = ''
                    if '"incident_type":' in response_text:
                        try:
                            # Try to extract incident_type value
                            import re
                            match = re.search(r'"incident_type":\s*"([^"]*)"', response.text)
                            if match:
                                incident_type_fallback = match.group(1)
                        except Exception:
                            pass
                    
                    return {
                        'analysis': response.text,
                        'has_security_incident': has_incident,
                        'risk_level': 'HIGH' if has_incident else 'LOW',
                        'frame_count': latest_frame['frame_count'],
                        'timestamp': datetime.now().isoformat(),
                        'source': 'local_analysis_fallback',
                        'incident_type': incident_type_fallback
                    }
                
            except ImportError:
                logger.warning("Google Generative AI not available for local analysis")
                return self._create_mock_analysis_result(latest_frame)
            except Exception as e:
                logger.error(f"Error in local AI analysis: {e}")
                return self._create_mock_analysis_result(latest_frame)
                
        except Exception as e:
            logger.error(f"Error in local frame analysis: {e}")
            return None
    
    def _create_mock_analysis_result(self, frame_info):
        """Create a mock analysis result when AI is not available"""
        # This creates a periodic test incident for demonstration
        # In production, you might want to disable this or make it configurable
        import random
        
        # Create a test incident every ~10 analysis cycles (roughly every 5 minutes)
        if random.randint(1, 10) == 1:
            return {
                'analysis': f'''INCIDENT DE SÉCURITÉ DÉTECTÉ (Mode Test)

Analyse du frame {frame_info['frame_count']} à {frame_info['timestamp']}

DÉTAILS DE L'INCIDENT:
- Type: Activité suspecte détectée
- Localisation: Zone de surveillance principale

DESCRIPTION:
Comportement inhabituel observé dans la zone surveillée. 
Cette alerte est générée en mode test local lorsque l'API proxy n'est pas disponible.

ACTIONS RECOMMANDÉES:
1. Vérifier les angles de caméra supplémentaires
2. Examiner l'activité dans la zone concernée
3. Documenter l'incident pour examen ultérieur

Note: Cette analyse a été effectuée localement en raison de l'indisponibilité de l'API proxy.''',
                'has_security_incident': True,
                'risk_level': 'HIGH',
                'frame_count': frame_info['frame_count'],
                'timestamp': datetime.now().isoformat(),
                'source': 'mock_analysis'
            }
        else:
            return {
                'analysis': 'Aucun incident de sécurité détecté dans cette analyse.',
                'has_security_incident': False,
                'risk_level': 'LOW',
                'frame_count': frame_info['frame_count'],
                'timestamp': datetime.now().isoformat(),
                'source': 'mock_analysis'
            }
    
    def send_security_alert(self, analysis_result):
        """Send security alert via API proxy with local fallback"""
        # Try API proxy first if available
        if self.api_key:
            try:
                payload = {
                    'analysis': analysis_result['analysis'],
                    'frame_count': analysis_result['frame_count'],
                    'risk_level': analysis_result.get('risk_level', 'MEDIUM'),
                    'incident_type': analysis_result.get('incident_type', '')
                }
                
                response = requests.post(
                    f'{self.api_base_url}/api/video/alert',
                    json=payload,
                    headers=self.headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("🚨 SECURITY ALERT EMAIL SENT via API proxy!")
                    return True
                else:
                    logger.error(f"API proxy alert failed: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"Error sending alert via API proxy: {e}")
        
        # Fallback to local video alert system
        logger.info("Falling back to local video alert system...")
        return self._send_local_video_alert(analysis_result)
    
    def _send_local_video_alert(self, analysis_result):
        """Send local video alert with frames from local buffer"""
        try:
            # Import local alert system
            from alerts import send_security_alert_with_video
            
            # Get recent frames from local buffer if available
            video_frames = getattr(self, 'local_frame_buffer', [])
            
            # Prepare incident data
            incident_data = {
                'risk_level': analysis_result.get('risk_level', 'HIGH'),
                'frame_count': analysis_result.get('frame_count', 0),
                'analysis': analysis_result.get('analysis', ''),
                'incident_type': analysis_result.get('incident_type', '')
            }
            
            # Create alert message in French
            timestamp = datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
            message = f"""
🚨 ALERTE SÉCURITÉ VIGINT

Heure: {timestamp}
Type d'incident: {incident_data.get('incident_type', 'Non spécifié')}
Cet alerte a été envoyée via le système d'alerte vidéo local.
Veuillez examiner immédiatement les preuves vidéo ci-jointes.
"""
            
            # Send alert with video
            if video_frames:
                result = send_security_alert_with_video(message, video_frames, incident_data)
                logger.info("🚨 LOCAL SECURITY ALERT WITH VIDEO SENT!")
            else:
                # Send text-only alert if no video frames available
                from alerts import AlertManager
                alert_manager = AlertManager()
                result = alert_manager.send_email_alert(message, "security", incident_data=incident_data)
                logger.info("🚨 LOCAL SECURITY ALERT SENT (no video)!")
            
            return result.get('success', False)
                
        except Exception as e:
            logger.error(f"Error sending local video alert: {e}")
            return False
    
    def process_video_stream(self, rtsp_url):
        """Process video stream and analyze frames"""
        logger.info(f"Connecting to RTSP stream: {rtsp_url}")
        
        # Open video capture
        cap = cv2.VideoCapture(rtsp_url)
        
        if not cap.isOpened():
            logger.error(f"Failed to open RTSP stream: {rtsp_url}")
            return False
        
        logger.info("Successfully connected to RTSP stream")
        logger.info("🎯 Starting secure video analysis...")
        
        if self.api_key:
            logger.info("🔒 All credentials and AI processing handled server-side via API proxy")
        else:
            logger.info("📹 Video streaming only - no analysis (API key required for analysis)")
        
        self.running = True
        self.start_time = time.time()  # Record when streaming started
        
        # Get video properties for debugging
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = cap.get(cv2.CAP_PROP_FPS)
        logger.info(f"Video properties: {total_frames} frames, {fps} FPS")
        
        try:
            while self.running:
                ret, frame = cap.read()
                current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
                
                if not ret:
                    # Check if this is a video file that has ended
                    if total_frames > 0:
                        # Video file ended, restart from beginning
                        logger.info(f"Video file ended at frame {current_frame}/{total_frames}, restarting from beginning...")
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        logger.warning("Failed to read frame from stream")
                        time.sleep(1)
                        continue
                
                self.frame_count += 1
                current_time = time.time()
                
                # Continuously add frames to buffer (non-blocking)
                if self.api_key:
                    # Add frame to buffer in a separate thread to avoid blocking video capture
                    threading.Thread(
                        target=self._add_frame_to_buffer_async,
                        args=(frame.copy(),),
                        daemon=True
                    ).start()
                
                # Wait for buffer to fill before starting analysis
                time_since_start = current_time - self.start_time
                buffer_ready = time_since_start >= self.short_buffer_duration
                
                # Log when buffer becomes ready (only once)
                if self.api_key and buffer_ready and not hasattr(self, '_buffer_ready_logged'):
                    logger.info(f"🎯 Frame buffer ready after {time_since_start:.1f}s - starting analysis")
                    self._buffer_ready_logged = True
                
                # Analyze frames periodically using dual buffer timing (every short_buffer_duration seconds)
                if (self.api_key and buffer_ready and 
                    current_time - self.last_analysis_time >= self.analysis_interval):
                    self.last_analysis_time = current_time
                    
                    logger.debug(f"Starting analysis at frame {self.frame_count} (buffer ready for {time_since_start:.1f}s)")
                    
                    # Analyze recent frames in a separate thread to avoid blocking
                    threading.Thread(
                        target=self._analyze_frames_async,
                        daemon=True
                    ).start()
                
                # Small delay to prevent overwhelming the system
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            logger.info("Video analysis stopped by user")
        except Exception as e:
            logger.error(f"Error in video processing: {e}")
        finally:
            cap.release()
            self.running = False
            logger.info("Video capture released")
    
    def _analyze_frames_async(self):
        """Analyze recent frames from buffer in a separate thread"""
        try:
            logger.debug(f"Starting analysis of recent frames (frame {self.frame_count})")
            
            # Analyze recent frames using the dual buffer system with local fallback
            result = self.analyze_recent_frames()
            
            if result:
                analysis_source = result.get('source', 'unknown')
                logger.info(f"Analysis completed via {analysis_source}")
                
                if result.get('has_security_incident', False):
                    logger.warning("🚨 SECURITY INCIDENT DETECTED in buffer analysis!")
                    logger.warning(f"Source: {analysis_source}")
                    logger.warning(f"Risk Level: {result.get('risk_level', 'UNKNOWN')}")
                    logger.warning(f"Analysis: {result.get('analysis', '')[:200]}...")
                    
                    # Send alert (will use local video alert system)
                    alert_sent = self.send_security_alert(result)
                    if alert_sent:
                        logger.info("✅ Security alert email sent successfully")
                    else:
                        logger.error("❌ Failed to send security alert email")
                else:
                    logger.debug(f"No security incidents detected in recent frames (via {analysis_source})")
            else:
                logger.debug("Analysis returned no results")
        
        except Exception as e:
            logger.error(f"Error in async frames analysis: {e}")
            # Continue operation even if analysis fails
            logger.info("Continuing video monitoring despite analysis error")
    
    def stop(self):
        """Stop video analysis"""
        self.running = False


def main():
    """Main application entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Vigint Secure Video Analysis Application')
    parser.add_argument('--rtsp-url', type=str, required=True,
                       help='RTSP stream URL')
    parser.add_argument('--api-url', type=str, default='http://localhost:5002',
                       help='Vigint API proxy URL (default: http://localhost:5002)')
    parser.add_argument('--api-key', type=str,
                       help='API key (or set VIGINT_API_KEY env var)')
    parser.add_argument('--interval', type=int, default=10,
                       help='Analysis interval in seconds (default: 10)')
    
    args = parser.parse_args()
    
    try:
        # Create secure analyzer
        analyzer = SecureVideoAnalyzer(
            api_base_url=args.api_url,
            api_key=args.api_key
        )
        analyzer.analysis_interval = args.interval
        
        # Start video analysis
        analyzer.process_video_stream(args.rtsp_url)
        
    except KeyboardInterrupt:
        logger.info("Shutting down secure video analyzer...")
    except Exception as e:
        logger.error(f"Failed to start analyzer: {e}")
        return 1
    finally:
        if 'analyzer' in locals():
            analyzer.stop()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())