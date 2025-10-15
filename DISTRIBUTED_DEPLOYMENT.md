# Distributed Deployment Guide

This guide explains how to run Vigint components on separate machines for distributed deployment.

## Current Architecture

The system currently uses a **monolithic architecture**:
- `start_vigint.py` imports and runs `api_proxy.py` in the same Python process
- Modules directly import functions from `api_proxy.py` (e.g., `from api_proxy import compress_video_for_email`)
- All communication happens via Python imports (no HTTP)

## Distributed Architecture

To run components on separate machines:

```
┌─────────────────────┐         HTTP          ┌─────────────────────┐
│  Machine 1          │ ──────────────────►   │  Machine 2          │
│  start_vigint.py    │                        │  api_proxy.py       │
│  - RTSP Server      │                        │  - Gemini AI        │
│  - Video Analyzer   │                        │  - API Endpoints    │
│  - Video Processing │                        │  - Database         │
└─────────────────────┘                        └─────────────────────┘
```

## Setup Instructions

### Step 1: Configure API Server URL

On **Machine 1** (where `start_vigint.py` runs), edit `config.ini`:

```ini
[API]
# Point to the remote API server
api_server_url = http://192.168.1.100:5002

# Or use a domain name
# api_server_url = https://api.yourdomain.com
```

**Note**: The `api_server_url` should point to the machine running `api_proxy.py`.

### Step 2: Start API Server (Machine 2)

On **Machine 2**, run the API proxy server:

```bash
python3 api_proxy.py
```

Or use a production WSGI server:

```bash
# Using gunicorn
gunicorn -w 4 -b 0.0.0.0:5002 api_proxy:app

# Using waitress
waitress-serve --host=0.0.0.0 --port=5002 api_proxy:app
```

### Step 3: Start Video Analysis (Machine 1)

On **Machine 1**, start Vigint:

```bash
python3 start_vigint.py --video-input /path/to/video.mp4
```

The system will detect the `api_server_url` configuration and skip starting the local API proxy.

## ⚠️ Current Limitation - Direct Imports

**IMPORTANT**: The current codebase still uses direct Python imports in many places. For true distributed deployment, these need to be converted to HTTP API calls.

### Files That Need Conversion

The following modules directly import from `api_proxy.py` and need to be refactored:

1. **video_analyzer.py** - Needs HTTP client for AI analysis
2. **alerts.py** - Needs HTTP client for alert creation
3. **gdpr_compliant_video_service.py** - Imports `create_video_from_frames`
4. **debug_compression.py** - Imports `compress_video_for_email`

### Conversion Example

**Before (Direct Import):**
```python
from api_proxy import compress_video_for_email

result = compress_video_for_email(video_path, max_size_mb)
```

**After (HTTP Client):**
```python
import requests
from config import config

def compress_video_for_email(video_path, max_size_mb):
    api_url = config.api_server_url or "http://localhost:5002"
    
    with open(video_path, 'rb') as f:
        files = {'video': f}
        data = {'max_size_mb': max_size_mb}
        response = requests.post(
            f"{api_url}/api/compress_video",
            files=files,
            data=data
        )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Compression failed: {response.text}")
```

## Recommended Implementation Plan

To fully enable distributed deployment:

### Phase 1: Create API Client Module

Create a new `api_client.py` module that wraps all API proxy functions:

```python
# api_client.py
import requests
from config import config

class APIClient:
    def __init__(self):
        self.base_url = config.api_server_url or "http://localhost:5002"
    
    def compress_video(self, video_path, max_size_mb):
        """Compress video via API"""
        # HTTP implementation
        pass
    
    def analyze_frame(self, frame_data):
        """Analyze frame via API"""
        # HTTP implementation
        pass
    
    def create_alert(self, alert_data):
        """Create alert via API"""
        # HTTP implementation
        pass
```

### Phase 2: Add API Endpoints to api_proxy.py

Add RESTful endpoints for all functions currently imported directly:

```python
@app.route('/api/compress_video', methods=['POST'])
@require_api_key
def api_compress_video():
    """Compress video endpoint"""
    # Implementation
    pass

@app.route('/api/analyze_frame', methods=['POST'])
@require_api_key
def api_analyze_frame():
    """Analyze frame endpoint"""
    # Implementation
    pass
```

### Phase 3: Update All Import Sites

Replace all direct imports with API client calls:

```python
# Old
from api_proxy import compress_video_for_email

# New
from api_client import APIClient
api_client = APIClient()
result = api_client.compress_video(video_path, max_size_mb)
```

## Networking Requirements

### Firewall Configuration

Ensure Machine 2 (API server) allows incoming connections:

```bash
# For Linux with ufw
sudo ufw allow 5002/tcp

# For Linux with iptables
sudo iptables -A INPUT -p tcp --dport 5002 -j ACCEPT
```

### Security Considerations

1. **Use HTTPS in production** - Don't expose API over plain HTTP
2. **API Key Authentication** - Ensure API keys are configured on both machines
3. **Network Isolation** - Consider VPN or private network for inter-machine communication
4. **Firewall Rules** - Only allow Machine 1 to access Machine 2's API port

### Environment Variables

On **Machine 1**, you can also use environment variables:

```bash
export VIGINT_CONFIG_PATH=/path/to/config.ini
export API_SERVER_URL=http://192.168.1.100:5002
```

## Testing Distributed Setup

### 1. Test API Server Accessibility

From Machine 1:

```bash
# Test basic connectivity
curl http://192.168.1.100:5002/health

# Test with API key
curl -H "X-API-Key: your-api-key" http://192.168.1.100:5002/api/status
```

### 2. Monitor Logs

**Machine 2 (API Server):**
```bash
tail -f vigint.log
```

**Machine 1 (Video Analysis):**
```bash
python3 start_vigint.py --video-input test.mp4
# Should log: "Using remote API server at: http://192.168.1.100:5002"
```

## Performance Considerations

### Network Latency

- Video frames sent over network will add latency
- Consider reducing frame analysis frequency for remote deployments
- Use video compression before sending over network

### Bandwidth Requirements

Approximate bandwidth for 1920x1080 frames at 25 FPS:

- Uncompressed: ~150 MB/s
- JPEG compressed (quality 85): ~5-10 MB/s
- H.264 stream: ~2-8 MB/s

**Recommendation**: Stream H.264 video instead of individual frames for remote analysis.

## Troubleshooting

### "Connection refused" errors

- Check if API server is running on Machine 2
- Verify firewall rules allow port 5002
- Test with: `telnet 192.168.1.100 5002`

### "Import errors" in distributed mode

- This means the code is still using direct imports
- Implement the API client conversion (Phase 1-3 above)

### Slow performance

- Check network latency: `ping 192.168.1.100`
- Monitor bandwidth usage
- Consider running components on same machine or faster network

## Summary

✅ **What's Implemented:**
- Configuration option for remote API server URL
- `start_vigint.py` detects and skips local API startup when remote URL is configured
- Documentation for distributed deployment

⚠️ **What Still Needs Work:**
- Convert direct imports to HTTP API calls
- Create API client wrapper module
- Add corresponding API endpoints to `api_proxy.py`
- Implement authentication and security for distributed setup

For now, you can use the configuration to **prepare** for distributed deployment, but full functionality requires the Phase 1-3 implementation described above.
