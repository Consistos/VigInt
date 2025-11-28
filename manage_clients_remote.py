#!/usr/bin/env python3
"""
Remote Client Management via Admin API
Manages clients on the Vigint server through HTTP API
"""

import os
import sys
import requests
import json
import argparse
from typing import Optional


class RemoteClientManager:
    """Manage clients on remote Vigint server via Admin API"""
    
    def __init__(self, server_url: Optional[str] = None, admin_key: Optional[str] = None):
        self.server_url = server_url or os.getenv('VIGINT_SERVER_URL', 'https://vigint.sparse-ai.com')
        self.admin_key = admin_key or os.getenv('VIGINT_ADMIN_KEY')
        
        if not self.admin_key:
            raise ValueError(
                "VIGINT_ADMIN_KEY environment variable not set.\n"
                "Set it with: export VIGINT_ADMIN_KEY=your-secret-key\n"
                "The admin key is the SECRET_KEY from your server's environment variables."
            )
        
        self.server_url = self.server_url.rstrip('/')
        self.headers = {
            'X-Admin-Key': self.admin_key,
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[dict] = None):
        """Make HTTP request to admin API"""
        url = f"{self.server_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    print(f"   {error_data.get('error', 'Unknown error')}")
                except:
                    print(f"   {e.response.text}")
            sys.exit(1)
    
    def list_clients(self):
        """List all clients"""
        print("📋 Listing all clients...\n")
        
        result = self._make_request('GET', '/admin/clients')
        
        if result['count'] == 0:
            print("No clients found.")
            return
        
        print("=" * 80)
        print("CLIENTS AND API KEYS")
        print("=" * 80 + "\n")
        
        for client in result['clients']:
            print(f"Client ID: {client['id']}")
            print(f"Name: {client['name']}")
            print(f"Email: {client['email']}")
            print(f"Created: {client['created_at']}")
            
            print(f"\nAPI Keys ({len(client['api_keys'])}):")
            if client['api_keys']:
                for key in client['api_keys']:
                    status = "✅ ACTIVE" if key['is_active'] else "❌ REVOKED"
                    print(f"  - ID: {key['id']} | {status} | {key.get('name', 'Unnamed')}")
                    print(f"    Created: {key['created_at']}")
            else:
                print("  No API keys found.")
            
            print("\n" + "-" * 80 + "\n")
    
    def create_client(self, name: str, email: str):
        """Create a new client"""
        print(f"➕ Creating client: {name} ({email})...\n")
        
        result = self._make_request('POST', '/admin/clients', {
            'name': name,
            'email': email
        })
        
        print("=" * 80)
        print("✅ CLIENT CREATED SUCCESSFULLY")
        print("=" * 80)
        print(f"Client ID: {result['client_id']}")
        print(f"Name: {result['name']}")
        print(f"Email: {result['email']}")
        print(f"\n🔑 API Key: {result['api_key']}")
        print("\n⚠️  IMPORTANT: Save this API key! It cannot be retrieved later.")
        print("=" * 80 + "\n")
    
    def revoke_client(self, client_id: int):
        """Revoke all API keys for a client"""
        print(f"🚫 Revoking client ID: {client_id}...")
        
        confirm = input("\nType 'yes' to confirm: ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            return
        
        result = self._make_request('POST', f'/admin/clients/{client_id}/revoke')
        
        print(f"\n✅ {result['message']}")
        print(f"   Revoked {result['revoked_count']} API key(s)\n")
    
    def reactivate_client(self, client_id: int):
        """Reactivate revoked API keys for a client"""
        print(f"✅ Reactivating client ID: {client_id}...\n")
        
        result = self._make_request('POST', f'/admin/clients/{client_id}/reactivate')
        
        print(f"✅ {result['message']}")
        print(f"   Reactivated {result['reactivated_count']} API key(s)\n")


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description='Manage Vigint clients remotely via Admin API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Set admin key (required)
  export VIGINT_ADMIN_KEY=your-secret-key
  
  # List all clients
  python manage_clients_remote.py --list
  
  # Create a new client
  python manage_clients_remote.py --create --name "Acme Corp" --email "acme@example.com"
  
  # Revoke access for a client
  python manage_clients_remote.py --revoke --client-id 3
  
  # Reactivate a client's access
  python manage_clients_remote.py --reactivate --client-id 3

Environment Variables:
  VIGINT_SERVER_URL    Server URL (default: https://vigint.sparse-ai.com)
  VIGINT_ADMIN_KEY     Admin key (required, same as server's SECRET_KEY)
        """
    )
    
    # Actions
    parser.add_argument('--list', action='store_true', help='List all clients')
    parser.add_argument('--create', action='store_true', help='Create a new client')
    parser.add_argument('--revoke', action='store_true', help='Revoke client API access')
    parser.add_argument('--reactivate', action='store_true', help='Reactivate a client')
    
    # Parameters
    parser.add_argument('--name', type=str, help='Client name (for --create)')
    parser.add_argument('--email', type=str, help='Client email (for --create)')
    parser.add_argument('--client-id', type=int, help='Client ID (for --revoke/--reactivate)')
    parser.add_argument('--server-url', type=str, help='Server URL (overrides VIGINT_SERVER_URL)')
    parser.add_argument('--admin-key', type=str, help='Admin key (overrides VIGINT_ADMIN_KEY)')
    
    args = parser.parse_args()
    
    try:
        manager = RemoteClientManager(
            server_url=args.server_url,
            admin_key=args.admin_key
        )
        
        if args.list:
            manager.list_clients()
        
        elif args.create:
            if not args.name or not args.email:
                print("❌ Error: --name and --email are required for --create")
                sys.exit(1)
            manager.create_client(args.name, args.email)
        
        elif args.revoke:
            if not args.client_id:
                print("❌ Error: --client-id is required for --revoke")
                sys.exit(1)
            manager.revoke_client(args.client_id)
        
        elif args.reactivate:
            if not args.client_id:
                print("❌ Error: --client-id is required for --reactivate")
                sys.exit(1)
            manager.reactivate_client(args.client_id)
        
        else:
            parser.print_help()
    
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
