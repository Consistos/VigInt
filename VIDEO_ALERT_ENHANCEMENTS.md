# Video Alert Enhancements

## Overview

The Vigint alert system has been enhanced to include video attachments in security alert emails. This provides visual evidence of security incidents, making alerts more actionable and informative.

## Key Features

### 1. Video Attachment Support
- **Automatic Video Creation**: Creates MP4 videos from buffered frames
- **Email Attachment**: Attaches videos directly to alert emails
- **Compression**: Automatically compresses videos to meet email size limits
- **Fallback**: Gracefully handles cases where video attachment fails

### 2. Enhanced Alert System
- **Rich Incident Data**: Includes risk levels, confidence scores, and detailed analysis
- **Professional Formatting**: Improved email formatting with incident metadata
- **Multiple Alert Types**: Supports different alert types (security, warning, critical)
- **Video Evidence**: Includes video duration and attachment status in emails

### 3. Frame Buffer Management
- **Continuous Buffering**: Maintains rolling buffer of recent frames
- **Configurable Duration**: Adjustable buffer size (default: 8-10 seconds)
- **Memory Efficient**: Uses deque with maximum size limits
- **Timestamp Overlay**: Adds timestamps to video frames

## Implementation Details

### Files Modified

1. **alerts.py**
   - Added video attachment functionality
   - Enhanced email formatting
   - Added video compression for email compatibility
   - New `send_security_alert_with_video()` function

2. **video_analyzer.py**
   - Added frame buffering
   - Enhanced alert sending with video evidence
   - Improved incident detection workflow

3. **secure_video_analyzer.py**
   - Added local video alert capability
   - Frame buffer management
   - Fallback when API proxy unavailable

### New Functions

#### AlertManager Class
- `send_email_alert()` - Enhanced with video support
- `create_video_from_frames()` - Creates MP4 from frame data
- `_attach_video_to_email()` - Handles video attachment
- `_compress_video_for_email()` - Compresses videos for email

#### Convenience Functions
- `send_security_alert_with_video()` - Main function for video alerts
- Enhanced existing alert functions with video support

## Usage Examples

### Basic Video Alert
```python
from alerts import send_security_alert_with_video

# Send alert with video from frames
result = send_security_alert_with_video(
    message="Security incident detected",
    frames=frame_buffer,  # List of frame data
    incident_data={
        'risk_level': 'HIGH',
        'confidence': 0.95,
        'analysis': 'Suspicious activity detected'
    }
)
```

### Using AlertManager Directly
```python
from alerts import AlertManager

alert_manager = AlertManager()
result = alert_manager.send_email_alert(
    message="Security alert",
    alert_type="security",
    video_path="/path/to/video.mp4",
    incident_data={'risk_level': 'MEDIUM'}
)
```

## Configuration

### Email Settings
Configure in `config.ini` or environment variables:
```ini
[Alerts]
smtp_server = smtp.gmail.com
smtp_port = 587
sender_email = alerts@vigint.com
sender_password = your_password
admin_email = admin@vigint.com
```

### Video Settings
```ini
[VideoAnalysis]
short_buffer_duration = 3
long_buffer_duration = 10
analysis_fps = 25
video_format = mp4
compression_quality = 0.85
max_email_size_mb = 20
```

## Technical Specifications

### Video Format
- **Codec**: H.264/MP4V (with fallbacks)
- **Format**: MP4
- **Resolution**: Maintains original or compressed for size
- **Frame Rate**: 25 FPS (configurable)
- **Compression**: Automatic when needed for email limits

### Email Compatibility
- **Size Limit**: 20MB default (configurable)
- **MIME Type**: Proper video/mp4 MIME types
- **Filename**: Descriptive with incident details
- **Fallback**: Text-only alerts if video fails

### Buffer Management
- **Duration**: 8-10 seconds of video evidence
- **Memory**: Efficient deque-based circular buffer
- **Frame Rate**: 25 FPS capture and playback
- **Storage**: Base64 encoded frames in memory

## Error Handling

### Video Creation Failures
- Logs detailed error messages
- Falls back to text-only alerts
- Continues operation without video

### Email Delivery Issues
- Retry mechanisms with exponential backoff
- Compression attempts for oversized videos
- Text-only fallback for persistent failures

### Storage Issues
- Temporary file cleanup
- Disk space monitoring
- Graceful degradation when storage full

## Testing

### Test Scripts
1. **test_video_alerts.py** - Comprehensive video alert testing
2. **example_video_alert_usage.py** - Usage examples and demos

### Manual Testing
```bash
# Test basic video alert functionality
python test_video_alerts.py

# Run usage examples
python example_video_alert_usage.py
```

## Benefits

### For Security Personnel
- **Visual Evidence**: See exactly what triggered the alert
- **Context**: Understand incident progression through video
- **Faster Response**: Make informed decisions quickly
- **Documentation**: Automatic evidence collection

### For System Administrators
- **Reliability**: Robust error handling and fallbacks
- **Monitoring**: Detailed logging of alert delivery
- **Scalability**: Efficient memory and storage usage
- **Maintenance**: Self-cleaning temporary files

## Future Enhancements

### Planned Features
- **Multiple Camera Angles**: Combine feeds from multiple cameras
- **AI-Enhanced Highlights**: Mark key moments in video timeline
- **Cloud Storage Integration**: Store videos in cloud for larger files
- **Mobile Notifications**: Push notifications with video previews

### Performance Optimizations
- **Streaming Compression**: Real-time video compression
- **Adaptive Quality**: Dynamic quality based on incident severity
- **Batch Processing**: Handle multiple incidents efficiently
- **Caching**: Intelligent frame caching strategies

## Troubleshooting

### Common Issues

1. **Video Not Attached**
   - Check email size limits
   - Verify video creation succeeded
   - Review compression settings

2. **Email Delivery Failures**
   - Verify SMTP configuration
   - Check network connectivity
   - Review authentication credentials

3. **Poor Video Quality**
   - Adjust compression settings
   - Increase buffer duration
   - Check source video quality

### Debug Commands
```bash
# Check email configuration
python -c "from alerts import AlertManager; AlertManager().send_email_alert('test')"

# Test video creation
python -c "from alerts import AlertManager; print(AlertManager().create_video_from_frames([]))"

# Verify buffer functionality
python test_video_alerts.py
```

## Conclusion

The video alert enhancements provide a significant improvement to the Vigint security system by adding visual evidence to security alerts. This makes the system more effective for security personnel and provides better documentation of security incidents.

The implementation is robust, with comprehensive error handling and fallback mechanisms to ensure reliable operation even when video functionality encounters issues.