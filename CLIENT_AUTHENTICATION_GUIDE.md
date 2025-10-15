# Client Authentication Guide - How API Keys Are Used

## Overview

**Server Side** (`config.ini`): Shared configuration for the Vigint server (database, email, AI settings)
**Client Side** (`.env` file or environment variables): Each client stores their **unique API key**

## ⚠️ CRITICAL: Client Only Needs ONE API Key

**Clients need ONLY:**
- ✅ `VIGINT_API_KEY` - Their unique authentication key

**Clients DO NOT need:**
- ❌ `GOOGLE_API_KEY` - This is SERVER-SIDE for AI analysis
- ❌ `SPARSE_AI_API_KEY` - This is SERVER-SIDE for video hosting
- ❌ `SECRET_KEY` - This is SERVER-SIDE for authentication
- ❌ Any email or payment credentials

See `API_KEYS_EXPLAINED.md` for complete details.

## Where Clients Store Their API Key

### Option 1: Environment Variable (Recommended)

Each client creates a `.env` file in their working directory:

```bash
# Client's .env file
VIGINT_API_KEY=8xK9mP2nQ5rT7vW1xZ4aC6eG8hJ0kL3mN6oP9qR2sT5uV8wX1yZ4bC7dF0gH3jK6
```

Or exports it in their shell:

```bash
export VIGINT_API_KEY=8xK9mP2nQ5rT7vW1xZ4aC6eG8hJ0kL3mN6oP9qR2sT5uV8wX1yZ4bC7dF0gH3jK6
```

### Option 2: Command Line Parameter

Pass the API key directly when running scripts:

```bash
python vigint/app.py \
  --api-key 8xK9mP2nQ5rT7vW1xZ4aC6eG8hJ0kL3mN6oP9qR2sT5uV8wX1yZ4bC7dF0gH3jK6 \
  --api-url http://your-vigint-server.com:5002
```

### Option 3: Programmatic (In Code)

```python
from vigint.app import SecureVideoAnalyzer

analyzer = SecureVideoAnalyzer(
    api_base_url='http://your-vigint-server.com:5002',
    api_key='8xK9mP2nQ5rT7vW1xZ4aC6eG8hJ0kL3mN6oP9qR2sT5uV8wX1yZ4bC7dF0gH3jK6'
)
```

## How Authentication Works

### 1. Client-Side Code Reads API Key

From `vigint/app.py`:

```python
class SecureVideoAnalyzer:
    def __init__(self, api_base_url='http://localhost:5002', api_key=None):
        # Priority: parameter > environment variable > None
        self.api_key = api_key or os.getenv('VIGINT_API_KEY')
        
        if not self.api_key:
            logger.warning("No API key provided. Some features may not work.")
        
        # Add API key to request headers
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
```

### 2. Client Sends API Key in Every Request

```python
response = requests.post(
    f"{self.api_base_url}/api/video/buffer",
    json={'frame_data': base64_frame, 'frame_count': 1},
    headers=self.headers  # Contains: Authorization: Bearer <api_key>
)
```

### 3. Server Validates API Key

From `auth.py`:

```python
@require_api_key_flexible
def buffer_frame():
    # Decorator extracts API key from headers
    # Hashes it and looks up in database
    # Sets request.current_client to the authenticated client
    client_buffer = get_client_buffer(request.current_client.id)
    # ... client-specific operations
```

## Complete Client Setup Example

### Step 1: Client Receives Their API Key

You (the server admin) create the client:

```bash
python manage_clients.py --create --name "Acme Corp" --email "security@acme.com"

# Output includes:
# 🔑 API Key: 8xK9mP2nQ5rT7vW1xZ4aC6eG8hJ0kL3mN6oP9qR2sT5uV8wX1yZ4bC7dF0gH3jK6
```

Send this API key to the client securely.

### Step 2: Client Creates Their `.env` File

The client creates a `.env` file in their project directory:

```bash
# Acme Corp's .env file
VIGINT_API_KEY=8xK9mP2nQ5rT7vW1xZ4aC6eG8hJ0kL3mN6oP9qR2sT5uV8wX1yZ4bC7dF0gH3jK6
```

### Step 3: Client Runs Vigint Application

```bash
# Option A: Using environment variable (from .env)
python vigint/app.py --api-url https://your-vigint-server.com:5002

# Option B: Using command-line parameter
python vigint/app.py \
  --api-url https://your-vigint-server.com:5002 \
  --api-key 8xK9mP2nQ5rT7vW1xZ4aC6eG8hJ0kL3mN6oP9qR2sT5uV8wX1yZ4bC7dF0gH3jK6
```

### Step 4: Authentication Flow

```
┌─────────────────┐
│  Client App     │  Reads VIGINT_API_KEY from .env
│  (vigint/app.py)│  
└────────┬────────┘
         │
         │ HTTP Request with header:
         │ Authorization: Bearer 8xK9mP2n...
         ▼
┌─────────────────┐
│  Vigint Server  │  Receives API key in header
│  (api_proxy.py) │
└────────┬────────┘
         │
         │ @require_api_key_flexible decorator
         ▼
┌─────────────────┐
│  Auth System    │  1. Hash the API key (SHA-256)
│  (auth.py)      │  2. Look up in api_keys table
└────────┬────────┘  3. Check is_active = True
         │           4. Get client_id
         │
         ▼
┌─────────────────┐
│  Database       │  SELECT * FROM api_keys 
│                 │  WHERE key_hash = '...' AND is_active = TRUE
└────────┬────────┘
         │
         │ Returns client_id = 5
         ▼
┌─────────────────┐
│  Request        │  request.current_client = Client(id=5, name="Acme Corp")
│  Context        │  request.current_api_key = APIKey(id=12)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Client-Specific│  client_buffer = get_client_buffer(5)
│  Operations     │  All data isolated by client_id
└─────────────────┘
```

## Key Points

### ❌ **NOT** Stored in `config.ini`
The `config.ini` file on the **server** contains:
- Database connection
- Email settings
- AI configuration
- **NO client API keys** (those are in the database)

### ✅ **Stored in Client's `.env`**
Each client has their own `.env` file containing:
```bash
VIGINT_API_KEY=<their_unique_key>
```

### 🔒 Security Model

1. **Server-Side** (`config.ini`):
   - Shared configuration for all clients
   - Gemini API key (for AI analysis)
   - Email credentials (for sending alerts)
   - Database connection

2. **Database** (SQLite/PostgreSQL):
   - Hashed API keys (SHA-256)
   - Client records
   - API usage tracking

3. **Client-Side** (`.env` or environment):
   - Each client's unique API key
   - Server URL to connect to
   - No other credentials needed

## Example: Three Clients Using Vigint

### Server (`config.ini` - SHARED)
```ini
[API]
secret_key = server-secret-key
host = 0.0.0.0
port = 5002

[AI]
gemini_api_key = AIzaSy...  # Shared for all clients

[Email]
smtp_server = smtp.gmail.com
username = alerts@vigint.com  # Shared for all clients
```

### Client A (Acme Corp's `.env`)
```bash
VIGINT_API_KEY=8xK9mP2nQ5rT7vW1xZ4aC6eG8hJ0kL3mN6oP9qR2sT5uV8wX1yZ4bC7dF0gH3jK6
```

### Client B (TechCo's `.env`)
```bash
VIGINT_API_KEY=2zN5pR8sV1wY4bD7fH0jL3nP6qS9tW2xA5cE8gK1mO4rU7vZ0yC3eG6iM9oQ2tX
```

### Client C (SecureInc's `.env`)
```bash
VIGINT_API_KEY=5yB8eH1kN4qT7wZ0cF3iL6oR9uX2aD5gJ8mP1sV4yC7fI0lO3rU6vY9bE2hK5nQ
```

Each client runs:
```bash
python vigint/app.py --api-url https://vigint-server.com:5002
```

The server:
1. Receives their API key in the request header
2. Looks up which client it belongs to
3. Routes all data to their isolated buffer and database records
4. Never mixes data between clients

## Template `.env` File for Clients

Create this as `.env.client_template`:

```bash
# Vigint Client Configuration
# Replace with your actual API key (provided by Vigint admin)

VIGINT_API_KEY=your-api-key-here

# Optional: Override server URL (default: http://localhost:5002)
# VIGINT_SERVER_URL=https://your-vigint-server.com:5002
```

## Troubleshooting

### "No API key provided" Warning

**Problem:** Client sees:
```
WARNING - No API key provided. Some features may not work.
```

**Solutions:**
1. Create `.env` file with `VIGINT_API_KEY=...`
2. Export environment variable: `export VIGINT_API_KEY=...`
3. Pass `--api-key` parameter when running

### "Invalid API key" Error (401)

**Problem:** Server returns:
```json
{"error": "Invalid API key"}
```

**Possible causes:**
1. API key was typed incorrectly
2. API key was revoked by admin
3. Client doesn't exist in database

**Check:**
```bash
python manage_clients.py --list
```

### "Access denied" Error (403)

**Problem:** Client trying to access another client's data

**Cause:** API endpoint checks:
```python
if request.current_client.id != client_id:
    return jsonify({'error': 'Access denied'}), 403
```

Clients can only access their own data.

## Best Practices

1. **Never commit `.env` to git**
   - Add `.env` to `.gitignore`
   - Use `.env.example` as a template

2. **Use environment-specific keys**
   - Development: `.env.development`
   - Production: `.env.production`

3. **Rotate keys regularly**
   - Create new API key
   - Update client's `.env`
   - Revoke old key

4. **Secure transmission**
   - Use HTTPS in production
   - Send API keys via encrypted email/password manager
   - Never send in plain text SMS or chat

5. **Monitor usage**
   - Check `api_usage` table regularly
   - Alert on suspicious patterns
   - Revoke compromised keys immediately
