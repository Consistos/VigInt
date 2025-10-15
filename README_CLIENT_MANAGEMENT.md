# Client Management Guide

## Overview

Each client in Vigint has **unique API keys** that are generated when the client is created. This allows you to control access on a per-client basis, including revoking access for non-paying users.

## How API Keys Work

1. **Unique Per Client**: Each time you create a client, a new random 32-character API key is generated
2. **Secure Storage**: API keys are hashed (SHA-256) before storage - the plain text is never saved
3. **Client Linking**: Each API key is linked to a specific client via `client_id`
4. **Revocable**: API keys can be deactivated without deleting the client data

## Management Script

Use `manage_clients.py` for all client operations:

### List All Clients

```bash
python manage_clients.py --list
```

Shows all clients with their API key status (active/revoked).

### Create New Client

```bash
python manage_clients.py --create --name "Acme Corp" --email "billing@acme.com"
```

**Output:**
- Client ID
- Client details
- **🔑 The generated API key** (save this - it cannot be retrieved later!)

### Revoke Access (Non-Paying User)

```bash
# First, list clients to get the ID
python manage_clients.py --list

# Revoke access for client ID 3
python manage_clients.py --revoke --client-id 3
```

This deactivates all API keys for the client. They can no longer access the API, but their data remains for record-keeping.

### Reactivate Access

```bash
# Reactivate all API keys for a client
python manage_clients.py --reactivate --client-id 3

# Reactivate a specific API key
python manage_clients.py --reactivate --client-id 3 --key-id 7
```

### Delete Client Permanently

```bash
python manage_clients.py --delete --client-id 3
```

**⚠️ WARNING**: This permanently deletes:
- The client record
- All API keys
- All API usage history
- All payment details

This cannot be undone!

## Workflow for Non-Paying Users

### Step 1: Identify the Client
```bash
python manage_clients.py --list
```

### Step 2: Revoke Access
```bash
python manage_clients.py --revoke --client-id 3
```

The client's API requests will now return `401 Invalid API key` errors.

### Step 3: (Optional) Reactivate After Payment
```bash
python manage_clients.py --reactivate --client-id 3
```

### Step 4: (Optional) Delete if Never Returning
```bash
python manage_clients.py --delete --client-id 3
```

## API Key Authentication Flow

When a request comes in with an API key:

1. System hashes the provided API key
2. Looks up the hash in the `api_keys` table
3. Checks if `is_active = True`
4. Retrieves the associated client
5. Grants or denies access

## Multiple API Keys Per Client

Clients can have multiple API keys (e.g., for different services):

```bash
# Create additional key by adding a new APIKey record manually
# Or enhance the script to support this
```

## Best Practices

1. **Save API keys immediately** - They're only shown once during creation
2. **Revoke instead of delete** - Preserves billing history and usage data
3. **Use meaningful names** - When creating clients, use company names for easy identification
4. **Regular audits** - Periodically review active clients and their usage
5. **Monitor failed auth attempts** - Multiple 401 errors may indicate a revoked client trying to access

## Integration with Billing

The client management system integrates with the invoice generation:

- Revoked clients won't incur new charges
- Historical usage data remains for past invoices
- Reactivated clients resume normal billing

## Security Notes

- API keys are 32-character URL-safe tokens (256 bits of entropy)
- Stored as SHA-256 hashes (not reversible)
- Each key is cryptographically unique
- Keys can be rotated by creating new ones and revoking old ones
