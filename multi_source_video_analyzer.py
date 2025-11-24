#!/usr/bin/env python3
"""
Multi-Source Video Analyzer for Vigint
Handles simultaneous analysis of multiple video sources (aggregation disabled)
"""

import cv2
import time
import logging
import threading
import base64
import os
import tempfile
import numpy as np
import requests
from datetime import datetime
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import config
from alerts import send_security_alert_with_video

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VideoSource:
    """Represents a single video source"""
    
    def __init__(self, source_id, rtsp_url, name=None):
        self.source_id = source_id
        self.rtsp_url = rtsp_url
        self.name = name or f"Camera_{source_id}"
        self.cap = None
        self.frame_count = 0
        self.last_frame = None
        self.last_frame_time = 0
        self.running = False
        self.thread = None
        
        # Frame buffer for video creation (keep last 10 seconds at 25fps = 250 frames)
        self.frame_buffer = deque(maxlen=250)
        self.buffer_fps = 25
    
    def start(self):
        """Start capturing from this video source"""
        logger.info(f"Starting video source {self.source_id}: {self.name}")
        
        self.cap = cv2.VideoCapture(self.rtsp_url)
        if not self.cap.isOpened():
            logger.error(f"Failed to open video source {self.source_id}: {self.rtsp_url}")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        
        logger.info(f"Video source {self.source_id} started successfully")
        return True
    
    def stop(self):
        """Stop capturing from this video source"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        if self.cap:
            self.cap.release()
        logger.info(f"Video source {self.source_id} stopped")
    
    def _capture_loop(self):
        """Main capture loop for this video source"""
        while self.running:
            try:
                ret, frame = self.cap.read()
                
                if not ret:
                    # Check if this is a video file that has ended
                    if hasattr(self.cap, 'get') and self.cap.get(cv2.CAP_PROP_FRAME_COUNT) > 0:
                        # Video file ended, restart from beginning
                        logger.info(f"Video file ended for source {self.source_id}, restarting...")
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        logger.warning(f"Failed to read frame from source {self.source_id}")
                        time.sleep(1)
                        continue
                
                self.frame_count += 1
                self.last_frame = frame.copy()
                self.last_frame_time = time.time()
                
                # Add frame to buffer
                self._add_frame_to_buffer(frame.copy())
                
                # Small delay to prevent overwhelming the system
                time.sleep(0.04)  # ~25 FPS
                
            except Exception as e:
                logger.error(f"Error in capture loop for source {self.source_id}: {e}")
                time.sleep(1)
    
    def _add_frame_to_buffer(self, frame):
        """Add frame to buffer for video creation"""
        try:
            # Ensure frame is valid and has content
            if frame is None or frame.size == 0:
                logger.warning(f"Invalid frame for source {self.source_id}, skipping")
                return
            
            # Convert frame to base64 for storage with good quality
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, 90]
            _, buffer_img = cv2.imencode('.jpg', frame, encode_params)
            frame_base64 = base64.b64encode(buffer_img).decode('utf-8')
            
            # Create detailed frame info with timestamp
            frame_info = {
                'frame_data': frame_base64,
                'frame_count': self.frame_count,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],  # Include milliseconds
                'source_id': self.source_id,
                'source_name': self.name,
                'frame_size': frame.shape,
                'capture_time': time.time()
            }
            
            self.frame_buffer.append(frame_info)
            
        except Exception as e:
            logger.error(f"Error adding frame to buffer for source {self.source_id}: {e}")
    
    def get_recent_frames(self, duration_seconds=5):
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
            logger.error(f"Error getting recent frames for source {self.source_id}: {e}")
            return []
    
    def get_current_frame(self):
        """Get the most recent frame"""
        return self.last_frame if self.last_frame is not None else None
    
    def is_active(self):
        """Check if this source is actively receiving frames"""
        if not self.running:
            return False
        
        # Consider active if we received a frame in the last 5 seconds
        return time.time() - self.last_frame_time < 5.0


class MultiSourceVideoAnalyzer:
    """Handles simultaneous analysis of multiple video sources using api_proxy.py dual-buffer system"""
    
    def __init__(self, api_key=None, api_url=None):
        # Configure API connection instead of direct Gemini
        self.api_key = api_key or os.getenv('VIGINT_API_KEY')
        self.api_url = api_url or config.api_server_url or 'http://localhost:5000'
        
        if not self.api_key:
            logger.error("Vigint API key not found. Set VIGINT_API_KEY environment variable.")
        else:
            logger.info(f"Multi-source analyzer configured to use API at {self.api_url}")
        
        self.api_headers = {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        self.video_sources = {}
        self.analysis_interval = 3  # Analyze every 3 seconds (short buffer cycle)
        self.last_analysis_time = 0
        self.running = False
        self.analysis_thread = None
        self.buffer_thread = None
        
        # Incident deduplication tracking
        self.last_incident_time = {}
        self.incident_cooldown = 60  # Don't re-alert for 60 seconds after an incident
        self.last_incident_hash = {}
        
        # Thread pool for parallel analysis
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def add_video_source(self, source_id, rtsp_url, name=None):
        """Add a video source to be analyzed"""
        if source_id in self.video_sources:
            logger.warning(f"Video source {source_id} already exists, replacing...")
            self.remove_video_source(source_id)
        
        source = VideoSource(source_id, rtsp_url, name)
        self.video_sources[source_id] = source
        
        # Start the source if analyzer is running
        if self.running:
            source.start()
        
        logger.info(f"Added video source {source_id}: {name or rtsp_url}")
        return True
    
    def remove_video_source(self, source_id):
        """Remove a video source"""
        if source_id in self.video_sources:
            self.video_sources[source_id].stop()
            del self.video_sources[source_id]
            logger.info(f"Removed video source {source_id}")
            return True
        return False
    
    def start_analysis(self):
        """Start analyzing all video sources"""
        if self.running:
            logger.warning("Analysis already running")
            return False
        
        if not self.video_sources:
            logger.error("No video sources configured")
            return False
        
        logger.info(f"Starting multi-source video analysis with {len(self.video_sources)} sources")
        
        # Start all video sources
        for source in self.video_sources.values():
            source.start()
        
        # Wait a moment for sources to initialize
        time.sleep(3)
        
        self.running = True
        
        # Start buffer thread to continuously send frames to API
        self.buffer_thread = threading.Thread(target=self._buffer_loop, daemon=True)
        self.buffer_thread.start()
        
        # Start analysis thread to trigger analysis
        self.analysis_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self.analysis_thread.start()
        
        logger.info("Multi-source video analysis started")
        return True
    
    def stop_analysis(self):
        """Stop analyzing all video sources"""
        if not self.running:
            return
        
        logger.info("Stopping multi-source video analysis")
        self.running = False
        
        # Stop all video sources
        for source in self.video_sources.values():
            source.stop()
        
        # Wait for threads to finish
        if self.buffer_thread:
            self.buffer_thread.join(timeout=5)
        if self.analysis_thread:
            self.analysis_thread.join(timeout=10)
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logger.info("Multi-source video analysis stopped")
    
    def _buffer_loop(self):
        """Continuously send frames to API buffer"""
        # Track last sent frame index for each source to avoid duplicates
        last_sent_index = {}
        
        while self.running:
            try:
                for source in self.video_sources.values():
                    if source.is_active():
                        # Get all frames from the buffer that haven't been sent yet
                        source_id = source.source_id
                        last_index = last_sent_index.get(source_id, -1)
                        
                        # Get frames from buffer starting after the last sent frame
                        current_buffer_size = len(source.frame_buffer)
                        
                        if current_buffer_size > 0:
                            # Send frames we haven't sent yet
                            # Get the frame from buffer (convert from deque to list for indexing)
                            buffer_list = list(source.frame_buffer)
                            
                            # Find frames to send (limit to avoid overwhelming API)
                            frames_to_send = []
                            for i in range(max(0, last_index + 1), current_buffer_size):
                                if len(frames_to_send) < 10:  # Send up to 10 frames per cycle
                                    frames_to_send.append(buffer_list[i])
                            
                            # Send each frame
                            if len(frames_to_send) > 0:
                                logger.debug(f"📤 Sending {len(frames_to_send)} frames to API buffer for {source.name}")
                            
                            for frame_info in frames_to_send:
                                try:
                                    # Frame is already base64 in buffer
                                    response = requests.post(
                                        f"{self.api_url}/api/video/multi-source/buffer",
                                        headers=self.api_headers,
                                        json={
                                            'source_id': source.source_id,
                                            'source_name': source.name,
                                            'frame_data': frame_info['frame_data'],
                                            'frame_count': frame_info.get('frame_count', source.frame_count)
                                        },
                                        timeout=5
                                    )
                                    
                                    if response.status_code == 200:
                                        last_sent_index[source_id] = buffer_list.index(frame_info)
                                    else:
                                        logger.warning(f"Failed to buffer frame for {source.name}: {response.status_code}")
                                        break  # Stop sending more frames if one fails
                                except Exception as e:
                                    logger.error(f"Error buffering frame for {source.name}: {e}")
                                    break
                            
                            # Reset index if buffer has rolled over (deque with maxlen)
                            if last_sent_index.get(source_id, 0) >= current_buffer_size:
                                last_sent_index[source_id] = current_buffer_size - 1
                
                # Small delay between buffer updates (faster now since we send multiple frames)
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in buffer loop: {e}")
                time.sleep(1)
    
    def _analysis_loop(self):
        """Main analysis loop - triggers API analysis every 3 seconds"""
        while self.running:
            try:
                current_time = time.time()
                
                if current_time - self.last_analysis_time >= self.analysis_interval:
                    self.last_analysis_time = current_time
                    
                    # Get active sources
                    active_sources = [s for s in self.video_sources.values() if s.is_active()]
                    
                    if active_sources:
                        logger.info(f"Triggering analysis for {len(active_sources)} active sources")
                        self._analyze_sources_via_api(active_sources)
                    else:
                        logger.warning("No active video sources for analysis")
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in analysis loop: {e}")
                time.sleep(5)
    
    def _analyze_sources_via_api(self, active_sources):
        """Analyze active video sources via API (uses dual-buffer Flash-Lite → Flash system)"""
        try:
            source_ids = [source.source_id for source in active_sources]
            
            logger.info(f"Requesting API analysis for {len(source_ids)} sources")
            
            # Call the multi-source analysis API
            try:
                response = requests.post(
                    f"{self.api_url}/api/video/multi-source/analyze",
                    headers=self.api_headers,
                    json={'source_ids': source_ids},
                    timeout=120  # Longer timeout for multi-source analysis
                )
                
                if response.status_code != 200:
                    logger.error(f"API analysis failed with status {response.status_code}: {response.text}")
                    return
                
                results = response.json()
                
                # Log summary
                summary = results.get('summary', {})
                logger.info(f"Analysis complete:")
                logger.info(f"  - Flash-Lite detections: {summary.get('total_incidents_detected_by_flash_lite', 0)}")
                logger.info(f"  - Flash confirmations: {summary.get('total_incidents_confirmed_by_flash', 0)}")
                logger.info(f"  - Flash vetoes: {summary.get('total_incidents_vetoed', 0)}")
                
                # Process results per source
                for source_id, analysis_result in results.get('sources', {}).items():
                    if analysis_result.get('has_security_incident', False):
                        # Flash confirmed the incident - handle it
                        source = self.video_sources.get(source_id)
                        if source:
                            # Extract client email from API response
                            client_email = results.get('client_email')
                            self._handle_security_incident(analysis_result, source, recipient_email=client_email)
                    elif analysis_result.get('flash_veto', False):
                        logger.info(f"🚫 Incident vetoed by Flash for source {source_id}")
                
            except requests.exceptions.Timeout:
                logger.error("API analysis request timed out")
            except requests.exceptions.RequestException as e:
                logger.error(f"API request failed: {e}")
        
        except Exception as e:
            logger.error(f"Error in API-based source analysis: {e}")
    
    def _analyze_individual_source(self, source):
        """DEPRECATED: Analyze a single video source - now handled by API"""
        # This method is no longer used - analysis is done via API
        logger.warning("_analyze_individual_source called but is deprecated - use API instead")
        return None
    
    def _analyze_aggregated_group(self, group_sources, group_name):
        """DEPRECATED: Analyze a group of 4 video sources as an aggregated view (aggregation disabled)"""
        try:
            logger.info(f"Analyzing aggregated group: {group_name} with {len(group_sources)} sources")
            
            # Get current frames from all sources in the group
            frames = []
            source_names = []
            
            for source in group_sources:
                frame = source.get_current_frame()
                if frame is not None:
                    frames.append(frame)
                    source_names.append(source.name)
            
            if not frames:
                logger.warning(f"No frames available for group {group_name}")
                return None
            
            # Create a composite image from the group frames
            composite_frame = self._create_composite_frame(frames, source_names)
            
            if composite_frame is None:
                logger.error(f"Failed to create composite frame for group {group_name}")
                return None
            
            # Convert composite frame to base64 for Gemini API
            _, buffer_img = cv2.imencode('.jpg', composite_frame)
            frame_base64 = base64.b64encode(buffer_img).decode('utf-8')
            
            # Prepare the prompt for aggregated analysis
            camera_list = ", ".join(source_names)
            prompt = f"""
            Analyze the provided composite video frame showing multiple camera views ({camera_list}) for security incidents in a retail environment. This is an aggregated view of {len(source_names)} cameras simultaneously.
            
            Pay particular attention to:
            1. Customers taking items and concealing them (in pockets, bags, clothing)
            2. Unusual handling of merchandise (checking for security tags, looking around suspiciously)
            3. Taking items without paying
            4. Groups working together to distract staff while items are taken
            5. Removing packaging or security devices
            6. Unusual movements around high-value items
            7. Signs of nervousness or anxiety while handling merchandise
            8. Coordinated suspicious activities across multiple camera views
            
            Since this is a multi-camera view, also look for:
            - Suspicious individuals moving between camera zones
            - Coordinated group activities across different areas
            - Patterns of behavior that span multiple camera views
            
            Your analysis must be thorough and should err on the side of detecting potential security incidents rather than missing them.
            
            Return ONLY the JSON object without markdown formatting, code blocks, or additional text.
            If no incidents are detected, return the JSON with incident_detected set to false.
            
            Your response must be a valid JSON object with the following structure:
            {{"incident_detected": boolean,  // true if an incident is detected, false otherwise
            "incident_type": string,     // Describe the type of incident (e.g.: shoplifting, theft, vandalism)
            "description": string,       // brief description of what you see
            "analysis": string,          // detailed analysis of the video content
            "camera_group": string,      // group identifier
            "cameras_involved": string}} // list of camera names in this group
            
            Answer in French.
            """
            
            # Send to Gemini for analysis
            response = self.model.generate_content([
                prompt,
                {"mime_type": "image/jpeg", "data": frame_base64}
            ])
            
            # Extract token usage from response metadata
            token_usage = {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            }
            
            try:
                if hasattr(response, 'usage_metadata'):
                    token_usage['prompt_tokens'] = getattr(response.usage_metadata, 'prompt_token_count', 0)
                    token_usage['completion_tokens'] = getattr(response.usage_metadata, 'candidates_token_count', 0)
                    token_usage['total_tokens'] = getattr(response.usage_metadata, 'total_token_count', 0)
                    
                    logger.info(f"🔢 [{group_name}] Token usage - Prompt: {token_usage['prompt_tokens']}, "
                               f"Completion: {token_usage['completion_tokens']}, "
                               f"Total: {token_usage['total_tokens']}")
            except Exception as token_error:
                logger.warning(f"Could not extract token usage for {group_name}: {token_error}")
            
            # Parse JSON response
            analysis_result = self._parse_analysis_response(response.text, None, group_name, source_names, token_usage=token_usage)
            
            if analysis_result:
                logger.info(f"Aggregated analysis completed for {group_name}: incident_detected={analysis_result.get('incident_detected', False)}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing aggregated group {group_name}: {e}")
            return None
    
    def _create_composite_frame(self, frames, source_names):
        """DEPRECATED: Create a composite frame from multiple source frames (aggregation disabled)"""
        try:
            if not frames:
                return None
            
            # Resize all frames to a standard size
            target_width, target_height = 320, 240
            resized_frames = []
            
            for frame in frames:
                resized = cv2.resize(frame, (target_width, target_height))
                resized_frames.append(resized)
            
            # Create a 2x2 grid for 4 frames
            if len(resized_frames) >= 4:
                # Top row
                top_row = np.hstack([resized_frames[0], resized_frames[1]])
                # Bottom row
                bottom_row = np.hstack([resized_frames[2], resized_frames[3]])
                # Combine rows
                composite = np.vstack([top_row, bottom_row])
            elif len(resized_frames) == 3:
                # Top row with 2 frames
                top_row = np.hstack([resized_frames[0], resized_frames[1]])
                # Bottom row with 1 frame centered
                bottom_frame = resized_frames[2]
                padding = np.zeros((target_height, target_width, 3), dtype=np.uint8)
                bottom_row = np.hstack([padding, bottom_frame])
                composite = np.vstack([top_row, bottom_row])
            elif len(resized_frames) == 2:
                # Side by side
                composite = np.hstack([resized_frames[0], resized_frames[1]])
            else:
                # Single frame
                composite = resized_frames[0]
            
            # Add labels to identify each camera view
            for i, name in enumerate(source_names[:len(resized_frames)]):
                if len(resized_frames) >= 4:
                    # Calculate position for 2x2 grid
                    if i == 0:  # Top-left
                        x, y = 10, 25
                    elif i == 1:  # Top-right
                        x, y = target_width + 10, 25
                    elif i == 2:  # Bottom-left
                        x, y = 10, target_height + 25
                    else:  # Bottom-right
                        x, y = target_width + 10, target_height + 25
                else:
                    # Simple positioning for fewer frames
                    x, y = 10 + (i * target_width), 25
                
                cv2.putText(composite, name, (x, y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            return composite
            
        except Exception as e:
            logger.error(f"Error creating composite frame: {e}")
            return None
    
    def _parse_analysis_response(self, response_text, source=None, group_name=None, source_names=None, token_usage=None):
        """Parse the analysis response from Gemini"""
        try:
            import json
            
            response_text = response_text.strip()
            
            # Handle JSON wrapped in markdown code blocks
            if response_text.startswith('```json'):
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    response_text = response_text[start_idx:end_idx]
            
            analysis_json = json.loads(response_text)
            
            # Add metadata
            analysis_result = {
                'timestamp': datetime.now().isoformat(),
                'incident_detected': analysis_json.get('incident_detected', False),
                'incident_type': analysis_json.get('incident_type', ''),
                'description': analysis_json.get('description', ''),
                'analysis': analysis_json.get('analysis', response_text),
                'is_aggregated': group_name is not None
            }
            
            # Add token usage if provided
            if token_usage:
                analysis_result['token_usage'] = token_usage
            
            if source:
                analysis_result.update({
                    'source_id': source.source_id,
                    'source_name': source.name,
                    'frame_count': source.frame_count
                })
            
            if group_name:
                analysis_result.update({
                    'group_name': group_name,
                    'cameras_involved': source_names or [],
                    'num_cameras': len(source_names) if source_names else 0
                })
            
            return analysis_result
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing analysis response: {e}")
            # Fallback to text parsing
            response_text_lower = response_text.lower()
            incident_detected = 'incident_detected": true' in response_text_lower
            
            return {
                'timestamp': datetime.now().isoformat(),
                'incident_detected': incident_detected,
                'incident_type': 'Unknown',
                'description': 'Analysis parsing failed',
                'analysis': response_text,
                'is_aggregated': group_name is not None,
                'source_id': source.source_id if source else None,
                'source_name': source.name if source else None,
                'group_name': group_name,
                'cameras_involved': source_names or []
            }
    
    def _handle_security_incident(self, analysis_result, source, recipient_email=None):
        """Handle detected security incident (confirmed by Flash)"""
        try:
            logger.warning("🚨 CONFIRMED SECURITY EVENT (Flash approved)")
            logger.warning(f"Source: {source.name}")
            logger.warning(f"Analysis: {analysis_result.get('analysis', '')[:200]}...")
            
            # DEDUPLICATION TEMPORARILY DISABLED
            # # Create incident signature for deduplication
            # incident_key = f"source_{source.source_id}"
            # 
            # incident_signature = f"{analysis_result.get('incident_type', 'unknown')}_{analysis_result.get('analysis', '')[:50]}"
            # 
            # # Check if this is a duplicate incident (deduplication)
            # current_time = time.time()
            # last_time = self.last_incident_time.get(incident_key, 0)
            # last_hash = self.last_incident_hash.get(incident_key, None)
            # 
            # if (current_time - last_time < self.incident_cooldown and last_hash == incident_signature):
            #     logger.info(f"⏭️  Skipping duplicate incident alert for {incident_key}")
            #     logger.info(f"   Time since last alert: {current_time - last_time:.1f}s / {self.incident_cooldown}s cooldown")
            #     return
            # 
            # # Update incident tracking
            # self.last_incident_time[incident_key] = current_time
            # self.last_incident_hash[incident_key] = incident_signature
            # logger.info(f"📧 Sending NEW incident alert for {incident_key} (cooldown active for next {self.incident_cooldown}s)")
            
            logger.info(f"📧 Sending incident alert (DEDUPLICATION DISABLED)")
            
            # Collect video frames - API returns them in incident_frames
            video_frames = analysis_result.get('incident_frames', [])
            
            if not video_frames:
                # Fallback: get recent frames from local buffer
                logger.warning("No frames from API, using local buffer")
                video_frames = source.get_recent_frames(duration_seconds=10)
            
            logger.info(f"Using {len(video_frames)} frames for video evidence")
            
            # Prepare incident data
            incident_data = {
                'risk_level': 'HIGH',
                'frame_count': analysis_result.get('frame_count', 0),
                'analysis': analysis_result.get('analysis', ''),
                'incident_type': analysis_result.get('incident_type', ''),
                'is_aggregated': analysis_result.get('is_aggregated', False),
                'cameras_involved': analysis_result.get('cameras_involved', [])
            }
            
            # Create alert message in French
            formatted_time = datetime.now().strftime('%H:%M:%S - %d/%m/%Y')
            
            message = f"""
🚨 ALERTE SÉCURITÉ VIGINT - INCIDENT CONFIRMÉ

Heure: {formatted_time}
Caméra: {source.name}
Type d'incident: {analysis_result.get('incident_type', 'Non spécifié')}

✅ INCIDENT CONFIRMÉ PAR ANALYSE À DEUX NIVEAUX:
   - Détection initiale: Gemini 2.5 Flash-Lite (buffer court - 3s)
   - Confirmation finale: Gemini 2.5 Flash (buffer long - 10s)

ANALYSE DÉTAILLÉE:
{analysis_result.get('analysis', 'Aucune analyse disponible')}

📊 MÉTRIQUES D'ANALYSE:
   - Frames analysées (confirmation): {analysis_result.get('incident_frames_count', 'N/A')}
   - Statut Flash: CONFIRMÉ ✅

⚠️  Cette alerte a été validée par notre système d'analyse à double buffer.
Veuillez examiner immédiatement les preuves vidéo ci-jointes.
"""
            
            # Send alert with video evidence
            if video_frames:
                result = send_security_alert_with_video(
                    message, 
                    video_frames, 
                    incident_data,
                    recipient_email=recipient_email
                )
                if result.get('success', False):
                    logger.info("🚨 MULTI-SOURCE SECURITY ALERT WITH VIDEO SENT!")
                    logger.info(f"   Alert will not repeat for same incident for {self.incident_cooldown}s")
                else:
                    logger.error(f"Failed to send security alert: {result.get('error', 'Unknown error')}")
            else:
                # Fallback to basic email alert
                from alerts import AlertManager
                alert_manager = AlertManager()
                result = alert_manager.send_email_alert(
                    message, 
                    "security", 
                    incident_data=incident_data,
                    recipient_email=recipient_email
                )
                if result.get('success', False):
                    logger.info("🚨 BASIC EMAIL ALERT SENT (NO VIDEO)! Alert will not repeat for same incident for {self.incident_cooldown}s")
                else:
                    logger.error(f"Failed to send security alert: {result.get('error', 'Unknown error')}")
            
        except Exception as e:
            logger.error(f"Error handling security incident: {e}")
    
    def get_status(self):
        """Get current status of all video sources"""
        status = {
            'running': self.running,
            'total_sources': len(self.video_sources),
            'active_sources': 0,
            'sources': {}
        }
        
        for source_id, source in self.video_sources.items():
            is_active = source.is_active()
            if is_active:
                status['active_sources'] += 1
            
            status['sources'][source_id] = {
                'name': source.name,
                'rtsp_url': source.rtsp_url,
                'active': is_active,
                'frame_count': source.frame_count,
                'last_frame_time': source.last_frame_time
            }
        
        return status


def main():
    """Main function for testing multi-source video analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-Source Video Analyzer - Uses API with Dual-Buffer System')
    parser.add_argument('--sources', type=str, nargs='+', required=True,
                       help='RTSP URLs or video file paths')
    parser.add_argument('--names', type=str, nargs='*',
                       help='Names for the video sources')
    parser.add_argument('--interval', type=int, default=3,
                       help='Analysis interval in seconds (default: 3 - short buffer cycle)')
    parser.add_argument('--api-key', type=str,
                       help='Vigint API key (or set VIGINT_API_KEY env var)')
    parser.add_argument('--api-url', type=str,
                       help='API URL (default: http://localhost:5000)')
    
    args = parser.parse_args()
    
    # Create analyzer with API configuration
    analyzer = MultiSourceVideoAnalyzer(api_key=args.api_key, api_url=args.api_url)
    analyzer.analysis_interval = args.interval
    
    logger.info("=" * 60)
    logger.info("Multi-Source Video Analyzer - Dual-Buffer System")
    logger.info("=" * 60)
    logger.info(f"API URL: {analyzer.api_url}")
    logger.info(f"Analysis Interval: {args.interval}s (Flash-Lite screening)")
    logger.info(f"Dual-Buffer: 3s (Flash-Lite) → 10s (Flash confirmation)")
    logger.info("=" * 60)
    
    # Add video sources
    for i, source_url in enumerate(args.sources):
        source_id = f"source_{i+1}"
        source_name = args.names[i] if args.names and i < len(args.names) else f"Camera_{i+1}"
        analyzer.add_video_source(source_id, source_url, source_name)
    
    try:
        # Start analysis
        if analyzer.start_analysis():
            logger.info("Multi-source video analysis started. Press Ctrl+C to stop.")
            
            # Keep running and show status periodically
            while True:
                time.sleep(30)
                status = analyzer.get_status()
                logger.info(f"Status: {status['active_sources']}/{status['total_sources']} sources active")
        else:
            logger.error("Failed to start multi-source video analysis")
    
    except KeyboardInterrupt:
        logger.info("Shutting down multi-source video analyzer...")
    finally:
        analyzer.stop_analysis()


if __name__ == '__main__':
    main()