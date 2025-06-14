#!/bin/bash
# Deployment script for CPR application
# Starts both backend and frontend servers

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}================ CPR Application Deployment =================${NC}"
echo -e "${GREEN}============================================================${NC}"
echo "Started at: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Check environment variables
echo -e "${GREEN}Checking environment variables...${NC}"

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
fi

if [ -z "$CODEGEN_TOKEN" ]; then
    echo -e "${RED}Error: CODEGEN_TOKEN environment variable is not set${NC}"
    echo "Please set it with: export CODEGEN_TOKEN=your_token"
    exit 1
fi

if [ -z "$CODEGEN_ORG_ID" ]; then
    echo -e "${RED}Error: CODEGEN_ORG_ID environment variable is not set${NC}"
    echo "Please set it with: export CODEGEN_ORG_ID=your_org_id"
    exit 1
fi

echo -e "${GREEN}Environment variables are set correctly${NC}"
echo "CODEGEN_ORG_ID: $CODEGEN_ORG_ID"
echo "CODEGEN_TOKEN: ${CODEGEN_TOKEN:0:10}..."
echo ""

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
echo "Installing Python requirements..."
pip install -r requirements.txt

echo "Installing npm packages..."
npm install
echo ""

# Check if ports are available
echo -e "${GREEN}Checking if ports are available...${NC}"
if lsof -Pi :8002 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${YELLOW}Warning: Port 8002 is already in use${NC}"
    echo "Stopping existing process..."
    pkill -f "uvicorn api:app" || true
    sleep 2
fi

if lsof -Pi :3001 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${YELLOW}Warning: Port 3001 is already in use${NC}"
    echo "Stopping existing process..."
    pkill -f "nuxt dev" || true
    sleep 2
fi

echo -e "${GREEN}Ports are available${NC}"
echo ""

# Start backend server
echo -e "${GREEN}Starting backend server...${NC}"
cd backend
nohup python -m uvicorn api:app --host 0.0.0.0 --port 8002 --reload > server.log 2>&1 &
BACKEND_PID=$!
echo "Backend server started with PID: $BACKEND_PID"
echo "Logs available at: backend/server.log"
cd ..
echo ""

# Wait for backend to start
echo -e "${GREEN}Waiting for backend to start...${NC}"
MAX_RETRIES=10
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8002/ > /dev/null; then
        echo -e "${GREEN}Backend server is running${NC}"
        break
    fi
    echo "Waiting for backend to start... ($(($RETRY_COUNT + 1))/$MAX_RETRIES)"
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}Error: Backend server failed to start${NC}"
    echo "Check logs at: backend/server.log"
    exit 1
fi
echo ""

# Start frontend server
echo -e "${GREEN}Starting frontend server...${NC}"
nohup npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend server started with PID: $FRONTEND_PID"
echo "Logs available at: frontend.log"
echo ""

# Wait for frontend to start
echo -e "${GREEN}Waiting for frontend to start...${NC}"
MAX_RETRIES=15
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:3001/ > /dev/null; then
        echo -e "${GREEN}Frontend server is running${NC}"
        break
    fi
    echo "Waiting for frontend to start... ($(($RETRY_COUNT + 1))/$MAX_RETRIES)"
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}Error: Frontend server failed to start${NC}"
    echo "Check logs at: frontend.log"
    exit 1
fi
echo ""

# Run validation
echo -e "${GREEN}Running validation...${NC}"
python tests/ui/validate_ui.py
VALIDATION_RESULT=$?

if [ $VALIDATION_RESULT -eq 0 ]; then
    echo -e "${GREEN}============================================================${NC}"
    echo -e "${GREEN}================ CPR Application is Ready! =================${NC}"
    echo -e "${GREEN}============================================================${NC}"
    echo "Backend API: http://localhost:8002"
    echo "Frontend: http://localhost:3001"
    echo ""
    echo "To stop the application, run: ./stop.sh"
else
    echo -e "${RED}Validation failed. Please check the logs.${NC}"
    exit 1
fi

