# Server Client Management Guide

## Critical Understanding

**`manage_clients.py` must run ON THE SERVER**, not on client machines.

## Architecture

```
┌─────────────────────────────────────────────────┐
│  SERVER (e.g., Render.com)                     │
│  - api_proxy.py (Flask API)                     │
│  - vigint.db (PostgreSQL database)              │
│  - Manages ALL clients                          │
│                                                  │
│  Run manage_clients.py HERE →                  │
└───────────────┬─────────────────────────────────┘
                │ HTTP API with authentication
                │
        ┌───────┴────────┬──────────────┐
        │                │              │
┌───────▼──────┐  ┌──────▼────┐  ┌─────▼──────┐
│  CLIENT A    │  │ CLIENT B  │  │ CLIENT C   │
│  (Your PC)   │  │ (Other)   │  │ (Other)    │
│              │  │           │  │            │
│  .env:       │  │ .env:     │  │ .env:      │
│  API_KEY=... │  │ API_KEY=..│  │ API_KEY=...│
└──────────────┘  └───────────┘  └────────────┘
```

## The Problem You Encountered

1. **You ran `manage_clients.py --create` on your LOCAL machine**
   - Created entry in LOCAL database (vigint.db on your machine)
   - Generated API key for LOCAL database
   - **Server has no knowledge of this client**

2. **You put credentials in wrong place**
   - Updated `config.ini` [SparseAI] section (wrong - that's for video hosting)
   - Should have created `.env` file with client API key

3. **You revoked locally**
   - Revoked in LOCAL database only
   - **Server database unchanged**
   - Analysis works because server doesn't know about the revocation

## Solution: Managing Clients on the Server

### Option 1: SSH Access to Server

If you have SSH access to your server:

```bash
# SSH into server
ssh user@your-server.com

# Navigate to Vigint directory
cd /path/to/vigint

# Create client
python manage_clients.py --create --name "Moi" --email "davidbagory@gmail.com"

# List clients
python manage_clients.py --list

# Revoke client
python manage_clients.py --revoke --client-id 6
```

### Option 2: Render.com (No Direct Shell Access)

Render.com doesn't provide persistent shell access, but you have options:

#### A. Using Render Shell (Temporary Session)

1. Go to https://dashboard.render.com
2. Select your `vigint-api-server` service
3. Click **"Shell"** tab in the top navigation
4. Wait for shell to connect
5. Run commands:
   ```bash
   # List clients
   python manage_clients.py --list
   
   # Create client
   python manage_clients.py --create --name "Moi" --email "davidbagory@gmail.com"
   
   # Revoke client  
   python manage_clients.py --revoke --client-id 6
   ```

**Important**: The Render shell session is temporary and closes after inactivity.

#### B. Use the Admin API (✅ IMPLEMENTED)

**The Vigint server now includes Admin API endpoints for remote client management.**

These endpoints are protected by admin authentication (using the server's SECRET_KEY).

**From your local machine:**

##### Using Python Script (Recommended):

```bash
# Get your SECRET_KEY from Render.com dashboard
# Go to: Dashboard → vigint-api-server → Environment → SECRET_KEY
export VIGINT_ADMIN_KEY=your-secret-key-from-render

# List all clients
python manage_clients_remote.py --list

# Create a client
python manage_clients_remote.py --create --name "Moi" --email "davidbagory@gmail.com"

# Revoke a client
python manage_clients_remote.py --revoke --client-id 6

# Reactivate a client
python manage_clients_remote.py --reactivate --client-id 6
```

##### Using Shell Script:

```bash
export VIGINT_ADMIN_KEY=your-secret-key-from-render
./manage_clients_remote.sh list
./manage_clients_remote.sh create "Moi" "davidbagory@gmail.com"
./manage_clients_remote.sh revoke 6
```

##### Using curl Directly:

```bash
# List clients
curl -H "X-Admin-Key: your-secret-key" \
  https://vigint-api-server.onrender.com/admin/clients

# Create client
curl -X POST \
  -H "X-Admin-Key: your-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"name":"Moi","email":"davidbagory@gmail.com"}' \
  https://vigint-api-server.onrender.com/admin/clients

# Revoke client
curl -X POST \
  -H "X-Admin-Key: your-secret-key" \
  https://vigint-api-server.onrender.com/admin/clients/6/revoke

# Reactivate client
curl -X POST \
  -H "X-Admin-Key: your-secret-key" \
  https://vigint-api-server.onrender.com/admin/clients/6/reactivate
```

#### Admin API Endpoints Reference:

- `GET /admin/clients` - List all clients and their API keys
- `POST /admin/clients` - Create a new client (body: `{"name": "...", "email": "..."}`)
- `POST /admin/clients/<id>/revoke` - Revoke all API keys for a client
- `POST /admin/clients/<id>/reactivate` - Reactivate revoked API keys

All endpoints require `X-Admin-Key` header with the server's SECRET_KEY.

#### C. Create a Web-Based Admin Interface (Future Enhancement)

Create an admin endpoint in `api_proxy.py` to manage clients via HTTP:

```python
@app.route('/admin/clients', methods=['GET'])
@require_admin_auth  # Implement admin authentication
def admin_list_clients():
    """List all clients via API"""
    from vigint.models import Client, APIKey
    clients = Client.query.all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'email': c.email,
        'api_keys': [{
            'id': k.id,
            'is_active': k.is_active,
            'name': k.name
        } for k in APIKey.query.filter_by(client_id=c.id).all()]
    } for c in clients])

@app.route('/admin/clients', methods=['POST'])
@require_admin_auth
def admin_create_client():
    """Create client via API"""
    from auth import create_client_with_api_key
    data = request.json
    client, api_key = create_client_with_api_key(
        name=data['name'],
        email=data['email']
    )
    return jsonify({
        'client_id': client.id,
        'api_key': api_key  # Return once - cannot be retrieved later
    })

@app.route('/admin/clients/<int:client_id>/revoke', methods=['POST'])
@require_admin_auth
def admin_revoke_client(client_id):
    """Revoke client via API"""
    from auth import revoke_api_key
    from vigint.models import APIKey
    api_keys = APIKey.query.filter_by(client_id=client_id, is_active=True).all()
    for key in api_keys:
        revoke_api_key(key.id)
    return jsonify({'status': 'revoked', 'count': len(api_keys)})
```

Then manage from your local machine:
```bash
curl -X POST https://vigint-api-server.onrender.com/admin/clients \
  -H "X-Admin-Key: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d '{"name":"Moi","email":"davidbagory@gmail.com"}'
```

#### C. Deploy a Separate Admin Service

Create a lightweight admin web interface that connects to the same database.

### Option 3: Local Development Server

If you're just testing locally:

1. **Run the server locally** on the same machine:
   ```bash
   python api_proxy.py
   ```

2. **In another terminal, manage clients**:
   ```bash
   python manage_clients.py --create --name "Moi" --email "davidbagory@gmail.com"
   ```

3. **Use the generated API key** in your client application's `.env` file:
   ```bash
   # .env file in your client application
   VIGINT_API_KEY=<api-key-from-manage-clients>
   VIGINT_API_URL=http://localhost:5002
   ```

## Correct Client Configuration

When you create a client and get an API key, configure the CLIENT application:

### Client Application Setup (.env file)

```bash
# .env - Place in your CLIENT application directory
VIGINT_API_KEY=abc123def456...generated-from-manage-clients
VIGINT_API_URL=https://vigint-api-server.onrender.com
```

### Server Configuration (config.ini) - UNCHANGED

```ini
[SparseAI]
# This is for VIDEO HOSTING, not client authentication
api_key = your-sparse-ai-key-here
base_url = https://vigint-api-server.onrender.com
```

## Understanding the Two Systems

### System 1: Client Authentication (Vigint API Keys)
- **Purpose**: Authenticate client applications with your Vigint server
- **Managed by**: `manage_clients.py` on SERVER
- **Stored in**: Server database (vigint.db / PostgreSQL)
- **Used by**: Client applications in their `.env` file
- **Example**: `VIGINT_API_KEY=abc123...`

### System 2: Video Hosting (Sparse AI Credentials)
- **Purpose**: Upload videos to video hosting service
- **Configured in**: `config.ini` under `[SparseAI]`
- **Used by**: Server to upload incident videos
- **Example**: `api_key = your-sparse-ai-key`

## Why Your Analysis Still Works

The analysis continues to work because:

1. **You're not actually using client authentication yet** - the analysis might be running locally without API authentication
2. **OR** you're using a different API key that's still valid on the server
3. **The revocation was only local** - server doesn't know about it

## Recommended Next Steps

1. **Determine where your server is running**:
   - Local machine? (`python api_proxy.py`)
   - Render.com? (deployed service)
   - Other cloud provider?

2. **Access the server** using one of the methods above

3. **Create client on the SERVER**:
   ```bash
   python manage_clients.py --create --name "Moi" --email "davidbagory@gmail.com"
   ```

4. **Save the generated API key** (shown only once!)

5. **Configure your CLIENT application** with the API key in `.env`

6. **Test authentication**:
   ```bash
   curl -H "X-API-Key: your-api-key" \
        https://your-server.com/api/health
   ```

## Database Locations

- **Local development**: `vigint.db` in project directory
- **Render.com**: PostgreSQL database (managed by Render)
- **Check your config**: `config.ini` → `[Database]` → `database_url`

## Quick Check: Where Am I?

Run this to see which database you're using:

```bash
python -c "from config import config; print(f'Database: {config.database_url}')"
```

- If it shows `sqlite:///vigint.db` → Local database
- If it shows `postgresql://...` → Remote PostgreSQL (server)

## Summary

❌ **Don't do**:
- Run `manage_clients.py` on client machines
- Put client API keys in `config.ini`
- Confuse Sparse AI credentials with Vigint client credentials

✅ **Do**:
- Run `manage_clients.py` on the SERVER (where the database is)
- Put client API keys in client application's `.env` file
- Keep Sparse AI credentials in server's `config.ini`
