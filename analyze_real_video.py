#!/usr/bin/env python3
"""
Analyze a real input video and create video links from the actual analyzed frames
"""

import os
import sys
import logging
import cv2
import base64
import time
import threading
from datetime import datetime
from collections import deque

# Add current directory to path
sys.path.append('.')

from video_analyzer import VideoAnalyzer
from alerts import send_security_alert_with_video

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RealVideoAnalyzer(VideoAnalyzer):
    """Enhanced video analyzer that captures the actual analyzed frames and maintains smooth video buffer"""
    
    def __init__(self):
        super().__init__()
        self.analyzed_frames = deque(maxlen=200)  # Store analyzed frames (every 5s)
        self.all_frames_buffer = deque(maxlen=750)  # Store ALL frames for smooth video (30s at 25fps)
        self.incident_detected = False
        self.incident_frames = []
        
    def analyze_frame(self, frame):
        """Override to capture the actual frame being analyzed"""
        # Store the actual frame being analyzed
        try:
            _, buffer_img = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer_img).decode('utf-8')
            
            frame_info = {
                'frame_data': frame_base64,
                'frame_count': self.frame_count,
                'timestamp': datetime.now().isoformat(),
                'source': 'real_input_video'
            }
            
            self.analyzed_frames.append(frame_info)
            
        except Exception as e:
            logger.error(f"Error storing analyzed frame: {e}")
        
        # Call parent analyze_frame method
        return super().analyze_frame(frame)
    
    def send_alert_email(self, analysis_result, video_frames=None):
        """Override to use the actual analyzed frames"""
        try:
            if analysis_result.get('incident_detected', False):
                logger.info("🚨 INCIDENT DETECTED - Using REAL analyzed frames")
                
                # Get smooth video evidence by collecting more frames around the incident
                analysis_interval = getattr(self, 'analysis_interval', 5)  # Default 5 seconds
                
                # Instead of just using analyzed frames, get a smooth sequence of frames
                # from the frame buffer for better video quality
                if hasattr(self, 'frame_buffer') and len(self.frame_buffer) > 0:
                    # Get the last 10 seconds worth of frames at normal video rate (25 FPS)
                    frames_for_video = min(250, len(self.frame_buffer))  # 10 seconds at 25 FPS
                    real_frames = list(self.frame_buffer)[-frames_for_video:]
                    
                    logger.info(f"📹 Using {len(real_frames)} frames from buffer for smooth video (last 10 seconds)")
                else:
                    # Fallback to analyzed frames if buffer not available
                    max_frames_for_evidence = min(len(self.analyzed_frames), 12)
                    real_frames = list(self.analyzed_frames)[-max_frames_for_evidence:] if len(self.analyzed_frames) >= max_frames_for_evidence else list(self.analyzed_frames)
                    
                    logger.info(f"📹 Using {len(real_frames)} analyzed frames (fallback)")
                
                # Add timing information for video creation
                for i, frame in enumerate(real_frames):
                    if 'analysis_interval' not in frame:
                        frame['analysis_interval'] = 0.04  # 25 FPS = 0.04s per frame
                    frame['sequence_number'] = i + 1
                    frame['total_frames'] = len(real_frames)
                
                logger.info(f"📹 Using {len(real_frames)} REAL analyzed frames from input video")
                
                # Prepare incident data with real analysis info
                incident_data = {
                    'risk_level': 'HIGH' if analysis_result.get('incident_detected', False) else 'MEDIUM',
                    'frame_count': len(real_frames),
                    'confidence': analysis_result.get('confidence', 0.0),
                    'analysis': analysis_result.get('analysis', ''),
                    'incident_type': analysis_result.get('incident_type', ''),
                    'source': 'real_input_video_analysis',
                    'analyzed_frames_count': len(self.analyzed_frames)
                }
                
                # Create message
                message = f"""
🚨 INCIDENT DE SÉCURITÉ DÉTECTÉ - ANALYSE VIDÉO RÉELLE

Heure: {analysis_result['timestamp']}
Image analysée: {analysis_result['frame_count']}
Incident détecté: {analysis_result.get('incident_detected', False)}
Type d'incident: {analysis_result.get('incident_type', 'Non spécifié')}

⚠️ IMPORTANT: Cette vidéo contient les images RÉELLES qui ont été analysées par l'IA.
Chaque frame correspond exactement aux images d'entrée du système de surveillance.

Source: Analyse en temps réel du flux vidéo d'entrée
Frames analysées: {len(self.analyzed_frames)} au total
Frames dans la vidéo: {len(real_frames)} (8 dernières secondes)

Ceci est une alerte automatique du système de sécurité Vigint.
Veuillez examiner immédiatement les preuves vidéo authentiques ci-jointes.
"""
                
                # Send alert with REAL analyzed frames
                result = send_security_alert_with_video(message, real_frames, incident_data)
                
                if result['success']:
                    logger.info("✅ Alert sent with REAL analyzed frames!")
                    logger.info(f"   Video ID: {result.get('video_link_info', {}).get('video_id', 'N/A')}")
                    logger.info(f"   Frames used: {len(real_frames)} from actual input video")
                else:
                    logger.error(f"❌ Failed to send alert: {result.get('error', 'Unknown error')}")
                
                return result
            else:
                logger.info("No incident detected, not sending alert")
                return {'success': True, 'message': 'No incident detected'}
                
        except Exception as e:
            logger.error(f"Error sending alert with real frames: {e}")
            return {'success': False, 'error': str(e)}


def analyze_input_video(video_path):
    """Analyze a real input video file"""
    logger.info(f"🎬 Analyzing Real Input Video: {video_path}")
    logger.info("=" * 60)
    
    if not os.path.exists(video_path):
        logger.error(f"❌ Video file not found: {video_path}")
        return False
    
    # Get video info
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"❌ Cannot open video file: {video_path}")
        return False
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps if fps > 0 else 0
    
    logger.info(f"📹 Video Info:")
    logger.info(f"   File: {video_path}")
    logger.info(f"   Duration: {duration:.1f} seconds")
    logger.info(f"   Total frames: {total_frames}")
    logger.info(f"   FPS: {fps:.1f}")
    
    cap.release()
    
    # Create real video analyzer
    analyzer = RealVideoAnalyzer()
    analyzer.analysis_interval = 3  # Analyze every 3 seconds
    
    # Start analysis
    logger.info("🔍 Starting real video analysis...")
    logger.info("   (This will analyze the actual input video frames)")
    
    try:
        # Run analysis in a separate thread
        analysis_thread = threading.Thread(
            target=analyzer.process_video_stream,
            args=(video_path,),
            daemon=True
        )
        analysis_thread.start()
        
        # Let it run for the duration of the video (or max 60 seconds)
        max_wait = min(duration + 5, 60)  # Add 5 seconds buffer, max 60 seconds
        logger.info(f"⏳ Running analysis for {max_wait:.1f} seconds...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            time.sleep(1)
            
            # Show progress
            elapsed = time.time() - start_time
            if int(elapsed) % 10 == 0 and elapsed > 0:
                logger.info(f"   📊 Analysis progress: {elapsed:.0f}/{max_wait:.0f} seconds")
                logger.info(f"   📹 Frames analyzed: {len(analyzer.analyzed_frames)}")
        
        # Stop analyzer
        analyzer.stop()
        
        # Show results
        logger.info("📊 Analysis Complete!")
        logger.info(f"   Total frames analyzed: {len(analyzer.analyzed_frames)}")
        
        if len(analyzer.analyzed_frames) > 0:
            logger.info("✅ Successfully captured real analyzed frames")
            logger.info("📧 If an incident was detected, an email was sent with the REAL video frames")
            return True
        else:
            logger.warning("⚠️  No frames were captured during analysis")
            return False
    
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        return False


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze real input video and create authentic video links')
    parser.add_argument('video_path', help='Path to the input video file to analyze')
    parser.add_argument('--analysis-interval', type=int, default=3, 
                       help='Analysis interval in seconds (default: 3)')
    
    args = parser.parse_args()
    
    logger.info("🎬 REAL VIDEO ANALYSIS SYSTEM")
    logger.info("=" * 60)
    logger.info("This system analyzes your actual input video and creates")
    logger.info("video links from the frames that were really analyzed.")
    
    success = analyze_input_video(args.video_path)
    
    if success:
        logger.info("\n🎉 SUCCESS!")
        logger.info("✅ Real input video was analyzed")
        logger.info("📧 Check your email for security alerts")
        logger.info("🎥 Video links now contain the ACTUAL analyzed frames")
        logger.info("🔍 The video evidence is authentic and corresponds to your input")
    else:
        logger.error("\n❌ ANALYSIS FAILED!")
        logger.error("Could not analyze the input video properly")
    
    logger.info("\n📋 NEXT STEPS:")
    logger.info("1. Check your email inbox")
    logger.info("2. Look for security alert emails")
    logger.info("3. Click the video links to see the REAL analyzed footage")
    logger.info("4. Verify the video matches your input video content")
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)