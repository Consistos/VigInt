# API Keys Quick Reference

## The Golden Rule

**Clients**: Only need `VIGINT_API_KEY`  
**Server**: Needs all other keys (`GOOGLE_API_KEY`, `SPARSE_AI_API_KEY`, etc.)

---

## API Key Cheat Sheet

| API Key | Who Needs It | What It's For | Where It's Stored |
|---------|--------------|---------------|-------------------|
| **VIGINT_API_KEY** | 👤 **CLIENT** | Authenticate with Vigint server | Client's `.env` |
| **GOOGLE_API_KEY** | 🖥️ **SERVER** | Access Gemini AI for video analysis | Server's `.env` |
| **SPARSE_AI_API_KEY** | 🖥️ **SERVER** | Upload videos to hosting service | Server's `.env` |
| **SECRET_KEY** | 🖥️ **SERVER** | JWT token generation | Server's `.env` |
| **EMAIL_PASSWORD** | 🖥️ **SERVER** | Send alert emails | Server's `.env` |

---

## Quick Setup

### For Clients
```bash
# 1. Get your API key from admin
# 2. Create .env with ONLY this:
cat > .env << EOF
VIGINT_API_KEY=your-key-from-admin
EOF

# 3. Run the app
python vigint/app.py
```

### For Server
```bash
# 1. Copy template
cp .env.example .env

# 2. Fill in ALL server credentials
# GOOGLE_API_KEY=...
# SECRET_KEY=...
# etc.

# 3. Start server
python api_proxy.py
```

---

## File Reference

| File | For | Contains |
|------|-----|----------|
| `.env.client_template` | Clients | Just `VIGINT_API_KEY` |
| `.env.example` | Server | All server credentials |
| `.env.server_template` | Server | All server credentials (alternative) |

---

## Common Questions

### Q: Why can't clients use GOOGLE_API_KEY?
**A:** It's expensive and shared. Server controls access and tracks usage per client.

### Q: What's the difference between VIGINT_API_KEY and SPARSE_AI_API_KEY?
**A:** 
- **VIGINT_API_KEY**: Client → Server authentication (client-side)
- **SPARSE_AI_API_KEY**: Server → Video hosting authentication (server-side)

### Q: Why do I see GOOGLE_API_KEY in my .env?
**A:** If you're running the **server**, you need it. If you're a **client**, remove it.

---

## Read More

- **API_KEYS_EXPLAINED.md** - Detailed explanation of all API keys
- **CLIENT_AUTHENTICATION_GUIDE.md** - How client authentication works
- **SETUP_NEW_CLIENT.md** - Step-by-step client setup
