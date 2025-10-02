# Step-by-Step Migration Guide: Option 2

**Migrating from separate sparse-ai-video-server to unified API server**

**Estimated Time:** 30-45 minutes  
**Risk Level:** Low (old service remains running during migration)

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Access to Render.com dashboard
- [ ] GitHub repository with latest Vigint code
- [ ] Old server URL: `https://sparse-ai-video-server.onrender.com`
- [ ] Old server API key (from Render environment variables)
- [ ] Google Gemini API key
- [ ] Email SMTP credentials
- [ ] 30-45 minutes of uninterrupted time

---

## Phase 1: Deploy New Unified Service (15 minutes)

### Step 1.1: Push Latest Code to GitHub

```bash
cd /Users/david2/dev/Vigint

# Verify all files are present
ls -la api_proxy.py api_client.py render.yaml

# Add and commit
git add api_proxy.py api_client.py render.yaml config.ini.example \
  RENDER_DEPLOYMENT.md QUICK_START_RENDER.md \
  UNIFIED_SERVICE_MIGRATION.md MIGRATION_STEP_BY_STEP.md \
  migrate_to_unified_service.py

git commit -m "Add unified API server with integrated video storage"

git push origin main
```

**Expected output:** `✓ All files pushed successfully`

---

### Step 1.2: Get Your Current sparse-ai-video-server API Key

1. **Go to Render Dashboard:** https://dashboard.render.com
2. **Click on** `sparse-ai-video-server` service
3. **Go to** Environment tab
4. **Copy** the value of `SPARSE_AI_API_KEY`
5. **Save it** - you'll need it for the new service

**Example:**
```
SPARSE_AI_API_KEY=abc123def456...
```

---

### Step 1.3: Create New Unified Service on Render

#### Option A: Using Blueprint (Recommended)

1. **Go to** https://dashboard.render.com
2. **Click** "New" → "Blueprint"
3. **Connect** your GitHub repository
4. **Select** branch: `main`
5. **Render detects** `render.yaml` automatically
6. **Click** "Apply"

Render will automatically create:
- ✅ PostgreSQL database (`vigint-db`)
- ✅ Web service (`vigint-api-server`)
- ✅ 10GB persistent disk for videos

#### Option B: Manual Creation

If Blueprint doesn't work:

1. **Create Database First:**
   - New → PostgreSQL
   - Name: `vigint-db`
   - Database: `vigint`
   - User: `vigint`
   - Region: Oregon
   - Plan: Starter (free)
   - Click "Create Database"
   - **Save the Internal Database URL**

2. **Create Web Service:**
   - New → Web Service
   - Connect GitHub repository
   - Branch: `main`
   - Build Command: `pip install -r requirements-api-server.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 api_proxy:app`
   - Plan: Starter ($7/month)
   
3. **Add Disk Storage:**
   - In service settings → Disk
   - Name: `video-storage`
   - Mount Path: `/opt/render/project/src/uploads`
   - Size: 10 GB
   - Click "Add"

---

### Step 1.4: Configure Environment Variables

In Render Dashboard → `vigint-api-server` → Environment tab:

**Copy these settings:**

```bash
# Core Authentication (CRITICAL)
SECRET_KEY=<generate-new-or-use-existing>
SPARSE_AI_API_KEY=<same-as-old-sparse-ai-server>

# AI Processing
GOOGLE_API_KEY=<your-gemini-api-key>

# Database (auto-filled if using Blueprint)
DATABASE_URL=<from-vigint-db-connection-string>

# Video Storage
VIDEO_STORAGE_DIR=/opt/render/project/src/uploads

# System
RENDER=true
FLASK_ENV=production
PYTHON_VERSION=3.11.0

# Email Configuration
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=<your-email@gmail.com>
EMAIL_PASSWORD=<your-gmail-app-password>
EMAIL_FROM=<your-email@gmail.com>
EMAIL_TO=<alert-recipient@example.com>
```

**Important Notes:**
- `SPARSE_AI_API_KEY` should be the **same** as your old sparse-ai-video-server
- This ensures video tokens work correctly
- If you don't have the old key, generate a new one: `openssl rand -hex 32`

**Click "Save Changes"** - Service will redeploy (~3-5 minutes)

---

### Step 1.5: Wait for Deployment

1. **Go to** Logs tab
2. **Watch** the build progress
3. **Wait for:**
   ```
   Starting gunicorn...
   Database initialized successfully
   Created video storage directory: /opt/render/project/src/uploads
   ```
4. **Service shows:** "Live" status (green)

**Note your new service URL:**
```
https://vigint-api-server-XXXX.onrender.com
```

---

## Phase 2: Test New Unified Service (10 minutes)

### Step 2.1: Test Health Endpoint

```bash
# Replace XXXX with your actual service name
curl https://vigint-api-server-XXXX.onrender.com/api/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-02T10:30:00",
  "version": "1.0"
}
```

**✅ If successful, continue. ❌ If failed, check Render logs.**

---

### Step 2.2: Test Video Upload Endpoint

```bash
# Set your API key
export NEW_API_KEY="your-sparse-ai-api-key-here"
export NEW_SERVER="https://vigint-api-server-XXXX.onrender.com"

# Run automated tests
cd /Users/david2/dev/Vigint
python3 migrate_to_unified_service.py
```

**The script will:**
1. ✅ Test connectivity to both servers
2. ✅ Test upload endpoint with small test video
3. ✅ Test video serving with token
4. ✅ Confirm everything works

**Expected output:**
```
🔍 Testing old server: https://sparse-ai-video-server.onrender.com
   ✅ Old server is accessible

🔍 Testing new server: https://vigint-api-server-XXXX.onrender.com
   ✅ New server is accessible
   Status: healthy

🧪 Testing upload functionality
🔍 Testing video upload endpoint on new server
   ✅ Upload endpoint works!
   Video ID: test_1727872345
   Private link: https://vigint-api-server-XXXX.onrender.com/video/...

🔍 Testing video serving on new server
   ✅ Video serving works!
   Video size: 12345 bytes

✅ All tests passed - ready to migrate
```

**✅ If all tests pass, continue. ❌ If any fail, troubleshoot before proceeding.**

---

### Step 2.3: Test with Local System

Update `config.ini` (create from example if needed):

```bash
cp config.ini.example config.ini
nano config.ini
```

**Update these sections:**

```ini
[API]
# Point to NEW unified server (temporarily keep old one running)
api_server_url = https://vigint-api-server-XXXX.onrender.com
secret_key = your-sparse-ai-api-key

[SparseAI]
# Same URL - video storage is now integrated
base_url = https://vigint-api-server-XXXX.onrender.com
api_key = your-sparse-ai-api-key
default_expiration_hours = 48
```

**Test the system:**

```bash
python3 start_vigint.py --video-input local_videos/incident_HIGH_20250925_152759_2806e1c2.mp4
```

**Expected output:**
```
✅ Using remote API server at: https://vigint-api-server-XXXX.onrender.com
📡 Distributed deployment mode - API proxy will not start locally
🚀 Starting RTSP server...
✅ RTSP server started successfully
🎬 Starting video analysis...
```

**Wait for an incident to be detected and alert sent**

---

## Phase 3: Migrate Existing Videos (Optional, 10-15 minutes)

**Note:** Only necessary if you have important videos on the old server that must be preserved.

### Step 3.1: Identify Videos to Migrate

Videos to migrate are typically found in:

1. **Email alerts** - Check your alert emails for video links
2. **Local mock_sparse_ai_cloud/** directory - Check .json files
3. **Database records** - If you logged video IDs

**Video link format:**
```
https://sparse-ai-video-server.onrender.com/video/VIDEO_ID?token=TOKEN
```

---

### Step 3.2: Run Interactive Migration

```bash
cd /Users/david2/dev/Vigint

export OLD_SERVER_URL="https://sparse-ai-video-server.onrender.com"
export NEW_SERVER_URL="https://vigint-api-server-XXXX.onrender.com"
export NEW_API_KEY="your-sparse-ai-api-key"

python3 migrate_to_unified_service.py
```

**Follow the prompts:**

```
Migration options:
1. Interactive mode (enter videos manually)
2. Batch mode (provide CSV file)
3. Exit

Select option (1-3): 1

Enter video details to migrate (or 'done' to finish):
Video ID: incident_HIGH_20250925_152759_2806e1c2
Access token: abc123def456...
Optional metadata (press Enter to skip):
  Description: High-risk security incident from Sept 25

🔄 Migrating video: incident_HIGH_20250925_152759_2806e1c2
   📥 Downloading from old server...
   ✅ Downloaded 2456789 bytes
   📤 Uploading to new server...
   ✅ Upload successful!
   New link: https://vigint-api-server-XXXX.onrender.com/video/...
   📝 Migration logged to video_migration_log.json

✅ Migration successful!
```

**Repeat** for each video you want to migrate, or type `done` when finished.

---

### Step 3.3: Verify Migrated Videos

Check the migration log:

```bash
cat video_migration_log.json
```

**Test a migrated video:**

```bash
# Copy the new_link from the log
curl "https://vigint-api-server-XXXX.onrender.com/video/VIDEO_ID?token=NEW_TOKEN" -I

# Should return: HTTP/2 200
```

---

## Phase 4: Production Cutover (5 minutes)

### Step 4.1: Run Parallel for 24 Hours

**Keep both services running for 24 hours:**
- ✅ Old sparse-ai-video-server (for existing links)
- ✅ New vigint-api-server (for new videos)

**During this period:**
1. New videos go to unified server
2. Old links still work
3. Monitor both services
4. Verify no issues

---

### Step 4.2: Update All Local Configurations

**Check all machines/configs using Vigint:**

```bash
# Find all config files
find /Users/david2/dev -name "config.ini" -type f

# Update each one
nano /path/to/config.ini
```

**Ensure all point to:**
```ini
[API]
api_server_url = https://vigint-api-server-XXXX.onrender.com

[SparseAI]
base_url = https://vigint-api-server-XXXX.onrender.com
```

---

### Step 4.3: Final System Test

Run complete system test:

```bash
cd /Users/david2/dev/Vigint

# Test video analysis
python3 start_vigint.py --video-input test_video.mp4

# Wait for alert email
# Verify video link in email works
# Confirm incident recorded in database
```

**Checklist:**
- [ ] Video analysis works
- [ ] Alert email received
- [ ] Video link in email accessible
- [ ] Video plays correctly
- [ ] No errors in logs

---

## Phase 5: Decommission Old Service (5 minutes)

**Only proceed after 24+ hours of successful operation**

### Step 5.1: Document Old Videos

Create a backup list of old videos:

```bash
cd /Users/david2/dev/Vigint

# If you have video_migration_log.json
cp video_migration_log.json video_migration_log_backup_$(date +%Y%m%d).json

# Save old server environment variables
echo "OLD_SPARSE_AI_API_KEY=<your-key>" > old_server_backup.env
```

---

### Step 5.2: Delete Old Service

1. **Go to** Render Dashboard
2. **Click on** `sparse-ai-video-server`
3. **Settings** → Delete Service
4. **Type service name** to confirm
5. **Click** "Delete"

**Service deleted! 🎉**

---

### Step 5.3: Update Documentation

Update any documentation referencing old URLs:

```bash
# Search for old URLs
grep -r "sparse-ai-video-server" /Users/david2/dev/Vigint/

# Update files as needed
```

---

## Cost Savings Summary

| Service | Before | After | Savings |
|---------|--------|-------|---------|
| sparse-ai-video-server | $7/mo | $0 | $7/mo |
| vigint-api-server | $7/mo | $7/mo | $0 |
| **Total** | **$14/mo** | **$7/mo** | **$7/mo** |

**Annual savings: $84/year** 💰

---

## Rollback Plan (If Needed)

If something goes wrong:

### Quick Rollback

1. **Update config.ini back to old server:**
   ```ini
   [SparseAI]
   base_url = https://sparse-ai-video-server.onrender.com
   ```

2. **Old server still running** (don't delete it until confirmed)

3. **System reverts to old behavior**

### Full Rollback

1. Keep old sparse-ai-video-server running
2. Delete new vigint-api-server
3. Re-deploy old setup
4. No data loss - videos still on old server

---

## Troubleshooting

### Issue: "Upload endpoint not found"

**Cause:** New service not properly deployed

**Solution:**
1. Check Render logs for errors
2. Verify `api_proxy.py` has video storage endpoints
3. Redeploy service

---

### Issue: "Invalid API key"

**Cause:** API key mismatch

**Solution:**
1. Verify `SPARSE_AI_API_KEY` in Render environment matches local config
2. Check both Bearer and X-API-Key authentication
3. Regenerate keys if needed

---

### Issue: "Video not found after migration"

**Cause:** Token mismatch

**Solution:**
1. Ensure `SPARSE_AI_API_KEY` is same as old server
2. Re-migrate video with correct API key
3. Check `video_migration_log.json` for errors

---

### Issue: "Disk full" errors

**Cause:** 10GB limit reached

**Solution:**
1. Clean up old videos:
   ```bash
   curl -X POST -H "X-API-Key: key" \
     https://vigint-api-server-XXXX.onrender.com/api/storage/cleanup \
     -d '{"max_age_hours": 168}'
   ```

2. Or increase disk size in Render dashboard

---

## Success Checklist

Before declaring migration complete:

- [ ] New unified service deployed and running
- [ ] All environment variables configured
- [ ] Health endpoint returns 200 OK
- [ ] Upload endpoint tested successfully
- [ ] Video serving tested successfully
- [ ] Local system connects to new server
- [ ] Alert emails work with video links
- [ ] Videos migrated (if needed)
- [ ] Ran parallel for 24+ hours
- [ ] No errors in logs
- [ ] Old service deleted
- [ ] Cost savings confirmed ($7/month)

---

## Support

If you encounter issues:

1. **Check Render logs** - Most issues show up there
2. **Review** [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md)
3. **Run tests** with `migrate_to_unified_service.py`
4. **Check** `video_migration_log.json` for migration issues

---

## Next Steps After Migration

1. ✅ Monitor performance for first week
2. ✅ Set up automated cleanup (weekly cron job)
3. ✅ Configure backup strategy for videos
4. ✅ Document new architecture
5. ✅ Train team on new unified service

---

**🎉 Congratulations! You've successfully migrated to the unified service and saved $84/year!**
