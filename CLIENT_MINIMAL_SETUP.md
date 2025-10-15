# Minimal Client Setup Guide

## The Absolute Minimum

Clients need **ONE file**:

```
project/
└── .env
    └── VIGINT_API_KEY=your-key-here
```

That's it!

---

## Quick Setup

### Step 1: Create .env
```bash
cat > .env << EOF
VIGINT_API_KEY=paste-your-key-here
EOF
```

### Step 2: Run
```bash
python vigint/app.py --api-url https://your-vigint-server.com:5002
```

Done!

---

## What Clients DON'T Need

### ❌ config.ini
The client code now uses built-in defaults:
- Short buffer: 3 seconds
- Long buffer: 10 seconds  
- Analysis FPS: 25
- Video format: MP4

These match the server configuration automatically.

### ❌ Server Credentials
No need for:
- GOOGLE_API_KEY
- SPARSE_AI_API_KEY
- SECRET_KEY
- EMAIL_PASSWORD
- Database credentials

All handled by the server!

---

## Files Breakdown

| File | Client Needs? | Server Needs? | Purpose |
|------|---------------|---------------|---------|
| `.env` with `VIGINT_API_KEY` | ✅ YES | ❌ No | Client authentication |
| `.env` with server creds | ❌ No | ✅ YES | Server operations |
| `config.ini` | ❌ No (optional) | ✅ YES | Server configuration |
| `vigint/app.py` | ✅ YES | ✅ YES | Client application |
| `api_proxy.py` | ❌ No | ✅ YES | Server API |

---

## Optional: Custom Buffer Settings

If a client wants custom buffer settings (advanced), they CAN create `config.ini`:

```ini
[VideoAnalysis]
short_buffer_duration = 5
long_buffer_duration = 15
analysis_fps = 30
```

But **99% of clients won't need this** - defaults work great!

---

## Full Working Example

### Project Structure
```
my-security-system/
├── .env                      # Only file needed!
│   └── VIGINT_API_KEY=abc123...
└── vigint/
    └── app.py                # Client application
```

### .env Contents
```bash
VIGINT_API_KEY=N7eltYz6wJSwl_55iS7tVB8q4rwXHGHDcJAzlmh2lYc
```

### Run
```bash
python vigint/app.py
```

### Console Output
```
INFO - No config.ini found - using default buffer settings (client mode)
INFO - Default buffer configuration:
INFO -   Short buffer: 3s
INFO -   Long buffer: 10s
INFO -   Analysis FPS: 25
INFO - Local frame buffer initialized (max 250 frames)
INFO - ✅ Connected to Vigint API proxy
```

---

## Comparison: Old vs New

### OLD (Before Update)
```
Client needs:
✅ .env (VIGINT_API_KEY)
✅ config.ini (buffer settings)
✅ config.py (to read config.ini)
```

### NEW (Now)
```
Client needs:
✅ .env (VIGINT_API_KEY)

That's it!
```

---

## FAQ

### Q: Will my client work without config.ini?
**A:** YES! The code automatically uses defaults.

### Q: What if I want custom settings?
**A:** You CAN still create config.ini for advanced configuration, but it's optional.

### Q: Do the defaults match the server?
**A:** YES! Defaults are:
- 3s short buffer (quick detection)
- 10s long buffer (incident videos)
- 25 FPS (standard video)

### Q: What if I'm running the server locally?
**A:** Then you DO need config.ini (for server settings like Gemini API key, etc.)

---

## Summary

**For Clients:**
```bash
# 1. Get API key from admin
# 2. Create .env
echo "VIGINT_API_KEY=your-key" > .env

# 3. Run
python vigint/app.py --api-url https://server.com:5002
```

**For Server:**
```bash
# Need both:
.env (all credentials)
config.ini (server settings)
```

Simple!
