#!/bin/bash
# Example: Setting up a new client for Vigint Video Analysis

set -e

echo "========================================="
echo "Vigint - New Client Setup Example"
echo "========================================="
echo ""

# Step 1: Create the client
echo "Step 1: Creating new client 'Acme Corp'..."
echo ""
python manage_clients.py --create \
  --name "Acme Corporation" \
  --email "security@acme.com"

echo ""
echo "⚠️  IMPORTANT: Copy the API key from above!"
echo "   You'll need to give this to the client."
echo ""
read -p "Press Enter after you've saved the API key..."

# Step 2: List all clients to confirm
echo ""
echo "Step 2: Verifying client was created..."
echo ""
python manage_clients.py --list

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Share the API key with your client (securely!)"
echo "2. Configure their email settings in config.ini [Email] section"
echo "3. Test their API access: curl -H 'X-API-Key: <key>' http://localhost:5002/api/health"
echo "4. Client can start sending video frames and receiving analysis"
echo ""
echo "To revoke access later:"
echo "  python manage_clients.py --revoke --client-id <id>"
echo ""
echo "To reactivate:"
echo "  python manage_clients.py --reactivate --client-id <id>"
echo ""
