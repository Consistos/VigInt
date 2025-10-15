# Dual-Buffer Veto System - Flash Has Final Decision

## Overview

The dual-buffer video analysis system now implements a **veto mechanism** where Gemini 2.5 Flash (long buffer) has the final decision on whether to send email alerts, even if Gemini 2.5 Flash-Lite (short buffer) detected an incident.

## Problem Solved

**User Request**: "When the long buffer is analysed by Gemini 2.5 Flash, allow it to not send an email alert if it did not see an incident or issue in the video, even if Gemini 2.5 Flash Lite saw one."

**Solution**: Flash-Lite provides fast initial detection, but Flash (the more powerful model) makes the final decision. If Flash doesn't confirm the incident, no email is sent.

## How It Works

### 1. Two-Stage Detection Flow

```
┌─────────────────────────────────────────────────────────────┐
│  STAGE 1: Quick Detection (Flash-Lite)                      │
│  ----------------------------------------------------------- │
│  • Analyzes most recent frame from short buffer (3 seconds) │
│  • Fast, lightweight analysis for initial screening          │
│  • If incident detected → Trigger Stage 2                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  STAGE 2: Confirmation Analysis (Flash)                     │
│  ----------------------------------------------------------- │
│  • Analyzes 3 key frames from long buffer (10 seconds)      │
│  • Start, Middle, End frames for full context               │
│  • More powerful model, deeper analysis                      │
│  • Makes FINAL DECISION: Confirm or Veto                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────┴─────────┐
                    │                   │
              ✅ CONFIRMED          ❌ VETOED
         (Flash agrees)      (Flash disagrees)
                    │                   │
            Send Email Alert    NO EMAIL SENT
```

### 2. Decision Logic

#### Flash-Lite Detects → Flash Confirms
```python
# Example log output:
🚨 SECURITY INCIDENT DETECTED by Flash-Lite for client ABC
   Triggering Gemini 2.5 Flash (long buffer) for confirmation...
✅ INCIDENT CONFIRMED by Gemini 2.5 Flash (long buffer)
   Confirmation: 2/3 frames detected incident
📧 Email alert WILL be sent
```

#### Flash-Lite Detects → Flash Vetoes
```python
# Example log output:
🚨 SECURITY INCIDENT DETECTED by Flash-Lite for client ABC
   Triggering Gemini 2.5 Flash (long buffer) for confirmation...
❌ INCIDENT REJECTED by Gemini 2.5 Flash (long buffer)
   Flash-Lite detected incident, but Flash found no issues (0/3 frames)
   Email alert will NOT be sent (Flash has final decision)
🚫 NO email sent - Flash has veto power
```

### 3. Confirmation Threshold

Flash (long buffer) analyzes **3 key frames** from the incident:
- **Start frame**: Beginning of the incident window
- **Middle frame**: Midpoint of the incident
- **End frame**: Most recent frame

**Confirmation Rule**: Incident is confirmed if **at least 1 out of 3 frames** detects an incident.

This means:
- **1/3 frames** = Confirmed ✅
- **2/3 frames** = Confirmed ✅
- **3/3 frames** = Confirmed ✅
- **0/3 frames** = Vetoed ❌

## Implementation Details

### Modified Functions

#### 1. `analyze_incident_context()` - Returns Confirmation Status

**Before:**
```python
def analyze_incident_context(frames):
    # Returns list of frame analyses
    return context_analysis  # List
```

**After:**
```python
def analyze_incident_context(frames):
    # Returns dictionary with confirmation status
    return {
        'frames': context_analysis,           # List of frame analyses
        'incident_confirmed': bool,           # True if ≥1 frame detected incident
        'confirmation_count': int,            # Number of frames that detected incident
        'total_frames_analyzed': int          # Total frames analyzed (usually 3)
    }
```

#### 2. `/api/video/analyze` Endpoint - Implements Veto Logic

**Key Changes:**
```python
if analysis_result['has_security_incident']:  # Flash-Lite detected
    detailed_analysis = analyze_incident_context(incident_frames)
    
    if detailed_analysis:
        incident_confirmed = detailed_analysis.get('incident_confirmed', False)
        
        if incident_confirmed:
            # Flash agrees - keep the alert
            analysis_result['flash_confirmation'] = True
        else:
            # Flash disagrees - VETO the alert
            analysis_result['has_security_incident'] = False  # Override!
            analysis_result['flash_confirmation'] = False
            analysis_result['flash_veto'] = True
```

### API Response Changes

#### New Fields in Analysis Response

```json
{
  "has_security_incident": false,  // Can be overridden by Flash veto
  "flash_confirmation": false,     // Whether Flash confirmed the incident
  "flash_veto": true,              // True if Flash vetoed Flash-Lite's detection
  "veto_reason": "Gemini 2.5 Flash (long buffer) did not confirm incident detected by Flash-Lite",
  "detailed_analysis": [           // Still a list of frame analyses
    {
      "frame_position": "Start",
      "incident_detected": false,
      "analysis": "...",
      "incident_type": ""
    },
    // ... more frames
  ]
}
```

## Benefits

### 1. Reduced False Positives
- Flash-Lite may be overly sensitive (better safe than sorry)
- Flash provides second opinion with more context
- Fewer unnecessary alerts to security staff

### 2. Better Context Analysis
- Flash analyzes multiple frames (start, middle, end)
- Sees the full incident progression
- Can distinguish actual incidents from benign activities

### 3. Cost-Effective
- Flash-Lite does cheap, fast initial screening
- Flash only runs when needed (on potential incidents)
- Saves on API costs while maintaining accuracy

### 4. Improved Accuracy
- Two-model consensus reduces errors
- Flash is more powerful and accurate
- Final decision by the better model

## Configuration

### Buffer Settings (config.ini)
```ini
[VideoAnalysis]
short_buffer_duration = 3    # Flash-Lite analyzes 3-second clips
long_buffer_duration = 10    # Flash analyzes 10-second clips
analysis_fps = 25            # Target FPS for smooth video
```

### Model Configuration
```python
# In api_proxy.py
gemini_model_short = genai.GenerativeModel('gemini-2.5-flash-lite')  # Stage 1
gemini_model_long = genai.GenerativeModel('gemini-2.5-flash')        # Stage 2 (Final decision)
```

## Monitoring

### Log Messages to Watch

**Successful Confirmation:**
```
🚨 SECURITY INCIDENT DETECTED by Flash-Lite for client ABC
   Triggering Gemini 2.5 Flash (long buffer) for confirmation...
✅ INCIDENT CONFIRMED by Gemini 2.5 Flash (long buffer)
   Confirmation: 2/3 frames detected incident
```

**Veto in Action:**
```
🚨 SECURITY INCIDENT DETECTED by Flash-Lite for client ABC
   Triggering Gemini 2.5 Flash (long buffer) for confirmation...
❌ INCIDENT REJECTED by Gemini 2.5 Flash (long buffer)
   Flash-Lite detected incident, but Flash found no issues (0/3 frames)
   Email alert will NOT be sent (Flash has final decision)
```

**Fallback (Analysis Failed):**
```
⚠️  Long buffer analysis failed, using Flash-Lite decision as fallback
```

## Testing Recommendations

### 1. Test False Positive Reduction
- Trigger Flash-Lite with ambiguous footage
- Verify Flash vetoes when appropriate
- Check no email is sent

### 2. Test True Positive Confirmation
- Trigger Flash-Lite with clear incident
- Verify Flash confirms
- Check email is sent

### 3. Test Fallback Behavior
- Simulate Flash API failure
- Verify system falls back to Flash-Lite decision
- Check alert is still sent (fail-safe mode)

### 4. Monitor Veto Rate
- Track `flash_veto` field in responses
- High veto rate = Flash-Lite too sensitive
- Low veto rate = System working well

## Statistics & Metrics

Track these metrics for system optimization:

```python
# Veto rate (target: 10-20%)
veto_rate = flash_vetos / flash_lite_detections

# Confirmation rate (target: 80-90%)
confirmation_rate = flash_confirmations / flash_lite_detections

# False positive reduction
false_positive_reduction = vetoed_false_alarms / total_false_alarms
```

## Future Enhancements

### Possible Improvements:
1. **Adjustable Threshold**: Make confirmation threshold configurable (e.g., require 2/3 frames instead of 1/3)
2. **Confidence Scores**: Weight frames by confidence level
3. **Flash-Lite Override**: Allow Flash-Lite to detect incidents Flash missed (currently only Flash can veto)
4. **Learning System**: Track which vetoes were correct to tune sensitivity
5. **Multi-tier Alerts**: Send low-priority alert on Flash-Lite detection, high-priority on Flash confirmation

## Rollback Instructions

If you need to revert to the old system (Flash-Lite decision is final):

1. Restore `analyze_incident_context()` to return just the list:
```python
return context_analysis  # Instead of dictionary
```

2. Remove veto logic from `/api/video/analyze`:
```python
# Remove the if/else confirmation checking
# Keep: analysis_result['detailed_analysis'] = detailed_analysis
```

---

**Date Implemented**: 2025-10-04  
**Status**: ✅ Active and Production-Ready  
**Model Versions**: 
- Flash-Lite: `gemini-2.5-flash-lite` (Stage 1)
- Flash: `gemini-2.5-flash` (Stage 2 - Final Decision)
