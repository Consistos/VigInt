# Multi-Source Parallel Video Analysis

## Overview

Vigint now supports **parallel analysis of multiple video sources simultaneously**. This feature enables you to monitor multiple cameras or video feeds at once, with intelligent aggregation and parallel processing.

## Features

- ✅ **Parallel Processing**: All video sources are analyzed concurrently
- ✅ **Smart Aggregation**: Groups of 4+ sources are analyzed together for coordinated incident detection
- ✅ **Individual Analysis**: Fewer than 4 sources are analyzed individually
- ✅ **Real Gemini AI**: Uses real AI analysis with automatic fallback
- ✅ **Incident Deduplication**: Prevents duplicate alerts across sources
- ✅ **GDPR Compliance**: Automatic video cleanup and secure storage
- ✅ **Configuration-Based**: Easy to manage sources via JSON config

## Quick Start

### 1. Configure Your Video Sources

Edit `multi_source_config.json` to define your video sources:

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
    "camera_1": {
      "source_id": "camera_1",
      "rtsp_url": "path/to/video1.mp4",
      "name": "Front Entrance",
      "enabled": true,
      "analysis_enabled": true,
      "alert_enabled": true
    },
    "camera_2": {
      "source_id": "camera_2",
      "rtsp_url": "path/to/video2.mp4",
      "name": "Back Entrance",
      "enabled": true,
      "analysis_enabled": true,
      "alert_enabled": true
    }
  }
}
```

### 2. Start Multi-Source Analysis

```bash
# Use the default config file (multi_source_config.json)
python3 start_vigint.py --multi-source

# Or specify a custom config file
python3 start_vigint.py --multi-source --config-file my_cameras.json

# Run with full stack (API + RTSP + Multi-Source)
python3 start_vigint.py --mode full --multi-source
```

## Configuration Guide

### Video Source Configuration

Each video source supports the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_id` | string | Yes | Unique identifier for the source |
| `rtsp_url` | string | Yes | Path to video file or RTSP stream URL |
| `name` | string | No | Human-readable name (default: Camera_{id}) |
| `enabled` | boolean | No | Enable/disable this source (default: true) |
| `location` | string | No | Physical location description |
| `description` | string | No | Additional notes about the source |
| `priority` | string | No | Priority level: low, normal, high |
| `analysis_enabled` | boolean | No | Enable AI analysis (default: true) |
| `alert_enabled` | boolean | No | Enable incident alerts (default: true) |
| `recording_enabled` | boolean | No | Enable continuous recording (default: false) |
| `tags` | array | No | Custom tags for organizing sources |

### Analysis Settings

Configure global analysis behavior:

```json
{
  "analysis_settings": {
    "analysis_interval": 10,        // Seconds between analyses
    "aggregation_threshold": 4,     // Min sources for aggregated analysis
    "max_concurrent_analyses": 4,   // Max parallel analysis threads
    "frame_buffer_duration": 10     // Buffer duration in seconds
  }
}
```

## How It Works

### Analysis Modes

**Individual Analysis** (< 4 sources):
- Each source is analyzed independently
- Full frame resolution for each camera
- Separate alerts for each source

**Aggregated Analysis** (≥ 4 sources):
- Sources grouped into sets of 4
- Composite view created (2x2 grid)
- Can detect coordinated activities across cameras
- More cost-efficient for large deployments

### Parallel Processing

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Camera 1   │    │  Camera 2   │    │  Camera 3   │    │  Camera 4   │
│   Capture   │    │   Capture   │    │   Capture   │    │   Capture   │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │                  │
       └──────────────────┴──────────────────┴──────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Frame Buffers    │
                    │  (Continuous)     │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Parallel         │
                    │  AI Analysis      │
                    │  (ThreadPool)     │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Incident         │
                    │  Detection        │
                    │  & Alerts         │
                    └───────────────────┘
```

## Command-Line Options

```bash
# Basic multi-source analysis
python3 start_vigint.py --multi-source

# Custom config file
python3 start_vigint.py --multi-source --config-file cameras.json

# Full mode with API server
python3 start_vigint.py --mode full --multi-source

# RTSP-only mode with multi-source
python3 start_vigint.py --mode rtsp --multi-source

# Combined with other options
python3 start_vigint.py --multi-source --no-rtsp
```

## Managing Video Sources

### Using Python

```python
from multi_source_config import MultiSourceConfig

# Load configuration
config = MultiSourceConfig('multi_source_config.json')

# Add a new source
config.add_video_source(
    source_id='camera_5',
    rtsp_url='rtsp://192.168.1.100:554/stream',
    name='Loading Dock',
    location='Warehouse',
    priority='high',
    tags=['outdoor', 'critical']
)

# Update a source
config.update_video_source('camera_5', enabled=False)

# Remove a source
config.remove_video_source('camera_5')

# List all enabled sources
sources = config.list_video_sources(enabled_only=True)
for source_id, source in sources.items():
    print(f"{source_id}: {source['name']}")
```

### Using the Config File

Simply edit `multi_source_config.json` directly and restart the analysis.

## Video Output

All video evidence is automatically saved to:
```
mock_sparse_ai_cloud/
├── incident_20250101_120000_camera_1.mp4
├── incident_20250101_120030_camera_2.mp4
└── ...
```

Videos include:
- 8 seconds of buffered footage (before incident)
- Smooth 25 FPS playback
- High-quality encoding
- GDPR-compliant automatic cleanup

## Monitoring

The system provides real-time logging:

```
🚀 Starting MULTI-SOURCE video analysis
✅ Loaded 5 enabled video source(s)
   📹 camera_1: Front Entrance -> video1.mp4
   📹 camera_2: Back Entrance -> video2.mp4
   📹 camera_3: Sales Floor -> video3.mp4
   📹 camera_4: Storage Room -> video4.mp4
   📹 camera_5: Loading Dock -> video5.mp4
⚙️  Analysis interval: 10s
🚀 Starting parallel analysis of all sources...
✅ Multi-source analysis running
🔍 All sources are being analyzed in parallel
🚨 Incidents will trigger automated alerts
```

## Performance Considerations

### Optimal Settings

| Scenario | Sources | Interval | Workers | Memory |
|----------|---------|----------|---------|--------|
| Small (1-3) | 1-3 | 10s | 2 | 2GB |
| Medium (4-8) | 4-8 | 10s | 4 | 4GB |
| Large (9-16) | 9-16 | 15s | 4 | 6GB |
| Extra Large (17+) | 17+ | 20s | 4 | 8GB |

### Resource Usage

- **CPU**: ~10-20% per active source
- **Memory**: ~500MB per source (buffer + processing)
- **Network**: Depends on video resolution and bitrate
- **Disk**: Videos are auto-cleaned after retention period

## Troubleshooting

### No sources detected
```
❌ No enabled video sources found in configuration
💡 Edit multi_source_config.json to add video sources
```
→ Check that `enabled: true` in your config

### Config file not found
```
❌ Configuration file not found: multi_source_config.json
💡 Create a configuration file or use --config-file
```
→ Create the config file or specify correct path

### Video not loading
- Verify the video file path is correct
- Check file permissions
- Ensure video format is supported (MP4, AVI, MOV, etc.)
- For RTSP streams, verify network connectivity

### High CPU usage
- Reduce `max_concurrent_analyses` in settings
- Increase `analysis_interval` (analyze less frequently)
- Reduce number of enabled sources

## Comparison: Single vs Multi-Source

### Single Source Mode
```bash
python3 start_vigint.py --video-input video.mp4
```
- ✅ Simple setup
- ✅ Lower resource usage
- ❌ One camera only
- ❌ No cross-camera correlation

### Multi-Source Mode
```bash
python3 start_vigint.py --multi-source
```
- ✅ Multiple cameras simultaneously
- ✅ Coordinated incident detection
- ✅ Aggregated analysis (cost-efficient)
- ✅ Scalable architecture
- ❌ Higher resource usage
- ❌ Requires configuration file

## Examples

### Example 1: Retail Store (4 cameras)

```json
{
  "video_sources": {
    "entrance": {
      "source_id": "entrance",
      "rtsp_url": "rtsp://10.0.1.10/entrance",
      "name": "Main Entrance",
      "location": "Front",
      "priority": "high",
      "enabled": true
    },
    "checkout": {
      "source_id": "checkout",
      "rtsp_url": "rtsp://10.0.1.11/checkout",
      "name": "Checkout Area",
      "location": "Center",
      "priority": "high",
      "enabled": true
    },
    "aisle_1": {
      "source_id": "aisle_1",
      "rtsp_url": "rtsp://10.0.1.12/aisle1",
      "name": "Electronics Aisle",
      "location": "East",
      "priority": "high",
      "enabled": true
    },
    "stockroom": {
      "source_id": "stockroom",
      "rtsp_url": "rtsp://10.0.1.13/stock",
      "name": "Stock Room",
      "location": "Back",
      "priority": "normal",
      "enabled": true
    }
  }
}
```

### Example 2: Warehouse (8 cameras)

For larger deployments, sources are automatically grouped for aggregated analysis, making it more efficient and cost-effective.

## Best Practices

1. **Start Small**: Begin with 2-3 cameras and scale up
2. **Test Configuration**: Verify each source works individually first
3. **Monitor Resources**: Watch CPU/memory usage as you add sources
4. **Tune Intervals**: Adjust analysis_interval based on your needs
5. **Use Priorities**: Mark critical cameras as "high" priority
6. **Tag Sources**: Use tags to organize cameras by location/function
7. **Regular Cleanup**: Monitor the video storage directory size
8. **Network Stability**: Ensure stable network for RTSP streams

## Integration with Existing Features

Multi-source analysis works seamlessly with:
- ✅ Email alerts (send_security_alert_with_video)
- ✅ API endpoints (all incident APIs)
- ✅ Video link service (GDPR-compliant)
- ✅ Token counting and billing
- ✅ Client isolation (multi-tenant)
- ✅ Automatic cleanup
- ✅ Invoice generation

## Next Steps

1. Configure your video sources in `multi_source_config.json`
2. Start the system with `--multi-source` flag
3. Monitor logs for successful source initialization
4. Wait for incident detection and alerts
5. Check `mock_sparse_ai_cloud/` for video evidence

## Support

For issues or questions:
- Check logs for detailed error messages
- Verify configuration file syntax (valid JSON)
- Test sources individually first
- Review system resources (CPU, memory, disk)
