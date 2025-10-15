#!/usr/bin/env python3
"""
Mock Sparse AI Service for GDPR-compliant video hosting demonstration
Simulates the sparse-ai.com API for testing purposes
"""

import os
import logging
import hashlib
import uuid
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from config import config

logger = logging.getLogger(__name__)


class MockSparseAIService:
    """Mock Sparse AI service that simulates cloud video hosting"""
    
    def __init__(self):
        # Create mock cloud storage directory
        self.mock_cloud_dir = Path('mock_sparse_ai_cloud')
        self.mock_cloud_dir.mkdir(exist_ok=True)
        
        # Use configured base_url from config.ini (same as real service)
        # This ensures mock service generates same URLs as production
        self.base_url = (
            os.getenv('SPARSE_AI_BASE_URL') or 
            config.get('SparseAI', 'base_url', 'http://127.0.0.1:9999')
        )
        self.api_key = os.getenv('SPARSE_AI_API_KEY', 'mock-key')
        self.default_expiration_hours = 48
        
        logger.info(f"Mock Sparse AI service initialized: {self.mock_cloud_dir.absolute()}")
        logger.info(f"Using base URL: {self.base_url}")
    
    def upload_video(self, video_path, incident_data=None, expiration_hours=None):
        """
        Mock video upload that simulates cloud storage
        
        Args:
            video_path: Path to the video file
            incident_data: Optional incident metadata
            expiration_hours: Hours until link expires
        
        Returns:
            dict: Result with mock private link
        """
        if not os.path.exists(video_path):
            return {
                'success': False,
                'error': f'Video file not found: {video_path}'
            }
        
        try:
            # Generate unique identifier
            video_id = str(uuid.uuid4())
            
            # Prepare metadata
            expiration_hours = expiration_hours or self.default_expiration_hours
            expiration_time = datetime.now() + timedelta(hours=expiration_hours)
            
            # Create filename for mock cloud storage
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            risk_level = incident_data.get('risk_level', 'UNKNOWN') if incident_data else 'UNKNOWN'
            cloud_filename = f"cloud_video_{risk_level}_{timestamp}_{video_id[:8]}.mp4"
            
            # Copy to mock cloud storage
            cloud_path = self.mock_cloud_dir / cloud_filename
            shutil.copy2(video_path, cloud_path)
            
            # Calculate file hash
            file_hash = self._calculate_file_hash(cloud_path)
            
            # Create metadata
            metadata = {
                'video_id': video_id,
                'upload_timestamp': datetime.now().isoformat(),
                'expiration_time': expiration_time.isoformat(),
                'source': 'vigint-security-system',
                'type': 'security_incident',
                'file_hash': file_hash,
                'cloud_path': str(cloud_path),
                'api_endpoint': 'mock_sparse_ai'
            }
            
            # Add incident-specific metadata
            if incident_data:
                metadata.update({
                    'incident_type': incident_data.get('incident_type', 'security_incident'),
                    'risk_level': incident_data.get('risk_level', 'UNKNOWN'),
                    'confidence': incident_data.get('confidence', 0.0),
                    'frame_count': incident_data.get('frame_count', 0),
                    'analysis': incident_data.get('analysis', ''),
                    'gdpr_compliant': incident_data.get('gdpr_compliant', True)
                })
            
            # Save metadata
            metadata_path = self.mock_cloud_dir / f"{cloud_filename}.json"
            import json
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Generate proper web link with token for simple server
            token = hashlib.sha256(f"{video_id}:{expiration_time.isoformat()}:mock-key".encode()).hexdigest()[:32]
            private_link = f"{self.base_url}/video/{video_id}?token={token}"
            
            # Also provide direct file path as backup
            direct_file_path = f"file://{cloud_path.absolute()}"
            local_path = str(cloud_path.absolute())
            
            logger.info(f"Video uploaded to mock cloud storage: {cloud_path}")
            
            return {
                'success': True,
                'video_id': video_id,
                'private_link': private_link,
                'direct_file_path': direct_file_path,
                'local_file': local_path,
                'local_filename': cloud_filename,
                'expiration_time': expiration_time.isoformat(),
                'file_hash': file_hash,
                'upload_response': {
                    'status': 'success',
                    'cloud_provider': 'mock_sparse_ai_local_files',
                    'storage_location': 'local_mock_storage'
                },
                'mock_service': True,
                'dual_buffer_system': True,
                'note': '🎬 Video created with DUAL-BUFFER system - smooth 25 FPS footage!'
            }
        
        except Exception as e:
            logger.error(f"Error in mock video upload: {e}")
            return {
                'success': False,
                'error': str(e),
                'mock_service': True
            }
    
    def _calculate_file_hash(self, file_path):
        """Calculate SHA256 hash of the file"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    def verify_link_access(self, video_id, token):
        """Mock link verification"""
        try:
            # Find video by ID
            for metadata_file in self.mock_cloud_dir.glob("*.json"):
                try:
                    import json
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    if metadata['video_id'] == video_id:
                        expiration_time = datetime.fromisoformat(metadata['expiration_time'])
                        current_time = datetime.now()
                        
                        if current_time < expiration_time:
                            remaining_hours = (expiration_time - current_time).total_seconds() / 3600
                            return {
                                'valid': True,
                                'expiration_time': metadata['expiration_time'],
                                'remaining_hours': round(remaining_hours, 1)
                            }
                        else:
                            return {
                                'valid': False,
                                'error': 'Link expired'
                            }
                
                except Exception:
                    continue
            
            return {
                'valid': False,
                'error': 'Video not found'
            }
        
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    def delete_video(self, video_id):
        """Mock video deletion"""
        try:
            deleted = False
            
            for metadata_file in self.mock_cloud_dir.glob("*.json"):
                try:
                    import json
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    if metadata['video_id'] == video_id:
                        # Delete video file
                        cloud_path = Path(metadata['cloud_path'])
                        if cloud_path.exists():
                            cloud_path.unlink()
                        
                        # Delete metadata file
                        metadata_file.unlink()
                        
                        deleted = True
                        logger.info(f"Mock video deleted: {video_id}")
                        break
                
                except Exception:
                    continue
            
            return {'success': deleted}
        
        except Exception as e:
            logger.error(f"Error deleting mock video: {e}")
            return {'success': False, 'error': str(e)}
    
    def cleanup_expired_videos(self):
        """Clean up expired videos from mock cloud storage"""
        cleaned_count = 0
        current_time = datetime.now()
        
        try:
            for metadata_file in self.mock_cloud_dir.glob("*.json"):
                try:
                    import json
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    expiration_time = datetime.fromisoformat(metadata['expiration_time'])
                    
                    if current_time > expiration_time:
                        # Delete video file
                        cloud_path = Path(metadata['cloud_path'])
                        if cloud_path.exists():
                            cloud_path.unlink()
                        
                        # Delete metadata file
                        metadata_file.unlink()
                        
                        cleaned_count += 1
                        logger.info(f"Cleaned up expired mock video: {metadata['video_id']}")
                
                except Exception as e:
                    logger.warning(f"Error cleaning up {metadata_file}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired mock videos")
        
        except Exception as e:
            logger.error(f"Error during mock cleanup: {e}")
        
        return cleaned_count
    
    def list_stored_videos(self):
        """List all videos in mock cloud storage"""
        videos = []
        
        try:
            for metadata_file in self.mock_cloud_dir.glob("*.json"):
                try:
                    import json
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    cloud_path = Path(metadata['cloud_path'])
                    if cloud_path.exists():
                        file_size = cloud_path.stat().st_size / (1024 * 1024)  # MB
                        
                        videos.append({
                            'video_id': metadata['video_id'],
                            'filename': cloud_path.name,
                            'size_mb': round(file_size, 1),
                            'upload_time': metadata['upload_timestamp'],
                            'expiration_time': metadata['expiration_time'],
                            'incident_type': metadata.get('incident_type', 'unknown'),
                            'risk_level': metadata.get('risk_level', 'unknown'),
                            'gdpr_compliant': metadata.get('gdpr_compliant', True)
                        })
                
                except Exception as e:
                    logger.warning(f"Error reading metadata {metadata_file}: {e}")
        
        except Exception as e:
            logger.error(f"Error listing mock videos: {e}")
        
        return videos


if __name__ == '__main__':
    # Test the mock service
    service = MockSparseAIService()
    
    print("Mock Sparse AI Service Test")
    print("=" * 40)
    
    # List current videos
    videos = service.list_stored_videos()
    print(f"Current videos: {len(videos)}")
    
    for video in videos:
        print(f"  - {video['filename']} ({video['size_mb']} MB) - {video['risk_level']} - GDPR: {video['gdpr_compliant']}")
    
    # Cleanup expired videos
    cleaned = service.cleanup_expired_videos()
    print(f"Cleaned up {cleaned} expired videos")
    
    print(f"\nMock cloud storage: {service.mock_cloud_dir.absolute()}")