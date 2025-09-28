#!/usr/bin/env python3
"""
Secure Video Analyzer - Uses API proxy for all sensitive operations
No credentials stored on client side
"""

import cv2
import time
import logging
import threading
import base64
import os
import requests
from datetime import datetime
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecureVideoAnalyzer:
    """Secure video analyzer that uses API proxy for all sensitive operations"""
    
    def __init__(self, api_base_url='http://localhost:5002', api_key=None):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key or os.getenv('VIGINT_API_KEY')
        
        if not self.api_key:
            raise ValueError("API key is required. Set VIGINT_API_KEY environment variable or pass api_key parameter")
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        self.frame_count = 0
        self.last_analysis_time = 0
        self.analysis_interval = 10  # Analyze every 10 seconds
        self.running = False
        
        # Frame buffer for video creation (keep last 15 seconds at 25fps = 375 frames)
        from collections import deque
        self.frame_buffer = deque(maxlen=375)
        self.buffer_fps = 25
        
        # Test API connection
        self._test_connection()
    
    def _test_connection(self):
        """Test connection to API proxy"""
        try:
            response = requests.get(
                f'{self.api_base_url}/api/health',
                headers={'Authorization': f'Bearer {self.api_key}'},
                timeout=5
            )
            if response.status_code == 200:
                logger.info("✅ Connected to Vigint API proxy")
            else:
                logger.warning(f"API proxy responded with status {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to connect to API proxy: {e}")
            raise ConnectionError("Cannot connect to Vigint API proxy")
    
    def analyze_frame(self, frame):
        """Analyze a video frame using the secure API proxy"""
        try:
            # Convert frame to base64
            _, buffer_img = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer_img).decode('utf-8')
            
            # Send to API proxy for analysis
            payload = {
                'frame_data': frame_base64,
                'frame_count': self.frame_count
            }
            
            response = requests.post(
                f'{self.api_base_url}/api/video/analyze',
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Frame {self.frame_count} analyzed via API proxy")
                return result
            else:
                logger.error(f"API analysis failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing frame {self.frame_count}: {e}")
            return None
    
    def send_security_alert(self, analysis_result):
        """Send security alert via API proxy"""
        try:
            payload = {
                'analysis': analysis_result['analysis'],
                'frame_count': analysis_result['frame_count'],
                'incident_type': analysis_result.get('incident_type', ''),
                'risk_level': 'HIGH' if analysis_result.get('has_security_incident', False) else 'MEDIUM'
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
                logger.error(f"Failed to send alert: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
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
        logger.info("🎯 Starting secure video analysis via API proxy...")
        logger.info("🔒 All credentials and AI processing handled server-side")
        
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
                
                # Add frame to buffer for video creation
                self._add_frame_to_buffer(frame.copy())
                
                # Analyze frame periodically
                if current_time - self.last_analysis_time >= self.analysis_interval:
                    self.last_analysis_time = current_time
                    
                    # Analyze frame in a separate thread to avoid blocking
                    threading.Thread(
                        target=self._analyze_frame_async,
                        args=(frame.copy(),),
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
    
    def _get_recent_frames(self, duration_seconds=10):
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
    
    def send_local_alert_with_video(self, analysis_result):
        """Send local alert with video when API proxy is unavailable"""
        try:
            from alerts import send_security_alert_with_video
            
            # Get recent frames for video evidence
            video_frames = self._get_recent_frames(duration_seconds=10)
            
            # Prepare incident data
            incident_data = {
                'risk_level': 'HIGH',
                'frame_count': analysis_result.get('frame_count', 0),
                'confidence': 0.8,  # Default high confidence for detected incidents
                'analysis': analysis_result.get('analysis', ''),
                'incident_type': analysis_result.get('incident_type', '')
            }
            
            # Create alert message in French
            message = f"""
INCIDENT DE SÉCURITÉ DÉTECTÉ (PROXY API INDISPONIBLE)

Heure: {datetime.now().isoformat()}
Image: {analysis_result.get('frame_count', 0)}

ANALYSE:
{analysis_result.get('analysis', 'Incident de sécurité détecté')}

Cette alerte a été envoyée directement en raison de l'indisponibilité du proxy API.
Veuillez examiner immédiatement les preuves vidéo ci-jointes.
"""
            
            # Send alert with video
            result = send_security_alert_with_video(message, video_frames, incident_data)
            
            if result.get('success', False):
                logger.info("🚨 LOCAL SECURITY ALERT WITH VIDEO SENT!")
                return True
            else:
                logger.error(f"Failed to send local alert: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending local alert with video: {e}")
            return False
    
    def _analyze_frame_async(self, frame):
        """Analyze frame in a separate thread"""
        try:
            result = self.analyze_frame(frame)
            
            if result and result.get('has_security_incident', False):
                logger.warning("🚨 POTENTIAL SECURITY EVENT DETECTED!")
                logger.warning(f"Analysis: {result['analysis'][:200]}...")
                
                # Try to send alert via API proxy first
                api_success = self.send_security_alert(result)
                
                # If API proxy fails, send local alert with video
                if not api_success:
                    logger.warning("API proxy alert failed, sending local alert with video")
                    self.send_local_alert_with_video(result)
        
        except Exception as e:
            logger.error(f"Error in async frame analysis: {e}")
    
    def stop(self):
        """Stop video analysis"""
        self.running = False


def main():
    """Main function to start secure video analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Secure Vigint Video Analyzer')
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
    finally:
        if 'analyzer' in locals():
            analyzer.stop()


if __name__ == '__main__':
    main()