# Automatic Cleanup - Setup Complete ✅

## Summary

Your Vigint system now has **automatic cleanup** of old incident files and videos to prevent unlimited storage growth.

## ✅ What's Been Added

### 1. Automatic Cleanup System
- **Retention period**: 30 days (configurable)
- **Frequency**: Daily (automatic)
- **What gets cleaned**:
  - Offline incident files (`offline_incidents/`)
  - Mock service videos (`mock_sparse_ai_cloud/`)

### 2. Built-in Periodic Cleanup
- **Integrated into**: `AlertManager.send_email_alert()`
- **Runs**: Once per day automatically
- **Execution**: Background thread (non-blocking)
- **Logging**: Shows in main log file

```python
# In alerts.py
self.last_cleanup_time = 0
self.cleanup_interval = 24 * 60 * 60  # 24 hours
```

### 3. Standalone Cleanup Script
- **File**: `cleanup_old_incidents.py`
- **Usage**: Can be run manually anytime
- **Features**:
  - Dry-run mode
  - Customizable retention
  - Selective cleanup (incidents/videos)
  - Detailed statistics

### 4. Cron Job Setup Script
- **File**: `setup_cleanup_cron.sh`
- **Purpose**: Additional cleanup for systems that restart
- **Schedule**: Daily at 3:00 AM
- **Optional**: But recommended for production

### 5. Documentation
- **AUTOMATIC_CLEANUP.md**: Complete cleanup documentation
- **INFRASTRUCTURE_FIXES_COMPLETE.md**: All fixes summary
- **README.md**: Updated with cleanup features

## Configuration

### Environment Variable (Primary Method)
```bash
# Set in .env or shell
export INCIDENT_RETENTION_DAYS=30
```

**Recommended values**:
- `7` = 1 week (testing/development)
- `30` = 1 month (default, production)
- `90` = 3 months (compliance/auditing)

### In Code (Advanced)
Edit `alerts.py` line 29 for cleanup frequency:
```python
self.cleanup_interval = 24 * 60 * 60  # 24 hours (default)
# Or: 12 * 60 * 60  # 12 hours (more frequent)
```

## Usage

### Automatic (Default) ✨
**Nothing to do!** Cleanup runs automatically once per day when the system is running.

### Manual Cleanup (Optional)
```bash
# See what would be deleted (dry run)
python3 cleanup_old_incidents.py --dry-run

# Actually delete old files
python3 cleanup_old_incidents.py

# Custom retention (e.g., 7 days)
python3 cleanup_old_incidents.py --days 7

# Clean only incidents
python3 cleanup_old_incidents.py --incidents-only

# Clean only videos
python3 cleanup_old_incidents.py --videos-only
```

### Cron Setup (Recommended for Production)
```bash
# One-time setup
./setup_cleanup_cron.sh

# Verify installation
crontab -l | grep cleanup
```

## Current Status

From your system (as of 2025-10-01):
```
Location: mock_sparse_ai_cloud/
Total files: 846 (423 videos + 423 metadata)
Total size: 118.06 MB
Files older than 30 days: 0 (all recent)

Next cleanup: No files to delete yet
When: Will automatically delete files as they age beyond 30 days
```

## What You'll See in Logs

### When Cleanup Runs
```
🧹 Running automatic cleanup (retention: 30 days)
Scanning /Users/david2/dev/Vigint/mock_sparse_ai_cloud for files older than 2025-09-01
✅ Cleanup complete: No files older than 30 days
```

### When Files Are Deleted
```
🧹 Running automatic cleanup (retention: 30 days)
Deleted (age: 35.2 days, size: 1.24 MB): cloud_video_20250826_143022.mp4
Deleted (age: 35.2 days, size: 0.01 MB): cloud_video_20250826_143022.mp4.json
✅ Cleanup complete: 2 files deleted, 1.25 MB freed
```

## Monitoring

### Check Cleanup Status
```bash
# View cleanup logs
grep "cleanup" vigint.log | tail -10

# Check storage usage
du -sh offline_incidents/ mock_sparse_ai_cloud/

# Count current files
find mock_sparse_ai_cloud/ -name "*.mp4" | wc -l
```

### Find Old Files Manually
```bash
# Files older than 30 days
find mock_sparse_ai_cloud/ -name "*.mp4" -mtime +30

# Files from last 7 days
find mock_sparse_ai_cloud/ -name "*.mp4" -mtime -7
```

## Safety Features

1. **Age-based deletion only** - Never deletes by size or random selection
2. **Dry-run testing** - Preview deletions before executing
3. **Detailed logging** - Every deletion is logged with age and size
4. **Error handling** - Errors reported but cleanup continues
5. **Non-destructive** - Only deletes specified file patterns

## Benefits

### Storage Management
- ✅ Prevents unlimited growth of incident files
- ✅ Automatically frees disk space
- ✅ Configurable retention periods
- ✅ No manual intervention needed

### Data Retention Compliance
- ✅ Automatic enforcement of retention policies
- ✅ Configurable per legal requirements
- ✅ Documented deletion process
- ✅ Logged audit trail

### System Performance
- ✅ Keeps directories clean and performant
- ✅ Faster file system operations
- ✅ Background execution doesn't block alerts
- ✅ Minimal resource usage

## Troubleshooting

### "Directory does not exist"
**Normal** - Means no offline incidents or videos yet. Directories are created when needed.

### Files Not Being Deleted
**Check age**: Are files actually old enough?
```bash
python3 cleanup_old_incidents.py --dry-run
```
If "Files to be deleted: 0", all files are within retention period.

### Want More Aggressive Cleanup
```bash
# Clean files older than 7 days instead of 30
python3 cleanup_old_incidents.py --days 7
```

Or set environment variable:
```bash
export INCIDENT_RETENTION_DAYS=7
```

## Next Steps

### For Development/Testing
1. ✅ System is ready - cleanup runs automatically
2. Test with: `python3 cleanup_old_incidents.py --dry-run`
3. Monitor logs: `grep "cleanup" vigint.log`

### For Production Deployment
1. ✅ Cleanup is configured (30-day retention)
2. **(Optional)** Setup cron: `./setup_cleanup_cron.sh`
3. Set environment variable in production: `INCIDENT_RETENTION_DAYS=30`
4. Monitor storage monthly: `du -sh mock_sparse_ai_cloud/`

### For Compliance/Legal Requirements
1. Adjust retention: `export INCIDENT_RETENTION_DAYS=90` (or as required)
2. Document retention policy
3. Review logs regularly
4. Archive important incidents before deletion if needed

## Files Added/Modified

### New Files
1. `cleanup_old_incidents.py` - Main cleanup script
2. `setup_cleanup_cron.sh` - Cron job setup script
3. `AUTOMATIC_CLEANUP.md` - Detailed documentation
4. `CLEANUP_SETUP_COMPLETE.md` - This file

### Modified Files
1. `alerts.py` - Added automatic cleanup integration
   - Line 28-29: Cleanup tracking variables
   - Line 58-59: Periodic cleanup call
   - Line 306-345: Cleanup methods

2. `README.md` - Updated feature list
   - Line 22-24: Added cleanup features

## Technical Details

### Cleanup Flow
```
1. System starts
   ↓
2. First alert sent
   ↓
3. Check: Time for cleanup? (24 hours since last)
   ├─ No → Continue with alert
   └─ Yes → Start background cleanup thread
       ↓
       4. Scan directories
       ↓
       5. Find files older than retention period
       ↓
       6. Delete old files
       ↓
       7. Log statistics
       ↓
       8. Update last_cleanup_time
```

### Storage Calculation
- **Videos**: ~0.5-2 MB each
- **Metadata**: ~1-5 KB each
- **Incidents**: ~1-5 KB each

**Example**: 1000 videos/month = ~1.5 GB/month
- With 30-day retention: ~1.5 GB max storage
- Cleanup frees ~50 MB per day

## Summary

✅ **Automatic cleanup is active**  
✅ **30-day retention period configured**  
✅ **Runs once per day automatically**  
✅ **No manual intervention needed**  
✅ **118 MB currently stored (all recent files)**  
✅ **System will clean as files age**  

**Your request**: ✅ **Old incident files will be automatically removed after 30 days**

**Status**: 🎉 **COMPLETE - No further action required!**

---

For more details, see: `AUTOMATIC_CLEANUP.md`
