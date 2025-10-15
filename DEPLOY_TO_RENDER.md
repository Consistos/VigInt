# Force Deploy to Render

## Your code is committed and pushed! ✅

Commit: `1b68589 - Add distributed mode with model fallbacks`

## If Render hasn't auto-deployed:

### Via Dashboard (Quick):
1. Go to: https://dashboard.render.com
2. Click: **vigint-api-server**
3. Click: **Manual Deploy** → **Deploy latest commit**
4. Wait 2-3 minutes

### Via CLI:
```bash
# Install Render CLI if needed
brew install render

# Deploy
render deploy --service vigint-api-server
```

## After Deployment (2-3 min wait):

Test again:
```bash
python3 test_distributed_mode.py
```

**Expected:**
✅ Analysis successful (via server, not mock)
✅ No 500 errors

## Check Logs if Still Failing:

1. Dashboard → vigint-api-server → **Logs**
2. Look for:
   - "✅ Gemini short buffer model initialized: [model-name]"
   - Any errors during startup
   
## Common Issues:

**If logs show "Gemini API key not configured":**
- Environment tab → verify `GOOGLE_API_KEY` is set

**If logs show "Failed to load model X":**
- Gemini API issue or model names changed
- Server will try fallback models automatically

**If logs show database errors:**
- Check `vigint-db` is running
- Environment → verify `DATABASE_URL` is set
