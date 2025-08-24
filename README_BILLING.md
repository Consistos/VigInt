# Vigint Billing System

This document describes the automated billing system for Vigint API services.

## Overview

The Vigint billing system provides automated invoice generation, payment processing, and usage tracking for API services. It supports multiple payment methods and frequencies with comprehensive reporting.

## Features

- **Automated Billing**: Weekly, monthly, and quarterly billing cycles
- **Multiple Payment Methods**: Credit cards, bank transfers, and direct debit
- **Usage Tracking**: Detailed API usage monitoring and cost calculation
- **Invoice Generation**: HTML and CSV invoice formats
- **Email Integration**: Automated invoice delivery
- **Payment Processing**: Stripe integration for credit card payments
- **Banking Integration**: Qonto integration for business banking
- **Cost Monitoring**: Real-time cost alerts and reporting

## Architecture

### Core Components

1. **Models** (`vigint/models.py`):
   - `Client`: Customer information
   - `APIKey`: API key management
   - `APIUsage`: Usage tracking and billing data
   - `PaymentDetails`: Payment method configuration

2. **Billing Manager** (`vigint/billing_manager.py`):
   - Weekly billing process
   - Usage calculation
   - Payment processing
   - Invoice generation coordination

3. **Invoice Generator** (`vigint/invoice_generator.py`):
   - HTML/CSV invoice creation
   - Email delivery
   - Qonto integration

4. **Authentication** (`auth.py`):
   - API key management
   - Usage logging for billing

## Quick Start

### Setup

1. **Configure Database**:
   ```bash
   # Initialize the database
   python3 start_vigint.py --init-db
   ```

2. **Configure Email** (in `config.ini`):
   ```ini
   [Email]
   smtp_server = smtp.gmail.com
   smtp_port = 587
   sender_email = billing@yourcompany.com
   sender_password = your-app-password
   ```

3. **Configure Payment Processing** (optional):
   ```ini
   [Stripe]
   api_key = sk_test_your_stripe_key
   webhook_secret = whsec_your_webhook_secret
   
   [Qonto]
   api_key = your-qonto-api-key
   organization_slug = your-organization
   ```

### Creating Clients

```python
from auth import create_client_with_api_key

# Create a new client with API key
client, api_key = create_client_with_api_key(
    name="Acme Corporation",
    email="billing@acme.com"
)

print(f"Client created with API key: {api_key}")
```

### Setting Up Payment Details

```python
from vigint.models import PaymentDetails, PaymentMethod, PaymentFrequency

# Create payment details for a client
payment_details = PaymentDetails(
    api_key_id=api_key_record.id,
    payment_method=PaymentMethod.CREDIT_CARD,
    payment_frequency=PaymentFrequency.MONTHLY,
    auto_pay_enabled=True,
    stripe_customer_id="cus_stripe_customer_id",
    stripe_payment_method_id="pm_stripe_payment_method"
)

db.session.add(payment_details)
db.session.commit()
```

## Billing Process

### Automated Weekly Billing

The system runs weekly billing every Monday:

```bash
# Manual run
python3 generate_weekly_invoices.py

# Cron job (add to crontab)
0 9 * * 1 /path/to/vigint/run_weekly_billing.py
```

### Billing Workflow

1. **Usage Collection**: API usage is tracked in real-time
2. **Billing Period Calculation**: Based on payment frequency
3. **Cost Calculation**: Usage × rate + VAT
4. **Invoice Generation**: HTML and CSV formats
5. **Payment Processing**: Automatic payment attempt
6. **Email Delivery**: Invoice sent to client
7. **Next Billing Date**: Calculated and scheduled

### Usage Tracking

Every API call is automatically logged:

```python
# Automatic usage logging (in api_proxy.py)
log_api_usage(
    api_key_id=request.current_api_key.id,
    endpoint='/api/rtsp/streams',
    method='GET',
    status_code=200,
    cost=0.001  # €0.001 per request
)
```

## Payment Methods

### Credit Card (Stripe)

```python
# Configure Stripe payment method
payment_details = PaymentDetails(
    payment_method=PaymentMethod.CREDIT_CARD,
    stripe_customer_id="cus_...",
    stripe_payment_method_id="pm_..."
)
```

### Bank Transfer

```python
# Configure bank transfer
payment_details = PaymentDetails(
    payment_method=PaymentMethod.BANK_TRANSFER,
    bank_account_iban="DE89370400440532013000",
    bank_account_bic="COBADEFFXXX"
)
```

### Direct Debit

```python
# Configure direct debit
payment_details = PaymentDetails(
    payment_method=PaymentMethod.DIRECT_DEBIT,
    bank_account_iban="DE89370400440532013000",
    bank_account_bic="COBADEFFXXX"
)
```

## Invoice Generation

### HTML Invoices

Invoices include:
- Company information
- Client details
- Billing period
- Usage breakdown by service
- VAT calculation (21%)
- Total amount

### CSV Export

Machine-readable format for accounting systems:
```csv
Invoice Number,VIGINT-2024-0001
Client Name,Acme Corporation
Billing Period,2024-01-01 to 2024-01-07
Service,Quantity,Unit Price (EUR),Total (EUR)
RTSP Streaming,1000,0.0010,1.00
API Calls,5000,0.0005,2.50
```

## Cost Monitoring

### Real-time Monitoring

```bash
# Run cost monitoring
python3 cost_monitor.py
```

### Alerts

The system monitors for:
- Daily cost thresholds (€100/day)
- Weekly cost thresholds (€500/week)
- Per-client thresholds (€50/client/day)

### Reports

Generate detailed cost reports:
```bash
# Generate report
python3 cost_monitor.py > cost_report.txt
```

## API Integration

### Usage Tracking API

```bash
# Get usage for current client
curl -H "X-API-Key: your-api-key" \
  http://localhost:5000/api/usage
```

### Billing API

```bash
# Get billing information
curl -H "X-API-Key: your-api-key" \
  http://localhost:5000/api/billing/invoices

# Get payment methods
curl -H "X-API-Key: your-api-key" \
  http://localhost:5000/api/billing/payment-methods
```

## Configuration

### Billing Settings

```ini
[Billing]
# Default cost per API request (EUR)
default_cost_per_request = 0.001

# VAT rate (21% for EU)
vat_rate = 0.21

# Currency
currency = EUR

# Invoice number format
invoice_number_format = VIGINT-{year}-{number:04d}
```

### Email Templates

Customize email templates in `invoice_generator.py`:

```python
def generate_invoice_email(client_name, invoice_number, amount):
    return f"""
    Dear {client_name},
    
    Your invoice {invoice_number} for €{amount:.2f} is ready.
    
    Thank you for using Vigint services!
    """
```

## Database Schema

### Key Tables

```sql
-- Clients
CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- API Keys
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id),
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- Usage Tracking
CREATE TABLE api_usage (
    id SERIAL PRIMARY KEY,
    api_key_id INTEGER REFERENCES api_keys(id),
    endpoint VARCHAR(255) NOT NULL,
    cost DECIMAL(10,6) NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Payment Details
CREATE TABLE payment_details (
    id SERIAL PRIMARY KEY,
    api_key_id INTEGER REFERENCES api_keys(id),
    payment_method VARCHAR(50) NOT NULL,
    payment_frequency VARCHAR(50) NOT NULL,
    auto_pay_enabled BOOLEAN DEFAULT FALSE,
    next_payment_date DATE,
    last_invoice_number VARCHAR(255)
);
```

## Cron Jobs

### Weekly Billing

```bash
# Add to crontab (runs every Monday at 9 AM)
0 9 * * 1 /path/to/vigint/run_weekly_billing.py

# With logging
0 9 * * 1 /path/to/vigint/run_weekly_billing.py >> /var/log/vigint/billing.log 2>&1
```

### Cost Monitoring

```bash
# Daily cost monitoring (runs every day at 8 AM)
0 8 * * * /path/to/vigint/cost_monitor.py

# Hourly monitoring for high-usage periods
0 * * * * /path/to/vigint/cost_monitor.py --quick
```

## Troubleshooting

### Common Issues

1. **Email Delivery Fails**:
   ```bash
   # Check email configuration
   python3 -c "from config import config; print(config.get('Email', 'smtp_server'))"
   
   # Test email connectivity
   telnet smtp.gmail.com 587
   ```

2. **Payment Processing Fails**:
   ```bash
   # Check Stripe configuration
   python3 -c "import stripe; stripe.api_key='sk_test_...'; print(stripe.Account.retrieve())"
   ```

3. **Database Connection Issues**:
   ```bash
   # Test database connection
   python3 -c "from vigint.models import db; print('DB connected')"
   ```

### Debug Mode

Enable debug logging:
```ini
[Logging]
level = DEBUG
```

### Manual Invoice Generation

```python
from vigint.billing_manager import process_weekly_billing

# Run billing manually
results = process_weekly_billing()
print(f"Success: {len(results['success'])}, Failed: {len(results['failed'])}")
```

## Security Considerations

1. **API Key Security**: Store hashed versions only
2. **Payment Data**: Use tokenization (Stripe tokens)
3. **Email Security**: Use app passwords, not account passwords
4. **Database**: Encrypt sensitive payment information
5. **Audit Trail**: Log all billing operations

## Performance Optimization

### Database Indexing

```sql
-- Optimize usage queries
CREATE INDEX idx_api_usage_timestamp ON api_usage(timestamp);
CREATE INDEX idx_api_usage_api_key_timestamp ON api_usage(api_key_id, timestamp);

-- Optimize billing queries
CREATE INDEX idx_payment_details_next_payment ON payment_details(next_payment_date);
```

### Batch Processing

For high-volume usage:
```python
# Batch insert usage records
usage_records = []
for usage in batch:
    usage_records.append(APIUsage(...))

db.session.bulk_save_objects(usage_records)
db.session.commit()
```

## Compliance

### GDPR Compliance

- Client data retention policies
- Right to data deletion
- Data export capabilities
- Privacy policy updates

### Financial Compliance

- Invoice numbering requirements
- VAT calculation accuracy
- Audit trail maintenance
- Financial reporting

## Support

For billing system issues:
- Check logs: `/var/log/vigint/billing.log`
- Monitor database: Check `api_usage` and `payment_details` tables
- Email delivery: Verify SMTP settings and authentication
- Payment processing: Check Stripe dashboard for failed payments

Contact: billing-support@vigint.com