#!/usr/bin/env python3
"""Cost monitoring and alerting system for Vigint API usage"""

import sys
import logging
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import config
from vigint.models import db, APIKey, APIUsage, Client, PaymentDetails
from flask import Flask
from sqlalchemy import func


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_app():
    """Create Flask application for database context"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = config.database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app


def get_usage_stats(days=7):
    """Get usage statistics for the last N days"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Total usage across all clients
    total_stats = db.session.query(
        func.count(APIUsage.id).label('total_requests'),
        func.sum(APIUsage.cost).label('total_cost'),
        func.avg(APIUsage.cost).label('avg_cost_per_request')
    ).filter(APIUsage.timestamp >= cutoff_date).first()
    
    # Usage by client
    client_stats = db.session.query(
        Client.id,
        Client.name,
        Client.email,
        func.count(APIUsage.id).label('requests'),
        func.sum(APIUsage.cost).label('cost')
    ).join(APIKey).join(APIUsage).filter(
        APIUsage.timestamp >= cutoff_date
    ).group_by(Client.id, Client.name, Client.email).all()
    
    # Usage by endpoint
    endpoint_stats = db.session.query(
        APIUsage.endpoint,
        func.count(APIUsage.id).label('requests'),
        func.sum(APIUsage.cost).label('cost'),
        func.avg(APIUsage.cost).label('avg_cost')
    ).filter(APIUsage.timestamp >= cutoff_date).group_by(
        APIUsage.endpoint
    ).order_by(func.sum(APIUsage.cost).desc()).all()
    
    return {
        'period_days': days,
        'total': {
            'requests': total_stats.total_requests or 0,
            'cost': float(total_stats.total_cost or 0),
            'avg_cost_per_request': float(total_stats.avg_cost_per_request or 0)
        },
        'by_client': [
            {
                'client_id': stat.id,
                'name': stat.name,
                'email': stat.email,
                'requests': stat.requests,
                'cost': float(stat.cost)
            }
            for stat in client_stats
        ],
        'by_endpoint': [
            {
                'endpoint': stat.endpoint,
                'requests': stat.requests,
                'cost': float(stat.cost),
                'avg_cost': float(stat.avg_cost)
            }
            for stat in endpoint_stats
        ]
    }


def check_cost_thresholds(stats):
    """Check if any cost thresholds are exceeded"""
    alerts = []
    
    # Define thresholds (these could be moved to config)
    DAILY_COST_THRESHOLD = 100.0  # €100 per day
    WEEKLY_COST_THRESHOLD = 500.0  # €500 per week
    CLIENT_DAILY_THRESHOLD = 50.0  # €50 per client per day
    
    # Check total daily cost (approximate)
    daily_cost = stats['total']['cost'] / stats['period_days']
    if daily_cost > DAILY_COST_THRESHOLD:
        alerts.append({
            'type': 'high_daily_cost',
            'message': f"Daily cost exceeds threshold: €{daily_cost:.2f} > €{DAILY_COST_THRESHOLD}",
            'severity': 'warning'
        })
    
    # Check total weekly cost
    if stats['period_days'] >= 7 and stats['total']['cost'] > WEEKLY_COST_THRESHOLD:
        alerts.append({
            'type': 'high_weekly_cost',
            'message': f"Weekly cost exceeds threshold: €{stats['total']['cost']:.2f} > €{WEEKLY_COST_THRESHOLD}",
            'severity': 'critical'
        })
    
    # Check individual client costs
    for client in stats['by_client']:
        client_daily_cost = client['cost'] / stats['period_days']
        if client_daily_cost > CLIENT_DAILY_THRESHOLD:
            alerts.append({
                'type': 'high_client_cost',
                'message': f"Client {client['name']} daily cost: €{client_daily_cost:.2f} > €{CLIENT_DAILY_THRESHOLD}",
                'severity': 'warning',
                'client_id': client['client_id']
            })
    
    return alerts


def send_alert_email(alerts, stats):
    """Send alert email to administrators"""
    try:
        smtp_server = config.get('Email', 'smtp_server', 'smtp.gmail.com')
        smtp_port = config.getint('Email', 'smtp_port', 587)
        sender_email = config.get('Email', 'sender_email')
        sender_password = config.get('Email', 'sender_password')
        admin_email = config.get('Email', 'admin_email', sender_email)
        
        if not sender_password:
            logging.warning("No email password configured, skipping alert email")
            return False
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = admin_email
        msg['Subject'] = f"Vigint Cost Alert - {len(alerts)} alerts"
        
        # Email body
        body = f"""
Vigint Cost Monitoring Alert

Time: {datetime.now().isoformat()}
Period: Last {stats['period_days']} days

ALERTS:
"""
        
        for alert in alerts:
            body += f"- [{alert['severity'].upper()}] {alert['message']}\n"
        
        body += f"""

SUMMARY:
- Total Requests: {stats['total']['requests']:,}
- Total Cost: €{stats['total']['cost']:.2f}
- Average Cost per Request: €{stats['total']['avg_cost_per_request']:.4f}
- Daily Average Cost: €{stats['total']['cost'] / stats['period_days']:.2f}

TOP CLIENTS BY COST:
"""
        
        # Add top 5 clients by cost
        top_clients = sorted(stats['by_client'], key=lambda x: x['cost'], reverse=True)[:5]
        for client in top_clients:
            body += f"- {client['name']}: €{client['cost']:.2f} ({client['requests']:,} requests)\n"
        
        body += f"""

TOP ENDPOINTS BY COST:
"""
        
        # Add top 5 endpoints by cost
        top_endpoints = stats['by_endpoint'][:5]
        for endpoint in top_endpoints:
            body += f"- {endpoint['endpoint']}: €{endpoint['cost']:.2f} ({endpoint['requests']:,} requests)\n"
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        logging.info(f"Alert email sent to {admin_email}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send alert email: {e}")
        return False


def generate_cost_report(stats):
    """Generate a detailed cost report"""
    report = f"""
VIGINT COST MONITORING REPORT
Generated: {datetime.now().isoformat()}
Period: Last {stats['period_days']} days

SUMMARY:
========
Total Requests: {stats['total']['requests']:,}
Total Cost: €{stats['total']['cost']:.2f}
Average Cost per Request: €{stats['total']['avg_cost_per_request']:.4f}
Daily Average Cost: €{stats['total']['cost'] / stats['period_days']:.2f}

CLIENT BREAKDOWN:
================
"""
    
    for client in sorted(stats['by_client'], key=lambda x: x['cost'], reverse=True):
        daily_avg = client['cost'] / stats['period_days']
        report += f"{client['name']:<30} €{client['cost']:>8.2f} ({client['requests']:>6,} req) [€{daily_avg:.2f}/day]\n"
    
    report += f"""

ENDPOINT BREAKDOWN:
==================
"""
    
    for endpoint in stats['by_endpoint']:
        report += f"{endpoint['endpoint']:<40} €{endpoint['cost']:>8.2f} ({endpoint['requests']:>6,} req) [€{endpoint['avg_cost']:.4f}/req]\n"
    
    return report


def main():
    """Main cost monitoring function"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting cost monitoring check...")
    
    try:
        app = create_app()
        
        with app.app_context():
            # Get usage statistics for the last 7 days
            stats = get_usage_stats(days=7)
            
            # Check for cost threshold violations
            alerts = check_cost_thresholds(stats)
            
            # Generate report
            report = generate_cost_report(stats)
            
            # Log report
            logger.info("Cost monitoring report:")
            for line in report.split('\n'):
                if line.strip():
                    logger.info(line)
            
            # Send alerts if any
            if alerts:
                logger.warning(f"Found {len(alerts)} cost alerts")
                for alert in alerts:
                    logger.warning(f"[{alert['severity'].upper()}] {alert['message']}")
                
                # Send email alert
                send_alert_email(alerts, stats)
            else:
                logger.info("No cost alerts detected")
            
            # Save report to file
            report_file = Path('cost_report.txt')
            with open(report_file, 'w') as f:
                f.write(report)
            logger.info(f"Report saved to {report_file}")
            
            return 0
            
    except Exception as e:
        logger.error(f"Error in cost monitoring: {e}")
        logger.exception("Full traceback:")
        return 1


if __name__ == '__main__':
    sys.exit(main())