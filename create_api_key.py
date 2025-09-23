#!/usr/bin/env python3
"""Create an API key for testing the secure video analyzer"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from vigint.models import db
from auth import create_client_with_api_key
from flask import Flask
from config import config

def create_test_api_key():
    """Create a test API key for the video analyzer"""
    
    # Create Flask app context
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config.secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = config.database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        try:
            # Create tables if they don't exist
            db.create_all()
            
            # Create test client and API key
            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument('--client-name', default="Video Analyzer Test Client")
            parser.add_argument('--list', action='store_true')
            args, _ = parser.parse_known_args()
            
            if args.list:
                from vigint.models import Client, APIKey
                clients = Client.query.all()
                for client in clients:
                    api_keys = APIKey.query.filter_by(client_id=client.id, is_active=True).all()
                    print(f"Client: {client.name} ({client.email})")
                    for key in api_keys:
                        print(f"  API Key Hash: {key.key_hash}")
                return None
            
            email = f"test-{args.client_name.lower().replace(' ', '-')}@vigint.local"
            client, api_key = create_client_with_api_key(
                name=args.client_name,
                email=email
            )
            
            print("✅ Test API key created successfully!")
            print(f"Client ID: {client.id}")
            print(f"Client Name: {client.name}")
            print(f"Client Email: {client.email}")
            print(f"API Key: {api_key}")
            print()
            print("🔧 To use this API key, set the environment variable:")
            print(f"export VIGINT_API_KEY={api_key}")
            print()
            print("Or add it to your .env file:")
            print(f"VIGINT_API_KEY={api_key}")
            
            return api_key
            
        except ValueError as e:
            if "already exists" in str(e):
                print("⚠️ Test client already exists. Retrieving existing API key...")
                
                from vigint.models import Client, APIKey
                client = Client.query.filter_by(email=email).first()
                if client:
                    api_keys = APIKey.query.filter_by(client_id=client.id, is_active=True).all()
                    if api_keys:
                        print(f"Existing API Key: {api_keys[0].key_hash}")
                        print("Note: This is the hashed version. You need the original key.")
                        print("If you lost the original key, delete the client and run this script again.")
                    else:
                        print("No active API keys found for existing client.")
                return None
            else:
                print(f"❌ Error creating API key: {e}")
                return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

if __name__ == '__main__':
    create_test_api_key()