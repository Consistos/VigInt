# Vigint Secure Video Analysis Architecture

## 🔒 Security Overview

The Vigint video analysis system now uses a secure client-server architecture where all sensitive credentials and AI processing happen server-side through an API proxy.

## 🏗️ Architecture Components

### 1. API Proxy (`api_proxy.py`)
- **Purpose**: Secure server-side processing of all sensitive operations
- **Features**:
  - Gemini AI analysis (server-side only)
  - Email alert sending (server-side only)
  - API key authentication
  - Usage tracking and billing
  - No credentials exposed to clients

### 2. Secure Video Analyzer (`vigint/app.py`)
- **Purpose**: Client-side video processing that communicates with API proxy
- **Features**:
  - RTSP video stream processing
  - Frame capture and encoding
  - API proxy communication
  - No direct AI or email credentials

### 3. Authentication System (`auth.py`)
- **Purpose**: API key management and client authentication
- **Features**:
  - Secure API key generation
  - Client management
  - Usage tracking

## 🔐 Security Benefits

### Credentials Protection
- ✅ **Gemini API Key**: Stored only on server, never exposed to clients
- ✅ **Email Credentials**: Stored only on server, never exposed to clients
- ✅ **API Keys**: Hashed and stored securely in database

### Client-Server Separation
- ✅ **Client Side**: Only handles video capture and basic processing
- ✅ **Server Side**: Handles all AI analysis and email sending
- ✅ **Communication**: Secured via API keys and HTTPS-ready

### Access Control
- ✅ **API Authentication**: All sensitive endpoints require valid API keys
- ✅ **Usage Tracking**: All API calls are logged for billing and monitoring
- ✅ **Client Isolation**: Each client has separate API keys and usage tracking

## 📡 API Endpoints

### Video Analysis
- `POST /api/video/analyze` - Analyze video frame using Gemini AI
- `POST /api/video/alert` - Send security alert email

### Management
- `GET /api/health` - Health check
- `GET /api/usage` - Get API usage statistics

### Legacy Proxies
- `/api/rtsp/*` - RTSP server management
- `/api/billing/*` - Billing operations

## 🚀 Usage

### 1. Create API Key
```bash
python3 create_api_key.py
```

### 2. Set Environment Variable
```bash
export VIGINT_API_KEY=your_generated_api_key
```

### 3. Start Secure System
```bash
python3 start_vigint.py --video-input /path/to/video.mp4
```

## 🔄 Data Flow

1. **Video Capture**: Client captures RTSP video frames
2. **Frame Processing**: Client encodes frames to base64
3. **API Request**: Client sends frame data to `/api/video/analyze`
4. **Server Analysis**: API proxy processes frame with Gemini AI
5. **Security Detection**: Server detects security events
6. **Alert Sending**: Server sends email alerts via `/api/video/alert`
7. **Usage Logging**: All operations logged for billing

## 📊 Current Status

✅ **Working Components**:
- Secure video analysis via API proxy
- Email alerts sent server-side
- API key authentication
- Usage tracking and logging
- Client-server separation

✅ **Security Features**:
- No credentials on client side
- All sensitive operations server-side
- API key-based authentication
- Usage monitoring and billing ready

✅ **Test Results**:
- Security events detected and analyzed
- Email alerts sent successfully
- API authentication working
- All HTTP requests returning 200 status

## 🎯 Benefits Over Previous Architecture

### Before (Insecure)
- ❌ Gemini API key in client code
- ❌ Email credentials in client code
- ❌ Direct AI API calls from client
- ❌ No usage tracking or billing

### After (Secure)
- ✅ All credentials server-side only
- ✅ API proxy handles all sensitive operations
- ✅ Client only handles video processing
- ✅ Full usage tracking and billing ready
- ✅ Scalable multi-client architecture

The system is now production-ready with proper security architecture!