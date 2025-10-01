# Automatic Cleanup System

## Overview

The Vigint system now includes **automatic cleanup** of old incident files and videos to prevent unlimited storage growth.

**Default retention period**: 30 days  
**Cleanup frequency**: Daily (automatically)  
**What gets cleaned**: Offline incident files + mock service videos

## How It Works

### 1. Automatic Cleanup (Recommended)
The system automatically cleans up old files in two ways:

#### A. Built-in Periodic Cleanup
- **When**: Once per day during normal operation
- **Trigger**: Automatically when sending email alerts
- **Background**: Runs in separate thread, doesn't block alerts
- **Logging**: Shows in main log file

```
🧹 Running automatic cleanup (retention: 30 days)
✅ Cleanup complete: 5 files deleted, 2.3 MB freed
```

#### B. Cron Job (Optional but Recommended)
For systems that restart frequently, also setup cron:

```bash
./setup_cleanup_cron.sh
```

This creates a daily cron job at 3:00 AM.

### 2. Manual Cleanup
You can also run cleanup manually anytime:

```bash
# Dry run (see what would be deleted)
python3 cleanup_old_incidents.py --dry-run

# Actually delete files
python3 cleanup_old_incidents.py

# Custom retention period (e.g., 7 days)
python3 cleanup_old_incidents.py --days 7

# Clean only incidents (not videos)
python3 cleanup_old_incidents.py --incidents-only

# Clean only videos (not incidents)
python3 cleanup_old_incidents.py --videos-only
```

## What Gets Cleaned

### Offline Incident Files
- **Location**: `offline_incidents/`
- **Pattern**: `offline_incident_*.txt`
- **When created**: When email sending fails (network down)
- **Size**: Typically 1-5 KB each
- **Default retention**: 30 days

### Mock Service Videos
- **Location**: `mock_sparse_ai_cloud/`
- **Pattern**: `*.mp4` and `*.json`
- **When created**: When cloud video upload fails (fallback to local)
- **Size**: Typically 0.5-2 MB per video
- **Default retention**: 30 days

## Configuration

### Environment Variable (Recommended)
Set retention period via environment variable:

```bash
# In your .env file or shell
export INCIDENT_RETENTION_DAYS=30
```

Values:
- `7` = Keep 1 week
- `30` = Keep 1 month (default)
- `90` = Keep 3 months
- `365` = Keep 1 year

### Current Storage Status

From your latest run:
```
Total files: 846 (423 videos + 423 metadata)
Total size: 118.06 MB
Files older than 30 days: 0
```

All your files are recent (less than 30 days old), so nothing will be deleted yet.

## Cleanup Schedule

### Automatic (Built-in)
- **First run**: When system starts and first alert is sent
- **Subsequent runs**: Every 24 hours
- **Execution**: Background thread, non-blocking
- **Log location**: Main vigint.log

### Cron Job (If setup)
- **Schedule**: Daily at 3:00 AM
- **Log location**: `/tmp/vigint_cleanup.log`
- **View cron**: `crontab -l`
- **Remove cron**: `crontab -e` (delete the cleanup line)

## Monitoring

### Check What Would Be Deleted
```bash
python3 cleanup_old_incidents.py --dry-run
```

Output shows:
- Files found (total count)
- Files to be deleted (older than retention)
- Total size and space to be freed

### View Cleanup Logs
```bash
# Built-in cleanup logs
grep "cleanup" vigint.log

# Cron job logs (if setup)
tail /tmp/vigint_cleanup.log
```

### Manual Storage Check
```bash
# Check current storage usage
du -sh offline_incidents/ mock_sparse_ai_cloud/

# Count files
find offline_incidents/ -name "*.txt" | wc -l
find mock_sparse_ai_cloud/ -name "*.mp4" | wc -l

# Find old files (30+ days)
find offline_incidents/ -name "*.txt" -mtime +30
find mock_sparse_ai_cloud/ -name "*.mp4" -mtime +30
```

## Safety Features

### 1. Dry Run Testing
Always test with `--dry-run` first to see what would be deleted:
```bash
python3 cleanup_old_incidents.py --dry-run
```

### 2. Age-Based Only
Files are deleted ONLY based on age (modification time), never by:
- File size
- Name pattern
- Random selection

### 3. Non-Destructive
The cleanup:
- ✅ Only deletes files older than retention period
- ✅ Preserves recent files
- ✅ Logs every deletion
- ✅ Reports errors but continues
- ✅ Never deletes system files or directories

### 4. Selective Cleanup
You can clean specific categories:
```bash
# Only incidents (keep all videos)
python3 cleanup_old_incidents.py --incidents-only

# Only videos (keep all incidents)
python3 cleanup_old_incidents.py --videos-only
```

## Examples

### Example 1: Check Status
```bash
$ python3 cleanup_old_incidents.py --dry-run

======================================================================
DRY RUN: AUTOMATIC CLEANUP - Retention: 30 days
======================================================================

Offline Incidents Cleanup Summary:
  Total files found: 0
  Files to be deleted: 0

Mock Videos Cleanup Summary:
  Total files found: 846 (423 videos, 423 metadata)
  Files to be deleted: 0
  Total size: 118.06 MB

TOTAL CLEANUP SUMMARY
Files to be deleted: 0
Space to be freed: 0.00 MB
```

### Example 2: Aggressive Cleanup (7 days)
```bash
$ python3 cleanup_old_incidents.py --days 7 --dry-run

# Shows files older than 7 days that would be deleted
# Review, then run without --dry-run to actually delete
```

### Example 3: Clean Only Very Old Files (90 days)
```bash
$ python3 cleanup_old_incidents.py --days 90

# Only removes files older than 3 months
# Keeps everything from last 90 days
```

## Troubleshooting

### Cleanup Not Running
**Check**: Is system running and sending alerts?
```bash
grep "cleanup" vigint.log
```

**Solution**: Cleanup runs when alerts are sent. If no alerts, no cleanup trigger.

### Files Not Being Deleted
**Check**: Are files actually old enough?
```bash
find mock_sparse_ai_cloud/ -name "*.mp4" -mtime +30
```

**If empty**: All files are less than 30 days old (normal)

### Permission Errors
**Error**: `Permission denied` when deleting
**Solution**: Check file ownership and permissions:
```bash
ls -la offline_incidents/
ls -la mock_sparse_ai_cloud/
```

### Cron Job Not Running
**Check**: Is cron job installed?
```bash
crontab -l | grep cleanup
```

**Check**: Are logs being created?
```bash
ls -lh /tmp/vigint_cleanup.log
```

**Solution**: Re-run setup:
```bash
./setup_cleanup_cron.sh
```

## Recommendations

### For Development/Testing
```bash
# Short retention for testing
export INCIDENT_RETENTION_DAYS=7
python3 cleanup_old_incidents.py --dry-run
```

### For Production
```bash
# Standard 30-day retention
export INCIDENT_RETENTION_DAYS=30

# Setup cron for redundancy
./setup_cleanup_cron.sh

# Monitor storage monthly
du -sh offline_incidents/ mock_sparse_ai_cloud/
```

### For High-Volume Systems
```bash
# More aggressive cleanup
export INCIDENT_RETENTION_DAYS=14

# Run cleanup more often (twice daily)
# Edit: alerts.py line 29
self.cleanup_interval = 12 * 60 * 60  # 12 hours instead of 24
```

### For Compliance/Auditing
```bash
# Longer retention for evidence
export INCIDENT_RETENTION_DAYS=90

# Or even longer for legal requirements
export INCIDENT_RETENTION_DAYS=365
```

## Summary

✅ **Automatic**: Runs once per day, no manual intervention  
✅ **Safe**: Age-based deletion, preserves recent files  
✅ **Configurable**: Adjust retention period via environment variable  
✅ **Visible**: Clear logging of all cleanup operations  
✅ **Non-blocking**: Runs in background thread  
✅ **Tested**: Dry-run mode to preview deletions  

**Current Status**:
- 846 files totaling 118 MB
- All files are recent (< 30 days)
- No cleanup needed yet
- System will automatically clean when files age beyond 30 days

**Action Required**: None - cleanup is automatic!

**Optional**: Run `./setup_cleanup_cron.sh` for additional cron-based cleanup
