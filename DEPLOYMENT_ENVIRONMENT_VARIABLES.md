# Environment Variables: Local vs Cloud Deployment

## TL;DR

**Render.com/Cloud:** Set env vars in dashboard - NO `.env` file needed  
**Local Development:** Use `.env` file

---

## Priority Order

Vigint checks for configuration in this order:

1. **Environment Variables** (Render.com dashboard, shell exports) - **HIGHEST PRIORITY**
2. `.env` file (loaded by python-dotenv)
3. `config.ini` file
4. Default fallback values - **LOWEST PRIORITY**

---

## Render.com Deployment

### ✅ What to Do

Set environment variables in Render.com dashboard:

1. Go to: Render.com Dashboard → Your Service → Environment
2. Add these variables:

```
GOOGLE_API_KEY=AIzaSy...
SECRET_KEY=<generate with: openssl rand -hex 32>
DATABASE_URL=<provided by Render for PostgreSQL>
SPARSE_AI_API_KEY=<your sparse-ai key>
SPARSE_AI_BASE_URL=https://sparse-ai-video-server.onrender.com
EMAIL_PASSWORD=<your email app password>
```

### ❌ What NOT to Do

- ❌ Don't create a `.env` file on Render.com
- ❌ Don't commit `.env` to your git repository
- ❌ Don't include secrets in `config.ini` that's committed to git

### Why?

- Environment variables set in Render.com dashboard are **more secure**
- They're not in your codebase (can't be accidentally committed)
- Easy to rotate without code changes
- Render provides `DATABASE_URL` automatically for PostgreSQL

---

## Local Development

### ✅ What to Do

Create a `.env` file locally:

```bash
# Copy the template
cp .env.example .env

# Edit with your local credentials
nano .env
```

Add to `.env`:
```bash
GOOGLE_API_KEY=AIzaSy...
SECRET_KEY=dev-secret-key-local
DATABASE_URL=sqlite:///vigint.db
SPARSE_AI_API_KEY=local-sparse-ai-key
EMAIL_PASSWORD=your-email-password
```

### ❌ What NOT to Do

- ❌ Don't commit `.env` to git (add to `.gitignore`)
- ❌ Don't use production credentials locally
- ❌ Don't share your `.env` file with others

---

## Configuration Priority Examples

### Example 1: Render.com with DATABASE_URL set

```python
# Render.com dashboard has: DATABASE_URL=postgresql://...
# .env file has: DATABASE_URL=sqlite:///vigint.db  (ignored)
# config.ini has: database_url=sqlite:///vigint.db  (ignored)

# Result: Uses postgresql:// from Render environment
```

### Example 2: Local Development

```bash
# No environment variable set
# .env file has: GOOGLE_API_KEY=AIzaSy...
# config.ini has: gemini_api_key=old-key  (ignored)

# Result: Uses AIzaSy... from .env
```

### Example 3: Override for Testing

```bash
# Terminal: export GOOGLE_API_KEY=test-key
# .env file has: GOOGLE_API_KEY=real-key  (ignored)

# Result: Uses test-key from environment variable
```

---

## How It Works (Code)

From `config.py`:

```python
@property
def database_url(self):
    """Get database URL"""
    # Environment variable takes precedence (for Render.com, etc.)
    return os.getenv('DATABASE_URL') or self.get('Database', 'database_url', 'sqlite:///vigint.db')

@property
def gemini_api_key(self):
    """Get Gemini API key"""
    return os.getenv('GOOGLE_API_KEY') or self.get('AI', 'gemini_api_key', None)
```

**Translation:**
1. Check environment variables first (`os.getenv()`)
2. If not found, check config files (`self.get()`)
3. If still not found, use default

---

## Best Practices

### For Production (Render.com)

```
✅ Set in Render.com dashboard:
   - GOOGLE_API_KEY
   - SECRET_KEY
   - DATABASE_URL (auto-provided by Render)
   - SPARSE_AI_API_KEY
   - EMAIL_PASSWORD

✅ In git repository:
   - .env.example (template only)
   - config.ini.example (template only)

❌ NOT in git:
   - .env (gitignored)
   - config.ini with secrets (gitignored)
```

### For Local Development

```
✅ On your machine:
   - .env (from .env.example)
   - config.ini (from config.ini.example)

✅ In .gitignore:
   .env
   config.ini

✅ In git repository:
   - .env.example
   - .env.server_template
   - .env.client_template
   - config.ini.example
```

---

## Deployment Checklist

### Render.com Setup

- [ ] Create service on Render.com
- [ ] Connect GitHub repository
- [ ] Add environment variables in dashboard:
  - [ ] `GOOGLE_API_KEY`
  - [ ] `SECRET_KEY`
  - [ ] `DATABASE_URL` (if using external PostgreSQL)
  - [ ] `SPARSE_AI_API_KEY`
  - [ ] `EMAIL_PASSWORD`
  - [ ] `STRIPE_API_KEY` (if using payments)
- [ ] Verify no `.env` file in repository
- [ ] Deploy!

### Local Development Setup

- [ ] Clone repository
- [ ] Copy `.env.example` to `.env`
- [ ] Fill in local credentials in `.env`
- [ ] Copy `config.ini.example` to `config.ini`
- [ ] Update `config.ini` if needed
- [ ] Verify `.env` and `config.ini` are in `.gitignore`
- [ ] Run locally: `python api_proxy.py`

---

## Common Questions

### Q: I have env vars in Render.com AND a .env file. Which wins?
**A:** Render.com environment variables win. The `.env` file is ignored.

### Q: Should I commit .env.example?
**A:** YES! It's a template for others. Never commit actual `.env`.

### Q: Can I use .env on Render.com?
**A:** You can, but it's not recommended. Use Render.com's environment variables instead.

### Q: How do I rotate secrets on Render.com?
**A:** 
1. Go to Render.com → Environment
2. Update the variable value
3. Save (triggers automatic redeploy)

### Q: What if I need different values for dev/staging/prod?
**A:** 
- Local dev: `.env` file
- Staging: Render.com env vars (staging service)
- Production: Render.com env vars (production service)

---

## Summary Table

| Deployment | Config Method | File Needed |
|------------|---------------|-------------|
| **Render.com** | Environment variables in dashboard | ❌ No `.env` |
| **Railway** | Environment variables in dashboard | ❌ No `.env` |
| **Heroku** | Environment variables via CLI/dashboard | ❌ No `.env` |
| **AWS/GCP** | Environment variables in platform | ❌ No `.env` |
| **Local Dev** | `.env` file | ✅ Yes `.env` |
| **Docker** | Environment variables in docker-compose | ✅ `.env` or compose file |
| **Bare Metal** | `.env` file or export in shell | ✅ `.env` recommended |

---

## See Also

- **API_KEYS_EXPLAINED.md** - Understanding different API keys
- **RENDER_DEPLOYMENT.md** - Complete Render.com deployment guide
- **README_API_KEYS.md** - API keys quick reference
