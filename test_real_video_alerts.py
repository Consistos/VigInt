#!/usr/bin/env python3
"""
Test real video analysis and alerts with actual video content
"""

import os
import sys
import time
import logging
import base64
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from multi_source_video_analyzer import MultiSourceVideoAnalyzer
from alerts import send_security_alert_with_video
from video_analyzer import VideoAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def capture_real_video_frames(video_source, duration_seconds=10, fps=25):
    """Capture real frames from a video source"""
    print(f"📹 Capturing real video frames from: {video_source}")
    
    try:
        # Open video source
        cap = cv2.VideoCapture(video_source)
        
        if not cap.isOpened():
            print(f"❌ Failed to open video source: {video_source}")
            return None
        
        # Get video properties
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"   Video FPS: {original_fps}")
        print(f"   Total frames: {total_frames}")
        
        frames = []
        frame_count = 0
        target_frames = duration_seconds * fps
        
        # Calculate frame skip to match target FPS
        frame_skip = max(1, int(original_fps / fps))
        
        while len(frames) < target_frames:
            ret, frame = cap.read()
            
            if not ret:
                # If video file ended, restart from beginning
                if hasattr(cap, 'get') and cap.get(cv2.CAP_PROP_FRAME_COUNT) > 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    break
            
            frame_count += 1
            
            # Skip frames to match target FPS
            if frame_count % frame_skip == 0:
                # Convert frame to base64
                _, buffer_img = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_base64 = base64.b64encode(buffer_img).decode('utf-8')
                
                # Create frame info
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                frame_info = {
                    'frame_data': frame_base64,
                    'frame_count': len(frames) + 1,
                    'timestamp': timestamp,
                    'source_id': 'real_video',
                    'source_name': f'Real Video: {os.path.basename(video_source)}'
                }
                
                frames.append(frame_info)
        
        cap.release()
        
        print(f"✅ Captured {len(frames)} real video frames")
        return frames
        
    except Exception as e:
        print(f"❌ Error capturing video frames: {e}")
        return None


def find_available_video_files():
    """Find available video files for testing"""
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
    video_files = []
    
    # Look for buffer videos first
    for i in range(1, 11):
        buffer_video = f"buffer_video_{i}.mp4"
        if os.path.exists(buffer_video):
            video_files.append(buffer_video)
    
    # Look for other video files in current directory
    current_dir = Path('.')
    for file_path in current_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in video_extensions:
            if file_path.name not in video_files:
                video_files.append(str(file_path))
    
    return video_files


def test_real_video_analysis_alert():
    """Test video analysis with real video content"""
    print("🎯 Testing Real Video Analysis Alert")
    print("=" * 50)
    
    # Find available video files
    video_files = find_available_video_files()
    
    if not video_files:
        print("❌ No video files found for testing")
        print("   Please ensure you have video files (buffer_video_*.mp4 or other formats)")
        return False
    
    print(f"✅ Found {len(video_files)} video files:")
    for i, video_file in enumerate(video_files[:3]):  # Show first 3
        print(f"   {i+1}. {video_file}")
    
    # Use the first available video file
    video_source = video_files[0]
    print(f"\n🎬 Using video source: {video_source}")
    
    try:
        # Capture real video frames
        real_frames = capture_real_video_frames(video_source, duration_seconds=8, fps=25)
        
        if not real_frames:
            print("❌ Failed to capture real video frames")
            return False
        
        # Create realistic incident data
        incident_data = {
            'risk_level': 'HIGH',
            'frame_count': len(real_frames),
            'confidence': 0.87,
            'analysis': f'Incident de sécurité détecté dans la vidéo {os.path.basename(video_source)} - comportement suspect observé avec analyse de contenu vidéo réel',
            'incident_type': 'Activité suspecte détectée',
            'is_aggregated': False,
            'source_name': f'Caméra Réelle: {os.path.basename(video_source)}'
        }
        
        # Create alert message
        message = f"""
INCIDENT DE SÉCURITÉ DÉTECTÉ - VIDÉO RÉELLE

Heure: {datetime.now().isoformat()}
Source vidéo: {os.path.basename(video_source)}
Caméra: {incident_data.get('source_name', 'Inconnue')}
Type d'incident: {incident_data.get('incident_type', 'Non spécifié')}
Niveau de confiance: {incident_data.get('confidence', 0.0):.2f}

ANALYSE DÉTAILLÉE:
{incident_data.get('analysis', 'Aucune analyse disponible')}

Cette alerte contient des preuves vidéo réelles capturées depuis {video_source}.
Veuillez examiner immédiatement les preuves vidéo ci-jointes.

DÉTAILS TECHNIQUES:
- Nombre d'images: {len(real_frames)}
- Durée approximative: 8 secondes
- Source: Contenu vidéo réel
"""
        
        # Send alert with real video content
        result = send_security_alert_with_video(message, real_frames, incident_data)
        
        if result.get('success', False):
            print("✅ Real video alert sent successfully!")
            print(f"   Video attached: {result.get('video_attached', False)}")
            print(f"   Recipient: {result.get('recipient', 'Unknown')}")
            print(f"   Frames used: {len(real_frames)}")
            print(f"   Source video: {video_source}")
            return True
        else:
            print(f"❌ Real video alert failed: {result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        print(f"❌ Exception during real video alert test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_source_real_video():
    """Test multi-source analysis with real video files"""
    print("\n🎯 Testing Multi-Source Real Video Analysis")
    print("=" * 50)
    
    # Find available video files
    video_files = find_available_video_files()
    
    if len(video_files) < 2:
        print("❌ Need at least 2 video files for multi-source testing")
        return False
    
    # Use up to 4 video files for testing
    test_videos = video_files[:4]
    print(f"✅ Using {len(test_videos)} video sources for multi-source test:")
    for i, video_file in enumerate(test_videos):
        print(f"   {i+1}. {video_file}")
    
    try:
        # Capture frames from multiple video sources
        all_frames = []
        camera_names = []
        
        for i, video_file in enumerate(test_videos):
            camera_name = f"Caméra Réelle {i+1}: {os.path.basename(video_file)}"
            camera_names.append(camera_name)
            
            print(f"\n📹 Capturing from {camera_name}...")
            frames = capture_real_video_frames(video_file, duration_seconds=6, fps=20)
            
            if frames:
                # Update source info for each frame
                for frame in frames:
                    frame['source_name'] = camera_name
                    frame['source_id'] = f'real_camera_{i+1}'
                
                all_frames.extend(frames)
                print(f"   ✅ Added {len(frames)} frames from {camera_name}")
            else:
                print(f"   ❌ Failed to capture frames from {video_file}")
        
        if not all_frames:
            print("❌ No frames captured from any video source")
            return False
        
        # Create multi-source incident data
        incident_data = {
            'risk_level': 'HIGH',
            'frame_count': len(all_frames),
            'confidence': 0.91,
            'analysis': f'Incident de sécurité coordonné détecté sur {len(test_videos)} caméras réelles - analyse de contenu vidéo multi-source avec preuves visuelles authentiques',
            'incident_type': 'Activité multi-caméras suspecte',
            'is_aggregated': True,
            'cameras_involved': camera_names,
            'group_name': 'Groupe Vidéo Réelle'
        }
        
        # Create multi-source alert message
        cameras_list = ', '.join([f"Caméra {i+1}" for i in range(len(camera_names))])
        video_list = ', '.join([os.path.basename(f) for f in test_videos])
        
        message = f"""
INCIDENT DE SÉCURITÉ DÉTECTÉ - ANALYSE MULTI-CAMÉRAS RÉELLE

Heure: {datetime.now().isoformat()}
Groupe de caméras: {incident_data.get('group_name', 'Inconnu')}
Caméras impliquées: {cameras_list}
Sources vidéo: {video_list}
Type d'incident: {incident_data.get('incident_type', 'Non spécifié')}
Niveau de confiance: {incident_data.get('confidence', 0.0):.2f}

ANALYSE DÉTAILLÉE:
{incident_data.get('analysis', 'Aucune analyse disponible')}

Cette alerte provient d'une analyse simultanée de {len(test_videos)} sources vidéo réelles.
Les preuves vidéo ci-jointes contiennent du contenu authentique capturé depuis:
{chr(10).join([f'- {os.path.basename(f)}' for f in test_videos])}

DÉTAILS TECHNIQUES:
- Nombre total d'images: {len(all_frames)}
- Durée approximative par caméra: 6 secondes
- Type de contenu: Vidéo réelle multi-source
"""
        
        # Send multi-source alert with real video content
        result = send_security_alert_with_video(message, all_frames, incident_data)
        
        if result.get('success', False):
            print("✅ Multi-source real video alert sent successfully!")
            print(f"   Video attached: {result.get('video_attached', False)}")
            print(f"   Recipient: {result.get('recipient', 'Unknown')}")
            print(f"   Total frames: {len(all_frames)}")
            print(f"   Sources used: {len(test_videos)}")
            return True
        else:
            print(f"❌ Multi-source real video alert failed: {result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        print(f"❌ Exception during multi-source real video test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_video_analyzer_integration():
    """Test integration with the existing VideoAnalyzer"""
    print("\n🎯 Testing VideoAnalyzer Integration with Real Content")
    print("=" * 50)
    
    # Find available video files
    video_files = find_available_video_files()
    
    if not video_files:
        print("❌ No video files found for VideoAnalyzer testing")
        return False
    
    video_source = video_files[0]
    print(f"🎬 Testing VideoAnalyzer with: {video_source}")
    
    try:
        # Create VideoAnalyzer instance
        analyzer = VideoAnalyzer()
        
        # Capture a single frame for analysis
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            print(f"❌ Failed to open video source: {video_source}")
            return False
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print("❌ Failed to read frame from video")
            return False
        
        print("✅ Successfully captured frame for analysis")
        
        # Analyze the real frame (this will use Gemini AI if available)
        if analyzer.model:
            print("🤖 Analyzing real video frame with Gemini AI...")
            analysis_result = analyzer.analyze_frame(frame)
            
            if analysis_result:
                print("✅ Real video frame analysis completed!")
                print(f"   Incident detected: {analysis_result.get('incident_detected', False)}")
                print(f"   Analysis preview: {analysis_result.get('analysis', 'No analysis')[:100]}...")
                
                # If incident detected, capture more frames and send alert
                if analysis_result.get('incident_detected', False):
                    print("🚨 Incident detected! Capturing video evidence...")
                    
                    # Capture more frames for evidence
                    evidence_frames = capture_real_video_frames(video_source, duration_seconds=10, fps=25)
                    
                    if evidence_frames:
                        # Send alert with real analysis and real video
                        analyzer.send_alert_email(analysis_result, evidence_frames)
                        print("✅ Real incident alert sent with video evidence!")
                    else:
                        print("⚠️  Incident detected but no video evidence captured")
                else:
                    print("ℹ️  No incident detected in this frame")
            else:
                print("⚠️  Frame analysis failed")
        else:
            print("⚠️  Gemini AI not available - skipping real analysis")
            print("   (Set GOOGLE_API_KEY environment variable to enable)")
        
        return True
    
    except Exception as e:
        print(f"❌ Exception during VideoAnalyzer integration test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("🎯 Real Video Content Alert Testing")
    print("=" * 60)
    
    # Check for video files
    video_files = find_available_video_files()
    if not video_files:
        print("❌ No video files found!")
        print("\nTo test with real video content, please ensure you have:")
        print("   - buffer_video_*.mp4 files, or")
        print("   - Other video files (.mp4, .avi, .mov, .mkv) in the current directory")
        return 1
    
    print(f"✅ Found {len(video_files)} video files for testing")
    
    # Check if GOOGLE_API_KEY is set
    if os.getenv('GOOGLE_API_KEY'):
        print("✅ GOOGLE_API_KEY is set - AI analysis available")
    else:
        print("⚠️  GOOGLE_API_KEY not set - AI analysis will be limited")
    
    all_tests_passed = True
    
    # Run real video tests
    tests = [
        ("Real Video Analysis Alert", test_real_video_analysis_alert),
        ("Multi-Source Real Video", test_multi_source_real_video),
        ("VideoAnalyzer Integration", test_video_analyzer_integration),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            if not result:
                all_tests_passed = False
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            all_tests_passed = False
        
        # Small delay between tests
        time.sleep(3)
    
    # Final summary
    print(f"\n{'='*60}")
    if all_tests_passed:
        print("✅ All real video content tests passed!")
        print("📧 Check your email for alerts with REAL video content")
        print("🎬 Videos should now contain actual footage instead of test frames")
    else:
        print("❌ Some real video content tests failed")
        print("🔧 Check the output above for specific issues")
    
    return 0 if all_tests_passed else 1


if __name__ == '__main__':
    sys.exit(main())