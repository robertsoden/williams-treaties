#!/bin/bash
#
# Quick start script for Williams Treaty Territories Map Application
#
# This script starts the web server and opens the map in your default browser.
#

echo "=========================================="
echo "Williams Treaty Territories"
echo "Interactive Map Browser"
echo "=========================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "Error: Python is not installed"
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# Check if Flask is installed
if ! $PYTHON_CMD -c "import flask" 2>/dev/null; then
    echo "Flask is not installed. Installing..."
    pip install flask flask-cors
fi

# Default port
PORT=8000

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -p, --port PORT    Port to run server on (default: 8000)"
            echo "  -h, --help         Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

echo "Starting server on port $PORT..."
echo ""
echo "Access the map at: http://localhost:$PORT"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "=========================================="
echo ""

# Start the server
$PYTHON_CMD web/server.py --port $PORT

# Cleanup on exit
trap "echo ''; echo 'Server stopped'; exit" INT TERM
