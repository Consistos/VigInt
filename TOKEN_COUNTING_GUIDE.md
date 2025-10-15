# Token Counting for RTSP Stream Analysis

## Overview

Vigint now tracks token usage for all Gemini API calls during RTSP stream analysis. This enables accurate billing, cost optimization, and usage analytics.

## Features

### ✅ Automatic Token Tracking
- **Real-time counting**: Tokens are counted for every Gemini API call
- **Detailed metrics**: Separate tracking for prompt tokens and completion tokens
- **Multi-source support**: Token tracking for both individual and aggregated camera analyses

### ✅ Database Integration
- Token counts stored in the `api_usage` table
- Fields: `prompt_tokens`, `completion_tokens`, `total_tokens`
- Available for historical analysis and reporting

### ✅ Billing Integration
- Token usage included in client invoices
- Cost calculation based on token consumption
- Integration with existing invoice generation system

## How It Works

### 1. Token Extraction

When the Gemini API is called for video analysis, the response includes usage metadata:

```python
response = model.generate_content([prompt, image_data])

# Extract token usage from response
if hasattr(response, 'usage_metadata'):
    prompt_tokens = response.usage_metadata.prompt_token_count
    completion_tokens = response.usage_metadata.candidates_token_count
    total_tokens = response.usage_metadata.total_token_count
```

### 2. Token Logging

Token usage is logged in real-time:

```
🔢 Token usage - Prompt: 1247, Completion: 89, Total: 1336
```

For multi-source analysis:
```
🔢 [Camera_1] Token usage - Prompt: 1247, Completion: 89, Total: 1336
🔢 [group_1] Token usage - Prompt: 2891, Completion: 156, Total: 3047
```

### 3. Data Storage

Token counts are included in analysis results:

```python
{
    'timestamp': '2025-10-03T10:54:18',
    'incident_detected': False,
    'analysis': '...',
    'token_usage': {
        'prompt_tokens': 1247,
        'completion_tokens': 89,
        'total_tokens': 1336
    }
}
```

## Setup

### 1. Run Database Migration

Add token tracking fields to the database:

```bash
python3 migrate_add_token_fields.py
```

This adds the following columns to `api_usage` table:
- `prompt_tokens` (INTEGER)
- `completion_tokens` (INTEGER)
- `total_tokens` (INTEGER)

### 2. Token Tracking is Automatic

Once migrated, token counting happens automatically:
- ✅ `video_analyzer.py` tracks tokens for single-source analysis
- ✅ `multi_source_video_analyzer.py` tracks tokens for multi-camera analysis
- ✅ Token data is logged and included in analysis results

### 3. View Token Usage

Run the example script to see token counting in action:

```bash
# Show features and examples
python3 example_token_counting.py

# Analyze a video with token tracking
python3 example_token_counting.py --video-path /path/to/video.mp4
```

## Usage Examples

### Single Video Analysis

```python
from video_analyzer import VideoAnalyzer

analyzer = VideoAnalyzer()
result = analyzer.analyze_frame(frame)

# Access token usage
if 'token_usage' in result:
    tokens = result['token_usage']
    print(f"Prompt tokens: {tokens['prompt_tokens']}")
    print(f"Completion tokens: {tokens['completion_tokens']}")
    print(f"Total tokens: {tokens['total_tokens']}")
```

### Multi-Source Analysis

```python
from multi_source_video_analyzer import MultiSourceVideoAnalyzer

analyzer = MultiSourceVideoAnalyzer()
analyzer.add_video_source('cam1', 'rtsp://camera1/stream', 'Camera 1')
analyzer.start_analysis()

# Token usage is automatically logged for each analysis
# Check logs for: 🔢 [Camera 1] Token usage - ...
```

### Query Token Usage from Database

```python
from vigint.models import APIUsage, db

# Get total tokens used today
from datetime import datetime, timedelta

today = datetime.utcnow().date()
total_tokens = db.session.query(
    func.sum(APIUsage.total_tokens)
).filter(
    APIUsage.timestamp >= today
).scalar()

print(f"Total tokens used today: {total_tokens}")

# Get token usage by endpoint
endpoint_tokens = db.session.query(
    APIUsage.endpoint,
    func.sum(APIUsage.total_tokens).label('tokens')
).group_by(APIUsage.endpoint).all()

for endpoint, tokens in endpoint_tokens:
    print(f"{endpoint}: {tokens} tokens")
```

## Cost Calculation

### Gemini API Pricing (Example)

Check current pricing at: https://ai.google.dev/pricing

Example rates (as of 2024):
- Prompt tokens: $0.125 per 1M tokens
- Completion tokens: $0.375 per 1M tokens

### Calculate Costs

```python
def calculate_token_cost(prompt_tokens, completion_tokens):
    """Calculate cost based on token usage"""
    PROMPT_COST_PER_1K = 0.000125  # $0.125 per 1M tokens
    COMPLETION_COST_PER_1K = 0.000375  # $0.375 per 1M tokens
    
    prompt_cost = (prompt_tokens / 1000) * PROMPT_COST_PER_1K
    completion_cost = (completion_tokens / 1000) * COMPLETION_COST_PER_1K
    
    return prompt_cost + completion_cost

# Example
cost = calculate_token_cost(1247, 89)
print(f"Cost: ${cost:.6f}")  # Cost: $0.000189
```

## Integration with Billing System

Token usage is automatically integrated with the existing billing system:

### 1. Token Tracking in APIUsage

```python
# When recording API usage, include tokens
usage = APIUsage(
    api_key_id=api_key.id,
    endpoint='/analyze/video',
    method='POST',
    status_code=200,
    cost=calculated_cost,
    prompt_tokens=token_usage['prompt_tokens'],
    completion_tokens=token_usage['completion_tokens'],
    total_tokens=token_usage['total_tokens']
)
db.session.add(usage)
db.session.commit()
```

### 2. Include in Invoices

The invoice generator can now include token statistics:

```python
# In billing_manager.py or invoice_generator.py
def calculate_client_usage(api_key_id, start_date, end_date):
    # Query includes token counts
    token_stats = db.session.query(
        func.sum(APIUsage.prompt_tokens).label('prompt_tokens'),
        func.sum(APIUsage.completion_tokens).label('completion_tokens'),
        func.sum(APIUsage.total_tokens).label('total_tokens')
    ).filter(
        APIUsage.api_key_id == api_key_id,
        APIUsage.timestamp >= start_date,
        APIUsage.timestamp <= end_date
    ).first()
    
    return {
        'request_count': ...,
        'total_cost': ...,
        'prompt_tokens': token_stats.prompt_tokens or 0,
        'completion_tokens': token_stats.completion_tokens or 0,
        'total_tokens': token_stats.total_tokens or 0
    }
```

## Optimization Tips

### 1. Reduce Prompt Tokens
- Use concise prompts
- Remove unnecessary instructions
- Cache common prompt components

### 2. Monitor Token Usage
- Track tokens per analysis
- Identify high-usage scenarios
- Adjust analysis frequency if needed

### 3. Optimize Analysis Intervals
- Increase interval between analyses
- Balance security coverage with cost
- Adjust based on activity patterns

### 4. Use Multi-Source Aggregation
- Analyze 4 cameras together when possible
- Reduces total API calls
- More cost-effective for multiple cameras

## Monitoring and Alerts

### Real-Time Monitoring

Token usage is logged for every analysis:

```
2025-10-03 10:54:18 - INFO - 🔢 Token usage - Prompt: 1247, Completion: 89, Total: 1336
```

### Daily Reports

Query token usage for reports:

```python
def generate_daily_token_report():
    """Generate daily token usage report"""
    today = datetime.utcnow().date()
    
    stats = db.session.query(
        func.sum(APIUsage.prompt_tokens).label('prompt_tokens'),
        func.sum(APIUsage.completion_tokens).label('completion_tokens'),
        func.sum(APIUsage.total_tokens).label('total_tokens'),
        func.count(APIUsage.id).label('api_calls')
    ).filter(
        APIUsage.timestamp >= today
    ).first()
    
    return {
        'date': today.isoformat(),
        'api_calls': stats.api_calls,
        'prompt_tokens': stats.prompt_tokens or 0,
        'completion_tokens': stats.completion_tokens or 0,
        'total_tokens': stats.total_tokens or 0,
        'estimated_cost': calculate_token_cost(
            stats.prompt_tokens or 0,
            stats.completion_tokens or 0
        )
    }
```

## Troubleshooting

### Token counts are 0

**Cause**: The Gemini API response doesn't include usage_metadata

**Solution**: 
- Check API key permissions
- Verify you're using a supported model
- Check logs for warnings about token extraction

### Migration fails

**Cause**: Database connection or permission issues

**Solution**:
```bash
# Check database connection
python3 -c "from config import config; print(config.database_url)"

# Run migration with verbose output
python3 migrate_add_token_fields.py
```

### Token usage not appearing in logs

**Cause**: Logging level too high

**Solution**:
```python
# In your config or script
import logging
logging.basicConfig(level=logging.INFO)
```

## API Reference

### Token Usage Structure

```python
token_usage = {
    'prompt_tokens': int,      # Tokens in the prompt
    'completion_tokens': int,  # Tokens in the response
    'total_tokens': int        # Sum of prompt + completion
}
```

### Analysis Result with Tokens

```python
analysis_result = {
    'timestamp': str,           # ISO format timestamp
    'frame_count': int,         # Frame number
    'analysis': str,            # AI analysis text
    'incident_detected': bool,  # Whether incident was detected
    'incident_type': str,       # Type of incident
    'frame_shape': tuple,       # Frame dimensions
    'token_usage': {            # Token usage for this analysis
        'prompt_tokens': int,
        'completion_tokens': int,
        'total_tokens': int
    }
}
```

## Related Documentation

- [README_BILLING.md](README_BILLING.md) - Billing system documentation
- [README_API_KEYS.md](README_API_KEYS.md) - API key management
- [README_VIDEO_ANALYSIS.md](README_VIDEO_ANALYSIS.md) - Video analysis guide
- [README_RTSP.md](README_RTSP.md) - RTSP streaming setup

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review example scripts in the repository
3. Check logs for detailed error messages
4. Verify database migration completed successfully

---

**Last Updated**: 2025-10-03
**Version**: 1.0.0
