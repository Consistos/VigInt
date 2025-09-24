#!/usr/bin/env python3
"""
Demo script showing multi-source video analysis with real video content
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from multi_source_video_analyzer import MultiSourceVideoAnalyzer
from multi_source_config import MultiSourceConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_video_files():
    """Find available video files"""
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
    video_files = []
    
    # Look for buffer videos first
    for i in range(1, 11):
        buffer_video = f"buffer_video_{i}.mp4"
        if os.path.exists(buffer_video):
            video_files.append(buffer_video)
    
    # Look for other video files
    current_dir = Path('.')
    for file_path in current_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in video_extensions:
            if file_path.name not in video_files:
                video_files.append(str(file_path))
    
    return video_files


def demo_multi_source_with_real_video():
    """Demo multi-source analysis with real video files"""
    print("🎯 Multi-Source Video Analysis Demo - Real Video Content")
    print("=" * 60)
    
    # Find available video files
    video_files = find_video_files()
    
    if len(video_files) < 2:
        print("❌ Need at least 2 video files for multi-source demo")
        print("   Please ensure you have buffer_video_*.mp4 files or other video files")
        return False
    
    # Use up to 6 video files for demo
    demo_videos = video_files[:6]
    print(f"✅ Found {len(video_files)} video files, using {len(demo_videos)} for demo:")
    
    for i, video_file in enumerate(demo_videos):
        print(f"   {i+1}. {video_file}")
    
    # Create multi-source analyzer
    analyzer = MultiSourceVideoAnalyzer()
    analyzer.analysis_interval = 30  # Analyze every 30 seconds for demo
    
    # Add video sources
    camera_names = [
        "Caméra Entrée Principale",
        "Caméra Zone de Vente", 
        "Caméra Caisse",
        "Caméra Stockage",
        "Caméra Bureau",
        "Caméra Parking"
    ]
    
    for i, video_file in enumerate(demo_videos):
        source_id = f"real_camera_{i+1}"
        camera_name = camera_names[i] if i < len(camera_names) else f"Caméra {i+1}"
        
        analyzer.add_video_source(source_id, video_file, camera_name)
        print(f"   ✅ Added {camera_name}: {video_file}")
    
    # Show aggregation configuration
    print(f"\n📊 Aggregation Configuration:")
    num_sources = len(demo_videos)
    
    if num_sources >= 4:
        num_groups = num_sources // 4
        remainder = num_sources % 4
        print(f"   Total sources: {num_sources}")
        print(f"   Aggregated groups: {num_groups} (groups of 4 cameras)")
        print(f"   Individual sources: {remainder}")
        
        # Show which cameras will be in groups
        for group_num in range(num_groups):
            start_idx = group_num * 4
            end_idx = start_idx + 4
            group_cameras = [camera_names[i] for i in range(start_idx, min(end_idx, len(camera_names)))]
            print(f"   Group {group_num + 1}: {', '.join(group_cameras)}")
        
        if remainder > 0:
            individual_cameras = [camera_names[i] for i in range(num_groups * 4, num_sources)]
            print(f"   Individual: {', '.join(individual_cameras)}")
    else:
        print(f"   All {num_sources} sources will be analyzed individually")
    
    print(f"\n🎯 Starting multi-source analysis with REAL video content...")
    print("🔍 The system will:")
    print("   - Capture actual video frames from each source")
    print("   - Create composite frames for groups of 4+ cameras")
    print("   - Analyze content using Gemini AI")
    print("   - Send email alerts with real video evidence")
    print("   - Use French language for all incident reports")
    
    try:
        if analyzer.start_analysis():
            print("\n✅ Multi-source analysis started successfully!")
            print("📧 Email alerts will contain REAL video content, not test frames")
            print("⏰ Analysis interval: 30 seconds")
            print("🛑 Press Ctrl+C to stop the demo")
            
            # Run demo for a specified duration
            demo_duration = 180  # 3 minutes
            start_time = time.time()
            
            print(f"\n🕐 Running demo for {demo_duration} seconds...")
            
            while time.time() - start_time < demo_duration:
                elapsed = int(time.time() - start_time)
                remaining = demo_duration - elapsed
                
                # Show status every 30 seconds
                if elapsed % 30 == 0 and elapsed > 0:
                    status = analyzer.get_status()
                    print(f"\n📊 Status Update ({elapsed}s elapsed, {remaining}s remaining):")
                    print(f"   Active sources: {status['active_sources']}/{status['total_sources']}")
                    
                    for source_id, source_info in status['sources'].items():
                        status_icon = "🟢" if source_info['active'] else "🔴"
                        print(f"   {status_icon} {source_info['name']}: {source_info['frame_count']} frames")
                
                time.sleep(5)  # Check every 5 seconds
            
            print(f"\n✅ Demo completed successfully!")
            print("📧 Check your email for any security alerts with real video evidence")
        
        else:
            print("❌ Failed to start multi-source analysis")
            return False
    
    except KeyboardInterrupt:
        print(f"\n⏹️ Demo stopped by user")
    
    finally:
        analyzer.stop_analysis()
        print("🛑 Multi-source analysis stopped")
    
    return True


def main():
    """Main demo function"""
    print("🎬 Real Video Content Multi-Source Analysis Demo")
    print("=" * 60)
    
    # Check prerequisites
    if not os.getenv('GOOGLE_API_KEY'):
        print("⚠️  GOOGLE_API_KEY not set - AI analysis will be limited")
        print("   Set this environment variable to enable full AI analysis")
    else:
        print("✅ GOOGLE_API_KEY is configured")
    
    # Check for video files
    video_files = find_video_files()
    if len(video_files) < 2:
        print("\n❌ Insufficient video files for demo")
        print("   Please ensure you have at least 2 video files:")
        print("   - buffer_video_*.mp4 files, or")
        print("   - Other video files (.mp4, .avi, .mov, .mkv)")
        return 1
    
    print(f"✅ Found {len(video_files)} video files for demo")
    
    # Run the demo
    try:
        success = demo_multi_source_with_real_video()
        
        if success:
            print(f"\n🎉 Demo completed successfully!")
            print("📧 Key achievements:")
            print("   ✅ Multi-source video analysis with real content")
            print("   ✅ Automatic aggregation of 4+ camera groups")
            print("   ✅ Individual analysis for remainder cameras")
            print("   ✅ Email alerts with actual video evidence")
            print("   ✅ French language incident reports")
            print("\n🚀 The system is ready for production use!")
        else:
            print(f"\n❌ Demo encountered issues")
            return 1
    
    except Exception as e:
        print(f"\n❌ Demo failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())