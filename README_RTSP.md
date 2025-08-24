# Vigint RTSP Server

This document describes the RTSP streaming functionality of the Vigint platform.

## Overview

The Vigint RTSP server provides real-time video streaming capabilities using the MediaMTX server. It supports multiple input sources and can stream to multiple clients simultaneously.

## Features

- **RTSP Streaming**: Real-time streaming protocol support
- **Multiple Sources**: Support for camera feeds, file playback, and live streams
- **Authentication**: Basic authentication for stream access
- **API Control**: RESTful API for stream management
- **Metrics**: Built-in metrics and monitoring
- **Recording**: Optional stream recording capabilities

## Quick Start

### Prerequisites

1. **MediaMTX Binary**: Download from [MediaMTX Releases](https://github.com/bluenviron/mediamtx/releases)
2. **Python 3.8+**: Required for the control scripts
3. **Configuration**: Copy and customize the configuration files

### Installation

1. **Download MediaMTX**:
   ```bash
   # Download the appropriate binary for your platform
   wget https://github.com/bluenviron/mediamtx/releases/latest/download/mediamtx_linux_amd64.tar.gz
   tar -xzf mediamtx_linux_amd64.tar.gz
   chmod +x mediamtx
   ```

2. **Setup Configuration**:
   ```bash
   # The mediamtx_simple.yml file is already configured
   # Customize it if needed for your specific requirements
   ```

3. **Start the Server**:
   ```bash
   # Using the control script
   ./start_rtsp_server start
   
   # Or using the Python wrapper
   ./run_vigint_rtsp.sh
   
   # Or directly
   ./mediamtx mediamtx_simple.yml
   ```

## Configuration

The RTSP server is configured via `mediamtx_simple.yml`. Key settings include:

### Basic Settings
```yaml
# Server addresses
rtspAddress: :8554        # RTSP port
apiAddress: 127.0.0.1:9997  # API port
metricsAddress: 127.0.0.1:9998  # Metrics port

# Authentication
publishUser: vigint
publishPass: vigint123
```

### Stream Paths
```yaml
paths:
  # Catch-all for any stream
  ~^.*$:
    source: publisher
  
  # Specific camera stream
  camera1:
    source: rtsp://admin:password@192.168.1.100:554/stream1
    sourceOnDemand: yes
  
  # File playback
  test:
    source: /path/to/video.mp4
    sourceOnDemand: yes
```

## Usage

### Streaming URLs

- **RTSP Base URL**: `rtsp://localhost:8554/`
- **Stream URL**: `rtsp://localhost:8554/stream_name`
- **API Base URL**: `http://localhost:9997/v1/`
- **Metrics URL**: `http://localhost:9998/metrics`

### Publishing a Stream

Using FFmpeg to publish a stream:
```bash
# From a camera
ffmpeg -f v4l2 -i /dev/video0 -c:v libx264 -preset ultrafast -f rtsp rtsp://vigint:vigint123@localhost:8554/camera1

# From a file
ffmpeg -re -i input.mp4 -c copy -f rtsp rtsp://vigint:vigint123@localhost:8554/test

# From another RTSP source
ffmpeg -i rtsp://source.example.com/stream -c copy -f rtsp rtsp://vigint:vigint123@localhost:8554/relay
```

### Viewing a Stream

Using VLC or other RTSP clients:
```bash
# VLC command line
vlc rtsp://localhost:8554/camera1

# FFplay
ffplay rtsp://localhost:8554/camera1

# GStreamer
gst-launch-1.0 rtspsrc location=rtsp://localhost:8554/camera1 ! decodebin ! autovideosink
```

## API Control

The MediaMTX API provides programmatic control over streams:

### List Active Streams
```bash
curl http://localhost:9997/v1/paths/list
```

### Get Stream Statistics
```bash
curl http://localhost:9997/v1/paths/get/camera1
```

### Add/Remove Streams
```bash
# Add a stream source
curl -X POST http://localhost:9997/v1/config/paths/patch/camera1 \
  -H "Content-Type: application/json" \
  -d '{"source": "rtsp://192.168.1.100:554/stream1"}'

# Remove a stream
curl -X DELETE http://localhost:9997/v1/config/paths/patch/camera1
```

## Control Scripts

### start_rtsp_server
Main control script for the RTSP server:

```bash
./start_rtsp_server start    # Start the server
./start_rtsp_server stop     # Stop the server
./start_rtsp_server restart  # Restart the server
./start_rtsp_server status   # Check status
./start_rtsp_server logs     # View logs
```

### run_vigint_rtsp.sh
Quick launcher that integrates with the Vigint application:

```bash
./run_vigint_rtsp.sh  # Start RTSP server with Vigint configuration
```

## Integration with Vigint API

The RTSP server integrates with the main Vigint API system:

### Authentication
- API keys are required for programmatic access
- Usage is tracked and billed through the billing system

### Monitoring
- Stream usage is logged for billing purposes
- Cost monitoring alerts for high usage

### Proxy Access
Access RTSP API through the main API proxy:
```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:5000/api/rtsp/paths/list
```

## Monitoring and Metrics

### Built-in Metrics
Access Prometheus-style metrics:
```bash
curl http://localhost:9998/metrics
```

### Log Files
- **MediaMTX Logs**: `mediamtx.log`
- **Application Logs**: `vigint.log`

### Health Checks
```bash
# Check if server is responding
curl http://localhost:9997/v1/config/global/get

# Check stream status
curl http://localhost:9997/v1/paths/list
```

## Recording

Enable recording in the configuration:
```yaml
pathDefaults:
  record: yes
  recordPath: ./recordings/%path/%Y-%m-%d_%H-%M-%S-%f.mp4
  recordFormat: mp4
  recordPartDuration: 1h
  recordDeleteAfter: 24h
```

## Troubleshooting

### Common Issues

1. **Server Won't Start**:
   - Check if MediaMTX binary is executable
   - Verify configuration file syntax
   - Check if ports are already in use

2. **Can't Connect to Stream**:
   - Verify stream is active: `curl http://localhost:9997/v1/paths/list`
   - Check authentication credentials
   - Ensure firewall allows RTSP traffic

3. **Poor Stream Quality**:
   - Adjust encoding settings in source
   - Check network bandwidth
   - Monitor CPU usage

### Debug Mode
Enable debug logging in `mediamtx_simple.yml`:
```yaml
logLevel: debug
```

### Port Conflicts
If default ports are in use, modify in configuration:
```yaml
rtspAddress: :8555        # Change RTSP port
apiAddress: :9998         # Change API port
metricsAddress: :9999     # Change metrics port
```

## Security Considerations

1. **Authentication**: Always use authentication in production
2. **Network Security**: Consider VPN or firewall rules
3. **HTTPS**: Use HTTPS for API access in production
4. **Access Control**: Limit API access to authorized clients

## Performance Tuning

### For High Load
```yaml
# Increase connection limits
rtspReadTimeout: 10s
rtspWriteTimeout: 10s

# Optimize recording
recordPartDuration: 30m
recordSegmentDuration: 10m
```

### For Low Latency
```yaml
# Reduce buffering
rtspReadBufferCount: 512
```

## Support

For issues and questions:
- Check the logs: `./start_rtsp_server logs`
- Review MediaMTX documentation: https://github.com/bluenviron/mediamtx
- Contact Vigint support: support@vigint.com