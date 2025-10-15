# Quick Reference: Client Setup & Authentication

## TL;DR

**Server Admin** → Creates client in database → Gets unique API key  
**Client** → Stores API key in `.env` file → Uses it to authenticate

---

## For Server Administrators

### Create New Client
```bash
python manage_clients.py --create --name "Client Name" --email "client@example.com"
```
→ Gives you a unique API key like: `8xK9mP2nQ5rT7vW1xZ4aC6eG8hJ0kL3mN6oP9qR2sT5u...`

### List All Clients
```bash
python manage_clients.py --list
```

### Revoke Non-Paying Client
```bash
python manage_clients.py --revoke --client-id 3
```

### Reactivate Client
```bash
python manage_clients.py --reactivate --client-id 3
```

---

## For Clients

### 1. Receive API Key
Your administrator sends you: `8xK9mP2nQ5rT7vW1xZ4aC6eG8hJ0kL3mN6oP9qR2sT5u...`

### 2. Create `.env` File (ONLY FILE NEEDED!)
```bash
# Create .env with your API key
echo "VIGINT_API_KEY=8xK9mP2nQ5rT7vW1xZ4aC6eG8hJ0kL3mN6oP9qR2sT5u..." > .env
```

**Client files needed:**
- ✅ `.env` (with VIGINT_API_KEY)
- ❌ NO config.ini needed
- ❌ NO server credentials needed

### 3. Run Vigint
```bash
python vigint/app.py --api-url https://your-vigint-server.com:5002
```

---

## Key Concepts

| Concept | Storage Location | Purpose |
|---------|------------------|---------|
| **Client API Key** | Client's `.env` file | Authenticates the client |
| **Client Record** | Server database | Stores client info (name, email) |
| **API Key Hash** | Server database | Validates client API keys |
| **Server Config** | Server's `config.ini` | Shared settings (email, AI, etc.) |
| **Frame Buffer** | Server memory | Per-client video buffer |

---

## Authentication Flow (Simplified)

```
Client Side:                Server Side:
┌──────────┐               ┌──────────┐
│ .env     │               │ Database │
│ API_KEY  │───────────────▶│ Validates│
│          │   HTTP Request │ & Routes │
└──────────┘               └──────────┘
     │                            │
     │                            ▼
     │                     ┌─────────────┐
     │                     │Client Buffer│
     │                     │[client_id=5]│
     └─────────────────────▶│ Isolated   │
                           └─────────────┘
```

---

## What Distinguishes Different Clients?

✅ **Unique API Key** - Different random key for each client  
✅ **Database Record** - Separate entry with unique `client_id`  
✅ **Isolated Buffers** - Each client has their own `client_frame_buffers[client_id]`  
✅ **Usage Tracking** - All API calls tracked per `api_key_id`  

❌ **NOT separate config files** - All clients share `config.ini` on server  
❌ **NOT different servers** - Multiple clients use same server instance  

---

## Files You Need to Know

### Server Admin
- `manage_clients.py` - Create/revoke/list clients
- `config.ini` - Server configuration (shared by all clients)
- `vigint.db` - Database with client records and API keys

### Client
- `.env` - Contains their unique `VIGINT_API_KEY`
- `vigint/app.py` - Client application that uses the API key

---

## Documentation Map

1. **SETUP_NEW_CLIENT.md** - Detailed step-by-step setup guide
2. **CLIENT_AUTHENTICATION_GUIDE.md** - How authentication works
3. **README_CLIENT_MANAGEMENT.md** - Managing clients (revoke, delete, etc.)
4. **README_BILLING.md** - Billing and invoicing system

---

## Common Scenarios

### Scenario 1: New Client Setup
```bash
# Admin creates client
python manage_clients.py --create --name "Acme" --email "acme@example.com"
# API Key: abc123...

# Send API key to client

# Client creates .env
echo "VIGINT_API_KEY=abc123..." > .env

# Client runs app
python vigint/app.py
```

### Scenario 2: Client Stops Paying
```bash
# Admin lists clients to find ID
python manage_clients.py --list
# Acme Corp is client_id=5

# Admin revokes access
python manage_clients.py --revoke --client-id 5

# Client's API requests now return 401 Unauthorized
```

### Scenario 3: Client Resumes Payment
```bash
# Admin reactivates
python manage_clients.py --reactivate --client-id 5

# Client's existing .env still works, no changes needed
```

---

## Security Checklist

- [ ] API keys transmitted via secure channel (encrypted email)
- [ ] Client adds `.env` to `.gitignore`
- [ ] Server uses HTTPS in production
- [ ] Regular audit of active clients
- [ ] Monitoring for unusual API usage patterns
- [ ] Keys rotated periodically (create new, revoke old)

---

## Need Help?

- **Setup issues**: See `SETUP_NEW_CLIENT.md`
- **Authentication problems**: See `CLIENT_AUTHENTICATION_GUIDE.md`
- **Billing questions**: See `README_BILLING.md`
- **Revoke/delete clients**: See `README_CLIENT_MANAGEMENT.md`
