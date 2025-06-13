#!/bin/bash
# Simple deployment script for CPR application

set -e  # Exit on any error

echo "🚀 Starting CPR Application Deployment..."

# Function to cleanup processes on exit
cleanup() {
    echo "🧹 Cleaning up processes..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    pkill -f "uvicorn.*api:app" || true
    pkill -f "nuxt.*dev" || true
}

# Set trap to cleanup on script exit
trap cleanup EXIT INT TERM

# Check if we're in the right directory
if [ ! -f "package.json" ] || [ ! -f "nuxt.config.ts" ]; then
    echo "❌ Error: This script must be run from the CPR project root directory"
    echo "   Make sure you're in the directory containing package.json and nuxt.config.ts"
    exit 1
fi

# Kill existing processes
echo "🔄 Stopping existing processes..."
pkill -f "uvicorn.*api:app" || true
pkill -f "nuxt.*dev" || true
sleep 2

# Clean and install dependencies
echo "📦 Installing dependencies..."
npm install

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
cd backend && pip install -r requirements.txt && cd ..

# Start backend API
echo "🔌 Starting backend API on port 8002..."
cd backend
uvicorn api:app --host 0.0.0.0 --port 8002 --reload &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Start frontend
echo "🎨 Starting frontend on port 3001..."
if npm run dev &
then
    FRONTEND_PID=$!
    echo "✅ Deployment complete!"
    echo "🌐 Frontend: http://localhost:3001"
    echo "🔌 Backend: http://localhost:8002"
    echo "📚 API Docs: http://localhost:8002/docs"
    echo ""
    echo "Press Ctrl+C to stop both services"
    
    # Keep script running and wait for both processes
    wait
else
    echo "❌ Failed to start frontend"
    exit 1
fi
