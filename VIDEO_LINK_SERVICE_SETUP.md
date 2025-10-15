# Video Link Service Setup Guide

The Vigint system now uses **private video links** instead of email attachments for security incident videos. Videos are uploaded to sparse-ai.com and secure, time-limited links are sent via email.

## 🎯 Benefits

- **No email size limits**: Videos of any size can be shared
- **Better security**: Private links with automatic expiration
- **Faster delivery**: No large attachments to slow down emails
- **Professional presentation**: Clean email with secure access links
- **Automatic cleanup**: Videos expire automatically after set time

## 📋 Configuration

### 1. Update config.ini

Add the SparseAI configuration section to your `config.ini`:

```ini
[SparseAI]
# Sparse AI video hosting service configuration
api_key = your-sparse-ai-api-key-here
base_url = https://sparse-ai.com
default_expiration_hours = 48
```

### 2. Environment Variables (Alternative)

You can also configure using environment variables:

```bash
export SPARSE_AI_API_KEY="your-api-key-here"
export SPARSE_AI_BASE_URL="https://sparse-ai.com"
export VIDEO_LINK_EXPIRATION_HOURS="48"
```

### 3. Get Your API Key

1. Visit [sparse-ai.com](https://sparse-ai.com)
2. Create an account or log in
3. Navigate to API Settings
4. Generate a new API key for video uploads
5. Copy the key to your configuration

## 🚀 How It Works

### Before (Email Attachments)
```
1. Incident detected
2. Video created from frames
3. Video compressed for email
4. Large attachment sent via email
5. Email delivery may fail due to size
```

### After (Private Links)
```
1. Incident detected
2. Video created from frames
3. Video uploaded to sparse-ai.com
4. Private link generated with expiration
5. Clean email sent with secure link
6. Video automatically expires after set time
```

## 📧 Email Format

The new email format includes:

```
🚨 ALERTE SYSTÈME VIGINT

Type d'alerte: SECURITY
Horodatage: 2024-12-19T10:30:00

Message:
Security incident detected in Store Section A

DÉTAILS DE L'INCIDENT:
Niveau de risque: HIGH
Numéro d'image: 150
Confiance: 0.9

📹 PREUVES VIDÉO DISPONIBLES
Lien privé sécurisé: https://sparse-ai.com/video/abc123?token=xyz789
Taille du fichier: 15.2 MB
Expiration: 2024-12-21T10:30:00
ID Vidéo: abc123-def456-ghi789

⚠️ IMPORTANT: Ce lien est privé et sécurisé. Il expirera automatiquement dans 48 heures.
Cliquez sur le lien pour visualiser la vidéo de l'incident.
```

## 🔧 Testing

Run the test script to verify everything is working:

```bash
python test_video_link_service.py
```

This will test:
- Video upload functionality
- Private link generation
- Link verification
- Email integration
- Error handling

## 🛠️ API Usage

### Upload Video Directly

```python
from video_link_service import upload_incident_video

incident_data = {
    'incident_type': 'shoplifting',
    'risk_level': 'HIGH',
    'analysis': 'Customer concealing merchandise',
    'frame_count': 75,
    'confidence': 0.9
}

result = upload_incident_video('video.mp4', incident_data, expiration_hours=24)

if result['success']:
    print(f"Private link: {result['private_link']}")
    print(f"Expires: {result['expiration_time']}")
else:
    print(f"Upload failed: {result['error']}")
```

### Create Video from Frames and Upload

```python
from video_link_service import create_and_upload_video_from_frames

# frames is a list of frame dictionaries with 'frame_data' (base64)
result = create_and_upload_video_from_frames(frames, incident_data)

if result['success']:
    print(f"Video ID: {result['video_id']}")
    print(f"Private link: {result['private_link']}")
```

### Send Alert with Video Link

```python
from alerts import send_security_alert_with_video

message = "Security incident detected"
result = send_security_alert_with_video(message, frames, incident_data)

if result['success']:
    print("Alert sent with video link")
    if result.get('video_link_info'):
        print(f"Video link: {result['video_link_info']['private_link']}")
```

## 🔒 Security Features

- **Private Links**: Each video gets a unique, non-guessable URL
- **Token-based Access**: Links include secure tokens for verification
- **Automatic Expiration**: Videos are automatically deleted after expiration
- **File Integrity**: SHA256 hashes verify file integrity
- **Access Logging**: All access attempts are logged

## ⚙️ Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `api_key` | Your Sparse AI API key | Required |
| `base_url` | Sparse AI service URL | https://sparse-ai.com |
| `default_expiration_hours` | Default link expiration time | 24 hours |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `SPARSE_AI_API_KEY` | API key (overrides config) |
| `SPARSE_AI_BASE_URL` | Service URL (overrides config) |
| `VIDEO_LINK_EXPIRATION_HOURS` | Default expiration (overrides config) |

## 🚨 Error Handling

The system gracefully handles various error scenarios:

- **No API Key**: Falls back to text-only alerts
- **Upload Failure**: Includes error message in email
- **Network Issues**: Retries with exponential backoff
- **Service Unavailable**: Sends alert without video link

## 📊 Monitoring

Check logs for video link service activity:

```bash
# Look for video upload logs
grep "sparse-ai.com" vigint.log

# Check for upload successes
grep "Video uploaded to sparse-ai.com" vigint.log

# Check for upload failures
grep "Failed to upload video" vigint.log
```

## 🔄 Migration from Email Attachments

The system automatically uses video links when configured. No code changes needed for existing alert calls.

### Backward Compatibility

- If Sparse AI is not configured, system falls back to text-only emails
- Existing alert functions work unchanged
- No breaking changes to API endpoints

## 📞 Support

If you encounter issues:

1. Check your API key configuration
2. Verify network connectivity to sparse-ai.com
3. Run the test script for diagnostics
4. Check logs for detailed error messages
5. Ensure sufficient disk space for temporary video files

## 🎉 Ready to Use

Once configured, the system will automatically:
- Upload incident videos to sparse-ai.com
- Generate secure private links
- Send clean emails with video access
- Handle all cleanup and expiration automatically

Your security alerts are now more reliable, professional, and secure! 🔒✨