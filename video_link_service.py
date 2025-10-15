#!/usr/bin/env python3
"""Video Link Service for uploading videos to sparse-ai.com and generating private links"""

import os
import logging
import requests
import hashlib
import uuid
import tempfile
import shutil
import json
from datetime import datetime, timedelta
from config import config

logger = logging.getLogger(__name__)


class VideoLinkService:
    """Service for uploading videos to sparse-ai.com and generating private access links"""
    
    def __init__(self):
        self.config = config
        
        # Configuration for video service (reads from config.ini or environment variables)
        # Environment variable takes precedence, then config file, then default
        self.base_url = (
            os.getenv('SPARSE_AI_BASE_URL') or 
            self.config.get('SparseAI', 'base_url', 'https://sparse-ai.com')
        )
        self.api_key = os.getenv('SPARSE_AI_API_KEY') or self.config.get('SparseAI', 'api_key', '')
        self.upload_endpoint = f"{self.base_url}/api/v1/videos/upload"
        self.link_endpoint = f"{self.base_url}/api/v1/videos/link"
        
        # Default link expiration (24 hours)
        self.default_expiration_hours = int(os.getenv('VIDEO_LINK_EXPIRATION_HOURS', '24'))
        
        if not self.api_key:
            logger.warning("Sparse AI API key not configured - video links will not work")
    
    def upload_video(self, video_path, incident_data=None, expiration_hours=None):
        """
        Upload video to sparse-ai.com and return private link
        
        Args:
            video_path: Path to the video file
            incident_data: Optional incident metadata
            expiration_hours: Hours until link expires (default: 24)
        
        Returns:
            dict: Result with private link or error
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'Sparse AI API key not configured'
            }
        
        if not os.path.exists(video_path):
            return {
                'success': False,
                'error': f'Video file not found: {video_path}'
            }
        
        try:
            # Prepare metadata
            expiration_hours = expiration_hours or self.default_expiration_hours
            expiration_time = datetime.now() + timedelta(hours=expiration_hours)
            
            # Generate unique identifier for this video
            video_id = str(uuid.uuid4())
            
            # Create metadata payload
            metadata = {
                'video_id': video_id,
                'upload_timestamp': datetime.now().isoformat(),
                'expiration_time': expiration_time.isoformat(),
                'source': 'vigint-security-system',
                'type': 'security_incident'
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
            
            # Calculate file hash for integrity verification
            file_hash = self._calculate_file_hash(video_path)
            metadata['file_hash'] = file_hash
            
            # Prepare upload request
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'X-Video-ID': video_id
            }
            
            # Upload video file
            with open(video_path, 'rb') as video_file:
                files = {
                    'video': (f'incident_{video_id}.mp4', video_file, 'video/mp4')
                }
                
                data = {
                    'metadata': json.dumps(metadata),  # Convert to JSON for form data
                    'expiration_hours': expiration_hours,
                    'access_type': 'private'
                }
                
                logger.info(f"Uploading video to sparse-ai.com: {video_id}")
                
                # Add retry logic for network issues
                max_retries = 3
                retry_delay = 2
                
                for attempt in range(max_retries):
                    try:
                        logger.info(f"Upload attempt {attempt + 1}/{max_retries}...")
                        
                        response = requests.post(
                            self.upload_endpoint,
                            headers=headers,
                            files=files,
                            data=data,
                            timeout=300  # 5 minute timeout for upload
                        )
                        
                        # Break on success or client error (4xx)
                        if response.status_code < 500:
                            break
                            
                        # Retry on server error (5xx)
                        if attempt < max_retries - 1:
                            logger.warning(f"Server error {response.status_code}, retrying in {retry_delay}s...")
                            import time
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                    
                    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Connection error, retrying in {retry_delay}s: {e}")
                            import time
                            time.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            raise
            
            if response.status_code == 200:
                result = response.json()
                
                # Use the private link from server response (server generates the token)
                # Don't generate our own token - the server knows its own API key
                private_link = result.get('private_link')
                if not private_link:
                    # Fallback: generate link if server didn't provide one (for older servers)
                    private_link = self._generate_private_link(video_id, expiration_time)
                
                logger.info(f"Video uploaded successfully: {video_id}")
                
                return {
                    'success': True,
                    'video_id': video_id,
                    'private_link': private_link,
                    'expiration_time': result.get('expiration_time', expiration_time.isoformat()),
                    'file_hash': file_hash,
                    'upload_response': result
                }
            
            else:
                error_msg = f"Upload failed with status {response.status_code}"
                try:
                    error_detail = response.json().get('error', 'Unknown error')
                    error_msg += f": {error_detail}"
                except:
                    error_msg += f": {response.text}"
                
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
        
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Upload timeout - video file may be too large'
            }
        
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': 'Connection error - unable to reach sparse-ai.com'
            }
        
        except Exception as e:
            logger.error(f"Error uploading video: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_private_link(self, video_id, expiration_time):
        """Generate private access link for the video"""
        # Create secure token based on video ID and expiration
        token_data = f"{video_id}:{expiration_time.isoformat()}:{self.api_key}"
        token = hashlib.sha256(token_data.encode()).hexdigest()[:32]
        
        # Generate private link
        private_link = f"{self.base_url}/video/{video_id}?token={token}"
        
        return private_link
    
    def _calculate_file_hash(self, file_path):
        """Calculate SHA256 hash of the file for integrity verification"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    def verify_link_access(self, video_id, token):
        """Verify if a private link is still valid and accessible"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }
            
            params = {
                'video_id': video_id,
                'token': token
            }
            
            response = requests.get(
                f"{self.link_endpoint}/verify",
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'valid': result.get('valid', False),
                    'expiration_time': result.get('expiration_time'),
                    'remaining_hours': result.get('remaining_hours', 0)
                }
            else:
                return {
                    'valid': False,
                    'error': f'Verification failed: {response.status_code}'
                }
        
        except Exception as e:
            logger.error(f"Error verifying link access: {e}")
            return {
                'valid': False,
                'error': str(e)
            }
    
    def extend_link_expiration(self, video_id, additional_hours=24):
        """Extend the expiration time of a private link"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'video_id': video_id,
                'additional_hours': additional_hours
            }
            
            response = requests.post(
                f"{self.link_endpoint}/extend",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'new_expiration': result.get('new_expiration'),
                    'total_hours': result.get('total_hours')
                }
            else:
                return {
                    'success': False,
                    'error': f'Extension failed: {response.status_code}'
                }
        
        except Exception as e:
            logger.error(f"Error extending link expiration: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_video(self, video_id):
        """Delete video from sparse-ai.com (for cleanup)"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }
            
            response = requests.delete(
                f"{self.upload_endpoint}/{video_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 204, 404]:  # 404 means already deleted
                logger.info(f"Video deleted successfully: {video_id}")
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': f'Deletion failed: {response.status_code}'
                }
        
        except Exception as e:
            logger.error(f"Error deleting video: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Convenience functions
def upload_incident_video(video_path, incident_data=None, expiration_hours=24):
    """Upload incident video and return private link"""
    service = VideoLinkService()
    return service.upload_video(video_path, incident_data, expiration_hours)


def create_and_upload_video_from_frames(frames, incident_data=None, expiration_hours=24):
    """Create video from frames and upload to sparse-ai.com"""
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
        # Upload video and get private link
        service = VideoLinkService()
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
    # Test the video link service
    service = VideoLinkService()
    
    # Test with a dummy video file (create a small test video)
    test_video_path = 'test_video.mp4'
    
    if os.path.exists(test_video_path):
        result = service.upload_video(test_video_path)
        print(f"Upload test result: {result}")
    else:
        print("No test video file found - create test_video.mp4 to test upload")