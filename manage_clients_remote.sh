#!/bin/bash
# Remote Client Management via Admin API
# Usage: ./manage_clients_remote.sh <command> [args]

# Configuration
SERVER_URL="${VIGINT_SERVER_URL:-https://vigint.sparse-ai.com}"
ADMIN_KEY="${VIGINT_ADMIN_KEY:-}"

# Check if admin key is set
if [ -z "$ADMIN_KEY" ]; then
    echo "❌ Error: VIGINT_ADMIN_KEY environment variable not set"
    echo ""
    echo "Set it with:"
    echo "  export VIGINT_ADMIN_KEY=your-secret-key"
    echo ""
    echo "The admin key is the SECRET_KEY from your server's environment variables."
    exit 1
fi

# Function to make API calls
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    if [ -z "$data" ]; then
        curl -s -X "$method" \
            -H "X-Admin-Key: $ADMIN_KEY" \
            -H "Content-Type: application/json" \
            "$SERVER_URL$endpoint"
    else
        curl -s -X "$method" \
            -H "X-Admin-Key: $ADMIN_KEY" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$SERVER_URL$endpoint"
    fi
}

# Commands
case "$1" in
    list)
        echo "📋 Listing all clients..."
        echo ""
        response=$(api_call "GET" "/admin/clients")
        echo "$response" | python3 -m json.tool
        ;;
    
    create)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "❌ Usage: $0 create <name> <email>"
            exit 1
        fi
        
        name=$2
        email=$3
        
        echo "➕ Creating client: $name ($email)..."
        echo ""
        
        data="{\"name\":\"$name\",\"email\":\"$email\"}"
        response=$(api_call "POST" "/admin/clients" "$data")
        
        echo "$response" | python3 -m json.tool
        echo ""
        echo "⚠️  SAVE THE API KEY ABOVE - It cannot be retrieved later!"
        ;;
    
    revoke)
        if [ -z "$2" ]; then
            echo "❌ Usage: $0 revoke <client-id>"
            exit 1
        fi
        
        client_id=$2
        
        echo "🚫 Revoking client ID: $client_id..."
        echo ""
        
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            echo "Cancelled."
            exit 0
        fi
        
        response=$(api_call "POST" "/admin/clients/$client_id/revoke")
        echo "$response" | python3 -m json.tool
        ;;
    
    reactivate)
        if [ -z "$2" ]; then
            echo "❌ Usage: $0 reactivate <client-id>"
            exit 1
        fi
        
        client_id=$2
        
        echo "✅ Reactivating client ID: $client_id..."
        echo ""
        
        response=$(api_call "POST" "/admin/clients/$client_id/reactivate")
        echo "$response" | python3 -m json.tool
        ;;
    
    *)
        echo "Vigint Remote Client Management"
        echo ""
        echo "Usage: $0 <command> [args]"
        echo ""
        echo "Commands:"
        echo "  list                      - List all clients"
        echo "  create <name> <email>     - Create a new client"
        echo "  revoke <client-id>        - Revoke client access"
        echo "  reactivate <client-id>    - Reactivate client access"
        echo ""
        echo "Environment Variables:"
        echo "  VIGINT_SERVER_URL         - Server URL (default: https://vigint.sparse-ai.com)"
        echo "  VIGINT_ADMIN_KEY          - Admin key (required, same as SECRET_KEY)"
        echo ""
        echo "Examples:"
        echo "  export VIGINT_ADMIN_KEY=your-secret-key"
        echo "  $0 list"
        echo "  $0 create \"Acme Corp\" \"billing@acme.com\""
        echo "  $0 revoke 3"
        echo "  $0 reactivate 3"
        ;;
esac
