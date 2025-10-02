# Migration Checklist - Print This!

**Migration from sparse-ai-video-server to unified API server**

---

## Pre-Migration (5 min)

- [ ] Save old server URL: `_______________________________`
- [ ] Save old API key: `_______________________________`
- [ ] Commit and push code to GitHub
- [ ] Have Gemini API key ready: `_______________________________`
- [ ] Have Email credentials ready

---

## Deploy New Service (15 min)

- [ ] Go to https://dashboard.render.com
- [ ] New → Blueprint → Select repo → Apply
- [ ] Wait for service to deploy (~5 min)
- [ ] Note new URL: `_______________________________`
- [ ] Set environment variables:
  - [ ] SECRET_KEY
  - [ ] SPARSE_AI_API_KEY (same as old)
  - [ ] GOOGLE_API_KEY
  - [ ] DATABASE_URL (auto)
  - [ ] VIDEO_STORAGE_DIR
  - [ ] Email settings (5 vars)
  - [ ] RENDER=true
- [ ] Save changes → Wait for redeploy
- [ ] Service shows "Live" status

---

## Test New Service (10 min)

- [ ] Test health: `curl https://NEW_URL/api/health`
- [ ] Run test script: `python3 migrate_to_unified_service.py`
- [ ] All tests pass ✅
- [ ] Update local config.ini:
  ```ini
  [API]
  api_server_url = https://NEW_URL
  
  [SparseAI]
  base_url = https://NEW_URL
  ```
- [ ] Test locally: `python3 start_vigint.py --video-input test.mp4`
- [ ] Receive test alert email
- [ ] Video link in email works

---

## Migrate Videos (Optional, 10 min)

- [ ] List videos to migrate: `_______________________________`
- [ ] Run: `python3 migrate_to_unified_service.py`
- [ ] Enter each video ID and token
- [ ] Verify migration log created
- [ ] Test one migrated video link

---

## Production Cutover (24 hours)

### Day 1
- [ ] Keep both services running
- [ ] Monitor logs on both
- [ ] New videos go to new server
- [ ] Old links still work

### Day 2 (after 24 hours)
- [ ] No errors in logs
- [ ] All alerts working
- [ ] Ready to delete old service

---

## Delete Old Service (5 min)

- [ ] Backup video migration log
- [ ] Go to Render dashboard
- [ ] Click on sparse-ai-video-server
- [ ] Settings → Delete Service
- [ ] Confirm deletion
- [ ] **Save $7/month! 💰**

---

## Verify Success

- [ ] New service URL: `_______________________________`
- [ ] Old service deleted ✅
- [ ] Local config updated ✅
- [ ] Alerts working ✅
- [ ] Videos accessible ✅
- [ ] Cost reduced by $7/month ✅

---

## Emergency Rollback

If problems occur:

1. Update config.ini back to:
   ```ini
   [SparseAI]
   base_url = https://sparse-ai-video-server.onrender.com
   ```

2. Old server still running (don't delete until confirmed)

3. System reverts to old behavior

---

## Key Commands

```bash
# Test new server
curl https://NEW_URL/api/health

# Run migration tool
python3 migrate_to_unified_service.py

# Test local system
python3 start_vigint.py --video-input test.mp4

# Check storage
curl -H "X-API-Key: KEY" https://NEW_URL/api/storage/status

# Cleanup old videos
curl -X POST -H "X-API-Key: KEY" \
  https://NEW_URL/api/storage/cleanup \
  -d '{"max_age_hours": 168}'
```

---

## Important URLs

- Render Dashboard: https://dashboard.render.com
- Old server: https://sparse-ai-video-server.onrender.com
- New server: `_______________________________`

---

## Support Resources

- Full guide: [MIGRATION_STEP_BY_STEP.md](./MIGRATION_STEP_BY_STEP.md)
- Deployment guide: [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md)
- Migration details: [UNIFIED_SERVICE_MIGRATION.md](./UNIFIED_SERVICE_MIGRATION.md)

---

**Total Time: ~45 minutes**  
**Cost Savings: $84/year**  
**Risk Level: Low (old service stays running)**

---

✅ **Migration completed:** `__________ (date)`  
✅ **Completed by:** `__________ (name)`  
✅ **New service URL:** `__________`
