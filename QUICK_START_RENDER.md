# Quick Start: Deploy API Server to Render.com

**Time Required:** 15-20 minutes

## Prerequisites

- GitHub repository with Vigint code
- Render.com account (sign up at https://render.com)
- Google Gemini API key (https://makersuite.google.com/app/apikey)
- Email SMTP credentials (Gmail, SendGrid, etc.)

## Step 1: Push Code to GitHub (2 minutes)

```bash
cd /Users/david2/dev/Vigint
git add .
git commit -m "Add distributed deployment support"
git push origin main
```

## Step 2: Deploy to Render.com (5 minutes)

### Option A: Blueprint (Automatic)

1. Go to https://dashboard.render.com
2. Click **"New"** → **"Blueprint"**
3. Connect your GitHub repository
4. Select branch: `main`
5. Click **"Apply"**
6. Render detects `render.yaml` and creates:
   - PostgreSQL database
   - Web service for API server

### Option B: Manual

1. **Create Database:**
   - New → PostgreSQL
   - Name: `vigint-db`
   - Plan: Starter (free)
   - Click "Create"

2. **Create Web Service:**
   - New → Web Service
   - Connect repository
   - Build Command: `pip install -r requirements-api-server.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 api_proxy:app`
   - Plan: Starter ($7/month) or Free
   - Click "Create"

## Step 3: Configure Environment Variables (3 minutes)

In Render dashboard → Your service → **Environment** tab:

**Required:**
```bash
SECRET_KEY=<generate with: openssl rand -hex 32>
GOOGLE_API_KEY=<your-gemini-api-key>
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=<your-email@gmail.com>
EMAIL_PASSWORD=<your-app-password>
EMAIL_FROM=<your-email@gmail.com>
EMAIL_TO=<alert-recipient@example.com>
```

**For Gmail App Password:**
1. Enable 2FA: https://myaccount.google.com/security
2. Create password: https://myaccount.google.com/apppasswords

Click **"Save Changes"** → Service will redeploy

## Step 4: Wait for Deployment (3-5 minutes)

Watch the **Logs** tab:
- Build dependencies
- Start gunicorn
- "Database initialized successfully"
- Service becomes "Live"

Note your service URL: `https://vigint-api-server-xxxx.onrender.com`

## Step 5: Test Deployment (2 minutes)

```bash
# Test health endpoint
curl https://vigint-api-server-xxxx.onrender.com/api/health

# Expected response:
# {"status":"healthy","timestamp":"..."}
```

## Step 6: Configure Local Machine (2 minutes)

Edit `/Users/david2/dev/Vigint/config.ini`:

```ini
[API]
# Your Render.com URL (replace with yours)
api_server_url = https://vigint-api-server-xxxx.onrender.com

# Same secret key as Render environment variable
secret_key = <your-secret-key>

host = 0.0.0.0
port = 5000
```

## Step 7: Test Connection (1 minute)

```bash
cd /Users/david2/dev/Vigint

# Test API client
python3 -c "from api_client import APIClient; client = APIClient(); print(client.health_check())"

# Should print: {'status': 'healthy', ...}
```

## Step 8: Run Distributed System (1 minute)

```bash
python3 start_vigint.py --video-input /path/to/video.mp4
```

**Expected output:**
```
✅ Using remote API server at: https://vigint-api-server-xxxx.onrender.com
📡 Distributed deployment mode - API proxy will not start locally
🚀 Starting RTSP server...
✅ RTSP server started successfully
🎬 Starting DUAL-BUFFER video analysis...
```

## Architecture

```
┌─────────────────────┐         HTTPS          ┌─────────────────────┐
│  Your Machine       │ ──────────────────►    │  Render.com         │
│  • RTSP Server      │                         │  • Gemini AI        │
│  • Video Analysis   │                         │  • Video Processing │
│  • Frame Buffer     │                         │  • Email Alerts     │
└─────────────────────┘                         │  • PostgreSQL       │
                                                 └─────────────────────┘
```

## Verification Checklist

- ✅ Render service shows "Live" status
- ✅ Health endpoint returns 200 OK
- ✅ Local machine connects to remote API
- ✅ `start_vigint.py` detects remote API server
- ✅ Video analysis creates incidents
- ✅ Email alerts are sent

## Troubleshooting

### "Connection refused"
```bash
# Verify service is running
curl https://your-service.onrender.com/api/health

# Check Render logs for errors
```

### "Database connection failed"
- Wait 1-2 minutes after database creation
- Restart web service in Render dashboard
- Verify DATABASE_URL environment variable

### "Module not found"
- Check `requirements-api-server.txt` includes all dependencies
- Trigger manual redeploy
- Check build logs for errors

### "Email not sending"
- Verify SMTP credentials in Render environment variables
- For Gmail: Use app password, not regular password
- Check Render logs for SMTP errors

## Cost

- **Free Tier:** $0/month (spins down after 15 min idle)
- **Starter:** $7/month (always on, no spin-down)
- **Database:** Free (1GB) or $7/month (10GB)

## Next Steps

- 📊 Monitor performance in Render dashboard
- 🔒 Add custom domain (optional)
- 📈 Upgrade plan if needed for performance
- 🔄 Set up auto-deploy from GitHub

## Support

- **Full Documentation:** [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md)
- **Render Docs:** https://render.com/docs
- **Issues:** https://github.com/your-repo/issues

---

**🎉 Congratulations!** Your distributed Vigint system is now running with the API server on Render.com.
