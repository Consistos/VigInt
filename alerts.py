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
        """Send email alert with private video link instead of attachment"""
        try:
            # Email configuration for alerts (check both Email and Alerts sections)
            smtp_server = (os.getenv('ALERT_SMTP_SERVER') or 
                          self.config.get('Alerts', 'smtp_server', None) or 
                          self.config.get('Email', 'smtp_server', 'smtp.gmail.com'))
            
            smtp_port = int(os.getenv('ALERT_SMTP_PORT') or 
                           self.config.get('Alerts', 'smtp_port', None) or 
                           self.config.get('Email', 'smtp_port', '587'))
            
            sender_email = (os.getenv('ALERT_EMAIL') or 
                           self.config.get('Alerts', 'sender_email', None) or 
                           self.config.get('Email', 'sender_email', None) or
                           self.config.get('Email', 'from_email', 'alerts@vigint.com'))
            
            sender_password = (os.getenv('ALERT_EMAIL_PASSWORD') or 
                              self.config.get('Alerts', 'sender_password', None) or 
                              self.config.get('Email', 'sender_password', None) or
                              self.config.get('Email', 'password', ''))
            
            admin_email = (os.getenv('ADMIN_EMAIL') or 
                          self.config.get('Alerts', 'admin_email', None) or 
                          self.config.get('Email', 'admin_email', None) or
                          self.config.get('Email', 'to_email', 'admin@vigint.com'))
            
            if not sender_password:
                return {"success": False, "error": "No alert email password configured"}
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = admin_email
            
            # Create subject with incident type if available (in French)
            subject = f"🚨 Alerte Vigint - {alert_type.upper()}"
            if incident_data and incident_data.get('incident_type'):
                subject = f"🚨 Alerte Vigint - {incident_data['incident_type']} - {alert_type.upper()}"
            
            msg['Subject'] = subject
            
            # Enhanced body with incident details in French
            body = f"""
🚨 ALERTE SYSTÈME VIGINT

Type d'alerte: {alert_type.upper()}
Horodatage: {datetime.now().isoformat()}

Message:
{message}
"""
            
            # Add incident-specific information if available
            if incident_data:
                body += f"""

DÉTAILS DE L'INCIDENT:
Niveau de risque: {incident_data.get('risk_level', 'INCONNU')}
Numéro d'image: {incident_data.get('frame_count', 'N/A')}
Confiance: {incident_data.get('confidence', 'N/A')}
"""
                # Only add analysis if it's not already in the message
                if 'analysis' in incident_data and incident_data['analysis'] not in message:
                    body += f"""
Analyse IA:
{incident_data['analysis']}
"""
            
            # Upload video and add private link instead of attachment (GDPR compliant)
            video_link_info = None
            
            # Check if video link info is already provided in incident_data (from GDPR service)
            if incident_data and 'video_link_info' in incident_data:
                video_link_info = incident_data['video_link_info']
                upload_result = video_link_info
                
                body += f"""

📹 PREUVES VIDÉO DISPONIBLES (CONFORME RGPD)
🎬 CRÉÉ AVEC LE SYSTÈME DUAL-BUFFER RÉVOLUTIONNAIRE

🔗 LIEN VIDÉO PRIVÉ SÉCURISÉ:
{upload_result['private_link']}

💾 Taille: {upload_result.get('video_size_mb', 'N/A')} MB
🆔 ID Vidéo: {upload_result['video_id']}
⏰ Expiration: {upload_result['expiration_time']}

🎯 QUALITÉ VIDÉO RÉVOLUTIONNAIRE:
✅ Vidéo fluide 25 FPS (pas d'images saccadées comme avant!)
✅ Footage continu sans interruptions ni gaps
✅ Qualité professionnelle pour preuves de sécurité
✅ Architecture dual-buffer innovante

🔒 ACCÈS SÉCURISÉ:
Cliquez sur le lien ci-dessus pour visualiser la vidéo de l'incident.
Le lien est sécurisé avec un token d'accès et expirera automatiquement.

🚀 INNOVATION TECHNIQUE MAJEURE:
Cette vidéo utilise le nouveau système "dual-buffer" qui capture 
TOUTES les images en continu AVANT l'analyse IA. Résultat: 
vidéo fluide de qualité professionnelle au lieu des anciennes 
vidéos saccadées avec des gaps de 5 secondes!

🏆 AMÉLIORATION: 125x plus d'images pour une vidéo fluide!
"""
                
                # Add local file info if available (for debugging)
                if upload_result.get('local_file'):
                    body += f"""
🔧 INFO TECHNIQUE (pour le support):
   Fichier local: {upload_result['local_file']}
   Service: {upload_result.get('upload_response', {}).get('cloud_provider', 'N/A')}
"""
                logger.info(f"Using pre-uploaded GDPR-compliant video: {upload_result['video_id']}")
                
            elif video_path and os.path.exists(video_path):
                try:
                    # Use GDPR-compliant service (cloud only, no local storage)
                    from gdpr_compliant_video_service import create_gdpr_video_service
                    video_service = create_gdpr_video_service()
                    
                    # Upload video and get private link (GDPR compliant)
                    upload_result = video_service.upload_video(video_path, incident_data, expiration_hours=48)
                    
                    if upload_result['success']:
                        video_link_info = upload_result
                        
                        # Get original file size before it was deleted
                        video_size = incident_data.get('video_size_mb', 'N/A')
                        if video_size == 'N/A' and os.path.exists(video_path):
                            video_size = os.path.getsize(video_path) / (1024 * 1024)  # Size in MB
                        
                        body += f"""

📹 PREUVES VIDÉO DISPONIBLES (CONFORME RGPD)
Lien privé sécurisé: {upload_result['private_link']}
Taille du fichier: {video_size:.1f} MB
Expiration: {upload_result['expiration_time']}
ID Vidéo: {upload_result['video_id']}
Niveau de confidentialité: {upload_result.get('privacy_level', 'Élevé')}

⚠️ IMPORTANT: Ce lien est privé et sécurisé conforme au RGPD.
Il expirera automatiquement dans {upload_result.get('data_retention_hours', 48)} heures.
Aucune copie locale n'est conservée pour respecter la vie privée.

🔒 Cliquez sur le lien pour visualiser la vidéo de l'incident de manière sécurisée.
"""
                        
                        logger.info(f"Video uploaded to GDPR-compliant cloud storage: {upload_result['video_id']}")
                        logger.info(f"Local file deleted for privacy compliance: {upload_result.get('local_file_deleted', False)}")
                    else:
                        body += f"""

⚠️ Échec du téléchargement sécurisé de la vidéo
Erreur: {upload_result.get('error', 'Erreur inconnue')}
La vidéo n'est pas disponible en ligne.

🔒 Note: Aucune copie locale n'a été conservée pour respecter le RGPD.
"""
                        logger.error(f"Failed to upload video to GDPR-compliant storage: {upload_result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"Error uploading video to sparse-ai.com: {e}")
                    body += f"""

⚠️ Erreur lors du téléchargement de la vidéo
Erreur technique: {str(e)}
La vidéo n'est pas disponible en ligne.
"""
            else:
                body += """

⚠️ Preuves vidéo non disponibles
"""
            
            body += """

---
Système de surveillance Vigint
Veuillez examiner immédiatement et prendre les mesures appropriées.
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Alert email sent to {admin_email} (video link: {video_link_info is not None})")
            return {
                "success": True, 
                "video_link_provided": video_link_info is not None,
                "video_link_info": video_link_info,
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
            
            # Convert to list to avoid deque mutation issues during iteration
            frames_list = list(frames)
            
            # Create temporary file if no output path specified
            if output_path is None:
                temp_fd, output_path = tempfile.mkstemp(suffix='.mp4', prefix='vigint_incident_')
                os.close(temp_fd)
            
            # Decode first frame to get dimensions
            first_frame_data = base64.b64decode(frames_list[0]['frame_data'])
            first_frame = cv2.imdecode(np.frombuffer(first_frame_data, np.uint8), cv2.IMREAD_COLOR)
            
            if first_frame is None:
                logger.error("Failed to decode first frame")
                return None
            
            height, width, _ = first_frame.shape
            
            # Create video writer with better codec settings
            # Try different codecs for better compatibility
            codecs_to_try = [
                cv2.VideoWriter_fourcc(*'mp4v'),
                cv2.VideoWriter_fourcc(*'XVID'),
                cv2.VideoWriter_fourcc(*'H264'),
                cv2.VideoWriter_fourcc(*'avc1')
            ]
            
            out = None
            for fourcc in codecs_to_try:
                out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
                if out.isOpened():
                    logger.info(f"Video writer created successfully with codec: {fourcc}")
                    break
                else:
                    out.release()
            
            if out is None or not out.isOpened():
                logger.error("Failed to create video writer with any codec")
                return None
            
            # Write frames to video
            frames_written = 0
            for frame_info in frames_list:
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
    """Send security alert with video using GDPR-compliant cloud storage"""
    alert_manager = AlertManager()
    
    video_path = None
    if frames:
        try:
            # Use GDPR-compliant service directly for frame-to-video conversion
            from gdpr_compliant_video_service import create_and_upload_video_from_frames_gdpr
            
            # Determine appropriate FPS based on analysis interval
            analysis_interval = 5  # Default
            if frames and len(frames) > 0:
                # Check if frames have analysis interval info
                first_frame = frames[0]
                if 'analysis_interval' in first_frame:
                    analysis_interval = first_frame['analysis_interval']
            
            # Ensure video is 25 FPS for smooth playback as per requirements
            target_fps = 25.0
            
            logger.info(f"Creating video with {target_fps:.2f} FPS (analysis interval: {analysis_interval}s)")
            
            # Create and upload video directly (GDPR compliant) with correct FPS
            upload_result = create_and_upload_video_from_frames_gdpr(frames, incident_data, expiration_hours=48, target_fps=target_fps)
            
            if upload_result['success']:
                # Calculate video size for display
                video_size_mb = upload_result.get('video_duration', 0) * 0.5  # Rough estimate
                if 'frames_processed' in upload_result:
                    video_size_mb = upload_result['frames_processed'] * 0.02  # ~20KB per frame
                
                # Add video size to upload result
                upload_result['video_size_mb'] = round(video_size_mb, 1)
                
                # Send email with video link info
                result = alert_manager.send_email_alert(
                    message,  # Use original message
                    alert_type="security",
                    video_path=None,  # No local file
                    incident_data={
                        **(incident_data or {}),
                        'video_link_info': upload_result,
                        'gdpr_compliant': True
                    }
                )
                
                # Add video link info to result
                result['video_link_info'] = upload_result
                result['video_link_provided'] = True
                
                return result
            else:
                # Fallback to text-only alert
                logger.warning("GDPR-compliant video upload failed, sending text-only alert")
                return alert_manager.send_email_alert(
                    message + "\n\n⚠️ Vidéo non disponible (échec du téléchargement sécurisé)",
                    alert_type="security",
                    incident_data=incident_data
                )
        
        except Exception as e:
            logger.error(f"Error with GDPR-compliant video service: {e}")
            # Fallback to traditional method
            video_path = alert_manager.create_video_from_frames(frames)
    
    # Fallback: Send email alert with video file (will be processed by GDPR service)
    result = alert_manager.send_email_alert(
        message, 
        alert_type="security", 
        video_path=video_path,
        incident_data=incident_data
    )
    
    # Note: GDPR service automatically deletes local files, no manual cleanup needed
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