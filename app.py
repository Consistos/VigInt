import cv2
import requests
import time
from collections import deque
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import json
import configparser
import google.generativeai as genai
from twilio.rest import Client

# --- Configuration ---
config = configparser.ConfigParser()
config.read('config.ini')

RTSP_URL = config.get('CCTV', 'rtsp_url')
GEMINI_API_KEY = config.get('Gemini', 'api_key')

EMAIL_SENDER = config.get('Email', 'sender_email')
EMAIL_PASSWORD = config.get('Email', 'sender_password')
EMAIL_RECEIVER = config.get('Email', 'receiver_email')
SMTP_SERVER = config.get('Email', 'smtp_server')
SMTP_PORT = config.getint('Email', 'smtp_port')

# WhatsApp configuration
TWILIO_ACCOUNT_SID = config.get('WhatsApp', 'account_sid')
TWILIO_AUTH_TOKEN = config.get('WhatsApp', 'auth_token')
WHATSAPP_FROM = config.get('WhatsApp', 'from_number')
WHATSAPP_TO = config.get('WhatsApp', 'to_number')

LONG_BUFFER_DURATION = config.getint('Analysis', 'long_buffer_duration')
FRAMES_PER_SECOND = config.getint('Analysis', 'frames_per_second') # Assuming a frame rate for timestamp calculation
# --- Initialize Gemini API ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-1.5-flash")  # Or a suitable video model

# --- Helper Functions ---

def send_email_alert(subject, body, video_path=None):
    """Sends an email with the alert details and optional video attachment."""
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    if video_path:
        with open(video_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.b64encode(part)
            part.add_header('Content-Disposition', f"attachment; filename=event_video.mp4")
            msg.attach(part)

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, text)
        server.quit()
        print("Email alert sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

def send_whatsapp_alert(message, video_path=None):
    """Sends a WhatsApp message using Twilio with optional video attachment."""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        media_url = None
        if video_path:
            # Convert video to MP4 format if needed (WhatsApp supports MP4)
            mp4_path = video_path
            if not video_path.endswith('.mp4'):
                mp4_path = video_path.rsplit('.', 1)[0] + '.mp4'
                cap = cv2.VideoCapture(video_path)
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(mp4_path, fourcc, cap.get(cv2.CAP_PROP_FPS),
                                    (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                                     int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                    out.write(frame)
                cap.release()
                out.release()
            
            # Upload video to Twilio Media
            with open(mp4_path, 'rb') as video_file:
                media = client.media.v1.media_list.create(
                    content_type='video/mp4',
                    data=video_file
                )
                media_url = media.uri

        # Send WhatsApp message with media if available
        message_params = {
            'from_': f"whatsapp:{WHATSAPP_FROM}",
            'body': message,
            'to': f"whatsapp:{WHATSAPP_TO}"
        }
        
        if media_url:
            message_params['media_url'] = [media_url]
            
        message = client.messages.create(**message_params)
        print("WhatsApp alert sent successfully!")
        
        # Clean up temporary MP4 file if it was created
        if video_path and mp4_path != video_path:
            import os
            os.remove(mp4_path)
            
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")

def send_alert(subject, body, video_path=None):
    """Sends both email and WhatsApp alerts."""
    # Send email alert
    send_email_alert(subject, body, video_path)
    
    # Send WhatsApp alert
    whatsapp_message = f"{subject}\n\n{body}"
    send_whatsapp_alert(whatsapp_message, video_path)

def create_video_from_frames(frames, output_path, fps):
    """Creates a video file from a list of frames."""
    if not frames:
        return False
    height, width, layers = frames[0].shape
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    video = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    for frame in frames:
        video.write(frame)
    cv2.destroyAllWindows()
    video.release()
    return True

import time

def analyze_buffer_with_gemini(video_path):
    """Analyzes the video buffer using the Gemini API for incident detection."""
    prompt = f"""Analyze the provided video. If water is detected, return a JSON object with a string describing the type of infrastructure. If no water is detected, return an empty JSON object.""" # For the test stream
    """
    Analyze the provided video for any incidents such as personal injury, theft, property damage, or other illegal activity.
    If an incident is detected, return a JSON object with the following keys:
    - "incident_type": A string describing the type of incident detected (e.g., "Theft", "Property Damage", "Assault").
    - "description": A brief description of the behavior observed during the incident.
    - "timestamps": A list containing the start and end timestamps of the incident within the video, in seconds.

    If no incident is detected, return an empty JSON object.
    """ # For incident detection
    
    try:
        # Configure the Gemini API
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Create a GenerativeModel instance
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Read the video file as binary data
        with open(video_path, "rb") as video_file:
            video_data = video_file.read()
        
        # Create the content parts for the generation request
        content = [
            prompt,
            {
                "mime_type": "video/mp4",
                "data": video_data
            }
        ]
        
        print("Making LLM inference request with video data...")
        response = model.generate_content(content)
        
        try:
            # Get the text content from the response and parse it as JSON
            response_text = response.text
            # Remove any markdown formatting if present
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            
            if not response_text:
                print("Received empty response from Gemini API")
                return {}
                
            print(f"Response: {response_text}")
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Error decoding Gemini API response: {response_text}")
            print(f"JSON decode error: {str(e)}")
            return {}
    except Exception as e:
        print(f"Error analyzing video: {e}")
        return {}

# --- Main Program ---

def main():
    cap = cv2.VideoCapture(RTSP_URL)
    if not cap.isOpened():
        print(f"Error: Could not open RTSP stream from {RTSP_URL}")
        return

    long_frame_buffer = deque()
    frame_count = 0

    print("Starting real-time analysis...")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame from stream. Exiting.")
            break

        long_frame_buffer.append(frame)

        # Keep long buffer within the desired duration
        if len(long_frame_buffer) > LONG_BUFFER_DURATION * FRAMES_PER_SECOND:
            long_frame_buffer.popleft()

        frame_count += 1

        # Analyze the buffer periodically (e.g., every LONG_BUFFER_DURATION seconds)
        if frame_count % (LONG_BUFFER_DURATION * FRAMES_PER_SECOND) == 0 and long_frame_buffer:
            print("Analyzing video buffer...")
            video_filename = "buffer_video.mp4"
            if create_video_from_frames(list(long_frame_buffer), video_filename, FRAMES_PER_SECOND):
                analysis_result = analyze_buffer_with_gemini(video_filename)

                if analysis_result is None:  # Only None indicates a failure
                    print("Failed to analyze video buffer.")
                elif analysis_result.get("incident_type"):
                    incident_type = analysis_result["incident_type"]
                    description = analysis_result["description"]
                    timestamps = analysis_result["timestamps"]

                    start_time_str = f"{timestamps[0]:.2f}s"
                    end_time_str = f"{timestamps[1]:.2f}s"

                    alert_subject = f"Vigint - Potentiel {incident_type} détecté"
                    alert_body = f"Un potentiel incident a été détecté '{incident_type}'.\n\n" \
                                 f"Description: {description}\n\n" \
                                 f"L'incident fut détecté entre {start_time_str} et {end_time_str}."

                    send_alert(alert_subject, alert_body, video_filename)
                else:
                    print("No incident detected in the buffer.")
                # Optionally delete the temporary video file
                # import os
                # os.remove(video_filename)


    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()