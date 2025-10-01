# Vigint Secure Video Analysis - Quick Start 🚀

## ✅ Recommended Secure Usage

### 1. **Main Application (Recommended)**
```bash
# Start the full secure application
python start_vigint.py --video-input /path/to/your/video.mp4

# Or with RTSP stream
python start_vigint.py --mode full
```

**Features**:
- 🔒 Secure API proxy architecture
- 🇫🇷 French email alerts with incident types
- 📹 Automatic video streaming and analysis
- 🔄 Local fallback if API proxy unavailable

### 2. **Standalone Secure Analyzer**
```bash
# Direct secure analysis of RTSP stream
python secure_video_analyzer.py --rtsp-url rtsp://localhost:8554/stream
```

**Features**:
- 🔒 Secure API proxy integration
- 🇫🇷 French email alerts
- 🏷️ incident_type in email subjects

## 🔧 Configuration

### Required Environment Variables:
```bash
# API Proxy Authentication
export VIGINT_API_KEY="your-api-key-here"

# Email Configuration (Server-side)
export ALERT_EMAIL="alerts@yourcompany.com"
export ALERT_EMAIL_PASSWORD="your-app-password"
export ADMIN_EMAIL="admin@yourcompany.com"

# Gemini AI (Server-side)
export GOOGLE_API_KEY="your-gemini-api-key"
```

### Configuration File (`config.ini`):
```ini
[VideoAnalysis]
short_buffer_duration = 3
long_buffer_duration = 10
analysis_interval = 3
analysis_fps = 25
video_format = mp4

[Email]
smtp_server = smtp.gmail.com
smtp_port = 587
```

## 📧 Email Alert Examples

### Subject Lines:
```
🚨 Vigint Alert - vol à l'étalage - [HIGH] - 2025-08-29 17:32:00
🚨 Vigint Alert - comportement suspect - SECURITY
🚨 Vigint Alert - activité suspecte - [MEDIUM]
```

### Email Content (French):
```
🚨 ALERTE SÉCURITÉ VIGINT - RISQUE HIGH

Client: Your Store
Heure: 2025-08-29 17:32:00 UTC
Niveau de risque: HIGH
Type d'incident: vol à l'étalage

ANALYSE:
Comportement suspect détecté: personne dissimulant des marchandises dans un sac sans passer à la caisse.

Ceci est une alerte automatique du système de sécurité Vigint.
Veuillez examiner immédiatement les images vidéo ci-jointes.

📹 Preuves vidéo jointes (8.5 secondes)
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Video Stream   │───▶│ SecureAnalyzer  │───▶│   API Proxy     │
│                 │    │                 │    │                 │
│ • RTSP/File     │    │ • Frame buffer  │    │ • Gemini AI     │
│ • Real-time     │    │ • Local fallback│    │ • Email sending │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                               ┌─────────────────┐
                                               │ French Emails   │
                                               │ with incident   │
                                               │ types & video   │
                                               └─────────────────┘
```

## 🧪 Testing

### Test the System:
```bash
# Test secure analyzer
python test_secure_analyzer_french.py

# Test email functionality
python test_french_email_fix.py

# Test incident type integration
python test_final_incident_type_fix.py
```

### Expected Results:
- ✅ All tests pass
- ✅ French email content
- ✅ incident_type in subjects
- ✅ No duplicate analysis

## 🔍 Incident Types Detected

Common incident types in French:
- `vol à l'étalage` (shoplifting)
- `vol` (theft)
- `comportement suspect` (suspicious behavior)
- `activité suspecte` (suspicious activity)
- `vandalisme` (vandalism)

## 🚨 Security Notes

### ✅ **DO USE** (Secure):
- `start_vigint.py` - Main application
- `secure_video_analyzer.py` - Standalone secure script
- `vigint.app.SecureVideoAnalyzer` - Secure class

### ❌ **DON'T USE** (Insecure):
- `video_analyzer.py` - Stores credentials client-side
- Direct Gemini API calls from client
- Hardcoded credentials

## 🆘 Troubleshooting

### Common Issues:

1. **API Proxy Connection Failed**
   ```
   Solution: Ensure API proxy is running on port 5002
   Check: python api_proxy.py
   ```

2. **Email Not Sending**
   ```
   Solution: Check email environment variables
   Test: python check_email_config.py
   ```

3. **No incident_type in Subject**
   ```
   Solution: Ensure Gemini API key is configured
   Check: API proxy logs for analysis results
   ```

4. **Video Stream Issues**
   ```
   Solution: Check RTSP server on port 8554
   Test: VLC → Open Network Stream → rtsp://localhost:8554/stream
   ```

## 📞 Support

For issues:
1. Check logs in console output
2. Verify environment variables are set
3. Test individual components
4. Check API proxy connectivity

---

**🎯 Quick Command**: `python start_vigint.py --video-input your_video.mp4` for full secure operation!