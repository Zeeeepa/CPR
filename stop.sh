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

# Stop backend and frontend servers by port
echo -e "${GREEN}Stopping all services...${NC}"
cleanup_port 8002  # Backend port
cleanup_port 3002  # Frontend port

# Additional check for specific processes (as a fallback)
echo -e "${GREEN}Checking for any remaining processes...${NC}"

# Check for backend processes
BACKEND_RUNNING=$(pgrep -f "uvicorn api:app" || echo "")
if [ -n "$BACKEND_RUNNING" ]; then
    echo -e "${YELLOW}Found backend processes still running. Stopping them...${NC}"
    pkill -9 -f "uvicorn api:app" || echo -e "${YELLOW}Failed to stop some backend processes${NC}"
fi

# Check for frontend processes
FRONTEND_RUNNING=$(pgrep -f "nuxt dev" || echo "")
if [ -n "$FRONTEND_RUNNING" ]; then
    echo -e "${YELLOW}Found frontend processes still running. Stopping them...${NC}"
    pkill -9 -f "nuxt dev" || echo -e "${YELLOW}Failed to stop some frontend processes${NC}"
fi

# Final verification
echo -e "${GREEN}Verifying all services are stopped...${NC}"
BACKEND_STILL_RUNNING=$(lsof -ti:8002 -sTCP:LISTEN || echo "")
FRONTEND_STILL_RUNNING=$(lsof -ti:3002 -sTCP:LISTEN || echo "")

if [ -n "$BACKEND_STILL_RUNNING" ] || [ -n "$FRONTEND_STILL_RUNNING" ]; then
    echo -e "${RED}Warning: Some services are still running${NC}"
    
    if [ -n "$BACKEND_STILL_RUNNING" ]; then
        echo -e "${RED}Backend port 8002 is still in use by PIDs: $BACKEND_STILL_RUNNING${NC}"
    else
        echo -e "${GREEN}Backend stopped successfully${NC}"
    fi
    
    if [ -n "$FRONTEND_STILL_RUNNING" ]; then
        echo -e "${RED}Frontend port 3002 is still in use by PIDs: $FRONTEND_STILL_RUNNING${NC}"
    else
        echo -e "${GREEN}Frontend stopped successfully${NC}"
    fi
else
    echo -e "${GREEN}All services stopped successfully${NC}"
fi

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}================ CPR Application Stopped! ===================${NC}"
echo -e "${GREEN}============================================================${NC}"

