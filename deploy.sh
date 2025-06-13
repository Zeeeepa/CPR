#!/bin/bash
# Simple deployment script for CPR application

echo "🚀 Starting CPR Application Deployment..."

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
cd backend && uvicorn api:app --host 0.0.0.0 --port 8002 --reload &
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Start frontend
echo "🎨 Starting frontend on port 3001..."
npm run dev &

echo "✅ Deployment complete!"
echo "🌐 Frontend: http://localhost:3001"
echo "🔌 Backend: http://localhost:8002"
echo "📚 API Docs: http://localhost:8002/docs"

# Keep script running
wait
