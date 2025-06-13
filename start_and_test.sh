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

# Create a stop script
cat > stop.sh << 'EOF'
#!/bin/bash
echo "Stopping CPR application..."
pkill -f "python api.py" || true
pkill -f "npm run dev" || true
echo "All processes stopped."
EOF

chmod +x stop.sh

# Wait for user to press Ctrl+C
wait $BACKEND_PID $FRONTEND_PID

