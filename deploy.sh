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

# Check for required environment variables
echo "🔍 Checking environment variables..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "⚠️  No .env file found. Creating from .env.example..."
        cp .env.example .env
        echo "⚠️  Please edit .env file with your actual credentials"
    else
        echo "❌ Error: No .env or .env.example file found"
        exit 1
    fi
fi

# Source environment variables
if [ -f ".env" ]; then
    echo "📥 Loading environment variables from .env..."
    export $(grep -v '^#' .env | xargs)
fi

# Validate environment variables
if [ -z "$CODEGEN_TOKEN" ] || [ -z "$CODEGEN_ORG_ID" ]; then
    echo "❌ Error: CODEGEN_TOKEN and CODEGEN_ORG_ID must be set in .env file"
    exit 1
fi

# Clean and install dependencies
echo "📦 Installing dependencies..."
npm install

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
cd backend && pip install -r requirements.txt && cd ..

# Run validation script
echo "🧪 Running validation script..."
python validate_ui.py
if [ $? -ne 0 ]; then
    echo "⚠️  Validation failed. Please fix the issues before deploying."
    echo "   You can continue with deployment by running this script again."
    exit 1
fi

# Start backend API
echo "🔌 Starting backend API on port 8002..."
cd backend
uvicorn api:app --host 0.0.0.0 --port 8002 --reload &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Test backend connection
echo "🔍 Testing backend connection..."
curl -s -o /dev/null -w "%{http_code}" http://localhost:8002/docs
if [ $? -ne 0 ]; then
    echo "❌ Error: Backend failed to start"
    exit 1
fi

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
