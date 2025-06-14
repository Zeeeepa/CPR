#!/bin/bash
# Script to start the backend server and run tests

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}========= Starting Backend Server and Running Tests ========${NC}"
echo -e "${GREEN}============================================================${NC}"
echo "Started at: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Load environment variables from .env file if it exists
if [ -f ../.env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' ../.env | xargs)
fi

# Check if required variables are set
if [ -z "$CODEGEN_ORG_ID" ] || [ -z "$CODEGEN_TOKEN" ]; then
    echo "Error: CODEGEN_ORG_ID and CODEGEN_TOKEN environment variables are required."
    echo "Please set them in .env file or export them before running this script."
    exit 1
fi

# Set default backend URL
BACKEND_URL=${BACKEND_URL:-"http://localhost:8002"}

# Print configuration
echo "=== Configuration ==="
echo "Organization ID: $CODEGEN_ORG_ID"
echo "Token: ${CODEGEN_TOKEN:0:10}..."
echo "Backend URL: $BACKEND_URL"
echo ""

# Start backend server
echo -e "${GREEN}Starting backend server...${NC}"
cd ..
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8002 &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 5

# Function to check if backend is running
check_backend() {
    if curl -s "$BACKEND_URL/docs" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Check if backend is running
if ! check_backend; then
    echo -e "${RED}Error: Backend server did not start properly.${NC}"
    echo "Please check for errors and try again."
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo -e "${GREEN}Backend server started successfully!${NC}"
echo ""

# Run tests
echo -e "${GREEN}Running tests...${NC}"
cd tests
./run_all_tests.sh

# Capture test result
TEST_RESULT=$?

# Stop backend server
echo ""
echo -e "${GREEN}Stopping backend server...${NC}"
kill $BACKEND_PID
wait $BACKEND_PID 2>/dev/null || true
echo "Backend server stopped."

# Exit with test result
exit $TEST_RESULT

