#!/bin/bash
# Stop script for CPR application
# Stops both backend and frontend servers

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}================ CPR Application Shutdown ===================${NC}"
echo -e "${GREEN}============================================================${NC}"
echo "Started at: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Stop backend server
echo -e "${GREEN}Stopping backend server...${NC}"
pkill -f "uvicorn api:app" || echo -e "${YELLOW}No backend server process found${NC}"
echo ""

# Stop frontend server
echo -e "${GREEN}Stopping frontend server...${NC}"
pkill -f "nuxt dev" || echo -e "${YELLOW}No frontend server process found${NC}"
echo ""

# Check if processes are still running
echo -e "${GREEN}Checking if processes are still running...${NC}"
BACKEND_RUNNING=$(pgrep -f "uvicorn api:app" || echo "")
FRONTEND_RUNNING=$(pgrep -f "nuxt dev" || echo "")

if [ -n "$BACKEND_RUNNING" ]; then
    echo -e "${YELLOW}Warning: Backend server is still running with PID: $BACKEND_RUNNING${NC}"
    echo "You may need to manually kill it with: kill -9 $BACKEND_RUNNING"
else
    echo -e "${GREEN}Backend server stopped successfully${NC}"
fi

if [ -n "$FRONTEND_RUNNING" ]; then
    echo -e "${YELLOW}Warning: Frontend server is still running with PID: $FRONTEND_RUNNING${NC}"
    echo "You may need to manually kill it with: kill -9 $FRONTEND_RUNNING"
else
    echo -e "${GREEN}Frontend server stopped successfully${NC}"
fi

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}================ CPR Application Stopped! ===================${NC}"
echo -e "${GREEN}============================================================${NC}"

