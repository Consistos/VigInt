# Admin API Setup - Quick Start

## What Was Added

✅ **Admin API endpoints** in `api_proxy.py` for remote client management  
✅ **Python script** (`manage_clients_remote.py`) to manage clients from your local machine  
✅ **Shell script** (`manage_clients_remote.sh`) for command-line management  
✅ **Documentation** (`SERVER_CLIENT_MANAGEMENT.md`) explaining the architecture  

## The Solution to Your Problem

You tried to run `manage_clients.py` on Render.com's shell but got "file not found". 

**Why?** The file wasn't deployed to Render.

**Solution:** Use the new **Admin API** to manage clients remotely from your local machine.

## How to Use (3 Steps)

### Step 1: Get Your Admin Key

1. Go to https://dashboard.render.com
2. Select your `vigint-api-server` service
3. Click **Environment** tab
4. Find `SECRET_KEY` and copy its value

### Step 2: Set Environment Variable

```bash
export VIGINT_ADMIN_KEY=your-secret-key-from-step-1
```

### Step 3: Manage Clients

```bash
# List all clients on the server
python manage_clients_remote.py --list

# Create a client on the server
python manage_clients_remote.py --create --name "Moi" --email "davidbagory@gmail.com"

# Revoke a client (use correct ID from --list)
python manage_clients_remote.py --revoke --client-id 6

# Reactivate a client
python manage_clients_remote.py --reactivate --client-id 6
```

## Deploy the Changes to Render

To make the Admin API available on your server:

```bash
# Add and commit changes
git add api_proxy.py manage_clients_remote.py manage_clients_remote.sh SERVER_CLIENT_MANAGEMENT.md ADMIN_API_SETUP.md
git commit -m "Add Admin API for remote client management"
git push origin main
```

Render will automatically redeploy (takes 2-3 minutes).

## Verify It Works

Once deployed, test the Admin API:

```bash
export VIGINT_ADMIN_KEY=your-secret-key

# Test listing (should return JSON with clients)
curl -H "X-Admin-Key: $VIGINT_ADMIN_KEY" \
  https://vigint-api-server.onrender.com/admin/clients
```

## Why This Is Better

❌ **Old way:** SSH into Render shell → run `manage_clients.py` → file not found  
✅ **New way:** Run from local machine → HTTP API → works instantly  

**Benefits:**
- No need for Render shell access
- Works from anywhere (your laptop, CI/CD, etc.)
- Same functionality as `manage_clients.py`
- Secure (requires admin key)

## Full Documentation

See `SERVER_CLIENT_MANAGEMENT.md` for complete architecture explanation and all options.

## Troubleshooting

### "Admin key required" error
- Make sure `VIGINT_ADMIN_KEY` is set
- Use the SECRET_KEY from your Render environment

### "Connection refused"
- Wait for Render to finish deploying
- Check service is running: `curl https://vigint-api-server.onrender.com/api/health`

### "Invalid admin key"
- Double-check you copied the correct SECRET_KEY from Render dashboard
- No spaces or extra characters

## Security Note

The admin key is your server's SECRET_KEY. Keep it secure:
- Don't commit it to Git
- Don't share it publicly
- Only use it from trusted machines
