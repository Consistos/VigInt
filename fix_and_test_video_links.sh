#!/bin/bash
# Quick fix and test script for video token issues

echo "=============================================="
echo "🔧 VIDEO TOKEN FIX & TEST SCRIPT"
echo "=============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check .env file
echo "Step 1: Checking .env configuration..."
echo "----------------------------------------------"

if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo "   Creating from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env file and add your actual API key${NC}"
    exit 1
fi

# Check for SPARSE_AI_BASE_URL
if grep -q "SPARSE_AI_BASE_URL" .env; then
    BASE_URL=$(grep "SPARSE_AI_BASE_URL" .env | cut -d '=' -f2)
    echo -e "${GREEN}✅ SPARSE_AI_BASE_URL found: $BASE_URL${NC}"
    
    # Check if it's the correct URL
    if [[ "$BASE_URL" == *"sparse-ai-video-server.onrender.com"* ]]; then
        echo -e "${GREEN}✅ URL is correct (Render.com deployment)${NC}"
    elif [[ "$BASE_URL" == *"sparse-ai.com"* ]]; then
        echo -e "${YELLOW}⚠️  URL might be outdated${NC}"
        echo "   Consider using: https://sparse-ai-video-server.onrender.com"
    fi
else
    echo -e "${RED}❌ SPARSE_AI_BASE_URL not found in .env${NC}"
    echo "   Add this line to .env:"
    echo "   SPARSE_AI_BASE_URL=https://sparse-ai-video-server.onrender.com"
    exit 1
fi

# Check for API key
if grep -q "SPARSE_AI_API_KEY" .env; then
    API_KEY=$(grep "SPARSE_AI_API_KEY" .env | cut -d '=' -f2)
    if [[ "$API_KEY" == "your-sparse-ai-api-key-here" ]] || [[ -z "$API_KEY" ]]; then
        echo -e "${RED}❌ SPARSE_AI_API_KEY not configured${NC}"
        echo "   Please add your actual API key to .env"
        exit 1
    else
        echo -e "${GREEN}✅ SPARSE_AI_API_KEY configured (${#API_KEY} chars)${NC}"
    fi
else
    echo -e "${RED}❌ SPARSE_AI_API_KEY not found in .env${NC}"
    exit 1
fi

echo ""

# Step 2: Check config.ini if it exists
echo "Step 2: Checking config.ini (if exists)..."
echo "----------------------------------------------"

if [ -f config.ini ]; then
    if grep -q "\[SparseAI\]" config.ini; then
        CONFIG_URL=$(grep "base_url" config.ini | grep -v "^#" | cut -d '=' -f2 | xargs)
        echo "   config.ini base_url: $CONFIG_URL"
        
        if [[ "$CONFIG_URL" != "$BASE_URL" ]]; then
            echo -e "${YELLOW}⚠️  config.ini URL differs from .env${NC}"
            echo "   .env takes precedence, but consider updating config.ini too"
        else
            echo -e "${GREEN}✅ config.ini matches .env${NC}"
        fi
    fi
else
    echo "   config.ini not found (using .env only)"
fi

echo ""

# Step 3: Run diagnostic tool
echo "Step 3: Running diagnostic tool..."
echo "----------------------------------------------"

if [ -f diagnose_video_token.py ]; then
    python diagnose_video_token.py
else
    echo -e "${YELLOW}⚠️  Diagnostic tool not found${NC}"
fi

echo ""

# Step 4: Test server connectivity
echo "Step 4: Testing server connectivity..."
echo "----------------------------------------------"

HEALTH_URL="$BASE_URL/health"
echo "   Checking: $HEALTH_URL"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" --max-time 10)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Server is responding (HTTP $HTTP_CODE)${NC}"
elif [ "$HTTP_CODE" = "000" ]; then
    echo -e "${RED}❌ Cannot connect to server (timeout or connection error)${NC}"
    echo "   Server might be sleeping (Render.com free tier)"
    echo "   Wait 30-60 seconds and try again"
else
    echo -e "${YELLOW}⚠️  Server responded with HTTP $HTTP_CODE${NC}"
fi

echo ""

# Step 5: Offer to generate test incident
echo "Step 5: Ready to test!"
echo "----------------------------------------------"
echo ""
echo "Your configuration is ready. To test with a new incident:"
echo ""
echo -e "${GREEN}python demo_video_alerts.py${NC}"
echo ""
echo "This will:"
echo "  1. Generate a test incident"
echo "  2. Create a video"
echo "  3. Upload to Sparse AI server"
echo "  4. Send you an email with a working video link"
echo ""
echo "Old video links will NOT work - they were generated with"
echo "different configuration. Only new links will work!"
echo ""
echo "=============================================="
echo "✅ Pre-flight checks complete!"
echo "=============================================="
