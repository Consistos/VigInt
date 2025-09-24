# Multi-Source Video Analysis System

The Multi-Source Video Analysis System allows simultaneous analysis of multiple video sources with intelligent aggregation for groups of 4 or more cameras.

## Features

### 🎯 Core Functionality
- **Simultaneous Analysis**: Process multiple video sources concurrently
- **Intelligent Aggregation**: Automatically group 4+ sources for combined analysis
- **Individual Processing**: Sources not in groups of 4 are analyzed individually
- **Real-time Monitoring**: Continuous monitoring with configurable intervals
- **Security Incident Detection**: AI-powered detection with French language alerts

### 📊 Aggregation Logic
- **4+ Sources**: Groups of exactly 4 sources are aggregated into composite frames
- **Remainder Sources**: Sources that don't form complete groups of 4 remain individual
- **Example**: 
  - 6 sources → 1 group of 4 + 2 individual sources
  - 9 sources → 2 groups of 4 + 1 individual source
  - 3 sources → 3 individual sources

### 🔧 Configuration Management
- **JSON-based Configuration**: Persistent storage of source configurations
- **Dynamic Source Management**: Add/remove sources without restart
- **Priority Levels**: Set source priorities (low, normal, high)
- **Location Tracking**: Organize sources by physical location
- **Analysis Settings**: Configurable intervals and thresholds

## Quick Start

### 1. Basic Usage with Video Files

```bash
# Quick start with existing video files
python run_multi_source_analysis.py quick-start \
  --sources buffer_video_1.mp4 buffer_video_2.mp4 buffer_video_3.mp4 buffer_video_4.mp4 \
  --names "Front Door" "Sales Floor" "Checkout" "Storage"
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
from multi_source_config import MultiSourceConfig

# Create analyzer
analyzer = MultiSourceVideoAnalyzer()

# Add video sources
analyzer.add_video_source("cam1", "rtsp://192.168.1.100:554/stream1", "Front Door")
analyzer.add_video_source("cam2", "rtsp://192.168.1.101:554/stream1", "Sales Floor")
analyzer.add_video_source("cam3", "rtsp://192.168.1.102:554/stream1", "Checkout")
analyzer.add_video_source("cam4", "rtsp://192.168.1.103:554/stream1", "Storage")

# Start analysis
analyzer.start_analysis()

# Monitor status
status = analyzer.get_status()
print(f"Active sources: {status['active_sources']}/{status['total_sources']}")

# Stop analysis
analyzer.stop_analysis()
```

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
- Frame buffering for video evidence creation
- Health monitoring and reconnection

### 2. Aggregation Logic
- Sources are grouped automatically based on threshold (default: 4)
- Groups of exactly 4 sources create composite frames
- Composite frames show 2x2 grid with camera labels
- Remainder sources are analyzed individually

### 3. AI Analysis
- Uses Google Gemini AI for incident detection
- Specialized prompts for retail security scenarios
- French language responses for alerts
- Confidence scoring and incident classification

### 4. Alert System
- Automatic email alerts with video evidence
- Multi-camera incident correlation
- Video compilation from multiple sources
- Detailed incident reports in French

## Security Features

### Incident Detection
- **Shoplifting Detection**: Concealment behaviors, suspicious handling
- **Theft Prevention**: Unpaid item detection, security tag removal
- **Group Activity**: Coordinated suspicious behavior across cameras
- **Multi-Camera Correlation**: Tracking individuals across camera zones

### Alert Types
- **Individual Camera Alerts**: Single source incident detection
- **Aggregated Group Alerts**: Multi-camera coordinated incidents
- **High Priority Alerts**: Immediate notification for critical events
- **Video Evidence**: Automatic compilation of relevant footage

## Performance Considerations

### Resource Usage
- **CPU**: Parallel processing with configurable thread limits
- **Memory**: Frame buffering with automatic cleanup
- **Network**: Efficient RTSP stream handling
- **Storage**: Temporary video files for evidence

### Optimization Tips
- Adjust `analysis_interval` based on security requirements
- Use `aggregation_threshold` to balance detail vs. overview
- Set `max_concurrent_analyses` based on system capabilities
- Configure `frame_buffer_duration` for evidence needs

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
- Verify Gemini API key is set: `export GOOGLE_API_KEY=your_key`
- Check video source URLs are accessible
- Ensure sufficient system resources

#### Email Alerts Not Working
- Verify email configuration in `config.ini`
- Check SMTP credentials and server settings
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