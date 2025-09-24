#!/usr/bin/env python3
"""
Integration script for Multi-Source Video Analysis with existing Vigint system
"""

import os
import sys
import logging
import threading
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from multi_source_video_analyzer import MultiSourceVideoAnalyzer
from multi_source_config import MultiSourceConfig
from rtsp_config import RTSPConfigManager
from config import config

logger = logging.getLogger(__name__)


class VigintMultiSourceIntegration:
    """Integrates multi-source analysis with existing Vigint system"""
    
    def __init__(self):
        self.multi_source_analyzer = None
        self.multi_source_config = MultiSourceConfig()
        self.rtsp_config = RTSPConfigManager()
        self.running = False
        self.integration_thread = None
    
    def sync_rtsp_sources(self):
        """Sync RTSP camera configuration with multi-source config"""
        logger.info("Syncing RTSP sources with multi-source configuration")
        
        # Get existing RTSP cameras
        rtsp_cameras = self.rtsp_config.list_cameras()
        
        # Add RTSP cameras to multi-source config if not already present
        for camera_id, camera_config in rtsp_cameras.items():
            if not self.multi_source_config.get_video_source(camera_id):
                logger.info(f"Adding RTSP camera {camera_id} to multi-source config")
                
                self.multi_source_config.add_video_source(
                    camera_id,
                    camera_config['rtsp_url'],
                    name=camera_config['name'],
                    location=camera_config.get('location', ''),
                    description=camera_config.get('description', ''),
                    enabled=camera_config.get('enabled', True),
                    analysis_enabled=camera_config.get('alert_enabled', True),
                    alert_enabled=camera_config.get('alert_enabled', True),
                    recording_enabled=camera_config.get('recording_enabled', False)
                )
        
        logger.info(f"Synced {len(rtsp_cameras)} RTSP sources")
    
    def setup_multi_source_analyzer(self):
        """Setup the multi-source analyzer with current configuration"""
        try:
            # Sync RTSP sources first
            self.sync_rtsp_sources()
            
            # Create analyzer
            self.multi_source_analyzer = MultiSourceVideoAnalyzer()
            
            # Get analysis settings from main config
            analysis_interval = config.getint('MultiSourceAnalysis', 'analysis_interval', 10)
            self.multi_source_analyzer.analysis_interval = analysis_interval
            
            # Add configured sources
            sources = self.multi_source_config.list_video_sources(enabled_only=True)
            analysis_sources = {k: v for k, v in sources.items() 
                              if v.get('analysis_enabled', True)}
            
            if not analysis_sources:
                logger.warning("No video sources configured for multi-source analysis")
                return False
            
            logger.info(f"Setting up multi-source analyzer with {len(analysis_sources)} sources")
            
            for source_id, source_config in analysis_sources.items():
                self.multi_source_analyzer.add_video_source(
                    source_id,
                    source_config['rtsp_url'],
                    source_config['name']
                )
                logger.info(f"Added source: {source_config['name']} ({source_id})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting up multi-source analyzer: {e}")
            return False
    
    def start_integration(self):
        """Start the integrated multi-source analysis"""
        if self.running:
            logger.warning("Integration already running")
            return False
        
        logger.info("Starting Vigint multi-source integration")
        
        # Setup analyzer
        if not self.setup_multi_source_analyzer():
            logger.error("Failed to setup multi-source analyzer")
            return False
        
        # Start the analyzer
        if not self.multi_source_analyzer.start_analysis():
            logger.error("Failed to start multi-source analysis")
            return False
        
        self.running = True
        
        # Start integration monitoring thread
        self.integration_thread = threading.Thread(target=self._integration_loop, daemon=True)
        self.integration_thread.start()
        
        logger.info("✅ Vigint multi-source integration started successfully")
        
        # Show configuration summary
        analysis_config = self.multi_source_config.get_sources_for_analysis()
        logger.info(f"📊 Analysis Configuration:")
        logger.info(f"   Total sources: {analysis_config['total_sources']}")
        logger.info(f"   Aggregated groups: {len(analysis_config['aggregated_groups'])}")
        logger.info(f"   Individual sources: {len(analysis_config['individual_sources'])}")
        
        return True
    
    def stop_integration(self):
        """Stop the integrated multi-source analysis"""
        if not self.running:
            return
        
        logger.info("Stopping Vigint multi-source integration")
        self.running = False
        
        if self.multi_source_analyzer:
            self.multi_source_analyzer.stop_analysis()
        
        if self.integration_thread:
            self.integration_thread.join(timeout=10)
        
        logger.info("✅ Vigint multi-source integration stopped")
    
    def _integration_loop(self):
        """Main integration monitoring loop"""
        while self.running:
            try:
                # Monitor system health
                if self.multi_source_analyzer:
                    status = self.multi_source_analyzer.get_status()
                    
                    # Log status periodically
                    if int(time.time()) % 300 == 0:  # Every 5 minutes
                        logger.info(f"Multi-source status: {status['active_sources']}/{status['total_sources']} sources active")
                    
                    # Check for inactive sources
                    for source_id, source_info in status['sources'].items():
                        if not source_info['active']:
                            logger.warning(f"Source {source_id} ({source_info['name']}) is inactive")
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in integration loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def get_status(self):
        """Get integration status"""
        status = {
            'running': self.running,
            'analyzer_status': None,
            'configuration_summary': None
        }
        
        if self.multi_source_analyzer:
            status['analyzer_status'] = self.multi_source_analyzer.get_status()
        
        status['configuration_summary'] = self.multi_source_config.get_sources_for_analysis()
        
        return status
    
    def add_camera_from_rtsp(self, camera_id):
        """Add a camera from RTSP configuration to multi-source analysis"""
        rtsp_camera = self.rtsp_config.get_camera(camera_id)
        if not rtsp_camera:
            logger.error(f"RTSP camera {camera_id} not found")
            return False
        
        # Add to multi-source config
        self.multi_source_config.add_video_source(
            camera_id,
            rtsp_camera['rtsp_url'],
            name=rtsp_camera['name'],
            location=rtsp_camera.get('location', ''),
            description=rtsp_camera.get('description', ''),
            enabled=rtsp_camera.get('enabled', True)
        )
        
        # Add to running analyzer if active
        if self.multi_source_analyzer and self.running:
            self.multi_source_analyzer.add_video_source(
                camera_id,
                rtsp_camera['rtsp_url'],
                rtsp_camera['name']
            )
        
        logger.info(f"Added camera {camera_id} to multi-source analysis")
        return True
    
    def remove_camera(self, camera_id):
        """Remove a camera from multi-source analysis"""
        # Remove from multi-source config
        self.multi_source_config.remove_video_source(camera_id)
        
        # Remove from running analyzer if active
        if self.multi_source_analyzer and self.running:
            self.multi_source_analyzer.remove_video_source(camera_id)
        
        logger.info(f"Removed camera {camera_id} from multi-source analysis")
        return True


def create_integration_service():
    """Create and return integration service instance"""
    return VigintMultiSourceIntegration()


def main():
    """Main function for testing integration"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Vigint Multi-Source Integration')
    parser.add_argument('--action', choices=['start', 'stop', 'status', 'sync'], 
                       default='start', help='Action to perform')
    parser.add_argument('--daemon', action='store_true', 
                       help='Run as daemon (keep running)')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create integration service
    integration = VigintMultiSourceIntegration()
    
    try:
        if args.action == 'start':
            if integration.start_integration():
                print("✅ Multi-source integration started")
                
                if args.daemon:
                    print("🔄 Running in daemon mode. Press Ctrl+C to stop.")
                    try:
                        while integration.running:
                            time.sleep(10)
                            # Show status every 5 minutes
                            if int(time.time()) % 300 == 0:
                                status = integration.get_status()
                                if status['analyzer_status']:
                                    analyzer_status = status['analyzer_status']
                                    print(f"Status: {analyzer_status['active_sources']}/{analyzer_status['total_sources']} sources active")
                    except KeyboardInterrupt:
                        print("\n⏹️ Stopping integration...")
                else:
                    print("🎯 Integration started. Use --daemon to keep running.")
            else:
                print("❌ Failed to start integration")
                return 1
        
        elif args.action == 'stop':
            integration.stop_integration()
            print("✅ Integration stopped")
        
        elif args.action == 'status':
            status = integration.get_status()
            print(f"Integration running: {'✅ Yes' if status['running'] else '❌ No'}")
            
            if status['analyzer_status']:
                analyzer_status = status['analyzer_status']
                print(f"Active sources: {analyzer_status['active_sources']}/{analyzer_status['total_sources']}")
                
                for source_id, source_info in analyzer_status['sources'].items():
                    status_icon = "🟢" if source_info['active'] else "🔴"
                    print(f"  {status_icon} {source_info['name']}: {source_info['frame_count']} frames")
            
            if status['configuration_summary']:
                config_summary = status['configuration_summary']
                print(f"Configuration: {config_summary['total_sources']} total sources")
                print(f"  Aggregated groups: {len(config_summary['aggregated_groups'])}")
                print(f"  Individual sources: {len(config_summary['individual_sources'])}")
        
        elif args.action == 'sync':
            integration.sync_rtsp_sources()
            print("✅ RTSP sources synced with multi-source configuration")
        
        return 0
    
    except Exception as e:
        logger.error(f"Integration error: {e}")
        return 1
    
    finally:
        integration.stop_integration()


if __name__ == '__main__':
    sys.exit(main())