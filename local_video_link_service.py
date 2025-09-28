#!/usr/bin/env python3
"""
Local Video Link Service - Temporary Workaround
Creates local video files and generates file:// links when Sparse AI is not available
"""

import os
import logging
import hashlib
import uuid
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalVideoLinkService:
    """Local video hosting service as fallback when Sparse AI is not available"""
    
    def __init__(self):
        # Create local video storage directory
        self.storage_dir = Path('local_videos')
        self.storage_dir.mkdir(exist_ok=True)
        
        # Default link expiration (24 hours)
        self.default_expiration_hours = 24
        
        logger.info(f"Local video storage initialized: {self.storage_dir.absolute()}")
    
    def upload_video(self, video_path, incident_data=None, expiration_hours=None):
        """
        Store video locally and return file link
        
        Args:
            video_path: Path to the video file
            incident_data: Optional incident metadata
            expiration_hours: Hours until link expires (default: 24)
        
        Returns:
            dict: Result with local file link
        """
        if not os.path.exists(video_path):
            return {
                'success': False,
                'error': f'Video file not found: {video_path}'
            }
        
        try:
            # Generate unique identifier for this video
            video_id = str(uuid.uuid4())
            
            # Prepare metadata
            expiration_hours = expiration_hours or self.default_expiration_hours
            expiration_time = datetime.now() + timedelta(hours=expiration_hours)
            
            # Create filename with incident info
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            risk_level = incident_data.get('risk_level', 'UNKNOWN') if incident_data else 'UNKNOWN'
            filename = f"incident_{risk_level}_{timestamp}_{video_id[:8]}.mp4"
            
            # Copy video to local storage
            local_video_path = self.storage_dir / filename
            shutil.copy2(video_path, local_video_path)
            
            # Calculate file hash for integrity
            file_hash = self._calculate_file_hash(local_video_path)
            
            # Create metadata file
            metadata = {
                'video_id': video_id,
                'upload_timestamp': datetime.now().isoformat(),
                'expiration_time': expiration_time.isoformat(),
                'source': 'vigint-security-system',
                'type': 'security_incident',
                'file_hash': file_hash,
                'original_path': str(video_path),
                'local_path': str(local_video_path)
            }
            
            # Add incident-specific metadata if available
            if incident_data:
                metadata.update({
                    'incident_type': incident_data.get('incident_type', 'security_incident'),
                    'risk_level': incident_data.get('risk_level', 'UNKNOWN'),
                    'confidence': incident_data.get('confidence', 0.0),
                    'frame_count': incident_data.get('frame_count', 0),
                    'analysis': incident_data.get('analysis', '')
                })
            
            # Save metadata
            metadata_path = self.storage_dir / f"{filename}.json"
            import json
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Generate local file link
            local_link = f"file://{local_video_path.absolute()}"
            
            logger.info(f"Video stored locally: {local_video_path}")
            
            return {
                'success': True,
                'video_id': video_id,
                'private_link': local_link,
                'local_path': str(local_video_path),
                'expiration_time': expiration_time.isoformat(),
                'file_hash': file_hash,
                'storage_type': 'local'
            }
        
        except Exception as e:
            logger.error(f"Error storing video locally: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_file_hash(self, file_path):
        """Calculate SHA256 hash of the file"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    def cleanup_expired_videos(self):
        """Clean up expired videos"""
        cleaned_count = 0
        current_time = datetime.now()
        
        try:
            for metadata_file in self.storage_dir.glob("*.json"):
                try:
                    import json
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    expiration_time = datetime.fromisoformat(metadata['expiration_time'])
                    
                    if current_time > expiration_time:
                        # Remove video file
                        video_file = Path(metadata['local_path'])
                        if video_file.exists():
                            video_file.unlink()
                        
                        # Remove metadata file
                        metadata_file.unlink()
                        
                        cleaned_count += 1
                        logger.info(f"Cleaned up expired video: {video_file.name}")
                
                except Exception as e:
                    logger.warning(f"Error cleaning up {metadata_file}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired videos")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        return cleaned_count
    
    def list_stored_videos(self):
        """List all stored videos with metadata"""
        videos = []
        
        try:
            for metadata_file in self.storage_dir.glob("*.json"):
                try:
                    import json
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    video_path = Path(metadata['local_path'])
                    if video_path.exists():
                        file_size = video_path.stat().st_size / (1024 * 1024)  # MB
                        
                        videos.append({
                            'video_id': metadata['video_id'],
                            'filename': video_path.name,
                            'size_mb': round(file_size, 1),
                            'upload_time': metadata['upload_timestamp'],
                            'expiration_time': metadata['expiration_time'],
                            'incident_type': metadata.get('incident_type', 'unknown'),
                            'risk_level': metadata.get('risk_level', 'unknown')
                        })
                
                except Exception as e:
                    logger.warning(f"Error reading metadata {metadata_file}: {e}")
        
        except Exception as e:
            logger.error(f"Error listing videos: {e}")
        
        return videos


def create_hybrid_video_service():
    """Create a hybrid service that tries Sparse AI first, then falls back to local"""
    
    class HybridVideoService:
        def __init__(self):
            # Try to initialize Sparse AI service
            try:
                from video_link_service import VideoLinkService
                self.sparse_ai_service = VideoLinkService()
                self.sparse_ai_available = (
                    self.sparse_ai_service.api_key and 
                    self.sparse_ai_service.api_key != 'your-sparse-ai-api-key-here'
                )
            except Exception as e:
                logger.warning(f"Sparse AI service not available: {e}")
                self.sparse_ai_service = None
                self.sparse_ai_available = False
            
            # Always initialize local service as fallback
            self.local_service = LocalVideoLinkService()
            
            if self.sparse_ai_available:
                logger.info("Hybrid service: Sparse AI primary, local fallback")
            else:
                logger.info("Hybrid service: Local only (Sparse AI not configured)")
        
        def upload_video(self, video_path, incident_data=None, expiration_hours=None):
            """Upload video using Sparse AI if available, otherwise use local storage"""
            
            # Try Sparse AI first if available
            if self.sparse_ai_available:
                try:
                    result = self.sparse_ai_service.upload_video(video_path, incident_data, expiration_hours)
                    if result['success']:
                        logger.info("Video uploaded to Sparse AI successfully")
                        return result
                    else:
                        logger.warning(f"Sparse AI upload failed: {result['error']}")
                except Exception as e:
                    logger.warning(f"Sparse AI upload error: {e}")
            
            # Fallback to local storage
            logger.info("Using local video storage as fallback")
            result = self.local_service.upload_video(video_path, incident_data, expiration_hours)
            
            if result['success']:
                # Modify the result to indicate it's a local file
                result['storage_type'] = 'local'
                result['note'] = 'Video stored locally (Sparse AI not available)'
            
            return result
    
    return HybridVideoService()


# Convenience functions that use the hybrid service
def upload_incident_video(video_path, incident_data=None, expiration_hours=24):
    """Upload incident video using hybrid service"""
    service = create_hybrid_video_service()
    return service.upload_video(video_path, incident_data, expiration_hours)


def create_and_upload_video_from_frames(frames, incident_data=None, expiration_hours=24):
    """Create video from frames and upload using hybrid service"""
    from alerts import AlertManager
    
    # Create video from frames
    alert_manager = AlertManager()
    temp_video_path = alert_manager.create_video_from_frames(frames)
    
    if not temp_video_path:
        return {
            'success': False,
            'error': 'Failed to create video from frames'
        }
    
    try:
        # Upload video using hybrid service
        service = create_hybrid_video_service()
        result = service.upload_video(temp_video_path, incident_data, expiration_hours)
        
        return result
    
    finally:
        # Clean up temporary video file
        if os.path.exists(temp_video_path):
            try:
                os.unlink(temp_video_path)
                logger.debug(f"Cleaned up temporary video: {temp_video_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary video: {e}")


if __name__ == '__main__':
    # Test the local video service
    service = LocalVideoLinkService()
    
    print("Local Video Link Service Test")
    print("=" * 40)
    
    # List current videos
    videos = service.list_stored_videos()
    print(f"Current videos: {len(videos)}")
    
    for video in videos:
        print(f"  - {video['filename']} ({video['size_mb']} MB) - {video['risk_level']}")
    
    # Cleanup expired videos
    cleaned = service.cleanup_expired_videos()
    print(f"Cleaned up {cleaned} expired videos")
    
    print(f"\nStorage directory: {service.storage_dir.absolute()}")