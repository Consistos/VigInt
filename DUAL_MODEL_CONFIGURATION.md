# Dual Model Configuration for Dual-Buffer Video Analysis

## Overview

The Vigint video analysis system now uses **two different Gemini models** optimized for different purposes in the dual-buffer architecture:

- **Short Buffer**: Gemini 2.5 Flash-Lite - Fast, lightweight analysis for initial incident detection
- **Long Buffer**: Gemini 2.5 Flash - Detailed, comprehensive analysis for confirmed incidents

## Architecture

### Dual-Buffer System
1. **Short Buffer (3 seconds)**
   - Used for rapid, continuous monitoring
   - Analyzed frequently (every 3 seconds)
   - Uses **Gemini 2.5 Flash-Lite** for faster, cost-effective analysis
   - Purpose: Quick incident detection

2. **Long Buffer (10 seconds)**
   - Used for detailed evidence gathering
   - Activated only when short buffer detects an incident
   - Uses **Gemini 2.5 Flash** for comprehensive, detailed analysis
   - Purpose: In-depth context analysis and video evidence creation

## Model Configuration

### In `api_proxy.py`

```python
# Two separate model instances
gemini_model_short = genai.GenerativeModel('gemini-2.5-flash-lite')  # Short buffer: fast, lightweight
gemini_model_long = genai.GenerativeModel('gemini-2.5-flash')        # Long buffer: detailed analysis
```

### Model Selection Logic

The `analyze_frame_for_security()` function automatically selects the appropriate model:

```python
def analyze_frame_for_security(frame_base64, frame_count, buffer_type="short"):
    # Select appropriate model based on buffer type
    if buffer_type == "short":
        model = gemini_model_short  # Flash-Lite
    else:
        model = gemini_model_long   # Flash (Full)
```

### Detailed Analysis

The `analyze_incident_context()` function uses the long buffer model:

```python
def analyze_incident_context(frames):
    """Analyze longer buffer for detailed incident context"""
    if not frames or not gemini_model_long:
        return None
    # Uses gemini_model_long for detailed frame-by-frame analysis
```

## Benefits

1. **Cost Efficiency**: Flash-Lite is more cost-effective for frequent, continuous monitoring
2. **Performance**: Faster response times for initial incident detection with the lighter model
3. **Quality**: Full Flash model provides detailed, high-quality analysis when it matters most
4. **Scalability**: Reduced API costs and quota usage with smart model selection

## Model Specifications

### Gemini 2.5 Flash-Lite (Short Buffer)
- **Speed**: Very fast
- **Cost**: Lower per request
- **Use Case**: Continuous monitoring, quick incident detection
- **Frequency**: Every 3 seconds

### Gemini 2.5 Flash (Long Buffer)
- **Speed**: Fast
- **Quality**: Higher accuracy and detail
- **Use Case**: Detailed incident analysis, evidence gathering
- **Frequency**: Only on incident detection

## Configuration Changes

### Files Modified
- `/Users/david2/dev/Vigint/api_proxy.py`
  - Lines 45-59: Model initialization
  - Lines 557-566: Model selection in `analyze_frame_for_security()`
  - Line 606: Model usage for short buffer analysis
  - Line 1415: Model check for long buffer context
  - Line 1444: Model usage for detailed frame analysis

### No Configuration File Changes Required
The model selection is automatic based on the `buffer_type` parameter. No changes needed to `config.ini`.

## Testing Recommendations

1. **Verify Model Loading**: Check startup logs for confirmation message
2. **Test Short Buffer**: Ensure fast response times for continuous monitoring
3. **Test Long Buffer**: Verify detailed analysis quality on incident detection
4. **Monitor API Usage**: Track quota consumption and cost savings

## Rollback

To revert to single model configuration, restore the original `api_proxy.py` lines:

```python
gemini_model = genai.GenerativeModel('gemini-2.5-flash')
```

And update all references from `gemini_model_short`/`gemini_model_long` back to `gemini_model`.

---

**Date**: 2025-10-01  
**Status**: ✅ Implemented and Ready for Testing
