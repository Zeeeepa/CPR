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

# Enhanced port cleanup function
cleanup_port() {
    local port=$1
    local killed_processes=0
    local process_info=""
    
    echo -e "${GREEN}Checking for processes using port $port...${NC}"
    
    # Get PIDs of processes using the port
    local pids=$(lsof -ti:$port -sTCP:LISTEN)
    
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}Found processes using port $port. Cleaning up...${NC}"
        
        # Get process details before killing them
        for pid in $pids; do
            local cmd=$(ps -p $pid -o comm= || echo "Unknown")
            local cmdline=$(ps -p $pid -o args= || echo "Unknown command")
            process_info="${process_info}PID: $pid - $cmd - $cmdline\n"
            killed_processes=$((killed_processes + 1))
        done
        
        # Kill the processes
        echo "$pids" | xargs kill -9
        sleep 2
        
        echo -e "${YELLOW}Killed $killed_processes processes using port $port:${NC}"
        echo -e "$process_info"
    else
        echo -e "${GREEN}No processes found using port $port${NC}"
    fi
}

# Check and clean up ports
echo -e "${GREEN}Checking and cleaning up ports...${NC}"
cleanup_port 8002  # Backend port
cleanup_port 3002  # Frontend port
echo -e "${GREEN}Port cleanup completed${NC}"
echo ""

# Start backend server
echo -e "${GREEN}Starting backend server...${NC}"
nohup python main.py > backend/server.log 2>&1 &
BACKEND_PID=$!
echo "Backend server started with PID: $BACKEND_PID"
echo "Logs available at: backend/server.log"
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
    if curl -s http://localhost:3002/ > /dev/null; then
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
    echo "Frontend: http://localhost:3002"
    echo ""
    echo "To stop the application, run: ./stop.sh"
else
    echo -e "${RED}Validation failed. Please check the logs.${NC}"
    exit 1
fi
