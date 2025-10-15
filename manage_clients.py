#!/usr/bin/env python3
"""Manage clients and their API keys"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from vigint.models import db, Client, APIKey
from auth import create_client_with_api_key, revoke_api_key
from flask import Flask
from config import config
import argparse
from datetime import datetime


def create_flask_app():
    """Create and configure Flask app"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config.secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = config.database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app


def list_clients():
    """List all clients and their API keys"""
    clients = Client.query.all()
    
    if not clients:
        print("No clients found.")
        return
    
    print("\n" + "="*80)
    print("CLIENTS AND API KEYS")
    print("="*80 + "\n")
    
    for client in clients:
        print(f"Client ID: {client.id}")
        print(f"Name: {client.name}")
        print(f"Email: {client.email}")
        print(f"Created: {client.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        api_keys = APIKey.query.filter_by(client_id=client.id).all()
        print(f"\nAPI Keys ({len(api_keys)}):")
        
        if api_keys:
            for key in api_keys:
                status = "✅ ACTIVE" if key.is_active else "❌ REVOKED"
                print(f"  - ID: {key.id} | {status} | {key.name or 'Unnamed'}")
                print(f"    Created: {key.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("  No API keys found.")
        
        print("\n" + "-"*80 + "\n")


def create_client(name, email):
    """Create a new client with an API key"""
    try:
        client, api_key = create_client_with_api_key(name=name, email=email)
        
        print("\n" + "="*80)
        print("✅ CLIENT CREATED SUCCESSFULLY")
        print("="*80)
        print(f"Client ID: {client.id}")
        print(f"Name: {client.name}")
        print(f"Email: {client.email}")
        print(f"\n🔑 API Key: {api_key}")
        print("\n⚠️  IMPORTANT: Save this API key! It cannot be retrieved later.")
        print("="*80 + "\n")
        
    except ValueError as e:
        print(f"\n❌ Error: {e}\n")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        return False
    
    return True


def revoke_client_access(client_id):
    """Revoke all API keys for a client"""
    client = Client.query.get(client_id)
    
    if not client:
        print(f"\n❌ Client with ID {client_id} not found.\n")
        return False
    
    api_keys = APIKey.query.filter_by(client_id=client_id, is_active=True).all()
    
    if not api_keys:
        print(f"\n⚠️  Client '{client.name}' has no active API keys.\n")
        return False
    
    print(f"\n⚠️  About to revoke {len(api_keys)} active API key(s) for:")
    print(f"   Client: {client.name} ({client.email})")
    
    confirm = input("\nType 'yes' to confirm: ")
    if confirm.lower() != 'yes':
        print("Cancelled.")
        return False
    
    revoked_count = 0
    for api_key in api_keys:
        if revoke_api_key(api_key.id):
            revoked_count += 1
    
    print(f"\n✅ Revoked {revoked_count} API key(s) for client '{client.name}'.")
    print("This client can no longer access the API.\n")
    return True


def delete_client(client_id, force=False):
    """Delete a client and all associated data"""
    client = Client.query.get(client_id)
    
    if not client:
        print(f"\n❌ Client with ID {client_id} not found.\n")
        return False
    
    api_keys = APIKey.query.filter_by(client_id=client_id).all()
    
    print(f"\n⚠️  WARNING: About to DELETE client:")
    print(f"   ID: {client.id}")
    print(f"   Name: {client.name}")
    print(f"   Email: {client.email}")
    print(f"   API Keys: {len(api_keys)}")
    print("\n   This will also delete:")
    print("   - All API keys")
    print("   - All API usage records")
    print("   - All payment details")
    print("\n   THIS CANNOT BE UNDONE!")
    
    if not force:
        confirm = input("\nType 'DELETE' (in capitals) to confirm: ")
        if confirm != 'DELETE':
            print("Cancelled.")
            return False
    
    try:
        # Delete associated records (cascade should handle this, but being explicit)
        for api_key in api_keys:
            db.session.delete(api_key)
        
        db.session.delete(client)
        db.session.commit()
        
        print(f"\n✅ Client '{client.name}' has been permanently deleted.\n")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error deleting client: {e}\n")
        return False


def reactivate_client(client_id, key_id=None):
    """Reactivate a revoked API key"""
    client = Client.query.get(client_id)
    
    if not client:
        print(f"\n❌ Client with ID {client_id} not found.\n")
        return False
    
    if key_id:
        # Reactivate specific key
        api_key = APIKey.query.get(key_id)
        if not api_key or api_key.client_id != client_id:
            print(f"\n❌ API key {key_id} not found for this client.\n")
            return False
        
        if api_key.is_active:
            print(f"\n⚠️  API key {key_id} is already active.\n")
            return False
        
        api_key.is_active = True
        db.session.commit()
        print(f"\n✅ Reactivated API key {key_id} for client '{client.name}'.\n")
    else:
        # Reactivate all keys
        revoked_keys = APIKey.query.filter_by(client_id=client_id, is_active=False).all()
        
        if not revoked_keys:
            print(f"\n⚠️  Client '{client.name}' has no revoked API keys.\n")
            return False
        
        for key in revoked_keys:
            key.is_active = True
        
        db.session.commit()
        print(f"\n✅ Reactivated {len(revoked_keys)} API key(s) for client '{client.name}'.\n")
    
    return True


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description='Manage Vigint clients and API keys',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all clients
  python manage_clients.py --list
  
  # Create a new client
  python manage_clients.py --create --name "Acme Corp" --email "acme@example.com"
  
  # Revoke access for a non-paying client
  python manage_clients.py --revoke --client-id 3
  
  # Delete a client permanently
  python manage_clients.py --delete --client-id 3
  
  # Reactivate a client's access
  python manage_clients.py --reactivate --client-id 3
        """
    )
    
    # Actions
    parser.add_argument('--list', action='store_true', help='List all clients')
    parser.add_argument('--create', action='store_true', help='Create a new client')
    parser.add_argument('--revoke', action='store_true', help='Revoke client API access')
    parser.add_argument('--delete', action='store_true', help='Delete a client permanently')
    parser.add_argument('--reactivate', action='store_true', help='Reactivate a client')
    
    # Parameters
    parser.add_argument('--name', type=str, help='Client name (for --create)')
    parser.add_argument('--email', type=str, help='Client email (for --create)')
    parser.add_argument('--client-id', type=int, help='Client ID (for --revoke/--delete/--reactivate)')
    parser.add_argument('--key-id', type=int, help='Specific API key ID (for --reactivate)')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    # Create Flask app context
    app = create_flask_app()
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Execute action
        if args.list:
            list_clients()
        
        elif args.create:
            if not args.name or not args.email:
                print("❌ Error: --name and --email are required for --create")
                sys.exit(1)
            create_client(args.name, args.email)
        
        elif args.revoke:
            if not args.client_id:
                print("❌ Error: --client-id is required for --revoke")
                sys.exit(1)
            revoke_client_access(args.client_id)
        
        elif args.delete:
            if not args.client_id:
                print("❌ Error: --client-id is required for --delete")
                sys.exit(1)
            delete_client(args.client_id, force=args.force)
        
        elif args.reactivate:
            if not args.client_id:
                print("❌ Error: --client-id is required for --reactivate")
                sys.exit(1)
            reactivate_client(args.client_id, key_id=args.key_id)
        
        else:
            parser.print_help()


if __name__ == '__main__':
    main()
