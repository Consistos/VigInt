#!/usr/bin/env python3
"""Alert and notification system for Vigint - Reconstructed"""

import os
import logging
import smtplib
import requests
import json
import base64
import tempfile
import cv2
import numpy as np
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from config import config

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages various alert and notification channels"""
    
    def __init__(self):
        self.config = config
        
    def send_alert(self, message, alert_type="info", channels=None):
        """Send alert through multiple channels"""
        if channels is None:
            channels = ["email"]  # Default to email
            
        results = {}
        
        for channel in channels:
            try:
                if channel == "email":
                    results[channel] = self.send_email_alert(message, alert_type)
                elif channel == "whatsapp":
                    results[channel] = self.send_whatsapp_alert(message, alert_type)
                elif channel == "sms":
                    results[channel] = self.send_sms_alert(message, alert_type)
                elif channel == "webhook":
                    results[channel] = self.send_webhook_alert(message, alert_type)
                else:
                    results[channel] = {"success": False, "error": f"Unknown channel: {channel}"}
            except Exception as e:
                logger.error(f"Error sending alert via {channel}: {e}")
                results[channel] = {"success": False, "error": str(e)}
                
        return results
    
    def send_email_alert(self, message, alert_type="info", video_path=None, incident_data=None):
        """Send email alert with optional video attachment"""
        try:
            # Email configuration for alerts (different from billing)
            smtp_server = os.getenv('ALERT_SMTP_SERVER') or self.config.get('Alerts', 'smtp_server', 'smtp.gmail.com')
            smtp_port = int(os.getenv('ALERT_SMTP_PORT') or self.config.get('Alerts', 'smtp_port', '587'))
            sender_email = os.getenv('ALERT_EMAIL') or self.config.get('Alerts', 'sender_email', 'alerts@vigint.com')
            sender_password = os.getenv('ALERT_EMAIL_PASSWORD') or self.config.get('Alerts', 'sender_password', '')
            admin_email = os.getenv('ADMIN_EMAIL') or self.config.get('Alerts', 'admin_email', 'admin@vigint.com')
            
            if not sender_password:
                return {"success": False, "error": "No alert email password configured"}
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = admin_email
            msg['Subject'] = f"🚨 Vigint Alert - {alert_type.upper()}"
            
            # Enhanced body with incident details
            body = f"""
🚨 VIGINT SYSTEM ALERT

Alert Type: {alert_type.upper()}
Timestamp: {datetime.now().isoformat()}

Message:
{message}
"""
            
            # Add incident-specific information if available
            if incident_data:
                body += f"""

INCIDENT DETAILS:
Risk Level: {incident_data.get('risk_level', 'UNKNOWN')}
Frame Count: {incident_data.get('frame_count', 'N/A')}
Confidence: {incident_data.get('confidence', 'N/A')}
"""
                if 'analysis' in incident_data:
                    body += f"""
AI Analysis:
{incident_data['analysis']}
"""
            
            # Add video attachment status
            if video_path and os.path.exists(video_path):
                video_size = os.path.getsize(video_path) / (1024 * 1024)  # Size in MB
                body += f"""

📹 VIDEO EVIDENCE ATTACHED
File: security_incident_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4
Size: {video_size:.1f} MB
"""
            else:
                body += """

⚠️ Video evidence not available
"""
            
            body += """

---
Vigint Monitoring System
Please review immediately and take appropriate action.
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach video if provided
            video_attached = False
            if video_path and os.path.exists(video_path):
                try:
                    video_attached = self._attach_video_to_email(msg, video_path, incident_data)
                    if video_attached:
                        logger.info(f"Video attachment added: {video_path}")
                    else:
                        logger.warning(f"Failed to attach video: {video_path}")
                except Exception as e:
                    logger.error(f"Error attaching video: {e}")
            
            # Send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Alert email sent to {admin_email} (video attached: {video_attached})")
            return {
                "success": True, 
                "video_attached": video_attached,
                "recipient": admin_email
            }
            
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            return {"success": False, "error": str(e)}
    
    def _attach_video_to_email(self, msg, video_path, incident_data=None):
        """Attach video file to email message"""
        try:
            # Check file size (limit to 20MB for email compatibility)
            file_size = os.path.getsize(video_path)
            max_size = 20 * 1024 * 1024  # 20MB
            
            if file_size > max_size:
                logger.warning(f"Video file too large ({file_size / (1024*1024):.1f} MB), attempting compression")
                compressed_path = self._compress_video_for_email(video_path)
                if compressed_path:
                    video_path = compressed_path
                else:
                    logger.error("Video compression failed, skipping attachment")
                    return False
            
            # Read video file and attach
            with open(video_path, 'rb') as video_file:
                # Determine MIME type based on file extension
                if video_path.lower().endswith('.mp4'):
                    main_type, sub_type = 'video', 'mp4'
                elif video_path.lower().endswith('.avi'):
                    main_type, sub_type = 'video', 'x-msvideo'
                else:
                    main_type, sub_type = 'application', 'octet-stream'
                
                video_attachment = MIMEBase(main_type, sub_type)
                video_attachment.set_payload(video_file.read())
                encoders.encode_base64(video_attachment)
                
                # Create filename with incident details
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                risk_level = incident_data.get('risk_level', 'ALERT') if incident_data else 'ALERT'
                filename = f"vigint_incident_{risk_level}_{timestamp}.mp4"
                
                video_attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{filename}"'
                )
                video_attachment.add_header(
                    'Content-Description',
                    f'Vigint Security Incident Video - {risk_level}'
                )
                
                msg.attach(video_attachment)
                return True
                
        except Exception as e:
            logger.error(f"Error attaching video to email: {e}")
            return False
    
    def _compress_video_for_email(self, video_path, max_size_mb=15):
        """Compress video file for email attachment"""
        try:
            # Create temporary compressed file
            temp_fd, temp_path = tempfile.mkstemp(suffix='_compressed.mp4', prefix='vigint_')
            os.close(temp_fd)
            
            # Open original video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
            
            # Get video properties
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Reduce resolution and FPS for compression
            new_width = int(width * 0.7)
            new_height = int(height * 0.7)
            new_fps = max(10, int(fps * 0.6))
            
            # Ensure even dimensions
            if new_width % 2 != 0:
                new_width -= 1
            if new_height % 2 != 0:
                new_height -= 1
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_path, fourcc, new_fps, (new_width, new_height))
            
            if not out.isOpened():
                cap.release()
                return None
            
            # Process frames
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Skip frames to reduce FPS
                if frame_count % max(1, int(fps / new_fps)) == 0:
                    resized_frame = cv2.resize(frame, (new_width, new_height))
                    out.write(resized_frame)
                
                frame_count += 1
            
            cap.release()
            out.release()
            
            # Check if compression was successful and size is acceptable
            if os.path.exists(temp_path):
                compressed_size = os.path.getsize(temp_path) / (1024 * 1024)
                if compressed_size <= max_size_mb:
                    logger.info(f"Video compressed successfully: {compressed_size:.1f} MB")
                    return temp_path
                else:
                    os.unlink(temp_path)
                    logger.warning(f"Compressed video still too large: {compressed_size:.1f} MB")
            
            return None
            
        except Exception as e:
            logger.error(f"Video compression failed: {e}")
            return None
    
    def send_whatsapp_alert(self, message, alert_type="info"):
        """Send WhatsApp alert using Twilio or WhatsApp Business API"""
        try:
            # WhatsApp configuration
            whatsapp_api_key = os.getenv('WHATSAPP_API_KEY') or self.config.get('WhatsApp', 'api_key', '')
            whatsapp_phone = os.getenv('WHATSAPP_PHONE') or self.config.get('WhatsApp', 'phone_number', '')
            admin_phone = os.getenv('ADMIN_PHONE') or self.config.get('WhatsApp', 'admin_phone', '')
            
            if not whatsapp_api_key or not admin_phone:
                return {"success": False, "error": "WhatsApp configuration missing"}
            
            # Example using Twilio WhatsApp API
            twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            
            if twilio_account_sid and twilio_auth_token:
                # Twilio WhatsApp implementation
                url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_account_sid}/Messages.json"
                
                data = {
                    'From': f'whatsapp:{whatsapp_phone}',
                    'To': f'whatsapp:{admin_phone}',
                    'Body': f"🚨 Vigint Alert ({alert_type.upper()})\n\n{message}"
                }
                
                response = requests.post(
                    url,
                    data=data,
                    auth=(twilio_account_sid, twilio_auth_token)
                )
                
                if response.status_code == 201:
                    logger.info("WhatsApp alert sent successfully")
                    return {"success": True}
                else:
                    return {"success": False, "error": f"Twilio API error: {response.status_code}"}
            else:
                return {"success": False, "error": "Twilio credentials not configured"}
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp alert: {e}")
            return {"success": False, "error": str(e)}
    
    def send_sms_alert(self, message, alert_type="info"):
        """Send SMS alert"""
        try:
            # SMS configuration
            twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            twilio_phone = os.getenv('TWILIO_PHONE') or self.config.get('SMS', 'phone_number', '')
            admin_phone = os.getenv('ADMIN_PHONE') or self.config.get('SMS', 'admin_phone', '')
            
            if not all([twilio_account_sid, twilio_auth_token, twilio_phone, admin_phone]):
                return {"success": False, "error": "SMS configuration missing"}
            
            url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_account_sid}/Messages.json"
            
            data = {
                'From': twilio_phone,
                'To': admin_phone,
                'Body': f"Vigint Alert ({alert_type.upper()}): {message[:140]}"  # SMS length limit
            }
            
            response = requests.post(
                url,
                data=data,
                auth=(twilio_account_sid, twilio_auth_token)
            )
            
            if response.status_code == 201:
                logger.info("SMS alert sent successfully")
                return {"success": True}
            else:
                return {"success": False, "error": f"Twilio SMS API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error sending SMS alert: {e}")
            return {"success": False, "error": str(e)}
    
    def send_webhook_alert(self, message, alert_type="info"):
        """Send webhook alert to external service"""
        try:
            webhook_url = os.getenv('ALERT_WEBHOOK_URL') or self.config.get('Webhooks', 'alert_url', '')
            
            if not webhook_url:
                return {"success": False, "error": "Webhook URL not configured"}
            
            payload = {
                'alert_type': alert_type,
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'source': 'vigint-system'
            }
            
            response = requests.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Webhook alert sent successfully")
                return {"success": True}
            else:
                return {"success": False, "error": f"Webhook error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error sending webhook alert: {e}")
            return {"success": False, "error": str(e)}


    def create_video_from_frames(self, frames, output_path=None, fps=25):
        """Create video file from a list of frame data"""
        try:
            if not frames:
                return None
            
            # Create temporary file if no output path specified
            if output_path is None:
                temp_fd, output_path = tempfile.mkstemp(suffix='.mp4', prefix='vigint_incident_')
                os.close(temp_fd)
            
            # Decode first frame to get dimensions
            first_frame_data = base64.b64decode(frames[0]['frame_data'])
            first_frame = cv2.imdecode(np.frombuffer(first_frame_data, np.uint8), cv2.IMREAD_COLOR)
            
            if first_frame is None:
                logger.error("Failed to decode first frame")
                return None
            
            height, width, _ = first_frame.shape
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if not out.isOpened():
                logger.error("Failed to create video writer")
                return None
            
            # Write frames to video
            frames_written = 0
            for frame_info in frames:
                try:
                    frame_data = base64.b64decode(frame_info['frame_data'])
                    frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        # Add timestamp overlay if available
                        if 'timestamp' in frame_info:
                            timestamp_text = frame_info['timestamp']
                            cv2.putText(frame, timestamp_text, (10, 30), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        
                        out.write(frame)
                        frames_written += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to process frame: {e}")
                    continue
            
            out.release()
            
            if frames_written > 0:
                logger.info(f"Created video with {frames_written} frames: {output_path}")
                return output_path
            else:
                logger.error("No frames were written to video")
                if os.path.exists(output_path):
                    os.unlink(output_path)
                return None
                
        except Exception as e:
            logger.error(f"Error creating video from frames: {e}")
            return None


# Convenience functions
def send_alert(message, alert_type="info", channels=None, video_path=None, incident_data=None):
    """Send alert through specified channels with optional video attachment"""
    alert_manager = AlertManager()
    return alert_manager.send_alert(message, alert_type, channels)


def send_security_alert_with_video(message, frames=None, incident_data=None):
    """Send security alert with video created from frames"""
    alert_manager = AlertManager()
    
    video_path = None
    if frames:
        video_path = alert_manager.create_video_from_frames(frames)
    
    # Send email alert with video attachment
    result = alert_manager.send_email_alert(
        message, 
        alert_type="security", 
        video_path=video_path,
        incident_data=incident_data
    )
    
    # Clean up temporary video file
    if video_path and os.path.exists(video_path):
        try:
            os.unlink(video_path)
        except Exception as e:
            logger.warning(f"Failed to clean up temporary video file: {e}")
    
    return result


def send_critical_alert(message):
    """Send critical alert through all available channels"""
    return send_alert(message, "critical", ["email", "sms", "whatsapp", "webhook"])


def send_warning_alert(message):
    """Send warning alert through email and webhook"""
    return send_alert(message, "warning", ["email", "webhook"])


def send_info_alert(message):
    """Send info alert through email only"""
    return send_alert(message, "info", ["email"])


if __name__ == '__main__':
    # Test the alert system
    alert_manager = AlertManager()
    result = alert_manager.send_email_alert("Test alert from Vigint system", "test")
    print(f"Alert test result: {result}")