# Migration Guide: Unified API Server with Video Storage

## Overview

Your Vigint system now **combines** the API server and video storage into **one Render.com instance**. This eliminates the need for a separate `sparse-ai-video-server` deployment.

## Benefits

- ✅ **Save $7/month** - One service instead of two
- ✅ **Simpler deployment** - Single render.yaml
- ✅ **Shared authentication** - One API key for everything
- ✅ **Better performance** - No cross-service network calls
- ✅ **Easier maintenance** - Single codebase
- ✅ **Same database** - Unified data management

## What Changed

### Before (Two Separate Services)

```
┌──────────────────────────────┐
│ sparse-ai-video-server       │
│ • Video upload endpoint      │
│ • Video serving with tokens  │
│ • 10GB disk storage          │
└──────────────────────────────┘

┌──────────────────────────────┐
│ vigint-api-server            │
│ • Gemini AI processing       │
│ • Video compression          │
│ • Email alerts               │
│ • PostgreSQL database        │
└──────────────────────────────┘
```

### After (One Unified Service)

```
┌──────────────────────────────┐
│ vigint-api-server (unified)  │
│ • Gemini AI processing       │
│ • Video compression          │
│ • Email alerts               │
│ • PostgreSQL database        │
│ • Video upload endpoint      │  ← Added
│ • Video serving with tokens  │  ← Added
│ • 10GB disk storage          │  ← Added
└──────────────────────────────┘
```

## Migration Steps

### Option 1: Fresh Deployment (Recommended)

If you haven't deployed yet or can start fresh:

1. **Deploy the unified service:**
   ```bash
   cd /Users/david2/dev/Vigint
   git add .
   git commit -m "Unified API server with video storage"
   git push origin main
   ```

2. **Follow the updated [QUICK_START_RENDER.md](./QUICK_START_RENDER.md)**
   - Deploy using the updated `render.yaml`
   - Set environment variables (including `SPARSE_AI_API_KEY`)
   - Video storage is automatically included

3. **Update local config:**
   ```ini
   [API]
   api_server_url = https://vigint-api-server.onrender.com
   
   [SparseAI]
   base_url = https://vigint-api-server.onrender.com
   api_key = your-api-key
   ```

### Option 2: Migrate Existing Deployment

If you already have `sparse-ai-video-server` running:

#### Step 1: Deploy New Unified Service

1. **Go to Render Dashboard**
2. **Create new web service** from your Vigint repo
3. **Use updated `render.yaml`** (includes disk storage)
4. **Set environment variables:**
   ```
   SECRET_KEY=<your-key>
   SPARSE_AI_API_KEY=<same-as-old-sparse-ai-server>
   GOOGLE_API_KEY=<your-gemini-key>
   VIDEO_STORAGE_DIR=/opt/render/project/src/uploads
   # ... email config ...
   ```

5. **Note the new URL:** `https://vigint-api-server-new.onrender.com`

#### Step 2: Test New Service

```bash
# Test API endpoints
curl https://vigint-api-server-new.onrender.com/api/health

# Test video upload endpoint (Sparse AI compatible)
curl https://vigint-api-server-new.onrender.com/api/v1/videos/upload \
  -H "Authorization: Bearer your-api-key" \
  -F "video=@test.mp4" \
  -F "metadata={\"video_id\":\"test123\"}"
```

#### Step 3: Update Local Configuration

Edit `config.ini`:
```ini
[API]
# New unified service URL
api_server_url = https://vigint-api-server-new.onrender.com

[SparseAI]
# Same URL - video storage is integrated
base_url = https://vigint-api-server-new.onrender.com
api_key = your-api-key
```

#### Step 4: Verify Everything Works

```bash
python3 start_vigint.py --video-input test.mp4
```

Expected output:
```
✅ Using remote API server at: https://vigint-api-server-new.onrender.com
🎬 Video storage integrated with API server
```

#### Step 5: Migrate Old Videos (Optional)

If you have videos on the old `sparse-ai-video-server`:

```bash
# Download videos from old server
curl "https://sparse-ai-video-server.onrender.com/video/VIDEO_ID?token=TOKEN" \
  -o video.mp4

# Upload to new unified server
curl https://vigint-api-server-new.onrender.com/api/v1/videos/upload \
  -H "Authorization: Bearer your-api-key" \
  -F "video=@video.mp4" \
  -F "metadata={\"video_id\":\"VIDEO_ID\"}"
```

Or use automated script:
```python
import requests
import os

OLD_SERVER = "https://sparse-ai-video-server.onrender.com"
NEW_SERVER = "https://vigint-api-server-new.onrender.com"
API_KEY = "your-api-key"

# List of video IDs to migrate
video_ids = ["video1", "video2", "video3"]

for video_id in video_ids:
    # Download from old server
    old_url = f"{OLD_SERVER}/video/{video_id}?token=..."
    response = requests.get(old_url)
    
    if response.status_code == 200:
        # Upload to new server
        files = {'video': ('video.mp4', response.content)}
        metadata = {'metadata': f'{{"video_id": "{video_id}"}}'}
        
        upload_response = requests.post(
            f"{NEW_SERVER}/api/v1/videos/upload",
            headers={'Authorization': f'Bearer {API_KEY}'},
            files=files,
            data=metadata
        )
        
        print(f"Migrated {video_id}: {upload_response.json()}")
```

#### Step 6: Delete Old Service

Once everything works:

1. **Verify new service is working** for at least 24 hours
2. **Check no videos are being uploaded to old service**
3. **Go to Render Dashboard**
4. **Delete `sparse-ai-video-server` service**
5. **Save $7/month!**

## API Endpoints

The unified service provides **all endpoints** from both services:

### Video Storage Endpoints (from sparse-ai-video-server)

**Upload Video:**
```bash
POST /api/v1/videos/upload
Authorization: Bearer <api-key>

# Multipart form data:
# - video: file
# - metadata: JSON string with video_id
# - expiration_hours: optional (default 720 = 30 days)
```

**Serve Video:**
```bash
GET /video/<video_id>?token=<token>

# No authentication needed - validated by token
```

### API Server Endpoints (from api_proxy)

**All existing endpoints:**
- `POST /api/video/analyze` - AI analysis
- `POST /api/video/compress` - Video compression
- `POST /api/video/alert` - Security alerts
- `GET /api/health` - Health check
- `POST /api/storage/cleanup` - Storage management
- `GET /api/usage` - Usage statistics

## Environment Variables

### Required for Unified Service

```bash
# Core API
SECRET_KEY=<generate-with-openssl-rand-hex-32>
GOOGLE_API_KEY=<your-gemini-api-key>

# Video Storage (NEW)
SPARSE_AI_API_KEY=<same-as-secret-key-or-different>
VIDEO_STORAGE_DIR=/opt/render/project/src/uploads

# Database
DATABASE_URL=<auto-set-by-render>

# Email
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=<your-email>
EMAIL_PASSWORD=<app-password>
EMAIL_FROM=<from-address>
EMAIL_TO=<alert-recipient>

# System
RENDER=true
FLASK_ENV=production
PYTHON_VERSION=3.11.0
```

### API Key Compatibility

The service accepts **both** authentication methods:

1. **Bearer Token** (Sparse AI style):
   ```bash
   Authorization: Bearer <SPARSE_AI_API_KEY>
   ```

2. **X-API-Key Header** (Vigint style):
   ```bash
   X-API-Key: <SECRET_KEY>
   ```

**Recommendation:** Set `SPARSE_AI_API_KEY` to the same value as `SECRET_KEY` for simplicity.

## Configuration Updates

### Local config.ini

```ini
[API]
# Unified service URL
api_server_url = https://vigint-api-server.onrender.com
secret_key = your-secret-key

[SparseAI]
# Same URL - video storage integrated
base_url = https://vigint-api-server.onrender.com
api_key = your-secret-key
default_expiration_hours = 48
```

## Disk Storage

The unified service includes **10GB persistent disk storage** for videos:

```yaml
disk:
  name: video-storage
  mountPath: /opt/render/project/src/uploads
  sizeGB: 10
```

**Features:**
- ✅ Persistent across deployments
- ✅ Automatic backup (on paid plans)
- ✅ Can be expanded if needed
- ✅ Same disk used for temporary processing files

## Cost Comparison

### Before (Two Services)

| Service | Plan | Cost |
|---------|------|------|
| sparse-ai-video-server | Starter | $7/month |
| vigint-api-server | Starter | $7/month |
| **Total** | | **$14/month** |

### After (Unified Service)

| Service | Plan | Cost |
|---------|------|------|
| vigint-api-server (unified) | Starter | $7/month |
| **Total** | | **$7/month** |

**Savings: $7/month or $84/year**

## Compatibility

### Backward Compatible

The unified service is **100% backward compatible** with existing code:

✅ **Sparse AI upload endpoint** - Same endpoint path and format
✅ **Video serving** - Same URL structure with tokens
✅ **Token validation** - Same algorithm
✅ **API authentication** - Supports both methods

### No Code Changes Required

Your existing code will work without modifications:
- `gdpr_compliant_video_service.py` - Works as-is
- `video_link_service.py` - Works as-is
- `local_video_link_service.py` - Works as-is

**Only change:** Update `base_url` in config to point to unified service.

## Testing

### Test Video Upload

```bash
# Create test video
ffmpeg -f lavfi -i testsrc=duration=5:size=1280x720:rate=25 test.mp4

# Upload to unified service
curl https://vigint-api-server.onrender.com/api/v1/videos/upload \
  -H "Authorization: Bearer your-api-key" \
  -F "video=@test.mp4" \
  -F "metadata={\"video_id\":\"test_$(date +%s)\"}" \
  -F "expiration_hours=48"

# Response:
# {
#   "success": true,
#   "video_id": "test_1234567890",
#   "private_link": "https://vigint-api-server.onrender.com/video/test_1234567890?token=abc123...",
#   "expiration_time": "2025-10-04T12:00:00",
#   "message": "Video uploaded successfully"
# }
```

### Test Video Access

```bash
# Open the private link in browser or use curl
curl "https://vigint-api-server.onrender.com/video/test_1234567890?token=abc123..."
```

### Test Full System

```bash
cd /Users/david2/dev/Vigint

# Update config.ini with new URL
python3 start_vigint.py --video-input test.mp4

# Should see:
# ✅ Using remote API server at: https://vigint-api-server.onrender.com
# 🎬 Video storage integrated with API server
```

## Monitoring

### Video Storage Status

Check disk usage:
```bash
curl -H "X-API-Key: your-key" \
  https://vigint-api-server.onrender.com/api/storage/status
```

Response:
```json
{
  "disk_free_gb": 8.5,
  "disk_used_gb": 1.5,
  "disk_total_gb": 10.0,
  "temp_files_count": 12,
  "temp_files_size_mb": 245.3
}
```

### Cleanup Old Files

```bash
curl -X POST \
  -H "X-API-Key: your-key" \
  https://vigint-api-server.onrender.com/api/storage/cleanup \
  -d '{"max_age_hours": 720}'  # Clean files older than 30 days
```

## Troubleshooting

### "Video not found" after deployment

**Cause:** Videos stored on old `sparse-ai-video-server`

**Solution:** Videos must be migrated or re-uploaded. Old videos won't automatically transfer.

### "Invalid token" errors

**Cause:** Token generated with different API key

**Solution:** Ensure `SPARSE_AI_API_KEY` on Render matches the key used locally to generate tokens.

### "Disk full" errors

**Cause:** 10GB disk storage limit reached

**Solutions:**
1. Clean up old videos:
   ```bash
   curl -X POST -H "X-API-Key: key" \
     https://your-api.onrender.com/api/storage/cleanup \
     -d '{"max_age_hours": 168}'  # 7 days
   ```

2. Increase disk size in Render dashboard:
   - Go to service → Settings → Disk
   - Change from 10GB to 20GB, 50GB, etc.
   - Cost: ~$0.25/GB/month

### Different URLs showing in logs

**Expected:** You may see messages mentioning "sparse-ai-video-server"

**Normal:** Legacy code comments - functionality now uses `api_server_url`

## Summary

✅ **Integrated video storage** into API server
✅ **Same endpoints** as sparse-ai-video-server
✅ **Backward compatible** with existing code
✅ **50% cost savings** ($7 vs $14/month)
✅ **Simpler deployment** (one service vs two)
✅ **10GB persistent disk** storage included

## Next Steps

1. ✅ Deploy unified service following [QUICK_START_RENDER.md](./QUICK_START_RENDER.md)
2. ✅ Update `config.ini` with new unified URL
3. ✅ Test video upload and serving
4. ✅ Run full system test with `start_vigint.py`
5. ✅ (Optional) Migrate old videos
6. ✅ Delete old `sparse-ai-video-server` service
7. 💰 Save $84/year!

---

**Your Vigint system is now more efficient and cost-effective! 🎉**
