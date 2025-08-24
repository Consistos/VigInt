#!/usr/bin/env python3
"""Generate weekly invoices for all clients with auto-pay enabled"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import config
from vigint.models import db
from vigint.billing_manager import process_weekly_billing
from flask import Flask


def setup_logging():
    """Setup logging configuration"""
    log_level = config.get('Logging', 'level', 'INFO')
    log_file = config.get('Logging', 'file', 'weekly_billing.log')
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def create_app():
    """Create Flask application for database context"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = config.database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app


def main():
    """Main function to generate weekly invoices"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting weekly invoice generation...")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    try:
        # Create Flask app for database context
        app = create_app()
        
        with app.app_context():
            # Process weekly billing
            results = process_weekly_billing()
            
            # Log results
            successful_count = len(results['success'])
            failed_count = len(results['failed'])
            
            logger.info(f"Weekly billing completed:")
            logger.info(f"  Successful: {successful_count}")
            logger.info(f"  Failed: {failed_count}")
            
            # Log successful invoices
            for success in results['success']:
                if 'invoice_number' in success:
                    logger.info(f"  ✓ {success['client_name']}: {success['invoice_number']} - €{success['amount']:.2f}")
                else:
                    logger.info(f"  ✓ {success['client_name']}: No usage to bill")
            
            # Log failed invoices
            for failure in results['failed']:
                client_name = failure.get('client_name', 'Unknown')
                error = failure.get('error', 'Unknown error')
                logger.error(f"  ✗ {client_name}: {error}")
            
            # Exit with appropriate code
            if failed_count > 0:
                logger.warning(f"Some invoices failed to process ({failed_count} failures)")
                return 1
            else:
                logger.info("All invoices processed successfully")
                return 0
                
    except Exception as e:
        logger.error(f"Error during weekly billing: {e}")
        logger.exception("Full traceback:")
        return 1


if __name__ == '__main__':
    sys.exit(main())