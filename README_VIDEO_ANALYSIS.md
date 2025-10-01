# Vigint Video Analysis System

## Overview

The `vigint/app.py` file is the main video analysis application that processes RTSP video streams and analyzes frames using Google's Gemini AI for security monitoring.

## Features

- **RTSP Stream Processing**: Connects to RTSP video streams using GStreamer
- **AI-Powered Analysis**: Uses Google Gemini AI to analyze video frames for security events
- **Real-time Monitoring**: Processes video frames in real-time with configurable analysis intervals
- **Email Alerts**: Sends email notifications when security events are detected
- **Frame Buffering**: Maintains a buffer of recent frames for context analysis
- **Error Recovery**: Robust error handling and stream reconnection capabilities

## Prerequisites

### System Dependencies

1. **GStreamer**: Required for video stream processing
   ```bash
   # macOS
   brew install gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly
   
   # Ubuntu/Debian
   sudo apt-get install gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly
   ```

2. **FFmpeg**: Used for stream verification
   ```bash
   # macOS
   brew install ffmpeg
   
   # Ubuntu/Debian
   sudo apt-get install ffmpeg
   ```

3. **Python Dependencies**: Install from requirements.txt
   ```bash
   pip install -r requirements.txt
   ```

### API Keys

1. **Google Gemini AI API Key**: Required for frame analysis
   - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Add to config.ini under `[AI]` section

2. **Email Configuration**: Required for alerts
   - Configure SMTP settings in config.ini under `[Email]` section

## Configuration

Copy `config.ini.example` to `config.ini` and configure:

```ini
[RTSP]
host = localhost
port = 8554
username = vigint
password = vigint123
path = camera1

[AI]
gemini_api_key = your-gemini-api-key-here
analysis_interval = 30
enable_alerts = true

[Email]
smtp_server = smtp.gmail.com
smtp_port = 587
username = your-email@example.com
password = your-email-password-here
from_email = your-email@example.com
to_email = alerts@example.com
```

## Usage

### Basic Usage

```bash
# Run with default configuration
python vigint/app.py

# Run with custom RTSP URL
python vigint/app.py --rtsp-url rtsp://username:password@host:port/path

# Run with custom analysis interval (frames)
python vigint/app.py --analysis-interval 60

# Run without email alerts
python vigint/app.py --no-email
```

### Integration with RTSP Server

1. **Start the RTSP server first**:
   ```bash
   ./start_rtsp_server
   ```

2. **Stream a video file**:
   ```bash
   ffmpeg -re -i your_video.mp4 -c copy -f rtsp rtsp://vigint:vigint123@localhost:8554/camera1
   ```

3. **Run the analysis application**:
   ```bash
   python vigint/app.py
   ```

### Full System Startup

Use the main startup script to run everything together:

```bash
# Start full system (RTSP server + video analysis)
./start.sh full

# Or use the Python entry point
python start_vigint.py --mode full --video-input /path/to/video.mp4
```

## How It Works

1. **Stream Connection**: Connects to RTSP stream using GStreamer pipeline
2. **Frame Extraction**: Extracts video frames and maintains a rolling buffer
3. **Periodic Analysis**: Analyzes frames at configurable intervals (default: every 30 frames)
4. **AI Processing**: Sends frames to Google Gemini AI for security analysis
5. **Alert Detection**: Scans analysis results for security-relevant keywords
6. **Notification**: Sends email alerts when potential security events are detected

## Analysis Features

The AI analysis identifies:
- People and vehicles in the frame
- Unusual or suspicious activity
- Overall scene description
- Security concerns and alerts

## Troubleshooting

### Common Issues

1. **GStreamer Pipeline Errors**:
   - Ensure GStreamer is properly installed with all plugins
   - Check RTSP stream accessibility with VLC first
   - Verify authentication credentials

2. **Stream Connection Issues**:
   - Test stream with FFmpeg: `ffprobe rtsp://your-stream-url`
   - Check network connectivity and firewall settings
   - Verify RTSP server is running

3. **AI Analysis Not Working**:
   - Verify Gemini API key is correct and has quota
   - Check internet connectivity for API calls
   - Review logs for API error messages

4. **Email Alerts Not Sending**:
   - Verify SMTP configuration
   - Check email credentials and app passwords
   - Test email settings with a simple script

### Debugging

Enable debug logging by setting log level in config.ini:

```ini
[Logging]
level = DEBUG
```

View real-time logs:
```bash
tail -f vigint.log
```

## Performance Considerations

- **Analysis Interval**: Higher intervals reduce CPU usage but may miss events
- **Frame Buffer Size**: Larger buffers use more memory but provide better context
- **Stream Quality**: Lower resolution streams process faster but may reduce analysis accuracy
- **Concurrent Analysis**: Frame analysis runs in separate threads to avoid blocking stream processing

## Security Notes

- Store API keys securely and never commit them to version control
- Use strong authentication for RTSP streams
- Consider encrypting email credentials
- Monitor API usage to avoid unexpected charges
- Implement rate limiting for analysis requests

## Integration

The video analysis system integrates with:
- **RTSP Server**: For video stream input
- **Billing System**: For API usage tracking
- **Email System**: For alert notifications
- **Configuration Management**: For centralized settings