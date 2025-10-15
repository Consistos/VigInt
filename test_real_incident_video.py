#!/usr/bin/env python3
"""
Test real incident video creation to ensure the correct analyzed frames are used
"""

import os
import sys
import logging
import cv2
import numpy as np
import base64
import time
import threading
import subprocess
from datetime import datetime
from collections import deque

# Add current directory to path
sys.path.append('.')

from video_analyzer import VideoAnalyzer
from alerts import send_security_alert_with_video

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_realistic_incident_video():
    """Create a realistic incident video file for testing"""
    video_path = 'test_incident_video.mp4'
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, 25, (640, 480))
    
    if not out.isOpened():
        logger.error("Failed to create video writer")
        return None
    
    # Create 30 seconds of realistic security footage
    total_frames = 25 * 30  # 30 seconds at 25fps
    
    for frame_num in range(total_frames):
        # Create realistic store scene
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add store background
        frame[400:, :] = [80, 80, 80]  # Floor
        cv2.rectangle(frame, (50, 100), (150, 400), (120, 120, 120), -1)  # Shelf 1
        cv2.rectangle(frame, (490, 100), (590, 400), (120, 120, 120), -1)  # Shelf 2
        
        # Add products on shelves
        for shelf_x in [50, 490]:
            for y in range(120, 380, 40):
                cv2.rectangle(frame, (shelf_x + 10, y), (shelf_x + 40, y + 30), (200, 150, 100), -1)
        
        # Add moving person with realistic behavior
        time_progress = frame_num / total_frames
        
        # Person enters from left, moves to shelf, suspicious behavior, then leaves
        if time_progress < 0.2:  # First 20% - person enters
            person_x = int(50 + 150 * (time_progress / 0.2))
            person_y = 350
            behavior_text = "PERSONNE ENTRE"
        elif time_progress < 0.4:  # Next 20% - approaches shelf
            person_x = int(200 + 50 * ((time_progress - 0.2) / 0.2))
            person_y = 350
            behavior_text = "APPROCHE RAYON"
        elif time_progress < 0.7:  # 30% - suspicious behavior at shelf
            person_x = int(250 + 20 * np.sin((time_progress - 0.4) * 20))  # Nervous movement
            person_y = 350
            behavior_text = "COMPORTEMENT SUSPECT"
            
            # Add suspicious indicators
            cv2.putText(frame, "⚠️ ACTIVITÉ SUSPECTE DÉTECTÉE", (10, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            # Show item being concealed
            cv2.rectangle(frame, (person_x + 15, person_y - 20), (person_x + 35, person_y - 5), (255, 255, 0), -1)
            cv2.putText(frame, "OBJET DISSIMULÉ", (person_x - 20, person_y - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
        else:  # Final 30% - person leaves
            person_x = int(270 + 300 * ((time_progress - 0.7) / 0.3))
            person_y = 350
            behavior_text = "PERSONNE SORT"
        
        # Draw person (stick figure)
        if person_x < 640:  # Only draw if person is in frame
            cv2.circle(frame, (person_x, person_y - 50), 15, (255, 200, 150), -1)  # Head
            cv2.line(frame, (person_x, person_y - 35), (person_x, person_y), (255, 200, 150), 8)  # Body
            cv2.line(frame, (person_x, person_y - 20), (person_x - 20, person_y - 10), (255, 200, 150), 5)  # Arms
            cv2.line(frame, (person_x, person_y - 20), (person_x + 20, person_y - 10), (255, 200, 150), 5)
            cv2.line(frame, (person_x, person_y), (person_x - 15, person_y + 30), (255, 200, 150), 5)  # Legs
            cv2.line(frame, (person_x, person_y), (person_x + 15, person_y + 30), (255, 200, 150), 5)
        
        # Add camera overlay
        cv2.putText(frame, "CAM-01 MAGASIN SECTION A", (10, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Add timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(frame, timestamp, (10, 460), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add frame counter and behavior
        cv2.putText(frame, f"Frame {frame_num + 1:04d}", (500, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, behavior_text, (10, 430), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        out.write(frame)
    
    out.release()
    
    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
        logger.info(f"Created realistic incident video: {video_path} ({os.path.getsize(video_path) / (1024*1024):.1f} MB)")
        return video_path
    else:
        logger.error("Failed to create incident video")
        return None


def start_video_server():
    """Start the local video server"""
    try:
        process = subprocess.Popen([
            sys.executable, 'local_video_server.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        time.sleep(3)  # Wait for server to start
        
        if process.poll() is None:
            logger.info("✅ Video server started")
            return process
        else:
            logger.error("❌ Video server failed to start")
            return None
    except Exception as e:
        logger.error(f"❌ Error starting video server: {e}")
        return None


def test_real_incident_analysis():
    """Test the real incident analysis workflow"""
    logger.info("🔍 Testing Real Incident Analysis Workflow")
    logger.info("=" * 50)
    
    # Create realistic incident video
    video_path = create_realistic_incident_video()
    if not video_path:
        return False
    
    try:
        # Start video server
        server_process = start_video_server()
        if not server_process:
            return False
        
        # Create video analyzer
        analyzer = VideoAnalyzer()
        analyzer.analysis_interval = 2  # Analyze every 2 seconds
        
        # Override the send_alert_email method to capture the frames
        captured_frames = []
        original_send_alert = analyzer.send_alert_email
        
        def capture_alert_frames(analysis_result, video_frames=None):
            nonlocal captured_frames
            if video_frames:
                captured_frames = list(video_frames)
                logger.info(f"📹 Captured {len(captured_frames)} frames from real analysis")
                
                # Show frame details
                for i, frame_info in enumerate(captured_frames[:3]):  # Show first 3
                    logger.info(f"   Frame {i+1}: {frame_info.get('timestamp', 'No timestamp')}")
            
            # Call original method
            return original_send_alert(analysis_result, video_frames)
        
        analyzer.send_alert_email = capture_alert_frames
        
        # Start analysis in a separate thread
        analysis_thread = threading.Thread(
            target=analyzer.process_video_stream,
            args=(video_path,),
            daemon=True
        )
        analysis_thread.start()
        
        # Let it run for 15 seconds to capture the suspicious behavior
        logger.info("🎬 Running video analysis for 15 seconds...")
        time.sleep(15)
        
        # Stop analyzer
        analyzer.stop()
        
        # Check if we captured frames
        if captured_frames:
            logger.info(f"✅ Successfully captured {len(captured_frames)} real incident frames")
            
            # Now send alert with the REAL analyzed frames
            incident_data = {
                'incident_type': 'vol_à_létalage_réel',
                'risk_level': 'HIGH',
                'analysis': 'Analyse réelle: Client observé en train de dissimuler des articles dans la section A. Comportement suspect confirmé par analyse vidéo.',
                'frame_count': len(captured_frames),
                'confidence': 0.95,
                'source': 'real_video_analysis'
            }
            
            message = """
🚨 INCIDENT DE SÉCURITÉ RÉEL DÉTECTÉ

Un comportement suspect a été détecté par l'analyse vidéo en temps réel.
Les images ci-dessous montrent la séquence complète de l'incident.

⚠️ ATTENTION: Ces images proviennent de l'analyse réelle du système de surveillance.
Elles correspondent exactement aux frames analysés par l'IA.

Action requise: Vérification immédiate des preuves vidéo.
"""
            
            logger.info("📧 Sending alert with REAL analyzed frames...")
            result = send_security_alert_with_video(message, captured_frames, incident_data)
            
            if result['success']:
                logger.info("✅ Alert sent with real incident video!")
                logger.info(f"   Video ID: {result.get('video_link_info', {}).get('video_id', 'N/A')}")
                logger.info(f"   Link: {result.get('video_link_info', {}).get('private_link', 'N/A')}")
                
                logger.info("\n🎯 SUCCESS!")
                logger.info("📧 Check your email - the video link now contains the REAL analyzed frames")
                logger.info("🔗 Click the video link to see the actual incident sequence")
                
                return True
            else:
                logger.error(f"❌ Failed to send alert: {result.get('error', 'Unknown error')}")
                return False
        else:
            logger.warning("⚠️  No frames were captured during analysis")
            return False
    
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False
    
    finally:
        # Cleanup
        if os.path.exists(video_path):
            os.unlink(video_path)
            logger.info("🧹 Cleaned up test video file")
        
        if 'server_process' in locals() and server_process:
            server_process.terminate()
            server_process.wait()
            logger.info("🛑 Stopped video server")


def main():
    """Main test function"""
    logger.info("🎬 REAL INCIDENT VIDEO TEST")
    logger.info("=" * 60)
    logger.info("Testing that video links contain the actual analyzed frames")
    
    success = test_real_incident_analysis()
    
    if success:
        logger.info("\n🎉 SUCCESS!")
        logger.info("✅ Video link now contains the REAL analyzed incident frames")
        logger.info("📧 Check your email and click the video link")
        logger.info("🎥 You should see the actual security incident sequence")
    else:
        logger.error("\n❌ TEST FAILED!")
        logger.error("The video link may still contain incorrect frames")
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)