#!/bin/bash
# Run all tests for the CPR application

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}================ Running CPR Application Tests =============${NC}"
echo -e "${GREEN}============================================================${NC}"
echo "Started at: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
fi

# Check if required variables are set
if [ -z "$CODEGEN_ORG_ID" ] || [ -z "$CODEGEN_TOKEN" ]; then
    echo "Error: CODEGEN_ORG_ID and CODEGEN_TOKEN environment variables are required."
    echo "Please set them in .env file or export them before running this script."
    exit 1
fi

# Set default backend URL
BACKEND_URL=${BACKEND_URL:-"http://localhost:8002"}

# Print test configuration
echo "=== CPR Application Test Configuration ==="
echo "Organization ID: $CODEGEN_ORG_ID"
echo "Token: ${CODEGEN_TOKEN:0:10}..."
echo "Backend URL: $BACKEND_URL"
echo

# Function to check if backend is running
check_backend() {
    echo "Checking if backend is running at $BACKEND_URL..."
    if curl -s "$BACKEND_URL/docs" > /dev/null; then
        echo "Backend is running."
        return 0
    else
        echo "Backend is not running at $BACKEND_URL."
        echo "Please start the backend server before running tests."
        return 1
    fi
}

# Check if backend is running
if ! check_backend; then
    echo "Would you like to start the backend server? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "Starting backend server in a new terminal..."
        # Start backend server in a new terminal
        if command -v gnome-terminal &> /dev/null; then
            gnome-terminal -- bash -c "cd $(pwd) && python -m uvicorn backend.api:app --host 0.0.0.0 --port 8002 --reload"
        elif command -v xterm &> /dev/null; then
            xterm -e "cd $(pwd) && python -m uvicorn backend.api:app --host 0.0.0.0 --port 8002 --reload" &
        else
            echo "Could not find a suitable terminal emulator. Please start the backend server manually."
            exit 1
        fi
        
        # Wait for backend to start
        echo "Waiting for backend to start..."
        for i in {1..10}; do
            if check_backend; then
                break
            fi
            sleep 2
        done
        
        if ! check_backend; then
            echo "Backend did not start within the expected time. Please check for errors."
            exit 1
        fi
    else
        echo "Exiting. Please start the backend server before running tests."
        exit 1
    fi
fi

# Run API tests
echo -e "${GREEN}Running API tests...${NC}"
python -m tests.api.test_thread_api
python -m tests.api.test_thread_api_full
python -m tests.api.test_request

# Run UI validation
echo -e "${GREEN}Running UI validation...${NC}"
python -m tests.ui.validate_ui

# Print summary
echo
echo "=== Test Summary ==="
echo "API Tests: $([ $? -eq 0 ] && echo "PASSED" || echo "FAILED")"
echo "UI Validation: $([ $? -eq 0 ] && echo "PASSED" || echo "FAILED")"

# Check if all tests passed
if [ $? -eq 0 ]; then
    echo
    echo "🎉 All tests passed! The CPR Application is working correctly."
    exit 0
else
    echo
    echo "❌ Some tests failed. Please check the output for details."
    exit 1
fi
