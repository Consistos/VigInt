# Setting Up a New Client - Complete Guide

## Overview

In Vigint, **clients are completely isolated from each other** at the application level. Each client:
- Has unique API key(s) for authentication
- Has their own video frame buffer in memory
- Has their own usage tracking and billing
- Can only access their own data

## What Distinguishes Different Clients?

### 1. **API Key** (Primary Identifier)
Each client's API key uniquely identifies them. When they make requests, the system:
- Authenticates via the API key
- Sets `request.current_client` to their Client record
- Routes all data to client-specific resources

### 2. **Isolated Data**
- **Frame Buffers**: `client_frame_buffers[client_id]` - Each client has their own in-memory video buffer
- **Database Records**: All usage, payments, and API keys are linked via `client_id`
- **No Cross-Client Access**: Clients cannot see or access other clients' data

### 3. **Independent Configuration**
Each client can have their own:
- Email address for alerts and invoices
- Payment details
- Multiple API keys
- Usage history

## Step-by-Step: Setting Up a New Client

### Step 1: Create the Client

```bash
python manage_clients.py --create \
  --name "Acme Corporation" \
  --email "security@acme.com"
```

**Output:**
```
================================================================================
✅ CLIENT CREATED SUCCESSFULLY
================================================================================
Client ID: 5
Name: Acme Corporation
Email: security@acme.com

🔑 API Key: 8xK9mP2nQ5rT7vW1xZ4aC6eG8hJ0kL3mN6oP9qR2sT5uV8wX1yZ4bC7dF0gH3jK6

⚠️  IMPORTANT: Save this API key! It cannot be retrieved later.
================================================================================
```

**💾 CRITICAL:** Save this API key immediately - it's shown only once and cannot be retrieved later!

### Step 2: Share API Key with Client

Send the client their API key securely (encrypted email, password manager, etc.):

```
Your Vigint Video Analysis API Key:
8xK9mP2nQ5rT7vW1xZ4aC6eG8hJ0kL3mN6oP9qR2sT5uV8wX1yZ4bC7dF0gH3jK6

⚠️ IMPORTANT: This is the ONLY API key you need!
Do NOT add GOOGLE_API_KEY or SPARSE_AI_API_KEY to your .env file.
Those are server-side credentials that you should not have access to.

Usage:
1. Create a .env file with:
   VIGINT_API_KEY=8xK9mP2nQ5rT7vW1xZ4aC6eG8hJ0kL3mN6oP9qR2sT5uV8wX1yZ4bC7dF0gH3jK6

2. Run: python vigint/app.py --api-url https://your-vigint-server.com/api/

For more details, see .env.client_template
```

### Step 3: Client Configuration

**Clients need ONLY their `.env` file with `VIGINT_API_KEY`**

- ❌ No `config.ini` needed (uses sensible defaults)
- ❌ No server credentials needed
- ✅ Just `.env` with their API key

All client settings are in the database and accessed via their API key. Buffer settings use defaults (3s/10s) which match the server configuration.

### Step 4: Verify Client Access

Test the client's API key:

```bash
curl -X GET "http://localhost:5002/api/health" \
  -H "X-API-Key: 8xK9mP2nQ5rT7vW1xZ4aC6eG8hJ0kL3mN6oP9qR2sT5uV8wX1yZ4bC7dF0gH3jK6"
```

Expected response:
```json
{
  "status": "ok",
  "timestamp": "2025-10-02T16:10:00Z"
}
```

### Step 5: Client Starts Using API

The client can now use these endpoints (all require their API key):

```bash
# Buffer video frames
curl -X POST "http://localhost:5002/api/video/buffer" \
  -H "X-API-Key: CLIENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"frame_data": "base64_encoded_frame", "frame_count": 1}'

# Analyze frames for security incidents
curl -X POST "http://localhost:5002/api/video/analyze" \
  -H "X-API-Key: CLIENT_API_KEY"

# Send security alert
curl -X POST "http://localhost:5002/api/alert" \
  -H "X-API-Key: CLIENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"analysis": "Security incident details", "risk_level": "HIGH"}'
```

## What Happens Behind the Scenes

### When Client Makes a Request:

1. **Authentication** (`auth.py`):
   ```python
   api_key = request.headers.get('X-API-Key')
   api_key_hash = hash_api_key(api_key)
   client = verify_api_key(api_key_hash)
   request.current_client = client  # Sets client context
   ```

2. **Data Isolation** (`api_proxy.py`):
   ```python
   # Each client gets their own buffer
   client_buffer = get_client_buffer(request.current_client.id)
   
   # All operations use the authenticated client
   logger.info(f"Frame analyzed for client {request.current_client.name}")
   ```

3. **Usage Tracking**:
   ```python
   # Automatically tracked per client
   usage = APIUsage(
       api_key_id=request.current_api_key.id,
       endpoint='/api/video/analyze',
       cost=0.05
   )
   ```

## Viewing Client Status

```bash
# List all clients
python manage_clients.py --list
```

Output shows:
- Client ID, name, email
- All API keys (active/revoked)
- Creation dates

## Managing Clients After Setup

### Add Additional API Key (if client needs separate keys for different services)
Currently requires manual database insertion. You can enhance `manage_clients.py` to support this.

### Revoke Access
```bash
python manage_clients.py --revoke --client-id 5
```

### Reactivate Access
```bash
python manage_clients.py --reactivate --client-id 5
```

### Delete Permanently
```bash
python manage_clients.py --delete --client-id 5
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                          Request                            │
│  X-API-Key: 8xK9mP2nQ5rT7vW1xZ4aC6eG8hJ0kL3mN6oP9qR2sT... │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
                   ┌────────────────┐
                   │  Auth System   │
                   │  (auth.py)     │
                   └────────┬───────┘
                            │
                    Hash & Verify Key
                            │
                            ▼
                   ┌────────────────┐
                   │  Database      │
                   │  Lookup        │
                   └────────┬───────┘
                            │
                   Find client_id = 5
                            │
                            ▼
                   ┌────────────────┐
                   │  Set Context   │
                   │  request.      │
                   │  current_client│
                   └────────┬───────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Frame Buffer │   │ Usage Track  │   │ API Response │
│  [client_5]  │   │  for client 5│   │  with client │
│              │   │              │   │  data only   │
└──────────────┘   └──────────────┘   └──────────────┘
```

## Common Questions

### Q: Do I need to create a config file for each client?
**A:** No! There are no per-client config files. All client data is in the database.

### Q: How do clients get different settings?
**A:** Currently, all clients share the same `config.ini` settings (buffer duration, AI model, etc.). If you need per-client settings, you'd need to extend the `Client` model in `vigint/models.py`.

### Q: Can clients see each other's data?
**A:** No. The system isolates data by `client_id`:
- Frame buffers: `client_frame_buffers[client_id]`
- Database queries: `filter_by(client_id=...)`
- Access control: Checked in API endpoints

### Q: What if I lose a client's API key?
**A:** You cannot retrieve it (it's hashed). Options:
1. Create a new API key for the client (requires code enhancement)
2. Delete and recreate the client (loses historical data)

### Q: Can a client have multiple API keys?
**A:** Yes, the database supports it, but `manage_clients.py` currently creates only one per client. You can manually add more or enhance the script.

## Security Best Practices

1. **API Key Transmission**: Share keys via secure channels (encrypted email, password manager)
2. **HTTPS Only**: Always use HTTPS in production to protect API keys in transit
3. **Key Rotation**: Plan for key rotation (revoke old, create new)
4. **Monitor Usage**: Regularly check `api_usage` table for suspicious activity
5. **Revoke Promptly**: Immediately revoke keys for clients who stop paying

## Next Steps

After setting up a client:

1. **Test their access** with a simple API call
2. **Configure their email alerts** (currently uses global `config.ini` email settings)
3. **Set up billing/payment details** in `payment_details` table
4. **Monitor their usage** via the database or upcoming dashboard
5. **Generate invoices** using the weekly invoice system

## Integration with Billing

See `README_BILLING.md` for:
- How usage is tracked per client
- How invoices are generated per client
- Payment methods and frequency
