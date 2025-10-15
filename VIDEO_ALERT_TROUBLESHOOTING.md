# Video Alert Troubleshooting Guide

## Overview

This guide helps diagnose and fix issues with video alerts in the Vigint system.

## Common Issues and Solutions

### 1. "No video are included in email alerts"

**Symptoms:**
- Emails are sent but no video attachment
- Logs show "Video evidence not available"
- Video creation fails

**Diagnosis Steps:**

1. **Check if video alerts are enabled:**
   ```bash
   python check_email_config.py
   ```

2. **Test local video alert functionality:**
   ```bash
   python test_local_video_alerts.py
   ```

3. **Check frame buffer:**
   - Look for "Local frame buffer initialized" in logs
   - Verify frames are being added to buffer

**Solutions:**

#### A. Enable Local Video Alerts (Recommended)
The system now includes local video alert functionality that works without the API proxy:

```bash
# Test the local video alert system
python test_local_video_alerts.py
```

#### B. Fix API Proxy Connection
If using API proxy mode:

1. **Check API proxy is running:**
   ```bash
   # API proxy should be on port 5000, not 5001
   curl http://localhost:5000/api/health
   ```

2. **Fix port configuration:**
   - The system was trying to connect to port 5001
   - API proxy actually runs on port 5000
   - This has been fixed in the code

#### C. Configure Email Settings
```bash
# Set environment variables
export ALERT_EMAIL="your-email@gmail.com"
export ALERT_EMAIL_PASSWORD="your-app-password"
export ADMIN_EMAIL="admin@company.com"
export ALERT_SMTP_SERVER="smtp.gmail.com"
export ALERT_SMTP_PORT="587"
```

Or update `config.ini`:
```ini
[Alerts]
smtp_server = smtp.gmail.com
smtp_port = 587
sender_email = your-email@gmail.com
sender_password = your-app-password
admin_email = admin@company.com
```

### 2. "Connection refused" Errors

**Symptoms:**
```
HTTPConnectionPool(host='localhost', port=5001): Max retries exceeded
```

**Root Cause:**
- System was configured to use port 5001
- API proxy actually runs on port 5000

**Solution:**
This has been fixed in the code. The system now:
1. Uses correct port (5000) for API proxy
2. Falls back to local video alerts if API proxy unavailable

### 3. "No frames in buffer" Error

**Symptoms:**
```
API analysis failed: 400 - {"error":"No frames in buffer"}
```

**Root Cause:**
- Frames not being added to buffer properly
- Buffer timing issues

**Solution:**
The system now maintains both server-side and local frame buffers:
- Local buffer always works (fallback)
- Server buffer used when API proxy available
- Automatic fallback to local when server fails

### 4. Email Timeout Issues

**Symptoms:**
```
Error sending alert: HTTPConnectionPool(host='localhost', port=5001): Read timed out
```

**Solutions:**

#### A. Use Local Email System
The enhanced system now sends emails directly:
```python
from alerts import send_security_alert_with_video

# This works without API proxy
result = send_security_alert_with_video(message, frames, incident_data)
```

#### B. Check Email Configuration
```bash
python check_email_config.py
```

#### C. Gmail App Passwords
If using Gmail, you need an App Password:
1. Enable 2-factor authentication
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use App Password instead of regular password

### 5. Video Compression Issues

**Symptoms:**
```
OpenCV: FFMPEG: tag 0x34363248/'H264' is not supported
```

**Solution:**
The system automatically handles codec fallbacks:
- Tries H264 first
- Falls back to avc1
- Falls back to mp4v
- Compresses videos for email size limits

### 6. Video Quality Issues

**Symptoms:**
- Videos are too compressed
- Poor video quality
- Videos too large for email

**Solutions:**

#### A. Adjust Compression Settings
In `config.ini`:
```ini
[VideoAnalysis]
compression_quality = 0.85  # Higher = better quality
max_email_size_mb = 20      # Increase if email server allows
```

#### B. Adjust Buffer Duration
```ini
[VideoAnalysis]
short_buffer_duration = 3   # Seconds of video for quick analysis
long_buffer_duration = 10   # Seconds of video for incidents
```

## Testing and Verification

### 1. Test Email Configuration
```bash
python check_email_config.py
```

### 2. Test Local Video Alerts
```bash
python test_local_video_alerts.py
```

### 3. Test Full Video Alert System
```bash
python test_video_alerts.py
```

### 4. Test with Real Video
```bash
python start_vigint.py --video-input '/path/to/your/video.mp4'
```

## System Architecture Changes

### Before (Issues)
- Only API proxy mode for video alerts
- Single point of failure
- Port configuration errors (5001 vs 5000)
- No local fallback

### After (Fixed)
- **Dual Mode**: API proxy + local fallback
- **Local Video Alerts**: Works without API proxy
- **Correct Ports**: Fixed port configuration
- **Robust Buffering**: Local + server-side buffers
- **Smart Fallback**: Automatic fallback when API proxy fails

## Configuration Examples

### Minimal Working Configuration
```bash
# Environment variables (recommended)
export ALERT_EMAIL="alerts@company.com"
export ALERT_EMAIL_PASSWORD="your-app-password"
export ADMIN_EMAIL="security@company.com"
```

### Full Configuration
```ini
# config.ini
[Alerts]
smtp_server = smtp.gmail.com
smtp_port = 587
sender_email = alerts@company.com
sender_password = your-app-password
admin_email = security@company.com

[VideoAnalysis]
short_buffer_duration = 3
long_buffer_duration = 10
analysis_fps = 25
video_format = mp4
compression_quality = 0.85
max_email_size_mb = 20
```

## Verification Steps

After applying fixes:

1. **Check Configuration:**
   ```bash
   python check_email_config.py
   ```

2. **Test Local Alerts:**
   ```bash
   python test_local_video_alerts.py
   ```

3. **Run System:**
   ```bash
   python start_vigint.py --video-input 'your-video.mp4'
   ```

4. **Verify Email:**
   - Check that security alert emails are received
   - Verify video attachments are present
   - Confirm videos play correctly

## Expected Behavior

### Normal Operation
```
✅ Local frame buffer initialized (max 250 frames)
✅ Connected to Vigint API proxy
✅ API authentication successful
🚨 SECURITY INCIDENT DETECTED in buffer analysis!
🚨 SECURITY ALERT EMAIL SENT via API proxy!
```

### Fallback Mode (API Proxy Unavailable)
```
✅ Local frame buffer initialized (max 250 frames)
❌ Failed to connect to API proxy
🚨 SECURITY INCIDENT DETECTED in buffer analysis!
ℹ️ Falling back to local video alert system...
🚨 LOCAL SECURITY ALERT WITH VIDEO SENT!
```

## Support

If issues persist after following this guide:

1. **Check Logs:** Look for specific error messages
2. **Test Components:** Use individual test scripts
3. **Verify Dependencies:** Ensure OpenCV, email libraries installed
4. **Check Network:** Verify SMTP server connectivity

The system is now much more robust with local fallback capabilities, so video alerts should work even when the API proxy is unavailable.