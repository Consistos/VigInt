# Sparse AI Video Server Setup - COMPLETE ✅

## Summary

The Vigint system has been successfully configured to use **sparse-ai.com** for video hosting instead of local storage. All necessary files have been created and configured for production deployment.

## What Was Changed

### 1. Video Link Service (`video_link_service.py`)
- ✅ Fixed upload endpoint to match server: `/api/v1/videos/upload`
- ✅ Base URL configured for sparse-ai.com
- ✅ API key authentication ready

### 2. Sparse AI Server (`~/dev/Vigint-private/server.py`)
- ✅ Production-ready Flask server
- ✅ Token-based video authentication
- ✅ Automatic HTTPS support for Render.com
- ✅ Health check endpoint
- ✅ Configurable expiration times
- ✅ Comprehensive logging

### 3. Deployment Configuration (`~/dev/Vigint-private/`)
- ✅ `render.yaml` - Render.com Blueprint configuration
- ✅ `.env.example` - Environment variable template
- ✅ `DEPLOYMENT.md` - Complete deployment guide (10 steps)
- ✅ `README.md` - Server documentation
- ✅ `.gitignore` - Git exclusions

### 4. Documentation (`~/dev/Vigint/`)
- ✅ `SPARSE_AI_SETUP.md` - Integration guide for Vigint
- ✅ `.env.example` - Already includes sparse-ai.com config

## How It Works Now

### Email Flow

**Before**: Videos attached to emails (large, slow, not GDPR compliant)  
**After**: Secure video links in emails (fast, GDPR compliant)

### Video Processing Flow

```
1. Incident detected by Vigint
2. Video created temporarily
3. Video uploaded to sparse-ai.com via API
4. Server returns secure link with token
5. Link embedded in email alert
6. Local video deleted immediately (GDPR)
7. Video accessible via link until expiration
8. Video auto-deleted from cloud after 48h
```

### Email Content (French)

```
📹 PREUVES VIDÉO DISPONIBLES (CONFORME RGPD)

🔗 LIEN VIDÉO PRIVÉ SÉCURISÉ:
https://sparse-ai.com/video/abc-123-def?token=xyz789

💾 Taille: 2.5 MB
🆔 ID Vidéo: abc-123-def-456
⏰ Expiration: 2025-10-02T16:00:00

🔒 ACCÈS SÉCURISÉ:
Le lien est sécurisé avec un token d'accès et expirera automatiquement.
```

## Deployment Steps (Quick Reference)

### Step 1: Generate API Key
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
**Save this key securely!**

### Step 2: Push Vigint-private to Git
```bash
cd ~/dev/Vigint-private
git add .
git commit -m "Production-ready sparse-ai.com video server"
git push origin main
```

### Step 3: Deploy to Render.com
1. Go to https://dashboard.render.com
2. New → Blueprint
3. Connect your Git repo
4. Select `Vigint-private`
5. Set environment variable: `SPARSE_AI_API_KEY`
6. Deploy!

### Step 4: Configure Custom Domain
1. In Render dashboard → Custom Domains
2. Add `sparse-ai.com`
3. Update DNS records as instructed
4. Wait for SSL certificate (automatic)

### Step 5: Configure Vigint
Add to `.env`:
```bash
SPARSE_AI_BASE_URL=https://sparse-ai.com
SPARSE_AI_API_KEY=your-api-key-from-step-1
VIDEO_LINK_EXPIRATION_HOURS=48
```

### Step 6: Test!
```bash
cd ~/dev/Vigint
python demo_video_alerts.py
```

## File Locations

### Vigint Project (`~/dev/Vigint`)
- `video_link_service.py` - Updated with correct endpoint
- `alerts.py` - Already configured to use video links
- `gdpr_compliant_video_service.py` - GDPR compliance layer
- `.env.example` - Includes sparse-ai.com configuration
- `SPARSE_AI_SETUP.md` - **New** - Integration guide
- `SPARSE_AI_VIDEO_SETUP_COMPLETE.md` - **New** - This file

### Vigint-private Project (`~/dev/Vigint-private`)
- `server.py` - **Updated** - Production-ready Flask server
- `render.yaml` - **New** - Render.com configuration
- `.env.example` - **New** - Environment variables template
- `DEPLOYMENT.md` - **New** - Complete deployment guide
- `README.md` - **New** - Server documentation
- `.gitignore` - **New** - Git exclusions
- `requirements.txt` - Already has Flask + Gunicorn

## Configuration Reference

### Environment Variables (Vigint)
```bash
# Required
SPARSE_AI_BASE_URL=https://sparse-ai.com
SPARSE_AI_API_KEY=your-secure-api-key

# Optional
VIDEO_LINK_EXPIRATION_HOURS=48  # Default: 24
```

### Environment Variables (Sparse AI Server)
```bash
# Required
SPARSE_AI_API_KEY=same-as-vigint-config

# Optional
VIDEO_STORAGE_DIR=/opt/render/project/src/uploads
PORT=8000  # Set automatically by Render
RENDER=true  # Set automatically by Render
```

## Testing Checklist

- [ ] Server deployed to Render.com
- [ ] Health check responds: `curl https://sparse-ai.com/health`
- [ ] API key set in both Vigint and Server
- [ ] Custom domain configured (sparse-ai.com)
- [ ] Test upload works
- [ ] Email alerts include video links
- [ ] Video links open in browser
- [ ] Links expire after configured time

## Security Features

✅ **Token-based authentication**: Unique token per video  
✅ **Time-limited access**: Links expire (default 48h)  
✅ **HTTPS only**: SSL certificate automatic  
✅ **No local storage**: Videos deleted after upload  
✅ **EU hosting**: Frankfurt region (GDPR compliant)  
✅ **API key authentication**: Secure upload endpoint  
✅ **Automatic expiration**: Videos deleted from cloud  

## Cost Estimate

- **Render.com**: Free tier for testing, $7/month for production
- **Storage**: ~$2.50/month for 10GB
- **Total**: ~$10/month for production use

Free tier includes:
- 750 hours/month
- 100GB bandwidth
- Perfect for testing!

## Support & Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| Deployment Guide | `~/dev/Vigint-private/DEPLOYMENT.md` | How to deploy server |
| Server README | `~/dev/Vigint-private/README.md` | Server documentation |
| Vigint Setup | `~/dev/Vigint/SPARSE_AI_SETUP.md` | Integration guide |
| This Summary | `~/dev/Vigint/SPARSE_AI_VIDEO_SETUP_COMPLETE.md` | Overview |

## Next Steps

1. **Deploy Now** (15 minutes):
   - Follow `~/dev/Vigint-private/DEPLOYMENT.md`
   - Complete all 10 steps
   - Test the health endpoint

2. **Configure Vigint** (5 minutes):
   - Update `.env` with API key and URL
   - Restart Vigint service

3. **Test End-to-End** (10 minutes):
   - Run demo scripts
   - Trigger a test incident
   - Verify email has video link
   - Click link and watch video

4. **Monitor** (Ongoing):
   - Check Render.com logs
   - Monitor upload success rate
   - Review storage usage

## Troubleshooting

### Issue: "Sparse AI API key not configured"
**Fix**: Set `SPARSE_AI_API_KEY` in `.env`

### Issue: "Connection error - unable to reach sparse-ai.com"
**Fix**: Deploy server first, verify URL is correct

### Issue: "Upload failed with status 401"
**Fix**: API key mismatch - must be identical in both configs

### Issue: "Upload failed with status 404"
**Fix**: Endpoint should be `/api/v1/videos/upload` (with `/upload`)

## Success Criteria

✅ All files created and configured  
✅ Server code production-ready  
✅ Deployment documentation complete  
✅ Integration guide written  
✅ Configuration examples provided  
✅ Security best practices implemented  
✅ GDPR compliance maintained  

## Ready to Deploy! 🚀

Everything is prepared for deployment. Follow the guides to:
1. Deploy server to Render.com
2. Configure custom domain
3. Update Vigint configuration
4. Test the complete flow

**Your video infrastructure is ready for production!**

---

**Questions?** Check the documentation files listed above.  
**Issues?** Review troubleshooting sections in each guide.  
**Ready?** Start with `~/dev/Vigint-private/DEPLOYMENT.md`!
