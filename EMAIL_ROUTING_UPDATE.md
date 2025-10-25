# Email Alert Routing Update

## Overview
Modified the email alert system to send alerts to the current client's email address instead of using the globally configured `EMAIL_TO` environment variable.

## Changes Made

### 1. `alerts.py` - AlertManager Updates

#### Modified `send_email_alert()` method:
- Added new parameter: `recipient_email=None`
- When `recipient_email` is provided, it overrides the configured admin email
- Falls back to configured `EMAIL_TO` when `recipient_email` is not provided
- Updated method signature:
  ```python
  def send_email_alert(self, message, alert_type="info", video_path=None, 
                       incident_data=None, recipient_email=None)
  ```

#### Modified `send_security_alert_with_video()` function:
- Added new parameter: `recipient_email=None`
- Passes `recipient_email` through to all `send_email_alert()` calls
- Updated function signature:
  ```python
  def send_security_alert_with_video(message, frames=None, incident_data=None, 
                                     recipient_email=None)
  ```

### 2. `api_proxy.py` - Main API Endpoint Updates

#### Updated `/api/video/alert` endpoint:
- **Line 2135-2144**: Removed requirement for `EMAIL_TO` environment variable
- **Line 2141-2144**: Added validation to ensure client has an email address configured
- **Line 2188**: Changed email recipient from `email_config['to_email']` to `request.current_client.email`
- **Line 2383**: Updated response to show client's email instead of configured EMAIL_TO

## How It Works

### For API Requests (Authenticated Clients):
1. Client makes authenticated API request with their API key
2. The `@require_api_key_flexible` decorator validates the key and sets `request.current_client`
3. Alert email is sent to `request.current_client.email` (from the `clients` table)
4. Response JSON shows which email address received the alert

### For Standalone/Local Processing:
- When `video_analyzer.py` or `vigint/app.py` send alerts without API context
- No `recipient_email` is provided, so alerts fall back to configured `EMAIL_TO`
- This maintains backward compatibility for non-API alert scenarios

## Database Schema

The system relies on the `Client` model in `vigint/models.py`:

```python
class Client(db.Model):
    __tablename__ = 'clients'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)  # Used for alerts
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## Environment Variables

### Still Required:
- `EMAIL_USERNAME` or `ALERT_EMAIL` - SMTP credentials
- `EMAIL_PASSWORD` or `ALERT_EMAIL_PASSWORD` - SMTP password
- `EMAIL_SMTP_SERVER` or `ALERT_SMTP_SERVER` - SMTP server
- `EMAIL_SMTP_PORT` or `ALERT_SMTP_PORT` - SMTP port

### No Longer Required for API Alerts:
- `EMAIL_TO` - Only used as fallback for non-API scenarios

### Deprecated (but kept for backward compatibility):
- `ADMIN_EMAIL` - Only used when no client context and EMAIL_TO not set

## Benefits

1. **Client Isolation**: Each client receives their own security alerts
2. **Multi-Tenant Support**: Multiple clients can use the same Vigint instance
3. **Cleaner Configuration**: No need to reconfigure EMAIL_TO per client
4. **Security**: Clients only receive alerts for their own incidents
5. **Scalability**: Easier to manage alerts for many clients

## Testing Recommendations

1. **Verify client email in database**:
   ```sql
   SELECT id, name, email FROM clients WHERE email IS NOT NULL;
   ```

2. **Test API alert endpoint**:
   ```bash
   curl -X POST https://your-domain.com/api/video/alert \
     -H "X-API-Key: your_api_key" \
     -H "Content-Type: application/json" \
     -d '{
       "analysis": "Test alert",
       "risk_level": "LOW",
       "incident_type": "test"
     }'
   ```

3. **Check response includes client email**:
   ```json
   {
     "success": true,
     "to": "client@example.com",
     "client_name": "Client Name",
     ...
   }
   ```

## Migration Notes

### For Existing Clients:
- Ensure all clients in the database have valid email addresses
- Run this query to check for clients without emails:
  ```sql
  SELECT * FROM clients WHERE email IS NULL OR email = '';
  ```

### For New Client Setup:
- Email address is required when creating a new client
- The `create_client_with_api_key()` function in `auth.py` requires an email parameter

## Error Handling

The system now returns a `400 Bad Request` if:
- Client email is not configured in database: `"Client email address not configured in database"`

The system still returns a `503 Service Unavailable` if:
- SMTP credentials are missing: `"Email not configured - Missing: EMAIL_USERNAME"`

## Backward Compatibility

- Standalone scripts (`video_analyzer.py`, `vigint/app.py`) continue to work
- Test scripts that call alert functions directly still use configured EMAIL_TO
- No breaking changes to the alert API interface
