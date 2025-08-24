#!/bin/bash

# Vigint Application Startup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PYTHON_CMD="python3"
VENV_DIR="venv"
CONFIG_FILE="config.ini"
SERVER_CONFIG_FILE="server_config.ini"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_python() {
    if ! command -v $PYTHON_CMD &> /dev/null; then
        log_error "Python 3 is not installed or not in PATH"
        exit 1
    fi
    
    local python_version=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    log_info "Using Python $python_version"
}

setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        log_info "Creating virtual environment..."
        $PYTHON_CMD -m venv $VENV_DIR
    fi
    
    log_info "Activating virtual environment..."
    source $VENV_DIR/bin/activate
    
    if [ -f "requirements.txt" ]; then
        log_info "Installing/updating dependencies..."
        pip install -r requirements.txt
    else
        log_warn "requirements.txt not found, skipping dependency installation"
    fi
}

check_config() {
    if [ -f "$SERVER_CONFIG_FILE" ]; then
        log_info "Using server configuration: $SERVER_CONFIG_FILE"
        export VIGINT_SERVER_CONFIG_PATH="$SERVER_CONFIG_FILE"
    elif [ -f "$CONFIG_FILE" ]; then
        log_info "Using development configuration: $CONFIG_FILE"
        export VIGINT_CONFIG_PATH="$CONFIG_FILE"
    else
        log_error "No configuration file found. Please create $CONFIG_FILE or $SERVER_CONFIG_FILE"
        log_info "You can copy from config.ini.example or server_config.ini.example"
        exit 1
    fi
}

check_mediamtx() {
    if [ ! -f "mediamtx" ] && ! command -v mediamtx &> /dev/null; then
        log_warn "MediaMTX binary not found. RTSP functionality may not work."
        log_info "Download MediaMTX from: https://github.com/bluenviron/mediamtx/releases"
    fi
}

init_database() {
    log_info "Initializing database..."
    $PYTHON_CMD start_vigint.py --init-db
}

start_application() {
    local mode=${1:-full}
    log_info "Starting Vigint application in $mode mode..."
    
    case $mode in
        "api")
            $PYTHON_CMD start_vigint.py --mode api
            ;;
        "rtsp")
            $PYTHON_CMD start_vigint.py --mode rtsp
            ;;
        "full")
            $PYTHON_CMD start_vigint.py --mode full
            ;;
        *)
            log_error "Invalid mode: $mode. Use 'api', 'rtsp', or 'full'"
            exit 1
            ;;
    esac
}

show_help() {
    echo "Vigint Application Startup Script"
    echo ""
    echo "Usage: $0 [OPTIONS] [MODE]"
    echo ""
    echo "MODES:"
    echo "  full    Start both API and RTSP servers (default)"
    echo "  api     Start only the API server"
    echo "  rtsp    Start only the RTSP server"
    echo ""
    echo "OPTIONS:"
    echo "  --help, -h      Show this help message"
    echo "  --init-db       Initialize database and exit"
    echo "  --no-venv       Skip virtual environment setup"
    echo "  --dev           Use development configuration"
    echo ""
    echo "Examples:"
    echo "  $0                    # Start full application"
    echo "  $0 api                # Start only API server"
    echo "  $0 --init-db          # Initialize database only"
}

# Main script
main() {
    local mode="full"
    local init_db_only=false
    local use_venv=true
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --init-db)
                init_db_only=true
                shift
                ;;
            --no-venv)
                use_venv=false
                shift
                ;;
            --dev)
                CONFIG_FILE="config.ini"
                shift
                ;;
            api|rtsp|full)
                mode=$1
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    log_info "Starting Vigint Application..."
    
    # Check prerequisites
    check_python
    check_config
    check_mediamtx
    
    # Setup virtual environment
    if [ "$use_venv" = true ]; then
        setup_venv
    fi
    
    # Initialize database if requested
    if [ "$init_db_only" = true ]; then
        init_database
        log_info "Database initialization completed"
        exit 0
    fi
    
    # Initialize database
    init_database
    
    # Start the application
    start_application $mode
}

# Run main function with all arguments
main "$@"