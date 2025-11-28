
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from video_analyzer import VideoAnalyzer
from multi_source_video_analyzer import MultiSourceVideoAnalyzer

class TestClientEmailAlertFlow(unittest.TestCase):
    
    def test_video_analyzer_uses_client_email(self):
        """Test that VideoAnalyzer passes client_email from API response to alert function"""
        # Mock the alerts module
        mock_alerts = MagicMock()
        mock_send_alert = MagicMock()
        mock_alerts.send_security_alert_with_video = mock_send_alert
        
        with patch.dict(sys.modules, {'alerts': mock_alerts}):
            analyzer = VideoAnalyzer()
            # Mock email config to pass validation
            analyzer.email_config['username'] = 'test_user'
            analyzer.email_config['to_email'] = 'test_to'
            
            analyzer.use_remote_api = False  # Test local mode to verify email passing
            analyzer.model = MagicMock() # Mock model to avoid real analysis
            
            # Mock API response (simulated from _analyze_frame_remote or just passed to send_alert_email)
            # In local mode, analyze_frame returns a result. 
            # But we want to test if send_alert_email uses the recipient_email.
            
            analysis_result = {
                'has_security_incident': True,
                'analysis': 'Test incident',
                'client_email': 'client@example.com'
            }
            
            # Call send_alert_email directly
            analyzer.send_alert_email(
                analysis_result, 
                video_frames=[{'frame_data': 'abc'}], 
                recipient_email='client@example.com'
            )
            
            # Verify send_security_alert_with_video was called with correct recipient_email
            mock_send_alert.assert_called_once()
            call_args = mock_send_alert.call_args
            self.assertEqual(call_args.kwargs.get('recipient_email'), 'client@example.com')
            print("\n✅ VideoAnalyzer passed client_email to send_security_alert_with_video (Local Mode)")

    @patch('multi_source_video_analyzer.send_security_alert_with_video')
    @patch('requests.post')
    def test_multi_source_analyzer_uses_client_email(self, mock_post, mock_send_alert):
        """Test that MultiSourceVideoAnalyzer passes client_email from API response to alert function"""
        analyzer = MultiSourceVideoAnalyzer(api_key='test')
        
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'client_email': 'client@example.com',
            'sources': {
                'cam1': {
                    'has_security_incident': True,
                    'analysis': 'Test incident',
                    'incident_frames': [{'frame_data': 'abc'}]
                }
            }
        }
        mock_post.return_value = mock_response
        
        # Mock video source
        mock_source = MagicMock()
        mock_source.source_id = 'cam1'
        mock_source.name = 'Camera 1'
        analyzer.video_sources = {'cam1': mock_source}
        
        # Call _analyze_sources_via_api
        analyzer._analyze_sources_via_api([mock_source])
        
        # Verify send_security_alert_with_video was called with correct recipient_email
        mock_send_alert.assert_called_once()
        call_args = mock_send_alert.call_args
        self.assertEqual(call_args.kwargs.get('recipient_email'), 'client@example.com')
        print("\n✅ MultiSourceVideoAnalyzer passed client_email to send_security_alert_with_video")

if __name__ == '__main__':
    unittest.main()
