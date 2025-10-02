# Distributed Deployment Implementation Summary

## Overview

Vigint now supports **distributed deployment** where the API server (`api_proxy.py`) runs on a separate machine (e.g., Render.com) while video analysis (`start_vigint.py`) runs locally. This enables:

- ✅ Cloud-based AI processing (Gemini API)
- ✅ Centralized database management
- ✅ Scalable API infrastructure
- ✅ Reduced local resource requirements
- ✅ Professional production deployment

## What Was Implemented

### 1. Configuration Support
**File:** `config.py`
- Added `api_server_url` property to specify remote API server
- Supports environment variables and config file

**Files:** `config.ini.example`
- Added documentation and example for `api_server_url`

### 2. API Client Module
**File:** `api_client.py` (NEW)
- HTTP client wrapper for all api_proxy functions
- Compatible interface with direct imports
- Automatic failover between local/remote
- Functions implemented:
  - `compress_video_for_email()`
  - `create_video_from_frames()`
  - `analyze_frame()`
  - `add_frame_to_buffer()`
  - `send_security_alert()`
  - `get_storage_status()`
  - `cleanup_storage()`
  - `get_usage_stats()`

### 3. API Endpoints
**File:** `api_proxy.py` (UPDATED)
- Added REST API endpoints:
  - `POST /api/video/compress` - Compress video files
  - `POST /api/video/create` - Create video from frames
  - `GET /api/video/download/<id>` - Download generated videos
- All endpoints use API key authentication
- Automatic cleanup of temporary files

### 4. Module Updates
**Files Updated:**
- `start_vigint.py` - Detects remote API server and skips local startup
- `gdpr_compliant_video_service.py` - Uses api_client when api_server_url configured
- `debug_compression.py` - Supports both local and remote modes

### 5. Render.com Deployment Files
**Files Created:**
- `render.yaml` - Infrastructure as Code for Render.com
- `requirements-api-server.txt` - Minimal dependencies for API server
- `RENDER_DEPLOYMENT.md` - Comprehensive deployment guide
- `QUICK_START_RENDER.md` - 15-minute quick start guide

## Architecture

### Before (Monolithic)
```
┌─────────────────────────────────────┐
│  Single Machine                     │
│  • start_vigint.py                  │
│  • api_proxy.py (imported)          │
│  • RTSP Server                      │
│  • Video Analysis                   │
│  • Gemini AI                        │
│  • Database                         │
└─────────────────────────────────────┘
```

### After (Distributed)
```
┌─────────────────────┐         HTTPS          ┌─────────────────────┐
│  Local Machine      │ ──────────────────►    │  Render.com         │
│  start_vigint.py    │                         │  api_proxy.py       │
│  • RTSP Server      │    API Client           │  • Gemini AI        │
│  • Video Analyzer   │    (HTTP/JSON)          │  • Video Processing │
│  • Frame Buffer     │                         │  • Email Alerts     │
└─────────────────────┘                         │  • PostgreSQL DB    │
                                                 └─────────────────────┘
```

## How to Deploy

### Quick Start (15-20 minutes)

1. **Push code to GitHub:**
   ```bash
   git add .
   git commit -m "Add distributed deployment"
   git push origin main
   ```

2. **Deploy to Render.com:**
   - Go to https://dashboard.render.com
   - New → Blueprint
   - Connect GitHub repo
   - Apply (uses `render.yaml`)

3. **Configure environment variables:**
   - `SECRET_KEY` - API authentication
   - `GOOGLE_API_KEY` - Gemini API
   - Email SMTP settings

4. **Update local config:**
   ```ini
   [API]
   api_server_url = https://vigint-api-server.onrender.com
   secret_key = your-secret-key
   ```

5. **Run distributed system:**
   ```bash
   python3 start_vigint.py --video-input video.mp4
   ```

**See [QUICK_START_RENDER.md](./QUICK_START_RENDER.md) for detailed steps.**

## Configuration

### Local Machine (where start_vigint.py runs)

**config.ini:**
```ini
[API]
# Remote API server URL (Render.com)
api_server_url = https://vigint-api-server.onrender.com

# API authentication key (must match Render)
secret_key = your-secret-key-here

# Local server config (not used when api_server_url is set)
host = 0.0.0.0
port = 5000
```

### Remote Server (Render.com)

**Environment Variables:**
- `SECRET_KEY` - API key for authentication
- `GOOGLE_API_KEY` - Google Gemini API key
- `DATABASE_URL` - PostgreSQL connection (auto-set by Render)
- `EMAIL_SMTP_SERVER` - SMTP server for alerts
- `EMAIL_SMTP_PORT` - SMTP port (587)
- `EMAIL_USERNAME` - Email username
- `EMAIL_PASSWORD` - Email app password
- `EMAIL_FROM` - From address
- `EMAIL_TO` - Alert recipient

## Behavior

### With api_server_url Set (Distributed Mode)

```bash
$ python3 start_vigint.py --video-input video.mp4

✅ Using remote API server at: https://vigint-api-server.onrender.com
📡 Distributed deployment mode - API proxy will not start locally
🚀 Starting RTSP server...
🎬 Starting video analysis...
```

- `api_proxy.py` does NOT start locally
- All API calls go to remote server via HTTP
- Video analysis runs locally
- AI processing happens remotely

### Without api_server_url (Local Mode)

```bash
$ python3 start_vigint.py --video-input video.mp4

Importing API proxy for local deployment...
Starting API server...
 * Running on http://0.0.0.0:5002
🚀 Starting RTSP server...
🎬 Starting video analysis...
```

- Everything runs on single machine
- Direct Python imports (no HTTP)
- Original monolithic behavior

## API Endpoints

All endpoints require `X-API-Key` header for authentication.

### Video Processing

**Compress Video:**
```bash
POST /api/video/compress
Content-Type: application/json
X-API-Key: your-api-key

{
  "video_data": "base64-encoded-video",
  "filename": "video.mp4",
  "max_size_mb": 20,
  "quality_reduction": 0.85
}
```

**Create Video from Frames:**
```bash
POST /api/video/create
Content-Type: application/json
X-API-Key: your-api-key

{
  "frames": ["base64-frame1", "base64-frame2", ...],
  "output_filename": "output.mp4",
  "fps": 25,
  "video_format": "mp4"
}
```

**Download Video:**
```bash
GET /api/video/download/{download_id}
X-API-Key: your-api-key
```

### Analysis & Alerts

**Analyze Frame:**
```bash
POST /api/video/analyze
Content-Type: application/json
X-API-Key: your-api-key

{
  "frame": "base64-encoded-frame",
  "frame_count": 42,
  "buffer_type": "short"
}
```

**Send Security Alert:**
```bash
POST /api/video/alert
Content-Type: application/json
X-API-Key: your-api-key

{
  "analysis": "Security incident detected",
  "risk_level": "HIGH",
  "video_data": "base64-encoded-video",
  "client_id": "camera-1"
}
```

### System Management

**Health Check:**
```bash
GET /api/health
# No authentication required

Response: {"status": "healthy", "timestamp": "..."}
```

**Storage Status:**
```bash
GET /api/storage/status
X-API-Key: your-api-key
```

**Cleanup Storage:**
```bash
POST /api/storage/cleanup
X-API-Key: your-api-key

{
  "max_age_hours": 24
}
```

**Usage Statistics:**
```bash
GET /api/usage
X-API-Key: your-api-key
```

## Files Created/Modified

### New Files
- ✅ `api_client.py` - HTTP client wrapper
- ✅ `requirements-api-server.txt` - Server dependencies
- ✅ `render.yaml` - Render.com configuration
- ✅ `RENDER_DEPLOYMENT.md` - Full deployment guide
- ✅ `QUICK_START_RENDER.md` - Quick start guide
- ✅ `DISTRIBUTED_DEPLOYMENT_SUMMARY.md` - This file

### Modified Files
- ✅ `config.py` - Added `api_server_url` property
- ✅ `config.ini.example` - Added `api_server_url` documentation
- ✅ `api_proxy.py` - Added REST API endpoints
- ✅ `start_vigint.py` - Detect and skip local API when remote configured
- ✅ `gdpr_compliant_video_service.py` - Use api_client when configured
- ✅ `debug_compression.py` - Support both local/remote modes

## Testing

### Test API Client
```bash
python3 -c "from api_client import APIClient; client = APIClient(); print(client.health_check())"
```

### Test Compression
```bash
python3 debug_compression.py
```

### Test Full System
```bash
python3 start_vigint.py --video-input test_video.mp4
```

## Cost Estimates

### Free Option (with limitations)
- **Render Web Service:** Free tier (spins down after 15min idle)
- **PostgreSQL:** Free (1GB storage, 5 connections)
- **Total:** $0/month

### Recommended Production
- **Render Web Service:** Starter ($7/month) - no spin-down
- **PostgreSQL:** Free or Starter ($7/month)
- **Total:** $7-14/month

### High Performance
- **Render Web Service:** Standard ($25/month)
- **PostgreSQL:** Standard ($7/month)
- **Redis Cache:** Standard ($10/month)
- **Total:** $42/month

## Monitoring

### Render Dashboard
- Real-time logs
- CPU/Memory metrics
- Request rates
- Error tracking
- Automatic health checks

### API Usage
```bash
curl -H "X-API-Key: your-key" \
  https://your-api.onrender.com/api/usage
```

### Storage Status
```bash
curl -H "X-API-Key: your-key" \
  https://your-api.onrender.com/api/storage/status
```

## Security

- ✅ HTTPS enforced (automatic via Render)
- ✅ API key authentication on all endpoints
- ✅ Environment variables for secrets
- ✅ Automatic certificate management
- ✅ PostgreSQL internal networking
- ✅ Temporary file cleanup

## Troubleshooting

### Connection Issues
```bash
# Test API server
curl https://your-api.onrender.com/api/health

# Check logs in Render dashboard
# Verify api_server_url in config.ini
```

### Database Issues
- Wait 1-2 minutes after creation
- Restart service in Render
- Verify DATABASE_URL environment variable

### Email Issues
- Use Gmail app password (not regular password)
- Enable 2FA and create app password
- Check SMTP logs in Render

## Next Steps

1. ✅ **Deploy to Render.com** - Follow [QUICK_START_RENDER.md](./QUICK_START_RENDER.md)
2. 📊 **Monitor Performance** - Check Render dashboard metrics
3. 🔒 **Add Custom Domain** - Optional for production
4. 📈 **Scale as Needed** - Upgrade plan if required
5. 🔄 **Enable Auto-Deploy** - Deploy on git push

## Documentation

- **Quick Start:** [QUICK_START_RENDER.md](./QUICK_START_RENDER.md) - 15-minute guide
- **Full Guide:** [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md) - Comprehensive documentation
- **Architecture:** [DISTRIBUTED_DEPLOYMENT.md](./DISTRIBUTED_DEPLOYMENT.md) - Design details

## Support

- **Render Documentation:** https://render.com/docs
- **Render Status:** https://status.render.com
- **Render Community:** https://community.render.com

---

**Implementation Complete! 🎉**

Your Vigint system now supports distributed deployment with the API server on Render.com while video analysis runs locally.
