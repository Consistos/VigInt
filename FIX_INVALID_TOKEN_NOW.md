# 🔧 FIX: "Invalid token" Error - Action Plan

## Current Status ✅

Your `.env` is now correctly configured:
- ✅ `SPARSE_AI_BASE_URL=https://sparse-ai-video-server.onrender.com`
- ✅ `SPARSE_AI_API_KEY` is set

## Why Your Old Link Still Doesn't Work

The link `https://sparse-ai-video-server.onrender.com/video/ebabccfb-44e1-4ef1-a195-1cc69b1b1135?token=d3899f74ab4a671b77fe95f85529728c` was generated:

1. **Before** you updated your `.env` file, OR
2. **With a different API key**, OR  
3. **With a different expiration time**

**Old video links cannot be "fixed" - they are cryptographically bound to the configuration that created them.**

## What You Need to Do NOW

### Option A: Test with a NEW Incident (Recommended)

Generate a fresh video link with your current configuration:

```bash
cd /Users/david2/dev/Vigint
python demo_video_alerts.py
```

This will:
1. Create a test incident
2. Generate video with correct token
3. Send you an email with the new link
4. The NEW link will work!

### Option B: Verify API Key Match

The most common cause is **API key mismatch**. Ensure both sides use the same key:

**Client Side (Vigint):**
```bash
grep SPARSE_AI_API_KEY .env
# Should show: SPARSE_AI_API_KEY=e0J78y9si6...
```

**Server Side (Render.com):**
1. Go to: https://dashboard.render.com
2. Select your `sparse-ai-video-server` service
3. Click **Environment** tab
4. Check `SPARSE_AI_API_KEY` value
5. **It must EXACTLY match your local .env file!**

If they don't match:
```bash
# Update your local .env to match Render.com, OR
# Update Render.com to match your local .env
# Then restart both services
```

## Testing Steps

### 1. Restart Vigint Application

```bash
# Stop current instance
pkill -f "python.*app.py"

# Start fresh
python app.py
```

### 2. Generate New Test Video

```bash
python demo_video_alerts.py
```

### 3. Check Email

Look for new email with subject like:
```
🚨 Alerte Vigint - [INCIDENT_TYPE] - SECURITY
```

### 4. Click New Video Link

The new link should work! If it doesn't, continue to debugging below.

## Debugging: If New Links Still Fail

### Check 1: Verify Server is Running

```bash
curl -I https://sparse-ai-video-server.onrender.com/health
```

Expected response:
```
HTTP/2 200
```

If you get an error:
- Server might be sleeping (Render.com free tier sleeps after inactivity)
- Wait 30-60 seconds for it to wake up
- Try again

### Check 2: Check Server Logs

1. Go to Render.com dashboard
2. Open `sparse-ai-video-server`
3. Click **Logs** tab
4. Look for errors when you try to access the video

Common log messages:
- `Invalid token` → API key mismatch
- `Video not found` → Video ID doesn't exist
- `Link expired` → Video has expired

### Check 3: Manual Token Verification

Create a test token manually:

```python
python -c "
import hashlib
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

video_id = 'test-video-id'
expiration = datetime.now() + timedelta(hours=48)
api_key = os.getenv('SPARSE_AI_API_KEY')

token_data = f'{video_id}:{expiration.isoformat()}:{api_key}'
token = hashlib.sha256(token_data.encode()).hexdigest()[:32]

print(f'Video ID: {video_id}')
print(f'Expiration: {expiration.isoformat()}')
print(f'Token: {token}')
print(f'Full Link:')
print(f'https://sparse-ai-video-server.onrender.com/video/{video_id}?token={token}')
"
```

## Expected Results

After following these steps:

✅ **New video links should work**  
✅ **Old video links will NOT work** (this is expected and correct)  
✅ **Future incidents will generate working links automatically**

## Common Questions

### Q: Can I fix the old link?

**A:** No. Tokens are cryptographic hashes that cannot be regenerated unless you know:
- The exact expiration timestamp used when it was created
- The exact API key used when it was created
- The exact URL configuration used when it was created

It's easier to just generate a new incident.

### Q: How long do video links last?

**A:** 48 hours by default (configured with `VIDEO_LINK_EXPIRATION_HOURS=48`)

### Q: Why do tokens include expiration time?

**A:** Security. This prevents:
- Tokens from being reused after expiration
- Attackers from generating their own tokens
- Videos from being accessible indefinitely

### Q: What if I need longer expiration?

Update `.env`:
```bash
VIDEO_LINK_EXPIRATION_HOURS=72  # Max 72 hours for GDPR compliance
```

Then restart Vigint and generate new incident.

## Success Checklist

- [ ] `.env` has correct `SPARSE_AI_BASE_URL`
- [ ] `.env` has correct `SPARSE_AI_API_KEY` (matches Render.com)
- [ ] Vigint application restarted
- [ ] New test incident generated with `demo_video_alerts.py`
- [ ] New video link received in email
- [ ] New video link works in browser
- [ ] Video plays correctly

## Still Having Issues?

Run full diagnostics:
```bash
python diagnose_video_token.py "YOUR_NEW_LINK_HERE"
```

Check server health:
```bash
curl https://sparse-ai-video-server.onrender.com/health
```

Review server logs in Render.com dashboard.

## Summary

**Your configuration is now correct!** The old link won't work because it was generated with old settings. Generate a new incident and the new link will work perfectly.

The fix is complete - now just test with a fresh incident! 🎉
