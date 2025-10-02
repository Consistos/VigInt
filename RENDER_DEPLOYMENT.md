# Vigint API Server Deployment on Render.com

This guide provides step-by-step instructions for deploying the Vigint API server (`api_proxy.py`) on Render.com for distributed deployment.

## Architecture Overview

```
┌─────────────────────────────────────────┐
│  Local Machine (start_vigint.py)       │
│  - RTSP Server                          │
│  - Video Analyzer                       │
│  - Frame Buffer                         │
└───────────────┬─────────────────────────┘
                │ HTTP/HTTPS
                │
                ▼
┌─────────────────────────────────────────┐
│  Render.com (api_proxy.py)              │
│  - Gemini AI Processing                 │
│  - Video Compression                    │
│  - Email Alerts                         │
│  - PostgreSQL Database                  │
└─────────────────────────────────────────┘
```

## Prerequisites

- **GitHub Account** - Your code needs to be in a GitHub repository
- **Render.com Account** - Sign up at https://render.com (free tier available)
- **Google Gemini API Key** - From https://makersuite.google.com/app/apikey
- **Email SMTP Credentials** - For sending alerts (Gmail, SendGrid, etc.)

## Step-by-Step Deployment

### Step 1: Prepare Your Repository

1. **Ensure all files are committed to GitHub:**
   ```bash
   cd /Users/david2/dev/Vigint
   git add api_proxy.py api_client.py requirements-api-server.txt render.yaml
   git commit -m "Add distributed deployment support"
   git push origin main
   ```

2. **Verify required files exist:**
   - ✅ `api_proxy.py` - Main API server
   - ✅ `requirements-api-server.txt` - Dependencies
   - ✅ `render.yaml` - Render configuration
   - ✅ `config.py` - Configuration loader
   - ✅ `auth.py` - API authentication
   - ✅ `vigint/models.py` - Database models

### Step 2: Create Render.com Service

#### Option A: Automatic Deployment (Blueprint)

1. **Login to Render.com** at https://dashboard.render.com

2. **Create New Blueprint Instance:**
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Select branch (usually `main`)
   - Render will detect `render.yaml` automatically
   - Click "Apply"

#### Option B: Manual Deployment

1. **Create PostgreSQL Database:**
   - Go to https://dashboard.render.com
   - Click "New" → "PostgreSQL"
   - Name: `vigint-db`
   - Database: `vigint`
   - User: `vigint`
   - Region: `Oregon` (or closest to you)
   - Plan: `Starter` (free tier)
   - Click "Create Database"
   - **Save the Internal Database URL** (starts with `postgresql://`)

2. **Create Web Service:**
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Select branch: `main`
   - **Configuration:**
     ```
     Name: vigint-api-server
     Region: Oregon
     Branch: main
     Root Directory: (leave empty)
     Runtime: Python 3
     Build Command: pip install -r requirements-api-server.txt
     Start Command: gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 api_proxy:app
     Plan: Starter ($7/month) or Free (with limitations)
     ```

### Step 3: Configure Environment Variables

In the Render.com dashboard, go to your web service → "Environment" and add:

#### Required Variables

| Variable Name | Value | Description |
|--------------|-------|-------------|
| `SECRET_KEY` | `your-secret-key-here` | API authentication key (generate with `openssl rand -hex 32`) |
| `GOOGLE_API_KEY` | `your-gemini-api-key` | Google Gemini API key from MakerSuite |
| `DATABASE_URL` | `postgresql://...` | Auto-filled from database connection |
| `PYTHON_VERSION` | `3.11.0` | Python version |
| `FLASK_ENV` | `production` | Environment mode |

#### Email Configuration (Required for Alerts)

| Variable Name | Value | Example |
|--------------|-------|---------|
| `EMAIL_SMTP_SERVER` | SMTP server | `smtp.gmail.com` |
| `EMAIL_SMTP_PORT` | SMTP port | `587` |
| `EMAIL_USERNAME` | Your email | `alerts@yourdomain.com` |
| `EMAIL_PASSWORD` | App password | `your-app-password` |
| `EMAIL_FROM` | From address | `alerts@yourdomain.com` |
| `EMAIL_TO` | Alert recipient | `security@yourdomain.com` |

**For Gmail:**
1. Enable 2FA: https://myaccount.google.com/security
2. Create App Password: https://myaccount.google.com/apppasswords
3. Use the 16-character app password as `EMAIL_PASSWORD`

#### Optional Variables

| Variable Name | Value | Description |
|--------------|-------|-------------|
| `VIGINT_CONFIG_PATH` | `/opt/render/project/src/server_config.ini` | Config file path |
| `LOG_LEVEL` | `INFO` | Logging level |

### Step 4: Deploy

1. **Trigger Deployment:**
   - Click "Manual Deploy" → "Deploy latest commit"
   - Or push to GitHub (auto-deploy if enabled)

2. **Monitor Deployment:**
   - Watch the build logs in Render dashboard
   - Build should complete in 2-5 minutes
   - Service will automatically start after build

3. **Check Health:**
   - Once deployed, note your service URL: `https://vigint-api-server.onrender.com`
   - Test health endpoint:
     ```bash
     curl https://vigint-api-server.onrender.com/api/health
     ```
   - Expected response:
     ```json
     {
       "status": "healthy",
       "timestamp": "2025-10-02T10:00:00",
       "version": "1.0"
     }
     ```

### Step 5: Configure Local Machine

On your local machine where `start_vigint.py` runs:

1. **Edit `config.ini`:**
   ```ini
   [API]
   # Your Render.com API server URL
   api_server_url = https://vigint-api-server.onrender.com
   
   # Same secret key as configured on Render
   secret_key = your-secret-key-here
   ```

2. **Test Connection:**
   ```bash
   python3 -c "from api_client import APIClient; client = APIClient(); print(client.health_check())"
   ```

3. **Start Vigint:**
   ```bash
   python3 start_vigint.py --video-input /path/to/video.mp4
   ```
   
   You should see:
   ```
   ✅ Using remote API server at: https://vigint-api-server.onrender.com
   📡 Distributed deployment mode - API proxy will not start locally
   ```

## Database Management

### Initial Database Setup

Render.com automatically creates the database, but you may need to initialize tables:

1. **SSH into your Render service:**
   - In Render dashboard → "Shell" tab
   - Run:
     ```bash
     python3 -c "from api_proxy import initialize_database; initialize_database()"
     ```

2. **Or use a one-time job:**
   - Create a new "Background Worker" in Render
   - Start Command: `python3 -c "from api_proxy import initialize_database; initialize_database()"`
   - Run once and delete

### Database Migrations

When you update database models:

```bash
# Local development
python3 -c "from vigint.models import db; from api_proxy import app; app.app_context().push(); db.create_all()"

# On Render (via Shell)
python3 -c "from api_proxy import initialize_database; initialize_database()"
```

## Monitoring & Debugging

### View Logs

1. **In Render Dashboard:**
   - Go to your service → "Logs" tab
   - Real-time log streaming
   - Filter by log level

2. **Common Log Locations:**
   ```bash
   # Application logs
   tail -f /var/log/render/application.log
   
   # Gunicorn logs
   tail -f /var/log/render/gunicorn.log
   ```

### Health Checks

Render automatically monitors `/api/health` endpoint:
- **Healthy:** Service receives traffic
- **Unhealthy:** Service is restarted automatically

### Performance Monitoring

1. **Render Metrics:**
   - Go to service → "Metrics" tab
   - View: CPU, Memory, Response times, Error rates

2. **Usage Statistics:**
   ```bash
   curl -H "X-API-Key: your-api-key" \
     https://vigint-api-server.onrender.com/api/usage
   ```

## Cost Optimization

### Free Tier (Starter Plan)

Render offers a free tier with limitations:
- **Spins down after 15 minutes of inactivity**
- **750 hours/month free** (about 31 days if always on)
- **First request after spin-down takes 30-60 seconds**

**Workaround for spin-down:**
```bash
# Add to crontab on local machine to keep service alive
*/10 * * * * curl https://vigint-api-server.onrender.com/api/health
```

### Paid Plans

| Plan | Price | Features |
|------|-------|----------|
| **Starter** | $7/month | No spin-down, 512MB RAM, 0.5 CPU |
| **Standard** | $25/month | 2GB RAM, 1 CPU, better performance |
| **Pro** | $85/month | 4GB RAM, 2 CPU, priority support |

### Database Costs

| Plan | Price | Storage | Connections |
|------|-------|---------|-------------|
| **Starter** | Free | 1GB | 5 concurrent |
| **Standard** | $7/month | 10GB | 40 concurrent |

## Security Best Practices

### 1. API Key Security

- **Never commit API keys to Git**
- Use Render's environment variables
- Rotate keys regularly:
  ```bash
  openssl rand -hex 32
  ```

### 2. HTTPS Only

Render automatically provides HTTPS:
- Certificate auto-renewed
- HTTP → HTTPS redirect enabled by default

### 3. Database Security

- Use Render's internal database URL (not public)
- Enable connection pooling
- Regular backups (automatic on paid plans)

### 4. Rate Limiting

Add to `api_proxy.py`:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
```

## Troubleshooting

### Issue: "Connection refused"

**Cause:** API server not running or wrong URL

**Solution:**
```bash
# Check service status in Render dashboard
# Verify URL in config.ini matches Render URL
# Test health endpoint
curl https://your-app.onrender.com/api/health
```

### Issue: "Database connection failed"

**Cause:** DATABASE_URL not set or database not ready

**Solution:**
1. Verify `DATABASE_URL` environment variable in Render
2. Check database status in Render dashboard
3. Wait 1-2 minutes after database creation
4. Restart web service

### Issue: "Module not found"

**Cause:** Missing dependencies in `requirements-api-server.txt`

**Solution:**
1. Add missing package to `requirements-api-server.txt`
2. Push to GitHub
3. Redeploy on Render

### Issue: "Video processing timeout"

**Cause:** Gunicorn timeout too short

**Solution:**
Update start command in Render:
```bash
gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 300 api_proxy:app
```

### Issue: "Out of memory"

**Cause:** Large video processing exceeds RAM limit

**Solutions:**
1. Upgrade to Standard plan (2GB RAM)
2. Reduce video quality in config
3. Implement video streaming instead of loading entire file

### Issue: "Cold start delay"

**Cause:** Free tier spins down after inactivity

**Solutions:**
1. Upgrade to Starter plan ($7/month) - no spin-down
2. Use cron job to ping health endpoint every 10 minutes
3. Accept 30-60s delay on first request

## Scaling & Performance

### Vertical Scaling (More Resources)

Upgrade plan in Render dashboard:
- **Starter → Standard:** 4x RAM, 2x CPU
- **Standard → Pro:** 2x RAM, 2x CPU

### Horizontal Scaling (More Instances)

Render doesn't support horizontal scaling on web services, but you can:
1. Use load balancer (CloudFlare, AWS ALB)
2. Deploy multiple Render services
3. Use Render's background workers for async tasks

### Optimization Tips

1. **Use Redis for Caching:**
   ```bash
   # Add to requirements-api-server.txt
   redis==5.0.0
   flask-caching==2.0.2
   ```

2. **Enable Gunicorn Pre-loading:**
   ```bash
   gunicorn --preload --bind 0.0.0.0:$PORT api_proxy:app
   ```

3. **Optimize Database Queries:**
   - Add indexes to frequently queried columns
   - Use connection pooling
   - Implement query caching

## Backup & Disaster Recovery

### Database Backups

**Automatic (Paid Plans):**
- Daily backups
- 7-day retention
- Point-in-time recovery

**Manual Backup:**
```bash
# In Render shell
pg_dump $DATABASE_URL > backup.sql

# Or from local machine
pg_dump postgresql://user:pass@host/db > backup.sql
```

### Service Backup

**Infrastructure as Code:**
- Keep `render.yaml` in version control
- Document environment variables
- Maintain deployment scripts

**Database Migration:**
```bash
# Export from old database
pg_dump old_db > dump.sql

# Import to new database
psql new_db < dump.sql
```

## Advanced Configuration

### Custom Domain

1. **Add Custom Domain in Render:**
   - Go to service → "Settings" → "Custom Domain"
   - Add domain: `api.yourdomain.com`

2. **Configure DNS:**
   - Add CNAME record:
     ```
     api.yourdomain.com -> vigint-api-server.onrender.com
     ```

3. **Update Local Config:**
   ```ini
   [API]
   api_server_url = https://api.yourdomain.com
   ```

### Environment-Specific Configuration

Create multiple Render services for different environments:

```
vigint-api-dev      → Development
vigint-api-staging  → Staging
vigint-api-prod     → Production
```

### CI/CD Integration

**Auto-deploy on Git push:**
1. Go to service → "Settings" → "Build & Deploy"
2. Enable "Auto-Deploy"
3. Select branch
4. Every push triggers deployment

**GitHub Actions Integration:**
```yaml
# .github/workflows/deploy.yml
name: Deploy to Render
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Trigger Render Deploy
        run: |
          curl -X POST \
            https://api.render.com/v1/services/$SERVICE_ID/deploys \
            -H "Authorization: Bearer $RENDER_API_KEY"
```

## Cost Estimation

### Minimal Setup (Free Tier)
- **Web Service:** Free (with spin-down)
- **Database:** Free (1GB)
- **Total:** $0/month

### Production Setup (Recommended)
- **Web Service:** Starter ($7/month)
- **Database:** Starter (Free or $7/month)
- **Total:** $7-14/month

### High-Performance Setup
- **Web Service:** Standard ($25/month)
- **Database:** Standard ($7/month)
- **Redis:** Standard ($10/month)
- **Total:** $42/month

## Support & Resources

- **Render Documentation:** https://render.com/docs
- **Render Status:** https://status.render.com
- **Render Community:** https://community.render.com
- **Vigint Issues:** https://github.com/your-repo/issues

## Next Steps

1. ✅ Deploy API server to Render.com
2. ✅ Configure environment variables
3. ✅ Test API endpoints
4. ✅ Update local config.ini
5. ✅ Run distributed system
6. 📊 Monitor performance
7. 🔒 Implement additional security
8. 📈 Scale as needed

---

**Deployment Complete! 🎉**

Your Vigint API server is now running on Render.com with automatic scaling, monitoring, and zero-downtime deployments.
