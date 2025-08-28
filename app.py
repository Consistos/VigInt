#!/usr/bin/env python3
"""Main Flask application for Vigint API services"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from flask import Flask, request, jsonify, render_template_string
from config import config
from auth import require_api_key, require_api_key_flexible, create_client_with_api_key, list_client_api_keys
from vigint.models import db, Client, APIKey, APIUsage, PaymentDetails
from rtsp_server import rtsp_server, list_active_streams, get_stream_stats
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
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

app = create_app()

@app.route('/')
def index():
    """Main index page"""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Vigint API Services</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .header { text-align: center; margin-bottom: 40px; }
            .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; }
            .status { color: green; font-weight: bold; }
            .error { color: red; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Vigint API Services</h1>
            <p>RTSP Streaming & Billing Platform</p>
        </div>
        
        <div class="section">
            <h2>🎥 RTSP Streaming</h2>
            <p><strong>Server Status:</strong> <span class="status">{{ rtsp_status }}</span></p>
            <p><strong>Stream URL:</strong> rtsp://localhost:8554/</p>
            <p><strong>API URL:</strong> http://localhost:9997/</p>
        </div>
        
        <div class="section">
            <h2>🔧 API Endpoints</h2>
            <ul>
                <li><strong>Health Check:</strong> <a href="/api/health">/api/health</a></li>
                <li><strong>RTSP Proxy:</strong> /api/rtsp/*</li>
                <li><strong>Billing:</strong> /api/billing/*</li>
                <li><strong>Usage:</strong> /api/usage</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>📊 System Info</h2>
            <p><strong>Database:</strong> {{ database_status }}</p>
            <p><strong>Config:</strong> {{ config_status }}</p>
            <p><strong>Gemini API:</strong> {{ gemini_status }}</p>
        </div>
    </body>
    </html>
    """, 
    rtsp_status="Running" if rtsp_server.is_running() else "Stopped",
    database_status="Connected",
    config_status="Loaded",
    gemini_status="Configured" if config.gemini_api_key else "Not configured"
    )

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'services': {
            'rtsp': 'running' if rtsp_server.is_running() else 'stopped',
            'database': 'connected',
            'gemini': 'configured' if config.gemini_api_key else 'not_configured'
        }
    })

@app.route('/api/clients', methods=['POST'])
def create_client():
    """Create a new client with API key"""
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        
        if not name or not email:
            return jsonify({'error': 'Name and email are required'}), 400
        
        client, api_key = create_client_with_api_key(name, email)
        
        return jsonify({
            'client_id': client.id,
            'name': client.name,
            'email': client.email,
            'api_key': api_key
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating client: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/clients/<int:client_id>/keys')
@require_api_key
def get_client_keys(client_id):
    """Get API keys for a client"""
    try:
        # Check if current user can access this client
        if request.current_client.id != client_id:
            return jsonify({'error': 'Access denied'}), 403
        
        keys = list_client_api_keys(client_id)
        
        return jsonify({
            'client_id': client_id,
            'api_keys': [
                {
                    'id': key.id,
                    'name': key.name,
                    'is_active': key.is_active,
                    'created_at': key.created_at.isoformat()
                }
                for key in keys
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting client keys: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/streams')
@require_api_key
def get_streams():
    """Get active RTSP streams"""
    try:
        streams = list_active_streams()
        return jsonify(streams)
    except Exception as e:
        logger.error(f"Error getting streams: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/streams/<stream_name>/stats')
@require_api_key
def get_stream_statistics(stream_name):
    """Get statistics for a specific stream"""
    try:
        stats = get_stream_stats(stream_name)
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stream stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/usage')
@require_api_key_flexible
def get_usage():
    """Get API usage for current client"""
    try:
        # Get recent usage for this API key
        recent_usage = APIUsage.query.filter_by(
            api_key_id=request.current_api_key.id
        ).order_by(APIUsage.timestamp.desc()).limit(100).all()
        
        usage_data = []
        for usage in recent_usage:
            usage_data.append({
                'timestamp': usage.timestamp.isoformat(),
                'endpoint': usage.endpoint,
                'method': usage.method,
                'status_code': usage.status_code,
                'cost': float(usage.cost)
            })
        
        return jsonify({
            'api_key_id': request.current_api_key.id,
            'client_name': request.current_client.name,
            'usage_count': len(usage_data),
            'usage': usage_data
        })
        
    except Exception as e:
        logger.error(f"Error getting usage data: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    import time
    
    # Initialize database
    with app.app_context():
        db.create_all()
        logger.info("Database initialized")
    
    # Run the application
    app.run(
        host=config.host,
        port=config.port,
        debug=config.debug
    )