# Multi-Source Video Analyzer - API Integration

## Overview

The `multi_source_video_analyzer.py` has been refactored to use the **api_proxy.py dual-buffer system** instead of directly calling Gemini AI. This provides:

- ✅ **Consistent analysis logic** across single and multi-source analysis
- ✅ **Dual-buffer system** with Flash-Lite → Flash confirmation
- ✅ **Veto power** where Flash has final decision on alerts
- ✅ **Cost optimization** with Flash-Lite for screening
- ✅ **Centralized configuration** and model management

## Architecture Changes

### Before (Direct Gemini)
```
multi_source_video_analyzer.py
    ↓
Directly calls Gemini API
    ↓
Email alert sent
```

### After (API-Based)
```
multi_source_video_analyzer.py
    ↓
Sends frames to api_proxy.py
    ↓
Stage 1: Flash-Lite (3s buffer)
    ↓ (if incident detected)
Stage 2: Flash (10s buffer) - FINAL DECISION
    ↓ (if Flash confirms)
Email alert sent
```

## Key Changes

### 1. New API Endpoints in `api_proxy.py`

#### `/api/video/multi-source/buffer`
- Receives frames from video sources
- Maintains per-source buffers
- Thread-safe buffer management

#### `/api/video/multi-source/analyze`
- Analyzes multiple sources simultaneously
- Uses dual-buffer logic per source
- Returns Flash-Lite and Flash results
- Includes veto information

### 2. Refactored `multi_source_video_analyzer.py`

**Removed:**
- Direct Gemini API calls
- `google.generativeai` import
- Model initialization code
- Direct prompt management

**Added:**
- API client functionality with `requests`
- Continuous buffer thread
- API-based analysis loop
- Flash confirmation handling

**Key Changes:**
- `analysis_interval` now defaults to 3 seconds (short buffer cycle)
- Two threads: buffer thread (continuous) + analysis thread (periodic)
- Incidents only trigger alerts if Flash confirms

### 3. Buffer Management Functions

```python
get_multi_source_buffer(client_id, source_id)
get_all_client_sources(client_id)
```

These manage per-source, per-client frame buffers in the API.

## Configuration

### Environment Variables
```bash
# Required for multi_source_video_analyzer.py
export VIGINT_API_KEY=your_vigint_api_key

# Required for api_proxy.py
export GOOGLE_API_KEY=your_gemini_api_key
```

### Command Line Arguments
```bash
python multi_source_video_analyzer.py \
  --sources rtsp://cam1 rtsp://cam2 \
  --names "Camera 1" "Camera 2" \
  --interval 3 \
  --api-key your_vigint_key \
  --api-url http://localhost:5000
```

## Usage Examples

### 1. Start API Proxy
```bash
# Terminal 1: Start the API proxy
python api_proxy.py
```

### 2. Run Multi-Source Analyzer
```bash
# Terminal 2: Start multi-source analysis
export VIGINT_API_KEY=your_key
python multi_source_video_analyzer.py \
  --sources video1.mp4 video2.mp4 video3.mp4 \
  --names "Entrance" "Checkout" "Aisle 1" \
  --interval 3
```

### 3. Programmatic Usage
```python
from multi_source_video_analyzer import MultiSourceVideoAnalyzer

# Create analyzer with API connection
analyzer = MultiSourceVideoAnalyzer(
    api_key='your_vigint_api_key',
    api_url='http://localhost:5000'
)

# Add sources
analyzer.add_video_source("cam1", "rtsp://camera1/stream", "Front Door")
analyzer.add_video_source("cam2", "rtsp://camera2/stream", "Back Door")

# Start analysis (begins dual-buffer flow)
analyzer.start_analysis()

# Analysis runs with:
# - Continuous frame buffering to API
# - Flash-Lite screening every 3 seconds
# - Flash confirmation on detections
# - Email only if Flash confirms
```

## Dual-Buffer Flow

### Stage 1: Flash-Lite Screening (Every 3 seconds)
1. Multi-source analyzer sends frames continuously to API buffer
2. Every 3 seconds, API analyzes latest frame with Flash-Lite
3. If incident detected → Trigger Stage 2
4. If no incident → Continue monitoring

### Stage 2: Flash Confirmation (On Detection)
1. API retrieves long buffer (10 seconds of frames)
2. Analyzes 3 key frames with Flash (more powerful model)
3. Flash makes **FINAL DECISION**: Confirm or Veto

### Decision Outcomes

**Flash Confirms (≥1/3 frames detect incident):**
```
🚨 Flash-Lite Detection → ✅ Flash Confirmation → 📧 Email Sent
```

**Flash Vetoes (0/3 frames detect incident):**
```
🚨 Flash-Lite Detection → ❌ Flash Veto → 🚫 NO Email
```

## Benefits

### 1. Reduced False Positives
- Flash-Lite may be overly sensitive
- Flash provides authoritative second opinion
- Fewer unnecessary alerts

### 2. Cost Optimization
- Flash-Lite: Cheap, fast screening
- Flash: Only runs on potential incidents
- Significant API cost savings

### 3. Consistency
- Same analysis logic across all video analysis
- Single point of configuration
- Unified prompt management

### 4. Maintainability
- Centralized model configuration in api_proxy.py
- Easier to update models or prompts
- Better separation of concerns

### 5. Scalability
- Multi-source analyzer can be deployed separately
- API handles multiple clients
- Load balancing possible

## API Response Format

```json
{
  "client_name": "Test Client",
  "timestamp": "2025-10-07T13:30:00",
  "sources_analyzed": 3,
  "sources": {
    "cam1": {
      "has_security_incident": true,
      "flash_confirmation": true,
      "incident_type": "shoplifting",
      "analysis": "Detailed analysis...",
      "detailed_analysis": [...],
      "incident_frames": [...],
      "source_name": "Front Door"
    },
    "cam2": {
      "has_security_incident": false,
      "flash_veto": true,
      "flash_confirmation": false,
      "veto_reason": "Gemini 2.5 Flash did not confirm incident"
    }
  },
  "summary": {
    "total_incidents_detected_by_flash_lite": 2,
    "total_incidents_confirmed_by_flash": 1,
    "total_incidents_vetoed": 1,
    "has_any_confirmed_incident": true
  }
}
```

## Monitoring

### Log Messages

**Flash-Lite Detection:**
```
🚨 INCIDENT DETECTED by Flash-Lite for source 'Front Door' (client: Test)
   Triggering Gemini 2.5 Flash (long buffer) for confirmation...
```

**Flash Confirmation:**
```
✅ INCIDENT CONFIRMED by Flash for source 'Front Door'
   Confirmation: 2/3 frames detected incident
```

**Flash Veto:**
```
❌ INCIDENT REJECTED by Flash for source 'Front Door'
   Flash found no issues (0/3 frames)
```

**Summary:**
```
Analysis complete:
  - Flash-Lite detections: 2
  - Flash confirmations: 1
  - Flash vetoes: 1
```

## Migration Guide

### For Existing Deployments

1. **Update api_proxy.py** (already includes new endpoints)
2. **Update multi_source_video_analyzer.py** (already refactored)
3. **Set environment variables:**
   ```bash
   export VIGINT_API_KEY=your_key
   export GOOGLE_API_KEY=your_gemini_key
   ```
4. **Start API proxy first:**
   ```bash
   python api_proxy.py
   ```
5. **Run multi-source analyzer:**
   ```bash
   python multi_source_video_analyzer.py --sources ... --names ...
   ```

### Backward Compatibility

The old direct Gemini code is commented out in `multi_source_video_analyzer.py` for reference but is no longer executed. The `_analyze_individual_source` method now returns `None` and logs a deprecation warning.

## Testing

### 1. Test API Connection
```bash
# Check API is responding
curl -H "X-API-Key: your_key" http://localhost:5000/api/health
```

### 2. Test Buffer Endpoint
```bash
curl -X POST http://localhost:5000/api/video/multi-source/buffer \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{"source_id": "test", "source_name": "Test", "frame_data": "base64...", "frame_count": 1}'
```

### 3. Test Analysis Endpoint
```bash
curl -X POST http://localhost:5000/api/video/multi-source/analyze \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{"source_ids": ["cam1", "cam2"]}'
```

## Performance Metrics

### Expected Timings
- **Frame buffering**: ~50ms per frame (network overhead)
- **Flash-Lite analysis**: 1-2 seconds per source
- **Flash analysis**: 3-5 seconds (on detection)
- **Total incident confirmation**: 5-7 seconds from detection

### Resource Usage
- **API Proxy**: Handles Gemini calls and buffer management
- **Multi-Source Analyzer**: Lighter weight, just captures and sends frames
- **Network**: Continuous frame transmission (monitor bandwidth)

## Troubleshooting

### API Connection Failed
- Check API proxy is running
- Verify API URL is correct
- Check API key is valid
- Review network connectivity

### No Incidents Detected
- Check Flash-Lite is analyzing (should see logs every 3s)
- Verify frames are being buffered (check buffer endpoint)
- Review video content (might not contain incidents)

### Flash Always Vetoes
- Flash may need prompt tuning
- Check long buffer has sufficient frames (10 seconds)
- Review detailed_analysis in response for Flash reasoning

## Future Enhancements

1. **Batch Analysis**: Analyze multiple sources in parallel batches
2. **Adaptive Intervals**: Adjust analysis frequency based on activity
3. **Priority Sources**: Analyze high-priority sources more frequently
4. **Cross-Source Correlation**: Detect incidents spanning multiple cameras
5. **Real-time Streaming**: WebSocket for live analysis updates

---

**Date**: 2025-10-07  
**Status**: ✅ Implemented and Ready for Testing  
**Models Used**:
- Flash-Lite: `gemini-2.5-flash-lite` (Initial detection)
- Flash: `gemini-2.5-flash` (Final confirmation)
