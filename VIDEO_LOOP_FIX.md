# Video Loop Duplicate Alert Fix

## Problem

When analyzing a video file that loops (e.g., test videos), the same incident was being detected **3 times per loop**:
- Once at the beginning of the loop
- Once in the middle
- Once at the end

**Root Cause**: The previous 60-second cooldown was insufficient because:
1. Video loops can be longer than 60 seconds
2. Each time the video loops, the same scene appears again
3. The incident appears "new" if cooldown expires between loops

## Solution: Persistent Global Cache

Implemented a **global incident cache** that persists across:
- ✅ Multiple video loops
- ✅ Analyzer instance recreations
- ✅ System restarts (saved to disk)

### How It Works

#### 1. Content-Based Hashing
```python
incident_hash = md5(analysis_text[:100])
# Example: "4a7f2e1b..." for "Mock analysis of frame 20165"
```

Each incident is identified by the **content** of its AI analysis, not just timing.

#### 2. Global Cache Storage
```json
{
  "4a7f2e1b...": {
    "timestamp": 1727791234.567,
    "incident_type": "shoplifting"
  }
}
```

Saved to: `.incident_cache.json` (gitignored)

#### 3. Dual-Layer Deduplication

**Layer 1: Global Cache (Primary)**
- **Cooldown**: 300 seconds (5 minutes)
- **Persists**: Across video loops and restarts
- **Scope**: Content-based (same scene = same hash)

**Layer 2: Local Instance (Backup)**
- **Cooldown**: 60 seconds
- **Scope**: Current analyzer instance only
- **Purpose**: Fast local checks

### Detection Flow

```
Video Loop 1 (time 0:00)
├─ Incident detected: "Person entering restricted area"
├─ Hash: 4a7f2e1b...
├─ Global cache: Not found
├─ Local cache: Not found
└─ ✅ SEND ALERT + Register in both caches

Video Loop 1 (time 0:45)
├─ Same incident: "Person entering restricted area"
├─ Hash: 4a7f2e1b... (same)
├─ Local cache: Found (45s < 60s)
└─ ⏭️  SKIP (local duplicate)

Video Loop 2 (time 1:30)
├─ Same incident: "Person entering restricted area" 
├─ Hash: 4a7f2e1b... (same)
├─ Local cache: Expired (90s > 60s) - would send
├─ Global cache: Found (90s < 300s)
└─ ⏭️  SKIP (global duplicate)

Video Loop 3 (time 6:00)
├─ Same incident: "Person entering restricted area"
├─ Hash: 4a7f2e1b... (same)
├─ Global cache: Expired (360s > 300s)
└─ ✅ SEND ALERT (legitimately new after 5 minutes)
```

## What You'll See in Logs

### Before Fix (3 duplicates)
```
🚨 POTENTIAL SECURITY EVENT DETECTED!
📧 Sending NEW incident alert...

[45 seconds later - same loop]
🚨 POTENTIAL SECURITY EVENT DETECTED!
📧 Sending NEW incident alert...

[90 seconds later - next loop]
🚨 POTENTIAL SECURITY EVENT DETECTED!
📧 Sending NEW incident alert...
```

### After Fix (1 alert, 2 skipped)
```
🚨 POTENTIAL SECURITY EVENT DETECTED!
📧 Sending NEW incident alert (global cache updated)
   Cooldowns: Local 60s | Global 300s

[45 seconds later - same loop]
🚨 POTENTIAL SECURITY EVENT DETECTED!
⏭️  Skipping local duplicate incident alert (cooldown: 60s)
   Time since last alert: 45.2s

[90 seconds later - next loop]
🚨 POTENTIAL SECURITY EVENT DETECTED!
⏭️  Skipping GLOBAL duplicate incident (seen 90.4s ago)
   Hash: 4a7f2e1b... | Type: shoplifting
   This prevents duplicates across video loops and restarts
```

## Configuration

### Cooldown Periods

**Global Cache** (line 513 in `video_analyzer.py`):
```python
cooldown_seconds=300  # 5 minutes
```

**Local Instance** (line 106 in `video_analyzer.py`):
```python
self.incident_cooldown = 60  # 1 minute
```

### Cache Expiration

**Automatic Cleanup** (line 63 in `video_analyzer.py`):
```python
if current_time - v.get('timestamp', 0) < 86400:  # 24 hours
```

Old cache entries are automatically removed after 24 hours.

## Benefits

### 1. Video Loop Handling ✅
- Same scene in looping video = Only 1 alert per 5 minutes
- Perfect for test videos that repeat

### 2. System Restart Resilience ✅
- Cache persists to disk (`.incident_cache.json`)
- Loaded on module import
- Survives system restarts

### 3. Content-Based Matching ✅
- Matches by analysis content, not just type
- "Person entering area" vs "Person exiting area" = Different incidents
- Same scene at different times = Same incident

### 4. Automatic Cleanup ✅
- Expires after 5 minutes (fresh alerts allowed)
- Old cache entries removed after 24 hours
- No manual maintenance needed

## Files Modified

### 1. `video_analyzer.py`
**Added**:
- Global cache functions (lines 52-116):
  - `_load_incident_cache()` - Load from disk
  - `_save_incident_cache()` - Save to disk
  - `_get_incident_hash()` - Create content hash
  - `_check_duplicate_global()` - Check cache
  - `_register_incident_global()` - Add to cache

**Modified**:
- Incident detection logic (lines 506-547):
  - Check global cache first (5-minute cooldown)
  - Then check local cache (60-second cooldown)
  - Register in both caches on new incident

### 2. `.gitignore`
**Added** (lines 207-212):
```
.incident_cache.json
offline_incidents/
mock_sparse_ai_cloud/
```

## Testing

### Test 1: Video Loop Deduplication
```bash
# Run video analyzer with looping video
python3 start_vigint.py --mode rtsp --video-input test_video.mp4

# Watch logs for deduplication
tail -f vigint.log | grep -E "SECURITY|duplicate|SKIP"
```

**Expected**:
- First detection: Alert sent
- Subsequent detections in same loop: Skipped
- Same scene in next loop (< 5 min): Skipped

### Test 2: Cache Persistence
```bash
# Run analyzer and trigger incident
python3 start_vigint.py --mode rtsp --video-input test_video.mp4

# Stop and restart immediately
^C
python3 start_vigint.py --mode rtsp --video-input test_video.mp4

# Check if incident is still cached
```

**Expected**:
```
Loaded 1 cached incidents
⏭️  Skipping GLOBAL duplicate incident (seen X.Xs ago)
```

### Test 3: Cache Expiration
```bash
# Check cache file
cat .incident_cache.json

# Wait 6 minutes and trigger same incident
# Should send new alert (5-minute cooldown expired)
```

## Cache File Format

Example `.incident_cache.json`:
```json
{
  "4a7f2e1b8c9d3e2f": {
    "timestamp": 1727791234.567,
    "incident_type": "shoplifting"
  },
  "f3e2d1c0b9a8e7f6": {
    "timestamp": 1727791289.123,
    "incident_type": "suspicious_behavior"
  }
}
```

**Location**: Project root directory  
**Permissions**: Readable/writable by application  
**Size**: ~100 bytes per incident  
**Cleanup**: Automatic (entries > 24h removed on load)

## Troubleshooting

### Still Getting Duplicates?

**Check 1**: Are they actually the same incident?
```bash
# View incident hashes in logs
grep "Hash:" vigint.log
```

**Check 2**: Is cooldown long enough?
```bash
# Increase global cooldown to 10 minutes
# Edit video_analyzer.py line 513
cooldown_seconds=600  # 10 minutes
```

**Check 3**: Is cache being saved?
```bash
# Check if cache file exists and is updated
ls -lh .incident_cache.json
cat .incident_cache.json | jq '.'
```

### Cache Not Loading?

**Error**: "Could not load incident cache"

**Check permissions**:
```bash
chmod 644 .incident_cache.json
```

**Check format**:
```bash
# Validate JSON
python3 -m json.tool .incident_cache.json
```

**Reset cache**:
```bash
# Delete and let it regenerate
rm .incident_cache.json
```

### Want to Disable Caching?

**Option 1**: Set very short cooldown
```python
# In video_analyzer.py line 513
cooldown_seconds=0  # Disable global cache
```

**Option 2**: Delete cache on startup
```python
# Add to __init__ method
if os.path.exists(_CACHE_FILE):
    os.remove(_CACHE_FILE)
```

## Advanced Configuration

### Adjust Hash Sensitivity

**More sensitive** (detect small differences):
```python
# Line 80-84 in video_analyzer.py
content = analysis_text[:200].lower().strip()  # Use 200 chars instead of 100
```

**Less sensitive** (group similar incidents):
```python
content = analysis_text[:50].lower().strip()  # Use 50 chars instead of 100
```

### Per-Incident-Type Cooldowns

```python
# Modify _check_duplicate_global to accept incident_type
COOLDOWN_BY_TYPE = {
    'shoplifting': 300,      # 5 minutes
    'violence': 600,         # 10 minutes  
    'fire': 120,             # 2 minutes (re-check frequently)
    'default': 300
}
```

## Summary

✅ **Fixed**: Duplicate alerts when video loops  
✅ **Method**: Persistent global cache with content hashing  
✅ **Cooldowns**: Local 60s + Global 300s (5 minutes)  
✅ **Persistence**: Saved to disk, survives restarts  
✅ **Cleanup**: Automatic expiration after 24 hours  
✅ **Smart**: Content-based matching, not just timing  

**Result**: Same incident in looping video = 1 alert per 5 minutes (instead of 3 per loop)

**Test it**: Run with looping video and watch logs for "Skipping GLOBAL duplicate"
