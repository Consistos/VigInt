# Sparse AI Video Server Setup Guide

This guide shows how to configure Vigint to use the sparse-ai.com video server for email alerts.

## Overview

Videos from security incidents are now uploaded to **sparse-ai.com** instead of being stored locally or attached to emails. This provides:

- ✅ **GDPR Compliance**: Videos automatically expire and are deleted
- ✅ **Better Email Delivery**: Links instead of large attachments
- ✅ **Secure Access**: Token-based authentication
- ✅ **Professional URLs**: `https://sparse-ai.com/video/xxx` instead of `file://` or `localhost`

## Prerequisites

1. **Deploy the video server** to Render.com following `~/dev/Vigint-private/DEPLOYMENT.md`
2. **Get your API key** from the deployment process
3. **Configure your custom domain** (sparse-ai.com) in Render

## Configuration

### Option 1: Environment Variables (Recommended)

Add these to your `.env` file:

```bash
# Sparse AI Video Server Configuration
# IMPORTANT: Use the actual deployed URL from Render.com
# If using Render.com deployment: https://sparse-ai-video-server.onrender.com
# If using custom domain: https://sparse-ai.com
SPARSE_AI_BASE_URL=https://sparse-ai-video-server.onrender.com
SPARSE_AI_API_KEY=your-api-key-from-render-deployment
VIDEO_LINK_EXPIRATION_HOURS=48
```

### Option 2: Config File

Add to `config.ini`:

```ini
[SparseAI]
api_key = your-api-key-from-render-deployment
base_url = https://sparse-ai.com
expiration_hours = 48
```

## How It Works

### Before (Old System)
```
1. Incident detected
2. Video created locally
3. Video attached to email (large attachment)
4. Video stored indefinitely on disk
```

### After (New System)
```
1. Incident detected
2. Video created temporarily
3. Video uploaded to sparse-ai.com
4. Secure link generated
5. Link included in email
6. Local video deleted immediately
7. Cloud video expires after 48 hours
```

## Email Format

Emails now include:

```
📹 PREUVES VIDÉO DISPONIBLES (CONFORME RGPD)

🔗 LIEN VIDÉO PRIVÉ SÉCURISÉ:
https://sparse-ai.com/video/abc-123-def?token=securetoken

💾 Taille: 2.5 MB
🆔 ID Vidéo: abc-123-def-456
⏰ Expiration: 2025-10-02T16:00:00

🔒 ACCÈS SÉCURISÉ:
Le lien est sécurisé avec un token d'accès et expirera automatiquement.
```

## Testing

### 1. Test Configuration

```bash
cd ~/dev/Vigint
python -c "
from video_link_service import VideoLinkService
import os

# Verify configuration
service = VideoLinkService()
print(f'✓ Base URL: {service.base_url}')
print(f'✓ Upload endpoint: {service.upload_endpoint}')
print(f'✓ API key configured: {bool(service.api_key)}')
"
```

### 2. Test Upload (with a test video)

```bash
python test_video_link_service.py
```

### 3. Test Full Alert Flow

```bash
python demo_video_alerts.py
```

## Verification Checklist

- [ ] Sparse AI video server deployed to Render.com
- [ ] Custom domain (sparse-ai.com) configured
- [ ] API key generated and saved securely
- [ ] Environment variables configured in Vigint
- [ ] Test upload successful
- [ ] Email alerts include video links
- [ ] Video links work in browser
- [ ] Videos expire after configured time

## Troubleshooting

### Issue: "Sparse AI API key not configured"

**Solution**: Set the `SPARSE_AI_API_KEY` environment variable:
```bash
export SPARSE_AI_API_KEY="your-api-key-here"
# Or add to .env file
```

### Issue: "Forbidden. Invalid token"

**Root Cause**: URL mismatch between token generation and video server.

**Solution**:
1. Check which URL your video links use (e.g., `https://sparse-ai-video-server.onrender.com`)
2. Update `.env` to match that EXACT URL:
   ```bash
   SPARSE_AI_BASE_URL=https://sparse-ai-video-server.onrender.com
   ```
3. Restart your Vigint application
4. Test with a new incident (old links won't work with new configuration)

**Diagnostic Tool**:
```bash
python diagnose_video_token.py "https://sparse-ai-video-server.onrender.com/video/xxx?token=yyy"
```

**Why This Happens**:
- Tokens are generated using: `SHA256(video_id + expiration + api_key)`
- If `.env` has `sparse-ai.com` but server is at `sparse-ai-video-server.onrender.com`
- The server validates with its URL but tokens were generated with a different URL
- Result: Token mismatch → "Invalid token" error

### Issue: "Connection error - unable to reach sparse-ai.com"

**Possible causes**:
1. Server not deployed yet → Deploy following DEPLOYMENT.md
2. Wrong URL → Verify `SPARSE_AI_BASE_URL` matches your actual deployment URL
3. Server down → Check Render.com dashboard

### Issue: "Upload failed with status 401"

**Solution**: API key mismatch. Ensure the same key is used on both:
- Vigint configuration (client)
- Render environment variables (server)

### Issue: "Upload failed with status 404"

**Solution**: Wrong endpoint. Verify upload endpoint is:
- `https://sparse-ai.com/api/v1/videos/upload`

### Issue: Videos not loading in browser

**Possible causes**:
1. Token expired → Links are time-limited (default 48 hours)
2. Video deleted → Check server storage and expiration settings
3. Wrong token → Token must match the one in the link

## Security Notes

1. **Keep API Key Secret**: Never commit to Git, use environment variables
2. **HTTPS Only**: Always use https:// not http://
3. **Token Expiration**: Links expire automatically (default 48 hours)
4. **GDPR Compliant**: Videos are automatically deleted after expiration
5. **EU Hosting**: Server runs in Frankfurt for GDPR compliance

## Maintenance

### Monitor Upload Success Rate

Check logs for upload failures:
```bash
grep "Video uploaded successfully" logs/vigint.log | wc -l
grep "Error uploading video" logs/vigint.log | wc -l
```

### Clean Up Old Local Videos (if any exist)

The system now automatically deletes local videos after upload, but you can clean old ones:
```bash
cd ~/dev/Vigint
python -c "
from local_video_link_service import LocalVideoLinkService
service = LocalVideoLinkService()
cleaned = service.cleanup_expired_videos()
print(f'Cleaned {cleaned} expired videos')
"
```

## Cost Estimate

With typical Vigint usage (2-10 incidents/day):

- **Render.com**: Free tier or $7/month (Starter plan)
- **Disk storage**: 10GB for ~$2.50/month
- **Bandwidth**: Included in plan
- **Total**: ~$10/month for production use

## Support

- **Vigint Issues**: Check project logs and configuration
- **Server Issues**: Check Render.com dashboard and logs
- **Deployment Help**: See `~/dev/Vigint-private/DEPLOYMENT.md`

## Related Documentation

- `DEPLOYMENT.md` - How to deploy the server
- `VIDEO_LINK_SERVICE_SETUP.md` - Original video link service docs
- `GDPR_COMPLIANT_SOLUTION_FINAL.md` - GDPR compliance details

---

Your video server is ready! Videos will now be served from **https://sparse-ai.com** 🚀
