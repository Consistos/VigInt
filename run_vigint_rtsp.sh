#!/bin/bash

# Quick RTSP server runner for Vigint
# This script starts just the RTSP server component

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    log_info "Activating virtual environment..."
    source venv/bin/activate
fi

# Check for configuration
if [ -f "server_config.ini" ]; then
    export VIGINT_SERVER_CONFIG_PATH="server_config.ini"
    log_info "Using server configuration"
elif [ -f "config.ini" ]; then
    export VIGINT_CONFIG_PATH="config.ini"
    log_info "Using development configuration"
else
    log_error "No configuration file found!"
    exit 1
fi

# Start RTSP server only
log_info "Starting Vigint RTSP server..."
python3 start_vigint.py --mode rtsp