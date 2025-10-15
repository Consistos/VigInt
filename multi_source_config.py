#!/usr/bin/env python3
"""
Multi-Source Video Configuration Manager
Handles configuration and management of multiple video sources
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from config import config

logger = logging.getLogger(__name__)


class MultiSourceConfig:
    """Manages configuration for multiple video sources"""
    
    def __init__(self, config_file="multi_source_config.json"):
        self.config_file = Path(config_file)
        self.config_data = self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                # Default configuration
                default_config = {
                    "version": "1.0",
                    "created_at": datetime.now().isoformat(),
                    "analysis_settings": {
                        "analysis_interval": 10,
                        "aggregation_threshold": 9999,
                        "max_concurrent_analyses": 4,
                        "frame_buffer_duration": 10
                    },
                    "video_sources": {},
                    "source_groups": {}
                }
                self.save_config(default_config)
                return default_config
        except Exception as e:
            logger.error(f"Error loading multi-source config: {e}")
            return {"video_sources": {}, "source_groups": {}}
    
    def save_config(self, config_data=None):
        """Save configuration to file"""
        try:
            if config_data is None:
                config_data = self.config_data
            
            config_data["last_updated"] = datetime.now().isoformat()
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info("Multi-source configuration saved")
            return True
        except Exception as e:
            logger.error(f"Error saving multi-source config: {e}")
            return False
    
    def add_video_source(self, source_id, rtsp_url, name=None, **kwargs):
        """Add a video source configuration"""
        source_config = {
            "source_id": source_id,
            "rtsp_url": rtsp_url,
            "name": name or f"Camera_{source_id}",
            "enabled": kwargs.get("enabled", True),
            "location": kwargs.get("location", ""),
            "description": kwargs.get("description", ""),
            "priority": kwargs.get("priority", "normal"),  # low, normal, high
            "analysis_enabled": kwargs.get("analysis_enabled", True),
            "alert_enabled": kwargs.get("alert_enabled", True),
            "recording_enabled": kwargs.get("recording_enabled", False),
            "created_at": datetime.now().isoformat(),
            "tags": kwargs.get("tags", [])
        }
        
        self.config_data["video_sources"][source_id] = source_config
        self.save_config()
        
        logger.info(f"Added video source {source_id}: {source_config['name']}")
        return True
    
    def remove_video_source(self, source_id):
        """Remove a video source configuration"""
        if source_id in self.config_data["video_sources"]:
            del self.config_data["video_sources"][source_id]
            
            # Remove from any groups
            for group_id, group_config in self.config_data["source_groups"].items():
                if source_id in group_config.get("source_ids", []):
                    group_config["source_ids"].remove(source_id)
            
            self.save_config()
            logger.info(f"Removed video source {source_id}")
            return True
        return False
    
    def update_video_source(self, source_id, **kwargs):
        """Update video source configuration"""
        if source_id not in self.config_data["video_sources"]:
            return False
        
        source_config = self.config_data["video_sources"][source_id]
        
        # Update allowed fields
        updatable_fields = [
            "name", "rtsp_url", "enabled", "location", "description", 
            "priority", "analysis_enabled", "alert_enabled", "recording_enabled", "tags"
        ]
        
        for field in updatable_fields:
            if field in kwargs:
                source_config[field] = kwargs[field]
        
        source_config["updated_at"] = datetime.now().isoformat()
        self.save_config()
        
        logger.info(f"Updated video source {source_id}")
        return True
    
    def get_video_source(self, source_id):
        """Get video source configuration"""
        return self.config_data["video_sources"].get(source_id)
    
    def list_video_sources(self, enabled_only=False):
        """List all video sources"""
        sources = self.config_data["video_sources"]
        
        if enabled_only:
            return {k: v for k, v in sources.items() if v.get("enabled", True)}
        
        return sources
    
    def create_source_group(self, group_id, source_ids, name=None, **kwargs):
        """Create a group of video sources"""
        # Validate that all source IDs exist
        for source_id in source_ids:
            if source_id not in self.config_data["video_sources"]:
                raise ValueError(f"Source {source_id} does not exist")
        
        group_config = {
            "group_id": group_id,
            "name": name or f"Group_{group_id}",
            "source_ids": source_ids,
            "analysis_type": kwargs.get("analysis_type", "aggregated"),  # aggregated or individual
            "priority": kwargs.get("priority", "normal"),
            "description": kwargs.get("description", ""),
            "created_at": datetime.now().isoformat(),
            "enabled": kwargs.get("enabled", True)
        }
        
        self.config_data["source_groups"][group_id] = group_config
        self.save_config()
        
        logger.info(f"Created source group {group_id} with {len(source_ids)} sources")
        return True
    
    def remove_source_group(self, group_id):
        """Remove a source group"""
        if group_id in self.config_data["source_groups"]:
            del self.config_data["source_groups"][group_id]
            self.save_config()
            logger.info(f"Removed source group {group_id}")
            return True
        return False
    
    def get_source_group(self, group_id):
        """Get source group configuration"""
        return self.config_data["source_groups"].get(group_id)
    
    def list_source_groups(self, enabled_only=False):
        """List all source groups"""
        groups = self.config_data["source_groups"]
        
        if enabled_only:
            return {k: v for k, v in groups.items() if v.get("enabled", True)}
        
        return groups
    
    def get_analysis_settings(self):
        """Get analysis settings"""
        return self.config_data.get("analysis_settings", {})
    
    def update_analysis_settings(self, **kwargs):
        """Update analysis settings"""
        if "analysis_settings" not in self.config_data:
            self.config_data["analysis_settings"] = {}
        
        updatable_fields = [
            "analysis_interval", "aggregation_threshold", "max_concurrent_analyses", 
            "frame_buffer_duration"
        ]
        
        for field in updatable_fields:
            if field in kwargs:
                self.config_data["analysis_settings"][field] = kwargs[field]
        
        self.save_config()
        logger.info("Updated analysis settings")
        return True
    
    def get_sources_for_analysis(self):
        """Get sources configured for analysis (aggregation disabled)"""
        enabled_sources = self.list_video_sources(enabled_only=True)
        analysis_sources = {k: v for k, v in enabled_sources.items() 
                          if v.get("analysis_enabled", True)}
        
        # Aggregation disabled - all sources analyzed individually
        return {
            "individual_sources": list(analysis_sources.keys()),
            "aggregated_groups": [],
            "total_sources": len(analysis_sources)
        }
    
    def _organize_sources_for_aggregation(self, sources, threshold):
        """Organize sources into aggregated groups and individual sources"""
        source_ids = list(sources.keys())
        
        # Create groups of 'threshold' size
        aggregated_groups = []
        individual_sources = []
        
        for i in range(0, len(source_ids), threshold):
            group = source_ids[i:i+threshold]
            if len(group) == threshold:
                aggregated_groups.append({
                    "group_id": f"auto_group_{len(aggregated_groups) + 1}",
                    "source_ids": group,
                    "source_names": [sources[sid]["name"] for sid in group]
                })
            else:
                individual_sources.extend(group)
        
        return {
            "individual_sources": individual_sources,
            "aggregated_groups": aggregated_groups,
            "total_sources": len(source_ids)
        }
    
    def validate_configuration(self):
        """Validate the current configuration"""
        errors = []
        warnings = []
        
        # Check video sources
        for source_id, source_config in self.config_data["video_sources"].items():
            if not source_config.get("rtsp_url"):
                errors.append(f"Source {source_id} missing RTSP URL")
            
            if not source_config.get("name"):
                warnings.append(f"Source {source_id} missing name")
        
        # Check source groups
        for group_id, group_config in self.config_data["source_groups"].items():
            source_ids = group_config.get("source_ids", [])
            
            for source_id in source_ids:
                if source_id not in self.config_data["video_sources"]:
                    errors.append(f"Group {group_id} references non-existent source {source_id}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def export_config(self, export_path=None):
        """Export configuration to a file"""
        if export_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = f"multi_source_config_export_{timestamp}.json"
        
        try:
            with open(export_path, 'w') as f:
                json.dump(self.config_data, f, indent=2)
            
            logger.info(f"Configuration exported to {export_path}")
            return export_path
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            return None
    
    def import_config(self, import_path):
        """Import configuration from a file"""
        try:
            with open(import_path, 'r') as f:
                imported_config = json.load(f)
            
            # Validate imported configuration
            if "video_sources" not in imported_config:
                raise ValueError("Invalid configuration file: missing video_sources")
            
            # Backup current configuration
            backup_path = f"multi_source_config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.export_config(backup_path)
            
            # Import new configuration
            self.config_data = imported_config
            self.save_config()
            
            logger.info(f"Configuration imported from {import_path}")
            logger.info(f"Previous configuration backed up to {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing configuration: {e}")
            return False


# Convenience functions
def create_default_config():
    """Create a default multi-source configuration"""
    config_manager = MultiSourceConfig()
    
    # Add some example sources
    config_manager.add_video_source(
        "camera_1", 
        "rtsp://localhost:8554/camera1",
        name="Front Door Camera",
        location="Main Entrance",
        priority="high"
    )
    
    config_manager.add_video_source(
        "camera_2", 
        "rtsp://localhost:8554/camera2",
        name="Sales Floor Camera",
        location="Sales Area",
        priority="high"
    )
    
    config_manager.add_video_source(
        "camera_3", 
        "rtsp://localhost:8554/camera3",
        name="Checkout Camera",
        location="Checkout Area",
        priority="high"
    )
    
    config_manager.add_video_source(
        "camera_4", 
        "rtsp://localhost:8554/camera4",
        name="Storage Room Camera",
        location="Storage Area",
        priority="normal"
    )
    
    return config_manager


if __name__ == '__main__':
    # Example usage
    config_manager = create_default_config()
    
    # Show configuration
    sources = config_manager.list_video_sources()
    print(f"Configured {len(sources)} video sources:")
    for source_id, source_config in sources.items():
        print(f"  {source_id}: {source_config['name']} - {source_config['rtsp_url']}")
    
    # Show analysis organization
    analysis_config = config_manager.get_sources_for_analysis()
    print(f"\nAnalysis organization:")
    print(f"  Individual sources: {len(analysis_config['individual_sources'])}")
    print(f"  Aggregated groups: {len(analysis_config['aggregated_groups'])}")
    print(f"  Total sources: {analysis_config['total_sources']}")
    
    # Validate configuration
    validation = config_manager.validate_configuration()
    print(f"\nConfiguration validation: {'✅ Valid' if validation['valid'] else '❌ Invalid'}")
    if validation['errors']:
        print(f"  Errors: {validation['errors']}")
    if validation['warnings']:
        print(f"  Warnings: {validation['warnings']}")