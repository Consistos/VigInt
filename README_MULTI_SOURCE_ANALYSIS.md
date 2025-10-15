# Multi-Source Video Analysis System

The Multi-Source Video Analysis System allows simultaneous analysis of multiple video sources using the **dual-buffer system** with Gemini 2.5 Flash-Lite and Flash models through the API proxy.

## Features

### 🎯 Core Functionality
- **Simultaneous Analysis**: Process multiple video sources concurrently via API
- **Dual-Buffer System**: Flash-Lite (3s) for detection → Flash (10s) for confirmation
- **Veto Power**: Flash has final decision on whether to send email alerts
- **API-Based Architecture**: Uses `api_proxy.py` for consistent analysis logic
- **Real-time Monitoring**: Continuous frame buffering with periodic analysis
- **Security Incident Detection**: AI-powered detection with French language alerts

### ⚡ Dual-Buffer Flow
1. **Continuous Buffering**: Frames sent to API buffer in real-time
2. **Flash-Lite Screening** (every 3s): Quick incident detection on short buffer
3. **Flash Confirmation** (on detection): Detailed analysis on long buffer (10s)
4. **Veto System**: Email sent ONLY if Flash confirms the incident

### 🔧 Configuration Requirements
- **API Server**: `api_proxy.py` must be running
- **API Key**: Vigint API key for authentication
- **Environment Variables**: 
  - `VIGINT_API_KEY`: Your API key
  - `GOOGLE_API_KEY`: Gemini API key (used by api_proxy.py)

## Quick Start

### Prerequisites

1. **Start the API proxy** (in a separate terminal):
```bash
python api_proxy.py
```

2. **Set your API key**:
```bash
export VIGINT_API_KEY=your_api_key_here
```

### 1. Basic Usage with Video Files

```bash
# Analyze multiple video sources with dual-buffer system
python multi_source_video_analyzer.py \
  --sources buffer_video_1.mp4 buffer_video_2.mp4 buffer_video_3.mp4 \
  --names "Front Door" "Sales Floor" "Checkout" \
  --interval 3
```

### 2. With RTSP Streams

```bash
# Analyze RTSP camera streams
python multi_source_video_analyzer.py \
  --sources rtsp://camera1/stream rtsp://camera2/stream \
  --names "Camera 1" "Camera 2" \
  --api-url http://localhost:5000 \
  --api-key your_api_key
```

### 2. Interactive Management

```bash
# Start interactive mode
python run_multi_source_analysis.py interactive

# Available commands in interactive mode:
# - start: Start analysis
# - stop: Stop analysis  
# - status: Show system status
# - add: Add video source
# - remove: Remove video source
# - list: List all sources
# - configure: Configure settings
# - quit: Exit
```

### 3. Command Line Management

```bash
# Add a video source
python run_multi_source_analysis.py add-source \
  --source-id camera1 \
  --rtsp-url rtsp://192.168.1.100:554/stream1 \
  --name "Front Door Camera" \
  --location "Main Entrance" \
  --priority high

# List all sources
python run_multi_source_analysis.py list-sources

# Start analysis
python run_multi_source_analysis.py start --interval 15

# Check status
python run_multi_source_analysis.py status
```

## Configuration Files

### Multi-Source Configuration (`multi_source_config.json`)

```json
{
  "version": "1.0",
  "analysis_settings": {
    "analysis_interval": 10,
    "aggregation_threshold": 4,
    "max_concurrent_analyses": 4,
    "frame_buffer_duration": 10
  },
  "video_sources": {
    "camera1": {
      "source_id": "camera1",
      "rtsp_url": "rtsp://192.168.1.100:554/stream1",
      "name": "Front Door Camera",
      "enabled": true,
      "location": "Main Entrance",
      "priority": "high",
      "analysis_enabled": true,
      "alert_enabled": true
    }
  }
}
```

### Main Configuration (`config.ini`)

```ini
[MultiSourceAnalysis]
analysis_interval = 10
aggregation_threshold = 4
max_concurrent_analyses = 4
frame_buffer_duration = 10
create_composite_frames = true
add_camera_labels = true
composite_grid_size = 2x2
```

## API Usage

### Python API

```python
from multi_source_video_analyzer import MultiSourceVideoAnalyzer

# Create analyzer with API configuration
analyzer = MultiSourceVideoAnalyzer(
    api_key='your_vigint_api_key',
    api_url='http://localhost:5000'
)

# Add video sources
analyzer.add_video_source("cam1", "rtsp://192.168.1.100:554/stream1", "Front Door")
analyzer.add_video_source("cam2", "rtsp://192.168.1.101:554/stream1", "Sales Floor")
analyzer.add_video_source("cam3", "rtsp://192.168.1.102:554/stream1", "Checkout")

# Configure analysis interval (Flash-Lite screening frequency)
analyzer.analysis_interval = 3  # seconds

# Start analysis (begins dual-buffer system)
analyzer.start_analysis()
# This starts:
# - Continuous frame buffering to API
# - Flash-Lite screening every 3 seconds
# - Flash confirmation on detections

# Monitor status
status = analyzer.get_status()
print(f"Active sources: {status['active_sources']}/{status['total_sources']}")

# Stop analysis
analyzer.stop_analysis()
```

### Direct API Endpoints

The system exposes these endpoints in `api_proxy.py`:

#### Buffer Frames
```bash
POST /api/video/multi-source/buffer
{
  "source_id": "cam1",
  "source_name": "Front Door",
  "frame_data": "base64_encoded_frame",
  "frame_count": 123
}
```

#### Analyze Multiple Sources
```bash
POST /api/video/multi-source/analyze
{
  "source_ids": ["cam1", "cam2", "cam3"]
}
```

Response includes:
- Per-source analysis results
- Flash-Lite detections
- Flash confirmations
- Veto information
- Summary statistics

### Configuration Management

```python
from multi_source_config import MultiSourceConfig

# Create config manager
config = MultiSourceConfig()

# Add sources
config.add_video_source(
    "camera1", 
    "rtsp://192.168.1.100:554/stream1",
    name="Front Door Camera",
    location="Main Entrance",
    priority="high"
)

# Get analysis organization
analysis_config = config.get_sources_for_analysis()
print(f"Aggregated groups: {len(analysis_config['aggregated_groups'])}")
print(f"Individual sources: {len(analysis_config['individual_sources'])}")
```

## Analysis Process

### 1. Source Management
- Each video source runs in its own thread
- Continuous frame capture at ~25 FPS
- Frames sent to API buffer in real-time
- Health monitoring and reconnection

### 2. Dual-Buffer Analysis (API-Based)
**Stage 1 - Flash-Lite Screening (Every 3 seconds):**
- Analyzes most recent frame from short buffer (3 seconds)
- Uses Gemini 2.5 Flash-Lite (fast, cost-effective)
- Quick incident detection
- If incident detected → Triggers Stage 2

**Stage 2 - Flash Confirmation (On Detection):**
- Analyzes 3 key frames from long buffer (10 seconds)
- Uses Gemini 2.5 Flash (more powerful, accurate)
- Makes FINAL DECISION: Confirm or Veto
- Email sent ONLY if Flash confirms

### 3. Veto System
- **Flash-Lite detects → Flash confirms**: Email sent ✅
- **Flash-Lite detects → Flash vetoes**: NO email ❌
- Reduces false positives
- Flash has final authority

### 4. Alert System
- Automatic email alerts ONLY on Flash confirmation
- Video evidence from long buffer (10 seconds)
- Detailed incident reports in French
- Includes Flash-Lite and Flash analysis results

## Security Features

### Incident Detection
- **Shoplifting Detection**: Concealment behaviors, suspicious handling
- **Theft Prevention**: Unpaid item detection, security tag removal
- **Group Activity**: Coordinated suspicious behavior across cameras
- **Multi-Camera Correlation**: Tracking individuals across camera zones

### Alert Types
- **Confirmed Incidents Only**: Alerts sent only after Flash confirmation
- **Per-Source Alerts**: Individual camera incident detection
- **Video Evidence**: 10-second clips from long buffer
- **Dual-Model Validation**: Flash-Lite + Flash analysis included

## Performance Considerations

### Resource Usage
- **CPU**: Parallel processing with configurable thread limits
- **Memory**: Frame buffering with automatic cleanup
- **Network**: Efficient RTSP stream handling
- **Storage**: Temporary video files for evidence

### Optimization Tips
- **Analysis Interval**: Keep at 3 seconds (matches short buffer cycle)
- **API Performance**: Ensure api_proxy.py has sufficient resources
- **Network**: Stable connection between analyzer and API required
- **Buffer Duration**: 10 seconds provides good context for confirmation

## Troubleshooting

### Common Issues

#### No Active Sources
```bash
# Check source configuration
python run_multi_source_analysis.py list-sources

# Test individual source
python run_multi_source_analysis.py status
```

#### Analysis Not Starting
- Verify API proxy is running: `python api_proxy.py`
- Check Vigint API key is set: `export VIGINT_API_KEY=your_key`
- Ensure Gemini API key is set in api_proxy environment: `export GOOGLE_API_KEY=your_key`
- Check video source URLs are accessible

#### API Connection Errors
- Verify API URL is correct (default: http://localhost:5000)
- Check API key is valid
- Ensure network connectivity to API server
- Review api_proxy.py logs for errors

#### Email Alerts Not Working
- Verify email configuration in `config.ini`
- Check Flash confirmation is occurring (not just Flash-Lite detection)
- Review logs for "Flash vetoed" messages
- Test email functionality with `test_email.py`

### Debug Mode
```bash
# Enable debug logging
export VIGINT_LOG_LEVEL=DEBUG
python run_multi_source_analysis.py start
```

## Demo and Testing

### Run Demo
```bash
# Interactive demo with multiple options
python demo_multi_source_analysis.py

# Video files demo (requires buffer_video_*.mp4 files)
python demo_multi_source_analysis.py

# Configuration management demo
python demo_multi_source_analysis.py
```

### Test with Sample Videos
```bash
# Use existing buffer videos for testing
python run_multi_source_analysis.py quick-start \
  --sources buffer_video_1.mp4 buffer_video_2.mp4 buffer_video_3.mp4 buffer_video_4.mp4 buffer_video_5.mp4 buffer_video_6.mp4
```

## Integration

### With Existing Vigint System
- Compatible with existing RTSP server setup
- Uses same email alert system
- Integrates with current configuration management
- Maintains security and authentication patterns

### With External Systems
- REST API endpoints for status and control
- Webhook support for external notifications
- JSON configuration for easy integration
- Standard RTSP input support

## Future Enhancements

### Planned Features
- **Web Dashboard**: Real-time monitoring interface
- **Mobile Alerts**: Push notifications to mobile devices
- **Advanced Analytics**: Heat maps, traffic patterns, dwell time
- **Cloud Integration**: Cloud storage for video evidence
- **Machine Learning**: Custom model training for specific scenarios

### Extensibility
- Plugin architecture for custom analysis modules
- Custom alert channels (Slack, Teams, etc.)
- Integration with access control systems
- Support for additional video formats and protocols

## Support

For issues, questions, or feature requests:
1. Check the troubleshooting section above
2. Review log files for error details
3. Test with demo scripts to isolate issues
4. Verify configuration files are valid JSON

## License

This multi-source video analysis system is part of the Vigint security platform and follows the same licensing terms as the main project.