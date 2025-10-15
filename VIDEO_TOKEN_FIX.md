# Fix: "Forbidden. Invalid token" Error

## Problem

When clicking video links in alert emails, you see:
```
Forbidden. Invalid token
```

## Root Cause

**URL mismatch** between token generation and video server validation.

Your video link uses: `https://sparse-ai-video-server.onrender.com`  
But your `.env` was configured for: `https://sparse-ai.com` (or default)

### Why Tokens Fail

Tokens are generated using a hash of:
```python
SHA256(video_id + expiration_time + api_key)
```

When the URL in your `.env` doesn't match the actual server URL, the token validation fails because the server expects tokens generated with its own URL.

## Solution

### Step 1: Update Your .env File

Edit your `.env` file and set:
```bash
SPARSE_AI_BASE_URL=https://sparse-ai-video-server.onrender.com
```

**Important**: Use the EXACT URL from your video links!

### Step 2: Restart Vigint

Stop and restart your Vigint application to pick up the new configuration:
```bash
# If running with Python
pkill -f "python.*app.py"
python app.py

# If running with Docker
docker-compose restart

# If running with Make
make restart
```

### Step 3: Test with New Incident

Old video links will NOT work with the new configuration (they were generated with the old URL).

Trigger a new test incident to generate a new video link:
```bash
python demo_video_alerts.py
```

## Verification

### Use the Diagnostic Tool

Run the diagnostic tool with your problematic link:
```bash
python diagnose_video_token.py "https://sparse-ai-video-server.onrender.com/video/ebabccfb-44e1-4ef1-a195-1cc69b1b1135?token=d3899f74ab4a671b77fe95f85529728c"
```

The tool will:
- ✅ Check your environment configuration
- ✅ Identify URL mismatches
- ✅ Provide specific fix recommendations
- ✅ Generate sample tokens for testing

### Manual Verification

1. **Check .env file**:
   ```bash
   grep SPARSE_AI_BASE_URL .env
   ```
   Should show: `SPARSE_AI_BASE_URL=https://sparse-ai-video-server.onrender.com`

2. **Verify in Python**:
   ```bash
   python -c "
   from video_link_service import VideoLinkService
   service = VideoLinkService()
   print(f'Base URL: {service.base_url}')
   print(f'Expected: https://sparse-ai-video-server.onrender.com')
   "
   ```

3. **Test new alert**:
   ```bash
   python demo_video_alerts.py
   ```
   Check that the generated link uses the correct URL.

## Common Mistakes

### ❌ Wrong: Using the default URL
```bash
SPARSE_AI_BASE_URL=https://sparse-ai.com
```

### ❌ Wrong: Using localhost
```bash
SPARSE_AI_BASE_URL=http://127.0.0.1:9999
```

### ✅ Correct: Using actual Render.com deployment
```bash
SPARSE_AI_BASE_URL=https://sparse-ai-video-server.onrender.com
```

## Why Old Links Won't Work

Once you change the `SPARSE_AI_BASE_URL`:
- **Old tokens** were generated with the old URL
- **New validation** uses the new URL
- **Hashes don't match** → Invalid token

**Solution**: Only new incidents will generate working links.

## API Key Reminder

Make sure your `SPARSE_AI_API_KEY` in `.env` matches the one configured on your Render.com deployment!

Check Render.com dashboard → Your Service → Environment → `SPARSE_AI_API_KEY`

## Quick Fix Checklist

- [ ] Update `.env` with correct `SPARSE_AI_BASE_URL`
- [ ] Verify `SPARSE_AI_API_KEY` matches server
- [ ] Restart Vigint application
- [ ] Run diagnostic tool to verify
- [ ] Trigger new test incident
- [ ] Click new video link to confirm it works

## Need Help?

Run the diagnostic tool for detailed analysis:
```bash
python diagnose_video_token.py "YOUR_PROBLEMATIC_LINK_HERE"
```

The tool will identify the exact issue and provide specific fixes.
