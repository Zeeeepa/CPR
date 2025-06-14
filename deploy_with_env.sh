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

# Load environment variables from .env file if it exists
echo -e "${GREEN}Loading environment variables...${NC}"
if [ -f .env ]; then
    echo "Found .env file, loading variables..."
    export $(grep -v '^#' .env | xargs)
    echo "Environment variables loaded successfully."
else
    echo -e "${YELLOW}No .env file found. Will use existing environment variables.${NC}"
fi

# Check environment variables
echo -e "${GREEN}Checking environment variables...${NC}"
if [ -z "$CODEGEN_TOKEN" ]; then
    echo -e "${RED}Error: CODEGEN_TOKEN environment variable is not set${NC}"
    echo "Please set it with: export CODEGEN_TOKEN=your_token"
    echo "Or create a .env file with: CODEGEN_TOKEN=your_token"
    exit 1
fi

if [ -z "$CODEGEN_ORG_ID" ]; then
    echo -e "${RED}Error: CODEGEN_ORG_ID environment variable is not set${NC}"
    echo "Please set it with: export CODEGEN_ORG_ID=your_org_id"
    echo "Or create a .env file with: CODEGEN_ORG_ID=your_org_id"
    exit 1
fi

echo -e "${GREEN}Using CODEGEN_ORG_ID: ${CODEGEN_ORG_ID}${NC}"
echo -e "${GREEN}Using CODEGEN_TOKEN: ${CODEGEN_TOKEN:0:10}...${NC}"

# Stop any existing processes
echo -e "${GREEN}Stopping any existing processes...${NC}"
pkill -f "python api.py" || true
pkill -f "npm run dev" || true
echo "Existing processes stopped."

# Start backend server
echo -e "${GREEN}Starting backend server...${NC}"
cd backend
python api.py &
BACKEND_PID=$!
cd ..
echo "Backend server started with PID: $BACKEND_PID"

# Wait for backend to start
echo -e "${GREEN}Waiting for backend to start...${NC}"
sleep 5

# Test backend connection
echo -e "${GREEN}Testing backend connection...${NC}"
RESPONSE=$(curl -s -X POST "http://localhost:8002/api/v1/test-connection" \
    -H "X-Organization-ID: $CODEGEN_ORG_ID" \
    -H "X-Token: $CODEGEN_TOKEN")
echo "Backend response: $RESPONSE"

# Check if backend connection was successful
if [[ $RESPONSE == *"success"* ]]; then
    echo -e "${GREEN}Backend connection successful!${NC}"
else
    echo -e "${RED}Backend connection failed!${NC}"
    echo "Response: $RESPONSE"
    echo "Stopping backend server..."
    kill $BACKEND_PID
    exit 1
fi

# Start frontend
echo -e "${GREEN}Starting frontend...${NC}"
npm run dev &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"

# Wait for frontend to start
echo -e "${GREEN}Waiting for frontend to start...${NC}"
sleep 10

# Create stop script
echo -e "${GREEN}Creating stop script...${NC}"
cat > stop.sh << 'EOF'
#!/bin/bash

# Set colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}================ CPR Application Shutdown ===================${NC}"
echo -e "${GREEN}============================================================${NC}"
echo "Started at: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

echo -e "${GREEN}Stopping backend server...${NC}"
if pgrep -f "python api.py" > /dev/null; then
    pkill -f "python api.py"
    echo "Backend server stopped"
else
    echo -e "${YELLOW}No backend server process found${NC}"
fi
echo ""

echo -e "${GREEN}Stopping frontend server...${NC}"
if pgrep -f "npm run dev" > /dev/null; then
    pkill -f "npm run dev"
    echo "Frontend server stopped"
else
    echo -e "${YELLOW}No frontend server process found${NC}"
fi
echo ""

echo -e "${GREEN}Checking if processes are still running...${NC}"
if pgrep -f "python api.py" > /dev/null; then
    echo -e "${YELLOW}Backend server is still running. Trying to force kill...${NC}"
    pkill -9 -f "python api.py"
else
    echo -e "${GREEN}Backend server stopped successfully${NC}"
fi

if pgrep -f "npm run dev" > /dev/null; then
    echo -e "${YELLOW}Frontend server is still running. Trying to force kill...${NC}"
    pkill -9 -f "npm run dev"
else
    echo -e "${GREEN}Frontend server stopped successfully${NC}"
fi
echo ""

echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}================ CPR Application Stopped! ===================${NC}"
echo -e "${GREEN}============================================================${NC}"
EOF

chmod +x stop.sh
echo "Stop script created: stop.sh"

# Print access URLs
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}================ CPR Application Running! ===================${NC}"
echo -e "${GREEN}============================================================${NC}"
echo "Backend API: http://localhost:8002"
echo "Frontend UI: http://localhost:3001"
echo "API Documentation: http://localhost:8002/docs"
echo ""
echo "To stop the application, run: ./stop.sh"
echo "Or press Ctrl+C to stop now"

# Wait for user to press Ctrl+C
wait $BACKEND_PID $FRONTEND_PID

