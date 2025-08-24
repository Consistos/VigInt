#!/usr/bin/env python3
"""Run weekly billing process - wrapper script for cron jobs"""

import sys
import os
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from generate_weekly_invoices import main as generate_invoices


def setup_cron_logging():
    """Setup logging for cron job execution"""
    log_dir = Path('/var/log/vigint')
    if not log_dir.exists():
        log_dir = Path('./logs')
        log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / 'weekly_billing.log'
    
    # Configure logging with rotation
    from logging.handlers import RotatingFileHandler
    
    handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    # Also log to stdout if not running from cron
    if os.isatty(sys.stdout.fileno()):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)


def check_if_should_run():
    """Check if billing should run today (Mondays)"""
    today = datetime.now()
    
    # Run on Mondays (weekday 0)
    if today.weekday() != 0:
        logging.info(f"Today is {today.strftime('%A')}, billing only runs on Mondays")
        return False
    
    return True


def send_notification(success, message):
    """Send notification about billing results"""
    try:
        # This could be extended to send emails, Slack notifications, etc.
        if success:
            logging.info(f"Billing completed successfully: {message}")
        else:
            logging.error(f"Billing failed: {message}")
            
        # Example: Send email notification (implement as needed)
        # send_admin_email(f"Weekly Billing {'Success' if success else 'Failure'}", message)
        
    except Exception as e:
        logging.error(f"Failed to send notification: {e}")


def main():
    """Main function for weekly billing cron job"""
    parser = argparse.ArgumentParser(description='Run weekly billing process')
    parser.add_argument('--force', action='store_true',
                       help='Force run even if not Monday')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode (no actual billing)')
    parser.add_argument('--quiet', action='store_true',
                       help='Quiet mode (minimal output)')
    
    args = parser.parse_args()
    
    # Setup logging
    if not args.quiet:
        setup_cron_logging()
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("=" * 50)
        logger.info("Weekly Billing Process Started")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info(f"Force mode: {args.force}")
        logger.info(f"Dry run mode: {args.dry_run}")
        
        # Check if we should run today
        if not args.force and not check_if_should_run():
            logger.info("Skipping billing - not scheduled to run today")
            return 0
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No actual billing will be performed")
            # In dry run, we could implement a preview of what would be billed
            return 0
        
        # Run the actual billing process
        logger.info("Starting invoice generation...")
        result = generate_invoices()
        
        if result == 0:
            message = "Weekly billing completed successfully"
            send_notification(True, message)
            logger.info(message)
        else:
            message = "Weekly billing completed with errors"
            send_notification(False, message)
            logger.error(message)
        
        logger.info("Weekly Billing Process Completed")
        logger.info("=" * 50)
        
        return result
        
    except Exception as e:
        error_msg = f"Critical error in weekly billing: {e}"
        logger.error(error_msg)
        logger.exception("Full traceback:")
        send_notification(False, error_msg)
        return 1


if __name__ == '__main__':
    sys.exit(main())