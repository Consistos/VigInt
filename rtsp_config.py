#!/usr/bin/env python3
"""RTSP URL and camera configuration management - Reconstructed"""

import os
import json
import logging
from pathlib import Path
from config import config

logger = logging.getLogger(__name__)


class RTSPConfigManager:
    """Manages RTSP URLs and camera configurations"""
    
    def __init__(self):
        self.config = config
        self.config_file = Path("rtsp_cameras.json")
        self.cameras = self.load_camera_config()
    
    def load_camera_config(self):
        """Load camera configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                # Default configuration
                default_config = {
                    "cameras": {},
                    "rtsp_settings": {
                        "base_url": "rtsp://localhost:8554",
                        "default_port": 8554,
                        "auth_user": "vigint",
                        "auth_pass": "vigint123"
                    }
                }
                self.save_camera_config(default_config)
                return default_config
        except Exception as e:
            logger.error(f"Error loading camera config: {e}")
            return {"cameras": {}, "rtsp_settings": {}}
    
    def save_camera_config(self, config_data=None):
        """Save camera configuration to file"""
        try:
            if config_data is None:
                config_data = self.cameras
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info("Camera configuration saved")
            return True
        except Exception as e:
            logger.error(f"Error saving camera config: {e}")
            return False
    
    def add_camera(self, camera_id, camera_config):
        """Add a new camera configuration"""
        required_fields = ['name', 'rtsp_url']
        
        for field in required_fields:
            if field not in camera_config:
                raise ValueError(f"Missing required field: {field}")
        
        self.cameras['cameras'][camera_id] = {
            'name': camera_config['name'],
            'rtsp_url': camera_config['rtsp_url'],
            'description': camera_config.get('description', ''),
            'location': camera_config.get('location', ''),
            'enabled': camera_config.get('enabled', True),
            'stream_path': camera_config.get('stream_path', f'/{camera_id}'),
            'recording_enabled': camera_config.get('recording_enabled', False),
            'alert_enabled': camera_config.get('alert_enabled', False),
            'created_at': camera_config.get('created_at', str(Path().stat().st_mtime))
        }
        
        self.save_camera_config()
        logger.info(f"Camera {camera_id} added successfully")
        return True
    
    def remove_camera(self, camera_id):
        """Remove a camera configuration"""
        if camera_id in self.cameras['cameras']:
            del self.cameras['cameras'][camera_id]
            self.save_camera_config()
            logger.info(f"Camera {camera_id} removed")
            return True
        else:
            logger.warning(f"Camera {camera_id} not found")
            return False
    
    def get_camera(self, camera_id):
        """Get camera configuration"""
        return self.cameras['cameras'].get(camera_id)
    
    def list_cameras(self):
        """List all cameras"""
        return self.cameras['cameras']
    
    def get_rtsp_url(self, camera_id):
        """Get the full RTSP URL for a camera"""
        camera = self.get_camera(camera_id)
        if not camera:
            return None
        
        if camera.get('enabled', True):
            return camera['rtsp_url']
        else:
            return None
    
    def get_stream_url(self, camera_id):
        """Get the local stream URL for a camera"""
        camera = self.get_camera(camera_id)
        if not camera:
            return None
        
        base_url = self.cameras['rtsp_settings'].get('base_url', 'rtsp://localhost:8554')
        stream_path = camera.get('stream_path', f'/{camera_id}')
        
        return f"{base_url}{stream_path}"
    
    def update_rtsp_settings(self, settings):
        """Update RTSP server settings"""
        if 'rtsp_settings' not in self.cameras:
            self.cameras['rtsp_settings'] = {}
        
        self.cameras['rtsp_settings'].update(settings)
        self.save_camera_config()
        logger.info("RTSP settings updated")
        return True
    
    def get_rtsp_settings(self):
        """Get RTSP server settings"""
        return self.cameras.get('rtsp_settings', {})
    
    def validate_rtsp_url(self, rtsp_url):
        """Validate RTSP URL format"""
        if not rtsp_url.startswith('rtsp://'):
            return False, "URL must start with rtsp://"
        
        # Basic validation - could be enhanced
        if '://' not in rtsp_url or len(rtsp_url.split('://')[1]) == 0:
            return False, "Invalid RTSP URL format"
        
        return True, "Valid RTSP URL"
    
    def test_camera_connection(self, camera_id):
        """Test camera connection (placeholder for actual implementation)"""
        camera = self.get_camera(camera_id)
        if not camera:
            return False, "Camera not found"
        
        rtsp_url = camera['rtsp_url']
        
        # Placeholder for actual connection test
        # In real implementation, this would use FFmpeg or similar to test the stream
        logger.info(f"Testing connection to {rtsp_url}")
        
        # Simulate test result
        return True, "Connection test successful (simulated)"
    
    def generate_mediamtx_config(self):
        """Generate MediaMTX configuration for all cameras"""
        config_lines = []
        
        # Add each camera as a path
        for camera_id, camera in self.cameras['cameras'].items():
            if camera.get('enabled', True):
                config_lines.append(f"  {camera_id}:")
                config_lines.append(f"    source: {camera['rtsp_url']}")
                config_lines.append(f"    sourceOnDemand: yes")
                
                if camera.get('recording_enabled', False):
                    config_lines.append(f"    record: yes")
                else:
                    config_lines.append(f"    record: no")
                
                config_lines.append("")
        
        return "\n".join(config_lines)


# Convenience functions
def add_camera(camera_id, name, rtsp_url, **kwargs):
    """Add a camera with basic parameters"""
    manager = RTSPConfigManager()
    camera_config = {
        'name': name,
        'rtsp_url': rtsp_url,
        **kwargs
    }
    return manager.add_camera(camera_id, camera_config)


def get_camera_stream_url(camera_id):
    """Get the local stream URL for a camera"""
    manager = RTSPConfigManager()
    return manager.get_stream_url(camera_id)


def list_all_cameras():
    """List all configured cameras"""
    manager = RTSPConfigManager()
    return manager.list_cameras()


if __name__ == '__main__':
    # Example usage
    manager = RTSPConfigManager()
    
    # Add example cameras
    manager.add_camera('camera1', {
        'name': 'Front Door Camera',
        'rtsp_url': 'rtsp://192.168.1.100:554/stream1',
        'location': 'Front Door',
        'description': 'Main entrance camera'
    })
    
    manager.add_camera('camera2', {
        'name': 'Back Yard Camera',
        'rtsp_url': 'rtsp://192.168.1.101:554/stream1',
        'location': 'Back Yard',
        'description': 'Backyard surveillance'
    })
    
    # List cameras
    cameras = manager.list_cameras()
    print("Configured cameras:")
    for cam_id, cam_info in cameras.items():
        print(f"  {cam_id}: {cam_info['name']} - {cam_info['rtsp_url']}")
    
    # Generate MediaMTX config
    mediamtx_config = manager.generate_mediamtx_config()
    print(f"\nMediaMTX configuration:\n{mediamtx_config}")