#!/usr/bin/env python3
"""Main entry point for Vigint application"""

import os
import sys
import logging
import argparse
import signal
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import config
from rtsp_server import rtsp_server
from vigint.models import db
from flask import Flask


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.get('Logging', 'level', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configure Flask app
    app.config['SECRET_KEY'] = config.secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = config.database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    return app


def initialize_database(app):
    """Initialize the database with tables"""
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    return True


def start_rtsp_server():
    """Start the RTSP server"""
    logger.info("Starting RTSP server...")
    if rtsp_server.start():
        logger.info("RTSP server started successfully")
        return True
    else:
        logger.error("Failed to start RTSP server")
        return False


def stop_rtsp_server():
    """Stop the RTSP server"""
    logger.info("Stopping RTSP server...")
    rtsp_server.stop()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    stop_rtsp_server()
    sys.exit(0)


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description='Vigint Application')
    parser.add_argument('--mode', choices=['api', 'rtsp', 'full'], default='full',
                       help='Run mode: api only, rtsp only, or full stack')
    parser.add_argument('--init-db', action='store_true',
                       help='Initialize database and exit')
    parser.add_argument('--no-rtsp', action='store_true',
                       help='Skip RTSP server startup')
    
    args = parser.parse_args()
    
    # Create Flask app
    app = create_app()
    
    # Initialize database if requested
    if args.init_db:
        logger.info("Initializing database...")
        if initialize_database(app):
            logger.info("Database initialization completed")
            return 0
        else:
            logger.error("Database initialization failed")
            return 1
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize database
        if not initialize_database(app):
            return 1
        
        # Start RTSP server if needed
        if args.mode in ['rtsp', 'full'] and not args.no_rtsp:
            if not start_rtsp_server():
                return 1
        
        # Start API server if needed
        if args.mode in ['api', 'full']:
            logger.info("Starting API server...")
            
            # Import API proxy after app is created
            from api_proxy import app as proxy_app
            
            # Run the application
            proxy_app.run(
                host=config.host,
                port=config.port,
                debug=config.debug,
                use_reloader=False  # Disable reloader to avoid issues with RTSP server
            )
        else:
            # If only RTSP mode, just keep the process alive
            logger.info("RTSP-only mode, keeping process alive...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
    
    except Exception as e:
        logger.error(f"Application error: {e}")
        return 1
    
    finally:
        # Cleanup
        stop_rtsp_server()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())