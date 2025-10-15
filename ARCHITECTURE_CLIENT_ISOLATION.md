# Vigint Architecture: Client Isolation

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         VIGINT SERVER                               │
│                      (Single Instance)                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────┐         ┌──────────────────┐                   │
│  │  config.ini   │         │   Database       │                   │
│  │  (Shared)     │         │   (vigint.db)    │                   │
│  ├───────────────┤         ├──────────────────┤                   │
│  │ - AI Key      │         │ Clients Table:   │                   │
│  │ - Email       │         │  1: Acme Corp    │                   │
│  │ - Database    │         │  2: TechCo       │                   │
│  │ - RTSP        │         │  3: SecureInc    │                   │
│  └───────────────┘         │                  │                   │
│                            │ API Keys Table:  │                   │
│                            │  1: hash_abc...  │                   │
│                            │  2: hash_def...  │                   │
│                            │  3: hash_ghi...  │                   │
│                            └──────────────────┘                   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────┐         │
│  │         In-Memory Frame Buffers                      │         │
│  │  client_frame_buffers = {                            │         │
│  │    1: deque([frame1, frame2, ...]),  # Acme's buffer │         │
│  │    2: deque([frame1, frame2, ...]),  # TechCo buffer │         │
│  │    3: deque([frame1, frame2, ...])   # SecureInc buf │         │
│  │  }                                                    │         │
│  └──────────────────────────────────────────────────────┘         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ HTTP API
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  CLIENT A     │      │  CLIENT B     │      │  CLIENT C     │
│  (Acme Corp)  │      │  (TechCo)     │      │  (SecureInc)  │
├───────────────┤      ├───────────────┤      ├───────────────┤
│               │      │               │      │               │
│ .env:         │      │ .env:         │      │ .env:         │
│ VIGINT_API_KEY│      │ VIGINT_API_KEY│      │ VIGINT_API_KEY│
│ = abc123...   │      │ = def456...   │      │ = ghi789...   │
│               │      │               │      │               │
│ vigint/app.py │      │ vigint/app.py │      │ vigint/app.py │
└───────────────┘      └───────────────┘      └───────────────┘
```

---

## Request Flow: Client A Makes API Call

```
Step 1: CLIENT A SENDS REQUEST
┌──────────────────────────────────────────────┐
│ POST /api/video/buffer                       │
│ Authorization: Bearer abc123...              │
│ {"frame_data": "...", "frame_count": 1}      │
└───────────────────┬──────────────────────────┘
                    │
                    ▼
Step 2: SERVER AUTHENTICATES
┌──────────────────────────────────────────────┐
│ @require_api_key_flexible decorator          │
│                                              │
│ 1. Extract: api_key = "abc123..."           │
│ 2. Hash:    key_hash = sha256(api_key)      │
│ 3. Query:   SELECT * FROM api_keys          │
│             WHERE key_hash = "..." AND       │
│                   is_active = TRUE           │
│ 4. Result:  client_id = 1 (Acme Corp)       │
└───────────────────┬──────────────────────────┘
                    │
                    ▼
Step 3: SET REQUEST CONTEXT
┌──────────────────────────────────────────────┐
│ request.current_client = Client(id=1)        │
│ request.current_api_key = APIKey(id=1)       │
└───────────────────┬──────────────────────────┘
                    │
                    ▼
Step 4: ROUTE TO CLIENT-SPECIFIC RESOURCES
┌──────────────────────────────────────────────┐
│ client_buffer = get_client_buffer(1)         │
│   → Returns client_frame_buffers[1]          │
│   → Isolated from clients 2 and 3            │
│                                              │
│ client_buffer.append(frame_info)             │
│   → Frame stored in Acme's buffer only       │
└───────────────────┬──────────────────────────┘
                    │
                    ▼
Step 5: TRACK USAGE
┌──────────────────────────────────────────────┐
│ INSERT INTO api_usage (                      │
│   api_key_id = 1,  -- Links to Acme          │
│   endpoint = '/api/video/buffer',            │
│   cost = 0.01                                │
│ )                                            │
└───────────────────┬──────────────────────────┘
                    │
                    ▼
Step 6: RETURN RESPONSE
┌──────────────────────────────────────────────┐
│ {"status": "buffered",                       │
│  "frame_count": 1,                           │
│  "buffer_size": 15}                          │
│   → Only Acme's buffer size shown            │
└──────────────────────────────────────────────┘
```

---

## Data Isolation Architecture

### Database Level
```sql
-- Clients Table
| id | name       | email              |
|----|------------|--------------------|
| 1  | Acme Corp  | acme@example.com   |
| 2  | TechCo     | tech@example.com   |
| 3  | SecureInc  | secure@example.com |

-- API Keys Table
| id | client_id | key_hash                           | is_active |
|----|-----------|----------------------------------- |-----------|
| 1  | 1         | sha256(abc123...)                  | TRUE      |
| 2  | 2         | sha256(def456...)                  | TRUE      |
| 3  | 3         | sha256(ghi789...)                  | TRUE      |

-- API Usage Table (automatically isolated by api_key_id → client_id)
| id | api_key_id | endpoint          | cost  | timestamp  |
|----|------------|-------------------|-------|------------|
| 1  | 1          | /api/video/buffer | 0.01  | 2025-10-02 |  # Acme
| 2  | 1          | /api/video/analyze| 0.05  | 2025-10-02 |  # Acme
| 3  | 2          | /api/video/buffer | 0.01  | 2025-10-02 |  # TechCo
| 4  | 3          | /api/alert        | 0.10  | 2025-10-02 |  # SecureInc
```

### Memory Level (Runtime Isolation)
```python
# api_proxy.py
client_frame_buffers = {}

def get_client_buffer(client_id):
    """Each client gets their own isolated buffer"""
    if client_id not in client_frame_buffers:
        max_frames = video_config['long_buffer_duration'] * video_config['analysis_fps']
        client_frame_buffers[client_id] = deque(maxlen=max_frames)
    return client_frame_buffers[client_id]

# When Client A (id=1) calls:
buffer_a = get_client_buffer(1)  # Returns deque for Client A only

# When Client B (id=2) calls:
buffer_b = get_client_buffer(2)  # Returns deque for Client B only

# These are DIFFERENT objects in memory, completely isolated
```

---

## What Each Client Sees

### Client A's Perspective
```
My API Key: abc123...
My Buffer: [frame1, frame2, frame3, ...] (15 frames)
My Usage: 157 API calls this week, €2.43 cost

Cannot see:
  ❌ Client B's buffer
  ❌ Client B's usage
  ❌ Client B's API key
  ❌ Client C's data
```

### Client B's Perspective
```
My API Key: def456...
My Buffer: [frame1, frame2, frame3, ...] (8 frames)
My Usage: 89 API calls this week, €1.32 cost

Cannot see:
  ❌ Client A's buffer
  ❌ Client A's usage
  ❌ Client A's API key
  ❌ Client C's data
```

---

## Configuration: Shared vs. Client-Specific

### SHARED Configuration (config.ini on server)
All clients use the same:
- ✅ Gemini AI model and API key
- ✅ Email server settings
- ✅ Buffer durations (3s short, 10s long)
- ✅ Analysis FPS (25 fps)
- ✅ Video compression settings
- ✅ Database connection

### CLIENT-SPECIFIC Data (database + memory)
Each client has their own:
- ✅ API key (unique authentication)
- ✅ Frame buffer (isolated in memory)
- ✅ Usage records (cost tracking)
- ✅ Email address (for invoices)
- ✅ Payment details
- ✅ API call history

---

## Security Boundaries

```
┌─────────────────────────────────────────────────────────┐
│                   SECURITY LAYERS                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Layer 1: API Key Authentication                       │
│  ┌───────────────────────────────────────────┐         │
│  │ Only requests with valid API keys pass    │         │
│  │ Invalid keys → 401 Unauthorized            │         │
│  └───────────────────────────────────────────┘         │
│                      ▼                                  │
│  Layer 2: Client Identification                        │
│  ┌───────────────────────────────────────────┐         │
│  │ API key mapped to specific client_id      │         │
│  │ request.current_client set                 │         │
│  └───────────────────────────────────────────┘         │
│                      ▼                                  │
│  Layer 3: Data Isolation                               │
│  ┌───────────────────────────────────────────┐         │
│  │ All operations use client_id as filter    │         │
│  │ get_client_buffer(client_id)               │         │
│  │ filter_by(client_id=...)                   │         │
│  └───────────────────────────────────────────┘         │
│                      ▼                                  │
│  Layer 4: Access Control                               │
│  ┌───────────────────────────────────────────┐         │
│  │ Endpoints verify client_id matches        │         │
│  │ if current_client.id != client_id:         │         │
│  │     return 403 Access Denied               │         │
│  └───────────────────────────────────────────┘         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Billing Integration

Each client's usage is automatically tracked and billed separately:

```
Weekly Invoice Generation:
1. Query all clients: SELECT * FROM clients
2. For each client:
   - Get their API usage: SELECT * FROM api_usage 
                          JOIN api_keys ON ...
                          WHERE client_id = X
   - Calculate total cost
   - Generate HTML invoice
   - Email to client's address
3. Result: Each client receives their own invoice

Client A receives:
  Invoice #2025-W40-001
  Usage: 157 calls, €2.43
  
Client B receives:
  Invoice #2025-W40-002
  Usage: 89 calls, €1.32
```

See **README_BILLING.md** for complete billing documentation.

---

## Summary

**ONE Server** → Shared config.ini, shared resources  
**MANY Clients** → Each with unique API key  
**ISOLATED Data** → Buffers, usage, tracking all separate  
**SECURE** → Multiple layers prevent cross-client access  
**BILLABLE** → Usage tracked per client automatically  
