#!/usr/bin/env python3
"""
Multi-Source Video Analysis Runner
Command-line interface for managing and running multi-source video analysis
"""

import os
import sys
import time
import logging
import argparse
import signal
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from multi_source_video_analyzer import MultiSourceVideoAnalyzer
from multi_source_config import MultiSourceConfig
from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MultiSourceRunner:
    """Manages the multi-source video analysis system"""
    
    def __init__(self):
        self.config_manager = MultiSourceConfig()
        self.analyzer = None
        self.running = False
    
    def setup_analyzer(self):
        """Setup the video analyzer with configured sources"""
        try:
            # Create analyzer
            self.analyzer = MultiSourceVideoAnalyzer()
            
            # Get analysis settings
            analysis_settings = self.config_manager.get_analysis_settings()
            self.analyzer.analysis_interval = analysis_settings.get("analysis_interval", 10)
            
            # Add configured video sources
            sources = self.config_manager.list_video_sources(enabled_only=True)
            analysis_sources = {k: v for k, v in sources.items() 
                              if v.get("analysis_enabled", True)}
            
            if not analysis_sources:
                logger.error("No video sources configured for analysis")
                return False
            
            logger.info(f"Setting up analyzer with {len(analysis_sources)} video sources")
            
            for source_id, source_config in analysis_sources.items():
                self.analyzer.add_video_source(
                    source_id,
                    source_config["rtsp_url"],
                    source_config["name"]
                )
            
            logger.info("Multi-source analyzer setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up analyzer: {e}")
            return False
    
    def start_analysis(self):
        """Start the multi-source video analysis"""
        if not self.analyzer:
            if not self.setup_analyzer():
                return False
        
        logger.info("Starting multi-source video analysis...")
        
        if self.analyzer.start_analysis():
            self.running = True
            logger.info("✅ Multi-source video analysis started successfully")
            
            # Show analysis configuration
            analysis_config = self.config_manager.get_sources_for_analysis()
            logger.info(f"📊 Analysis Configuration:")
            logger.info(f"   Total sources: {analysis_config['total_sources']}")
            logger.info(f"   Individual sources: {len(analysis_config['individual_sources'])}")
            logger.info(f"   Aggregated groups: {len(analysis_config['aggregated_groups'])}")
            
            for i, group in enumerate(analysis_config['aggregated_groups']):
                cameras = ', '.join(group['source_names'])
                logger.info(f"   Group {i+1}: {cameras}")
            
            return True
        else:
            logger.error("❌ Failed to start multi-source video analysis")
            return False
    
    def stop_analysis(self):
        """Stop the multi-source video analysis"""
        if self.analyzer and self.running:
            logger.info("Stopping multi-source video analysis...")
            self.analyzer.stop_analysis()
            self.running = False
            logger.info("✅ Multi-source video analysis stopped")
    
    def show_status(self):
        """Show current status of the analysis system"""
        if not self.analyzer:
            print("❌ Analyzer not initialized")
            return
        
        status = self.analyzer.get_status()
        
        print(f"\n📊 Multi-Source Video Analysis Status")
        print(f"   Running: {'✅ Yes' if status['running'] else '❌ No'}")
        print(f"   Total sources: {status['total_sources']}")
        print(f"   Active sources: {status['active_sources']}")
        
        print(f"\n📹 Video Sources:")
        for source_id, source_info in status['sources'].items():
            status_icon = "🟢" if source_info['active'] else "🔴"
            print(f"   {status_icon} {source_info['name']} ({source_id})")
            print(f"      URL: {source_info['rtsp_url']}")
            print(f"      Frames: {source_info['frame_count']}")
            if source_info['last_frame_time']:
                last_frame_ago = time.time() - source_info['last_frame_time']
                print(f"      Last frame: {last_frame_ago:.1f}s ago")
    
    def add_source_interactive(self):
        """Interactively add a video source"""
        print("\n➕ Add Video Source")
        
        source_id = input("Source ID: ").strip()
        if not source_id:
            print("❌ Source ID is required")
            return False
        
        if self.config_manager.get_video_source(source_id):
            print(f"❌ Source {source_id} already exists")
            return False
        
        rtsp_url = input("RTSP URL: ").strip()
        if not rtsp_url:
            print("❌ RTSP URL is required")
            return False
        
        name = input("Name (optional): ").strip()
        location = input("Location (optional): ").strip()
        description = input("Description (optional): ").strip()
        
        priority = input("Priority (low/normal/high) [normal]: ").strip().lower()
        if priority not in ['low', 'normal', 'high']:
            priority = 'normal'
        
        try:
            self.config_manager.add_video_source(
                source_id, rtsp_url, name,
                location=location,
                description=description,
                priority=priority
            )
            print(f"✅ Added video source {source_id}")
            
            # If analyzer is running, add the source
            if self.analyzer and self.running:
                self.analyzer.add_video_source(source_id, rtsp_url, name)
                print(f"✅ Source {source_id} added to running analyzer")
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding source: {e}")
            return False
    
    def remove_source_interactive(self):
        """Interactively remove a video source"""
        sources = self.config_manager.list_video_sources()
        if not sources:
            print("❌ No video sources configured")
            return False
        
        print("\n➖ Remove Video Source")
        print("Available sources:")
        for source_id, source_config in sources.items():
            print(f"   {source_id}: {source_config['name']}")
        
        source_id = input("Source ID to remove: ").strip()
        if not source_id or source_id not in sources:
            print("❌ Invalid source ID")
            return False
        
        confirm = input(f"Remove source {source_id}? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Cancelled")
            return False
        
        try:
            self.config_manager.remove_video_source(source_id)
            print(f"✅ Removed video source {source_id}")
            
            # If analyzer is running, remove the source
            if self.analyzer and self.running:
                self.analyzer.remove_video_source(source_id)
                print(f"✅ Source {source_id} removed from running analyzer")
            
            return True
            
        except Exception as e:
            print(f"❌ Error removing source: {e}")
            return False
    
    def list_sources(self):
        """List all configured video sources"""
        sources = self.config_manager.list_video_sources()
        
        if not sources:
            print("❌ No video sources configured")
            return
        
        print(f"\n📹 Configured Video Sources ({len(sources)} total):")
        
        for source_id, source_config in sources.items():
            enabled_icon = "✅" if source_config.get("enabled", True) else "❌"
            analysis_icon = "🔍" if source_config.get("analysis_enabled", True) else "⏸️"
            
            print(f"\n   {enabled_icon} {analysis_icon} {source_config['name']} ({source_id})")
            print(f"      URL: {source_config['rtsp_url']}")
            print(f"      Location: {source_config.get('location', 'Not specified')}")
            print(f"      Priority: {source_config.get('priority', 'normal')}")
            print(f"      Created: {source_config.get('created_at', 'Unknown')}")
    
    def configure_analysis_settings(self):
        """Configure analysis settings"""
        current_settings = self.config_manager.get_analysis_settings()
        
        print(f"\n⚙️ Analysis Settings")
        print(f"Current settings:")
        for key, value in current_settings.items():
            print(f"   {key}: {value}")
        
        print(f"\nEnter new values (press Enter to keep current):")
        
        new_settings = {}
        
        # Analysis interval
        interval = input(f"Analysis interval ({current_settings.get('analysis_interval', 10)}s): ").strip()
        if interval:
            try:
                new_settings['analysis_interval'] = int(interval)
            except ValueError:
                print("❌ Invalid interval, keeping current value")
        
        # Aggregation threshold
        threshold = input(f"Aggregation threshold ({current_settings.get('aggregation_threshold', 4)}): ").strip()
        if threshold:
            try:
                new_settings['aggregation_threshold'] = int(threshold)
            except ValueError:
                print("❌ Invalid threshold, keeping current value")
        
        # Max concurrent analyses
        max_concurrent = input(f"Max concurrent analyses ({current_settings.get('max_concurrent_analyses', 4)}): ").strip()
        if max_concurrent:
            try:
                new_settings['max_concurrent_analyses'] = int(max_concurrent)
            except ValueError:
                print("❌ Invalid value, keeping current value")
        
        # Frame buffer duration
        buffer_duration = input(f"Frame buffer duration ({current_settings.get('frame_buffer_duration', 10)}s): ").strip()
        if buffer_duration:
            try:
                new_settings['frame_buffer_duration'] = int(buffer_duration)
            except ValueError:
                print("❌ Invalid duration, keeping current value")
        
        if new_settings:
            self.config_manager.update_analysis_settings(**new_settings)
            print("✅ Analysis settings updated")
            
            # Update analyzer if running
            if self.analyzer:
                if 'analysis_interval' in new_settings:
                    self.analyzer.analysis_interval = new_settings['analysis_interval']
                    print("✅ Running analyzer updated")
        else:
            print("❌ No changes made")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    if 'runner' in globals():
        runner.stop_analysis()
    sys.exit(0)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Multi-Source Video Analysis System')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start multi-source analysis')
    start_parser.add_argument('--interval', type=int, default=10,
                             help='Analysis interval in seconds')
    
    # Stop command
    subparsers.add_parser('stop', help='Stop multi-source analysis')
    
    # Status command
    subparsers.add_parser('status', help='Show system status')
    
    # Add source command
    add_parser = subparsers.add_parser('add-source', help='Add a video source')
    add_parser.add_argument('--source-id', required=True, help='Source ID')
    add_parser.add_argument('--rtsp-url', required=True, help='RTSP URL')
    add_parser.add_argument('--name', help='Source name')
    add_parser.add_argument('--location', help='Source location')
    add_parser.add_argument('--priority', choices=['low', 'normal', 'high'], 
                           default='normal', help='Source priority')
    
    # Remove source command
    remove_parser = subparsers.add_parser('remove-source', help='Remove a video source')
    remove_parser.add_argument('--source-id', required=True, help='Source ID to remove')
    
    # List sources command
    subparsers.add_parser('list-sources', help='List all video sources')
    
    # Configure command
    subparsers.add_parser('configure', help='Configure analysis settings')
    
    # Interactive command
    subparsers.add_parser('interactive', help='Interactive management mode')
    
    # Quick start command
    quick_parser = subparsers.add_parser('quick-start', help='Quick start with example sources')
    quick_parser.add_argument('--sources', nargs='+', required=True,
                             help='RTSP URLs or video file paths')
    quick_parser.add_argument('--names', nargs='*',
                             help='Names for the video sources')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create runner
    global runner
    runner = MultiSourceRunner()
    
    try:
        if args.command == 'start':
            if args.interval:
                runner.config_manager.update_analysis_settings(analysis_interval=args.interval)
            
            if runner.start_analysis():
                print("🎯 Multi-source video analysis started. Press Ctrl+C to stop.")
                try:
                    while runner.running:
                        time.sleep(10)
                        runner.show_status()
                except KeyboardInterrupt:
                    pass
            else:
                return 1
        
        elif args.command == 'stop':
            runner.stop_analysis()
        
        elif args.command == 'status':
            runner.show_status()
        
        elif args.command == 'add-source':
            runner.config_manager.add_video_source(
                args.source_id, args.rtsp_url, args.name,
                location=args.location or "",
                priority=args.priority
            )
            print(f"✅ Added video source {args.source_id}")
        
        elif args.command == 'remove-source':
            if runner.config_manager.remove_video_source(args.source_id):
                print(f"✅ Removed video source {args.source_id}")
            else:
                print(f"❌ Source {args.source_id} not found")
                return 1
        
        elif args.command == 'list-sources':
            runner.list_sources()
        
        elif args.command == 'configure':
            runner.configure_analysis_settings()
        
        elif args.command == 'quick-start':
            # Add sources from command line
            for i, source_url in enumerate(args.sources):
                source_id = f"quick_source_{i+1}"
                source_name = args.names[i] if args.names and i < len(args.names) else f"Camera_{i+1}"
                
                runner.config_manager.add_video_source(
                    source_id, source_url, source_name,
                    description="Quick start source"
                )
                print(f"✅ Added source {source_id}: {source_name}")
            
            # Start analysis
            if runner.start_analysis():
                print("🎯 Multi-source video analysis started. Press Ctrl+C to stop.")
                try:
                    while runner.running:
                        time.sleep(30)
                        runner.show_status()
                except KeyboardInterrupt:
                    pass
            else:
                return 1
        
        elif args.command == 'interactive':
            print("🎯 Multi-Source Video Analysis - Interactive Mode")
            print("Commands: start, stop, status, add, remove, list, configure, quit")
            
            while True:
                try:
                    cmd = input("\n> ").strip().lower()
                    
                    if cmd in ['quit', 'exit', 'q']:
                        break
                    elif cmd == 'start':
                        runner.start_analysis()
                    elif cmd == 'stop':
                        runner.stop_analysis()
                    elif cmd == 'status':
                        runner.show_status()
                    elif cmd == 'add':
                        runner.add_source_interactive()
                    elif cmd == 'remove':
                        runner.remove_source_interactive()
                    elif cmd == 'list':
                        runner.list_sources()
                    elif cmd == 'configure':
                        runner.configure_analysis_settings()
                    elif cmd == 'help':
                        print("Commands: start, stop, status, add, remove, list, configure, quit")
                    else:
                        print(f"❌ Unknown command: {cmd}")
                
                except KeyboardInterrupt:
                    break
                except EOFError:
                    break
        
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    finally:
        runner.stop_analysis()


if __name__ == '__main__':
    sys.exit(main())