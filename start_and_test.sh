#!/bin/bash

# Start and test the CPR application
echo "Starting CPR application..."

# Check if environment variables are set
if [ -z "$CODEGEN_ORG_ID" ] || [ -z "$CODEGEN_TOKEN" ]; then
    echo "Error: CODEGEN_ORG_ID and CODEGEN_TOKEN environment variables must be set."
    echo "Please set them with:"
    echo "export CODEGEN_ORG_ID=your_org_id"
    echo "export CODEGEN_TOKEN=your_token"
    exit 1
fi

# Kill any existing processes
echo "Stopping any existing processes..."
pkill -f "python api.py" || true
pkill -f "npm run dev" || true

# Start the backend server
echo "Starting backend server..."
cd backend
python api.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 5

# Test backend connection
echo "Testing backend connection..."
curl -s -X POST "http://localhost:8002/api/v1/test-connection" \
    -H "X-Organization-ID: $CODEGEN_ORG_ID" \
    -H "X-Token: $CODEGEN_TOKEN"
echo ""

# Start the frontend
echo "Starting frontend..."
npm run dev &
FRONTEND_PID=$!

# Wait for frontend to start
echo "Waiting for frontend to start..."
sleep 10

# Create test script if it doesn't exist
if [ ! -f "test_ui_flow.py" ]; then
    echo "Creating UI flow test script..."
    cat > test_ui_flow.py << 'EOF'
import requests
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials from environment
org_id = os.getenv("CODEGEN_ORG_ID")
token = os.getenv("CODEGEN_TOKEN")

print(f"Using org_id: {org_id}")
print(f"Using token: {token[:10]}...")

# Base URLs
backend_url = "http://localhost:8002"
frontend_url = "http://localhost:3001"

# Headers
headers = {
    "Content-Type": "application/json",
    "X-Organization-ID": org_id,
    "X-Token": token
}

def test_connection():
    """Test connection to the backend"""
    print("\n=== Testing Connection ===")
    response = requests.post(f"{backend_url}/api/v1/test-connection", headers=headers)
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    return True

def send_message():
    """Send a message to the agent"""
    print("\n=== Sending Message ===")
    data = {
        "prompt": "Hello, this is a test message from the UI flow test",
        "stream": False
    }
    response = requests.post(f"{backend_url}/api/v1/run-task", headers=headers, json=data)
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    task_id = response.json().get("task_id")
    assert task_id is not None
    return task_id

def check_task_status(task_id):
    """Check the status of a task"""
    print(f"\n=== Checking Task Status for {task_id} ===")
    max_retries = 10
    for i in range(max_retries):
        response = requests.get(f"{backend_url}/api/v1/task/{task_id}/status", headers=headers)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        status = response.json().get("status")
        
        if status in ["completed", "complete", "failed", "error"]:
            return status
        
        print(f"Task still running, waiting... (attempt {i+1}/{max_retries})")
        time.sleep(3)
    
    return "timeout"

def list_tasks():
    """List all active tasks"""
    print("\n=== Listing Tasks ===")
    response = requests.get(f"{backend_url}/api/v1/tasks", headers=headers)
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.json().get("tasks", [])

def check_frontend():
    """Check if the frontend is accessible"""
    print("\n=== Checking Frontend ===")
    response = requests.get(frontend_url)
    print(f"Status code: {response.status_code}")
    print(f"Content length: {len(response.text)} bytes")
    assert response.status_code == 200
    assert "__NUXT__" in response.text
    assert "backendUrl" in response.text
    return True

def main():
    """Run the full UI flow test"""
    print("=== Starting UI Flow Test ===")
    
    # Test connection
    connection_ok = test_connection()
    if not connection_ok:
        print("❌ Connection test failed")
        return
    
    # Check frontend
    frontend_ok = check_frontend()
    if not frontend_ok:
        print("❌ Frontend check failed")
        return
    
    # Send message
    task_id = send_message()
    if not task_id:
        print("❌ Failed to send message")
        return
    
    # Check task status
    final_status = check_task_status(task_id)
    print(f"Final task status: {final_status}")
    
    # List tasks
    tasks = list_tasks()
    print(f"Found {len(tasks)} active tasks")
    
    print("\n=== UI Flow Test Complete ===")
    print("✅ All tests passed successfully")

if __name__ == "__main__":
    main()
EOF
fi

# Run the UI flow test
echo "Running UI flow test..."
python test_ui_flow.py

# Print access URLs
echo ""
echo "=== CPR Application is running ==="
echo "Backend API: http://localhost:8002"
echo "Frontend UI: http://localhost:3001"
echo ""
echo "To stop the application, run: ./stop.sh"
echo "Or press Ctrl+C to stop now"

# Create a stop script if it doesn't exist or update it
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

# Wait for user to press Ctrl+C
wait $BACKEND_PID $FRONTEND_PID

