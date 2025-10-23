"""
API Client for distributed Vigint deployment
Wraps all api_proxy functions with HTTP communication
"""

import requests
import logging
import base64
import json
from typing import Optional, Dict, Any, List
from config import config

logger = logging.getLogger(__name__)


class APIClient:
    """Client for communicating with remote API server"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize API client
        
        Args:
            api_key: API key for authentication (from config if not provided)
            base_url: Base URL of API server (from config if not provided)
        """
        import os
        self.base_url = base_url or config.api_server_url or "http://localhost:5002"
        # Use VIGINT_API_KEY from environment for client authentication
        self.api_key = api_key or os.getenv('VIGINT_API_KEY') or config.secret_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json'
        })
        
        # Remove trailing slash from base URL
        self.base_url = self.base_url.rstrip('/')
        
        logger.info(f"API Client initialized for: {self.base_url}")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request to API server
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests
            
        Returns:
            Response data as dictionary
            
        Raises:
            Exception: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            # Return JSON if available, otherwise return text
            try:
                return response.json()
            except ValueError:
                return {'result': response.text}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {method} {url} - {e}")
            raise Exception(f"API request failed: {str(e)}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check API server health"""
        return self._make_request('GET', '/api/health')
    
    def compress_video(self, video_path: str, max_size_mb: float = 20, 
                      quality_reduction: float = 0.85) -> Dict[str, Any]:
        """
        Compress video file via API
        
        Args:
            video_path: Path to video file
            max_size_mb: Maximum size in MB
            quality_reduction: Quality reduction factor (0.1-1.0)
            
        Returns:
            Dictionary with compression result
        """
        with open(video_path, 'rb') as f:
            video_data = base64.b64encode(f.read()).decode('utf-8')
        
        data = {
            'video_data': video_data,
            'filename': video_path.split('/')[-1],
            'max_size_mb': max_size_mb,
            'quality_reduction': quality_reduction
        }
        
        return self._make_request('POST', '/api/video/compress', json=data)
    
    def create_video_from_frames(self, frames: List[str], output_filename: str,
                                fps: Optional[int] = None, 
                                video_format: Optional[str] = None) -> Dict[str, Any]:
        """
        Create video from frames via API
        
        Args:
            frames: List of base64-encoded frame data
            output_filename: Desired output filename
            fps: Frames per second
            video_format: Video format (mp4, avi, etc.)
            
        Returns:
            Dictionary with video creation result and download URL
        """
        data = {
            'frames': frames,
            'output_filename': output_filename,
            'fps': fps,
            'video_format': video_format
        }
        
        return self._make_request('POST', '/api/video/create', json=data)
    
    def analyze_frame(self, frame_data: str, frame_count: int, 
                     buffer_type: str = "short") -> Dict[str, Any]:
        """
        Analyze frame for security incidents
        
        Args:
            frame_data: Base64-encoded frame data
            frame_count: Frame count in sequence
            buffer_type: Buffer type (short or long)
            
        Returns:
            Analysis results
        """
        data = {
            'frame': frame_data,
            'frame_count': frame_count,
            'buffer_type': buffer_type
        }
        
        return self._make_request('POST', '/api/video/analyze', json=data)
    
    def add_frame_to_buffer(self, client_id: str, frame_data: str, 
                          timestamp: Optional[str] = None, frame_count: int = 0) -> Dict[str, Any]:
        """
        Add frame to client's buffer
        
        Args:
            client_id: Client identifier (not used - server gets from auth)
            frame_data: Base64-encoded frame data
            timestamp: Frame timestamp
            frame_count: Frame number
            
        Returns:
            Buffer status
        """
        data = {
            'frame_data': frame_data,  # Server expects 'frame_data' not 'frame'
            'frame_count': frame_count,
            'timestamp': timestamp
        }
        
        return self._make_request('POST', '/api/video/buffer', json=data)
    
    def add_frames_batch(self, client_id: str, frames: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add multiple frames to client's buffer in one request
        
        Args:
            client_id: Client identifier (not used - server gets from auth)
            frames: List of frame dictionaries with frame_data, timestamp, frame_count
            
        Returns:
            Batch buffer status
        """
        data = {
            'frames': frames
        }
        
        return self._make_request('POST', '/api/video/buffer/batch', json=data)
    
    def send_security_alert(self, analysis: str, risk_level: str, 
                          video_path: Optional[str] = None,
                          client_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send security alert email
        
        Args:
            analysis: Analysis text
            risk_level: Risk level (LOW, MEDIUM, HIGH)
            video_path: Path to video file (will be uploaded)
            client_id: Client identifier
            
        Returns:
            Alert sending result
        """
        data = {
            'analysis': analysis,
            'risk_level': risk_level,
            'client_id': client_id
        }
        
        # If video path provided, encode and include
        if video_path:
            try:
                with open(video_path, 'rb') as f:
                    video_data = base64.b64encode(f.read()).decode('utf-8')
                data['video_data'] = video_data
                data['video_filename'] = video_path.split('/')[-1]
            except Exception as e:
                logger.warning(f"Could not read video file: {e}")
        
        return self._make_request('POST', '/api/video/alert', json=data)
    
    def get_storage_status(self) -> Dict[str, Any]:
        """Get storage status"""
        return self._make_request('GET', '/api/storage/status')
    
    def cleanup_storage(self, max_age_hours: Optional[int] = None) -> Dict[str, Any]:
        """
        Trigger storage cleanup
        
        Args:
            max_age_hours: Maximum age of files to keep
            
        Returns:
            Cleanup result
        """
        data = {'max_age_hours': max_age_hours} if max_age_hours else {}
        return self._make_request('POST', '/api/storage/cleanup', json=data)
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        return self._make_request('GET', '/api/usage')


# Global client instance
_api_client = None


def get_api_client() -> APIClient:
    """
    Get or create global API client instance
    
    Returns:
        APIClient instance
    """
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client


# Convenience functions that match api_proxy interface
def compress_video_for_email(video_path: str, max_size_mb: float = 20, 
                           quality_reduction: float = 0.85) -> Dict[str, Any]:
    """Compress video - compatible with api_proxy interface"""
    client = get_api_client()
    return client.compress_video(video_path, max_size_mb, quality_reduction)


def create_video_from_frames(frames, output_path: str, fps: Optional[int] = None,
                            video_format: Optional[str] = None, 
                            quality_optimization: bool = True) -> Dict[str, Any]:
    """Create video from frames - compatible with api_proxy interface"""
    client = get_api_client()
    
    # Convert frames to base64 if needed
    frames_data = []
    for frame in frames:
        if isinstance(frame, bytes):
            frames_data.append(base64.b64encode(frame).decode('utf-8'))
        elif isinstance(frame, str):
            frames_data.append(frame)
        else:
            # Assume it's numpy array or similar, encode as JPEG
            import cv2
            import numpy as np
            if isinstance(frame, np.ndarray):
                _, buffer = cv2.imencode('.jpg', frame)
                frames_data.append(base64.b64encode(buffer).decode('utf-8'))
    
    result = client.create_video_from_frames(
        frames_data, 
        output_path.split('/')[-1],
        fps=fps,
        video_format=video_format
    )
    
    # Download the created video
    if result.get('success') and result.get('download_url'):
        download_url = result['download_url']
        if not download_url.startswith('http'):
            download_url = f"{client.base_url}{download_url}"
        
        response = requests.get(download_url, headers={'X-API-Key': client.api_key})
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        result['output_path'] = output_path
    
    return result
