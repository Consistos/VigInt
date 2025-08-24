# Vigint API Services

A comprehensive platform providing RTSP video streaming and automated billing services with API management.

## 🚀 Features

### RTSP Streaming
- **Real-time Video Streaming** using MediaMTX
- **Multiple Input Sources** (cameras, files, live streams)
- **API-controlled Stream Management**
- **Authentication & Access Control**
- **Recording Capabilities**
- **Built-in Metrics & Monitoring**

### Billing System
- **Automated Invoice Generation** (weekly/monthly/quarterly)
- **Multiple Payment Methods** (credit cards, bank transfers, direct debit)
- **Real-time Usage Tracking**
- **Cost Monitoring & Alerts**
- **Email Invoice Delivery**
- **Stripe & Qonto Integration**

### API Management
- **API Key Authentication**
- **Usage-based Billing**
- **Rate Limiting & Monitoring**
- **Comprehensive Logging**

## 📋 Quick Start

### Prerequisites

- Python 3.8+
- MediaMTX binary (for RTSP functionality)
- Database (SQLite/PostgreSQL/MySQL)

### Installation

1. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd vigint
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure**:
   ```bash
   # Copy configuration templates
   cp config.ini.example config.ini
   cp server_config.ini.example server_config.ini
   
   # Edit configuration files with your settings
   nano config.ini
   ```

3. **Initialize Database**:
   ```bash
   python3 start_vigint.py --init-db
   ```

4. **Download MediaMTX** (for RTSP functionality):
   ```bash
   # Download from https://github.com/bluenviron/mediamtx/releases
   wget https://github.com/bluenviron/mediamtx/releases/latest/download/mediamtx_linux_amd64.tar.gz
   tar -xzf mediamtx_linux_amd64.tar.gz
   chmod +x mediamtx
   ```

### Running the Application

```bash
# Start full application (API + RTSP)
./start.sh

# Start only API server
./start.sh api

# Start only RTSP server
./start.sh rtsp

# Or use Python directly
python3 start_vigint.py --mode full
```

## 📖 Documentation

- **[RTSP Server Guide](README_RTSP.md)** - Complete RTSP streaming documentation
- **[Billing System Guide](README_BILLING.md)** - Billing and payment processing documentation

## 🔧 Configuration

### Basic Configuration (`config.ini`)

```ini
[Database]
database_url = sqlite:///vigint.db

[API]
secret_key = your-secret-key
host = 0.0.0.0
port = 5000

[Email]
smtp_server = smtp.gmail.com
smtp_port = 587
sender_email = your-email@example.com
sender_password = your-app-password

[Stripe]
api_key = sk_test_your_stripe_key
```

### Environment Variables

```bash
export VIGINT_CONFIG_PATH=/path/to/config.ini
export VIGINT_SERVER_CONFIG_PATH=/path/to/server_config.ini
```

## 🔐 API Usage

### Authentication

```bash
# Get API key (create client first)
curl -X POST http://localhost:5000/api/clients \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Client", "email": "test@example.com"}'
```

### RTSP Streaming

```bash
# List streams
curl -H "X-API-Key: your-api-key" \
  http://localhost:5000/api/rtsp/paths/list

# Stream URL format
rtsp://localhost:8554/stream_name
```

### Usage Monitoring

```bash
# Get usage statistics
curl -H "X-API-Key: your-api-key" \
  http://localhost:5000/api/usage
```

## 🔄 Automated Billing

### Setup Cron Jobs

```bash
# Weekly billing (Mondays at 9 AM)
0 9 * * 1 /path/to/vigint/run_weekly_billing.py

# Daily cost monitoring
0 8 * * * /path/to/vigint/cost_monitor.py
```

### Manual Billing

```bash
# Generate invoices manually
python3 generate_weekly_invoices.py

# Run cost monitoring
python3 cost_monitor.py
```

## 🏗️ Project Structure

```
vigint/
├── vigint/                     # Core package
│   ├── models.py              # Database models
│   ├── billing_manager.py     # Billing system
│   └── invoice_generator.py   # Invoice generation
├── config.py                  # Configuration management
├── auth.py                    # Authentication system
├── api_proxy.py               # API proxy and routing
├── rtsp_server.py             # RTSP server management
├── start_vigint.py            # Main application entry
├── start.sh                   # Startup script
├── mediamtx_simple.yml        # MediaMTX configuration
├── generate_weekly_invoices.py # Invoice generation
├── cost_monitor.py            # Cost monitoring
└── requirements.txt           # Dependencies
```

## 🔍 Monitoring & Logging

### Health Checks

```bash
# API health
curl http://localhost:5000/api/health

# RTSP server status
./start_rtsp_server status

# MediaMTX API
curl http://localhost:9997/v1/config/global/get
```

### Logs

- **Application**: `vigint.log`
- **MediaMTX**: `mediamtx.log`
- **Billing**: `/var/log/vigint/billing.log`

## 🧪 Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=vigint
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy vigint/
```

## 🐳 Docker Support

```bash
# Build image
docker build -t vigint .

# Run container
docker run -p 5000:5000 -p 8554:8554 vigint
```

## 📊 Metrics & Monitoring

### Prometheus Metrics

```bash
# MediaMTX metrics
curl http://localhost:9998/metrics

# Application metrics
curl http://localhost:5000/metrics
```

### Cost Alerts

The system automatically monitors:
- Daily cost thresholds
- Per-client usage limits
- Unusual usage patterns

## 🔒 Security

- **API Key Authentication** with secure hashing
- **Payment Tokenization** via Stripe
- **Configuration Security** with example templates
- **Audit Logging** for all operations
- **Rate Limiting** and usage monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check README_RTSP.md and README_BILLING.md
- **Issues**: Create an issue on GitHub
- **Email**: support@vigint.com

## 🔄 Changelog

See CHANGELOG.md for version history and updates.

---

**Vigint** - Professional API services with integrated RTSP streaming and automated billing.