# Duplicate Email Alert Fix - Complete Solution

## Problem Summary
**Issue:** 3 emails were being sent for the same incident from the same video on the same RTSP stream.

## Root Cause Analysis

### Primary Cause: No Incident Deduplication
The video analysis system was detecting the same ongoing incident multiple times:
- **Analysis interval:** Every 5 seconds
- **Incident duration:** Often lasts 10-15+ seconds
- **Result:** Same incident detected at 0s, 5s, 10s → 3 separate emails sent

```
Time 0s:  Incident detected → Email #1 sent ✉️
Time 5s:  Same incident still visible → Email #2 sent ✉️
Time 10s: Same incident still visible → Email #3 sent ✉️
```

### Contributing Factors
1. **No cooldown period** - System immediately re-alerted for the same incident
2. **No incident tracking** - Each detection treated as completely new
3. **No signature matching** - Similar incidents not recognized as duplicates

## Solution Implemented

### 1. Incident Deduplication in `video_analyzer.py`
Added intelligent deduplication with:
- **Incident signature:** Combination of `incident_type + analysis_summary`
- **Cooldown timer:** 60-second minimum between identical incidents
- **Tracking state:** `last_incident_time` and `last_incident_hash`

```python
# New deduplication fields added
self.last_incident_time = 0
self.incident_cooldown = 60  # 60 seconds
self.last_incident_hash = None
```

**How it works:**
1. Incident detected → Create signature from type + analysis
2. Check: Was similar incident alerted recently (< 60s ago)?
3. If YES → Skip alert, log "Skipping duplicate"
4. If NO → Send alert, start cooldown timer

### 2. Multi-Source Deduplication in `multi_source_video_analyzer.py`
Enhanced for multiple camera streams:
- **Per-source tracking:** Each camera/group has independent tracking
- **Dictionary-based:** `last_incident_time[source_id]` and `last_incident_hash[source_id]`
- **Handles both:** Individual cameras + aggregated groups

```python
# Multi-source deduplication
self.last_incident_time = {}  # Per source/group
self.incident_cooldown = 60
self.last_incident_hash = {}
```

## What You'll See in Logs

### Before Fix (3 duplicate emails)
```
🚨 POTENTIAL SECURITY EVENT DETECTED!
📧 Sending email alert...
✅ Email sent successfully

[5 seconds later]
🚨 POTENTIAL SECURITY EVENT DETECTED!
📧 Sending email alert...
✅ Email sent successfully

[5 seconds later]
🚨 POTENTIAL SECURITY EVENT DETECTED!
📧 Sending email alert...
✅ Email sent successfully
```

### After Fix (1 email, 2 duplicates skipped)
```
🚨 POTENTIAL SECURITY EVENT DETECTED!
📧 Sending NEW incident alert (cooldown active for next 60s)
✅ Email sent successfully

[5 seconds later]
🚨 POTENTIAL SECURITY EVENT DETECTED!
⏭️  Skipping duplicate incident alert (cooldown: 60s)
   Time since last alert: 5.2s

[5 seconds later]
🚨 POTENTIAL SECURITY EVENT DETECTED!
⏭️  Skipping duplicate incident alert (cooldown: 60s)
   Time since last alert: 10.4s
```

## Configuration Options

### VideoAnalyzer
```python
from video_analyzer import VideoAnalyzer

analyzer = VideoAnalyzer()

# Customize deduplication
analyzer.incident_cooldown = 120  # 2 minutes between alerts
analyzer.analysis_interval = 10   # Analyze every 10 seconds (less frequent)

analyzer.process_video_stream('rtsp://your-stream')
```

### MultiSourceVideoAnalyzer
```python
from multi_source_video_analyzer import MultiSourceVideoAnalyzer

analyzer = MultiSourceVideoAnalyzer()

# Customize per-source deduplication
analyzer.incident_cooldown = 90   # 90 seconds between alerts
analyzer.analysis_interval = 15   # Analyze every 15 seconds

analyzer.add_video_source('cam1', 'rtsp://camera1', 'Front Door')
analyzer.start_analysis()
```

## Recommended Settings

### For High-Traffic Areas
- `incident_cooldown = 60` (1 minute)
- `analysis_interval = 5` (frequent checks)
- **Why:** Catch incidents quickly, prevent spam

### For Low-Traffic Areas
- `incident_cooldown = 120` (2 minutes)
- `analysis_interval = 10` (less frequent checks)
- **Why:** Reduce API calls, still effective

### For Critical Areas
- `incident_cooldown = 30` (30 seconds)
- `analysis_interval = 3` (very frequent checks)
- **Why:** Maximum vigilance, willing to accept more alerts

## Testing the Fix

### 1. Run Diagnostic Script
```bash
python3 diagnose_duplicate_alerts.py
```

### 2. Monitor Logs During Video Analysis
Look for these key indicators:
- ✅ `📧 Sending NEW incident alert` - First detection
- ✅ `⏭️  Skipping duplicate incident alert` - Deduplication working
- ✅ `Time since last alert: X.Xs / 60s cooldown` - Cooldown tracking

### 3. Expected Behavior
- **First incident:** Email sent immediately
- **Same incident (< 60s):** Skipped with log message
- **New incident type:** Email sent (different signature)
- **After cooldown:** Email sent for similar incident

## Files Modified

1. **video_analyzer.py**
   - Added: `last_incident_time`, `incident_cooldown`, `last_incident_hash`
   - Modified: `_analyze_frames_async()` with deduplication logic
   - Lines: 96-99 (initialization), 431-452 (deduplication check)

2. **multi_source_video_analyzer.py**
   - Added: Dictionary-based tracking for multiple sources
   - Modified: `_handle_security_incident()` with per-source deduplication
   - Lines: 186-189 (initialization), 628-649 (deduplication check)

3. **diagnose_duplicate_alerts.py** (NEW)
   - Diagnostic tool to identify configuration issues
   - Example usage and recommendations

4. **DUPLICATE_EMAIL_FIX.md** (THIS FILE)
   - Complete documentation of the fix

## FAQ

### Q: What if I want immediate re-alerts?
**A:** Set `analyzer.incident_cooldown = 0` to disable deduplication.

### Q: What if I have different incidents happening simultaneously?
**A:** Deduplication uses incident signature (type + analysis). Different incidents have different signatures and will send separate alerts.

### Q: Can I adjust cooldown per incident type?
**A:** Current implementation uses a single cooldown. To customize per-type, modify the signature comparison logic.

### Q: Will this miss legitimate incidents?
**A:** No. Only duplicate detections of the same ongoing incident are filtered. New incidents always trigger alerts.

### Q: How do I verify it's working?
**A:** Check logs for "⏭️  Skipping duplicate" messages. If you see these, deduplication is active.

## Troubleshooting

### Still Getting Duplicates?
1. **Check if multiple instances running:** `ps aux | grep video_analyzer`
2. **Check configuration:** Ensure RTSP stream isn't added twice
3. **Check cooldown value:** Verify `analyzer.incident_cooldown > 0`
4. **Check logs:** Look for "Skipping duplicate" messages

### Not Getting Any Alerts?
1. **Check cooldown isn't too long:** Try `analyzer.incident_cooldown = 30`
2. **Check analysis interval:** Try `analyzer.analysis_interval = 5`
3. **Check email configuration:** Verify SMTP settings
4. **Check AI detection:** Review Gemini API responses

## Summary

✅ **Fixed:** Duplicate email alerts by adding intelligent incident deduplication  
✅ **Default:** 60-second cooldown prevents re-alerting for same incident  
✅ **Flexible:** Configurable cooldown and analysis intervals  
✅ **Smart:** Tracks incident signatures, not just timestamps  
✅ **Multi-source aware:** Independent tracking per camera/group  
✅ **Observable:** Clear logging of skipped duplicates  

**Result:** 3 emails → 1 email per unique incident
