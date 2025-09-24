#!/usr/bin/env python3
"""
Demo script for Multi-Source Video Analysis
Shows how to set up and run analysis with multiple video sources
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


def demo_with_video_files():
    """Demo using local video files"""
    print("🎬 Multi-Source Video Analysis Demo - Video Files")
    
    # Look for buffer video files in the current directory
    video_files = []
    for i in range(1, 11):  # Look for buffer_video_1.mp4 to buffer_video_10.mp4
        video_path = f"buffer_video_{i}.mp4"
        if os.path.exists(video_path):
            video_files.append(video_path)
    
    if len(video_files) < 2:
        print("❌ Need at least 2 video files for demo")
        print("   Looking for buffer_video_*.mp4 files in current directory")
        return False
    
    print(f"✅ Found {len(video_files)} video files for demo")
    
    # Create analyzer
    analyzer = MultiSourceVideoAnalyzer()
    analyzer.analysis_interval = 15  # Analyze every 15 seconds for demo
    
    # Add video sources (limit to first 6 for demo)
    demo_files = video_files[:6]
    for i, video_file in enumerate(demo_files):
        source_id = f"demo_video_{i+1}"
        source_name = f"Demo Camera {i+1}"
        analyzer.add_video_source(source_id, video_file, source_name)
        print(f"   Added {source_name}: {video_file}")
    
    print(f"\n📊 Demo Configuration:")
    print(f"   Total sources: {len(demo_files)}")
    
    if len(demo_files) >= 4:
        num_groups = len(demo_files) // 4
        remainder = len(demo_files) % 4
        print(f"   Will create {num_groups} aggregated groups of 4 cameras")
        if remainder > 0:
            print(f"   {remainder} cameras will be analyzed individually")
    else:
        print(f"   All {len(demo_files)} cameras will be analyzed individually")
    
    print(f"\n🎯 Starting demo analysis...")
    
    try:
        if analyzer.start_analysis():
            print("✅ Multi-source analysis started successfully!")
            print("🔍 Monitoring for security incidents...")
            print("   Press Ctrl+C to stop the demo")
            
            # Run for demo duration
            demo_duration = 120  # 2 minutes
            start_time = time.time()
            
            while time.time() - start_time < demo_duration:
                time.sleep(10)
                
                # Show status every 30 seconds
                if int(time.time() - start_time) % 30 == 0:
                    status = analyzer.get_status()
                    print(f"\n📊 Status: {status['active_sources']}/{status['total_sources']} sources active")
                    
                    for source_id, source_info in status['sources'].items():
                        status_icon = "🟢" if source_info['active'] else "🔴"
                        print(f"   {status_icon} {source_info['name']}: {source_info['frame_count']} frames")
            
            print(f"\n✅ Demo completed after {demo_duration} seconds")
        
        else:
            print("❌ Failed to start multi-source analysis")
            return False
    
    except KeyboardInterrupt:
        print(f"\n⏹️ Demo stopped by user")
    
    finally:
        analyzer.stop_analysis()
        print("🛑 Demo analysis stopped")
    
    return True


def demo_with_rtsp_streams():
    """Demo using RTSP streams"""
    print("📡 Multi-Source Video Analysis Demo - RTSP Streams")
    
    # Example RTSP URLs (these would need to be real streams)
    rtsp_sources = [
        ("camera_1", "rtsp://localhost:8554/camera1", "Front Door Camera"),
        ("camera_2", "rtsp://localhost:8554/camera2", "Sales Floor Camera"),
        ("camera_3", "rtsp://localhost:8554/camera3", "Checkout Camera"),
        ("camera_4", "rtsp://localhost:8554/camera4", "Storage Room Camera"),
        ("camera_5", "rtsp://localhost:8554/camera5", "Back Office Camera"),
    ]
    
    print(f"📹 Demo RTSP Sources:")
    for source_id, rtsp_url, name in rtsp_sources:
        print(f"   {name}: {rtsp_url}")
    
    # Create analyzer
    analyzer = MultiSourceVideoAnalyzer()
    analyzer.analysis_interval = 20  # Analyze every 20 seconds
    
    # Add RTSP sources
    for source_id, rtsp_url, name in rtsp_sources:
        analyzer.add_video_source(source_id, rtsp_url, name)
    
    print(f"\n📊 Demo Configuration:")
    print(f"   Total sources: {len(rtsp_sources)}")
    print(f"   Will create 1 aggregated group of 4 cameras")
    print(f"   1 camera will be analyzed individually")
    
    print(f"\n🎯 Starting RTSP demo analysis...")
    print("⚠️  Note: This demo requires actual RTSP streams to be available")
    
    try:
        if analyzer.start_analysis():
            print("✅ Multi-source RTSP analysis started!")
            print("🔍 Monitoring for security incidents...")
            print("   Press Ctrl+C to stop the demo")
            
            # Monitor for a while
            while True:
                time.sleep(30)
                status = analyzer.get_status()
                print(f"\n📊 Status: {status['active_sources']}/{status['total_sources']} sources active")
                
                if status['active_sources'] == 0:
                    print("⚠️  No active sources - check RTSP stream availability")
        
        else:
            print("❌ Failed to start RTSP analysis")
            return False
    
    except KeyboardInterrupt:
        print(f"\n⏹️ Demo stopped by user")
    
    finally:
        analyzer.stop_analysis()
        print("🛑 Demo analysis stopped")
    
    return True


def demo_configuration_management():
    """Demo configuration management features"""
    print("⚙️ Multi-Source Configuration Management Demo")
    
    # Create configuration manager
    config_manager = MultiSourceConfig("demo_config.json")
    
    print(f"\n➕ Adding demo video sources...")
    
    # Add some demo sources
    demo_sources = [
        ("demo_cam_1", "rtsp://demo.server/cam1", "Demo Camera 1", "Entrance"),
        ("demo_cam_2", "rtsp://demo.server/cam2", "Demo Camera 2", "Sales Floor"),
        ("demo_cam_3", "rtsp://demo.server/cam3", "Demo Camera 3", "Checkout"),
        ("demo_cam_4", "rtsp://demo.server/cam4", "Demo Camera 4", "Storage"),
        ("demo_cam_5", "rtsp://demo.server/cam5", "Demo Camera 5", "Office"),
        ("demo_cam_6", "rtsp://demo.server/cam6", "Demo Camera 6", "Parking"),
    ]
    
    for source_id, rtsp_url, name, location in demo_sources:
        config_manager.add_video_source(
            source_id, rtsp_url, name,
            location=location,
            priority="normal",
            description=f"Demo source for {location}"
        )
        print(f"   ✅ Added {name}")
    
    # Show configuration
    sources = config_manager.list_video_sources()
    print(f"\n📹 Configured Sources ({len(sources)} total):")
    for source_id, source_config in sources.items():
        print(f"   {source_config['name']} ({source_id})")
        print(f"      Location: {source_config['location']}")
        print(f"      Priority: {source_config['priority']}")
    
    # Show analysis organization
    analysis_config = config_manager.get_sources_for_analysis()
    print(f"\n📊 Analysis Organization:")
    print(f"   Total sources: {analysis_config['total_sources']}")
    print(f"   Individual sources: {len(analysis_config['individual_sources'])}")
    print(f"   Aggregated groups: {len(analysis_config['aggregated_groups'])}")
    
    for i, group in enumerate(analysis_config['aggregated_groups']):
        cameras = ', '.join(group['source_names'])
        print(f"   Group {i+1}: {cameras}")
    
    if analysis_config['individual_sources']:
        individual_names = []
        for source_id in analysis_config['individual_sources']:
            source_config = config_manager.get_video_source(source_id)
            if source_config:
                individual_names.append(source_config['name'])
        print(f"   Individual: {', '.join(individual_names)}")
    
    # Update analysis settings
    print(f"\n⚙️ Updating analysis settings...")
    config_manager.update_analysis_settings(
        analysis_interval=15,
        aggregation_threshold=4,
        max_concurrent_analyses=6
    )
    
    settings = config_manager.get_analysis_settings()
    print(f"   Analysis interval: {settings['analysis_interval']}s")
    print(f"   Aggregation threshold: {settings['aggregation_threshold']}")
    print(f"   Max concurrent analyses: {settings['max_concurrent_analyses']}")
    
    # Validate configuration
    validation = config_manager.validate_configuration()
    print(f"\n✅ Configuration validation: {'Valid' if validation['valid'] else 'Invalid'}")
    if validation['warnings']:
        print(f"   Warnings: {validation['warnings']}")
    
    # Export configuration
    export_path = config_manager.export_config("demo_export.json")
    if export_path:
        print(f"✅ Configuration exported to: {export_path}")
    
    print(f"\n🧹 Cleaning up demo configuration...")
    try:
        os.unlink("demo_config.json")
        if os.path.exists("demo_export.json"):
            os.unlink("demo_export.json")
        print("✅ Demo files cleaned up")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")


def main():
    """Main demo function"""
    print("🎯 Multi-Source Video Analysis System Demo")
    print("=" * 50)
    
    demos = [
        ("1", "Video Files Demo", demo_with_video_files),
        ("2", "RTSP Streams Demo", demo_with_rtsp_streams),
        ("3", "Configuration Management Demo", demo_configuration_management),
    ]
    
    print("\nAvailable demos:")
    for demo_id, demo_name, _ in demos:
        print(f"   {demo_id}. {demo_name}")
    
    print("   a. Run all demos")
    print("   q. Quit")
    
    while True:
        try:
            choice = input("\nSelect demo (1-3, a, q): ").strip().lower()
            
            if choice == 'q':
                print("👋 Goodbye!")
                break
            
            elif choice == 'a':
                print("\n🚀 Running all demos...")
                for demo_id, demo_name, demo_func in demos:
                    print(f"\n{'='*20} {demo_name} {'='*20}")
                    try:
                        demo_func()
                    except Exception as e:
                        print(f"❌ Demo {demo_name} failed: {e}")
                    print(f"{'='*50}")
                    time.sleep(2)
                break
            
            elif choice in ['1', '2', '3']:
                demo_index = int(choice) - 1
                demo_id, demo_name, demo_func = demos[demo_index]
                
                print(f"\n🚀 Running {demo_name}...")
                print("=" * 50)
                
                try:
                    demo_func()
                except Exception as e:
                    print(f"❌ Demo failed: {e}")
                
                print("=" * 50)
                break
            
            else:
                print("❌ Invalid choice. Please select 1-3, a, or q.")
        
        except KeyboardInterrupt:
            print("\n👋 Demo interrupted. Goodbye!")
            break
        except EOFError:
            print("\n👋 Goodbye!")
            break


if __name__ == '__main__':
    main()