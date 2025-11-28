
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

# Import app but don't import the views yet if we want to patch decorators (too late now)
from api_proxy import app, client_frame_buffers

class TestApiClientEmail(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
    @patch('api_proxy.gemini_model_short', MagicMock())
    @patch('api_proxy.analyze_video_with_gemini')
    @patch('auth.verify_api_key')
    @patch('vigint.models.APIKey')
    @patch('api_proxy.log_api_usage')
    def test_analyze_frame_returns_client_email(self, mock_log_usage, mock_api_key_cls, mock_verify_key, mock_analyze):
        # Setup mock client
        mock_client = MagicMock()
        mock_client.id = 1
        mock_client.name = "Test Client"
        mock_client.email = "client@example.com"
        mock_verify_key.return_value = mock_client
        
        # Mock API Key query
        mock_api_key_instance = MagicMock()
        mock_api_key_instance.id = 123
        mock_api_key_cls.query.filter_by.return_value.first.return_value = mock_api_key_instance
        
        # Mock client frame buffer
        client_frame_buffers[1] = {
            'type': 'video',
            'video_path': '/tmp/test_video.mp4',
            'duration': 10,
            'frame_count': 250
        }
        
        # Mock file existence
        with patch('os.path.exists', return_value=True):
            # Mock analysis result
            mock_analyze.return_value = {
                'has_security_incident': False,
                'analysis': 'No incident'
            }
            
            # Make request with API key
            response = self.client.post('/api/video/analyze', 
                                      headers={'X-API-Key': 'test_key'})
            
            # Check response
            if response.status_code != 200:
                print(f"Error response: {response.get_data(as_text=True)}")
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['client_email'], "client@example.com")
            print(f"\n✅ analyze_frame returned client_email: {data['client_email']}")

    @patch('api_proxy.gemini_model_short', MagicMock())
    @patch('api_proxy.analyze_short_video_for_security')
    @patch('api_proxy.get_all_client_sources')
    @patch('api_proxy.get_multi_source_buffer')
    @patch('auth.verify_api_key')
    @patch('vigint.models.APIKey')
    def test_analyze_multi_source_returns_client_email(self, mock_api_key_cls, mock_verify_key, mock_get_buffer, mock_get_sources, mock_analyze):
        # Setup mock client
        mock_client = MagicMock()
        mock_client.id = 1
        mock_client.name = "Test Client"
        mock_client.email = "client@example.com"
        mock_verify_key.return_value = mock_client
        
        # Mock API Key query
        mock_api_key_instance = MagicMock()
        mock_api_key_instance.id = 123
        mock_api_key_cls.query.filter_by.return_value.first.return_value = mock_api_key_instance
        
        # Mock sources
        mock_get_sources.return_value = ['cam1']
        
        # Mock buffer
        mock_get_buffer.return_value = [{'frame_data': 'abc', 'source_name': 'cam1'}]
        
        # Mock analysis
        mock_analyze.return_value = {
            'has_security_incident': False,
            'analysis': 'No incident'
        }
        
        # Make request with API key
        response = self.client.post('/api/video/multi-source/analyze', 
                                  json={'source_ids': ['cam1']},
                                  headers={'X-API-Key': 'test_key'})
        
        # Check response
        if response.status_code != 200:
            print(f"Error response: {response.get_data(as_text=True)}")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['client_email'], "client@example.com")
        print(f"\n✅ analyze_multi_source returned client_email: {data['client_email']}")

if __name__ == '__main__':
    unittest.main()
