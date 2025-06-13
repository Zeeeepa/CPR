#!/bin/bash

# A.sh - Full Refresher Upgrader to Clean Top Standard
# Comprehensive deployment script for CPR project

set -e  # Exit on any error

echo "🚀 CPR Full Refresher Upgrader Starting..."
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to kill processes by name
kill_process() {
    local process_name=$1
    print_status "Killing $process_name processes..."
    
    # Kill by process name
    pkill -f "$process_name" 2>/dev/null || true
    
    # Kill by port if it's a known service
    case $process_name in
        "api.py")
            # Kill anything running on port 8002
            lsof -ti:8002 | xargs kill -9 2>/dev/null || true
            ;;
        "nuxt"|"npm"|"node")
            # Kill anything running on port 3001
            lsof -ti:3001 | xargs kill -9 2>/dev/null || true
            ;;
    esac
    
    sleep 2
    print_success "$process_name processes killed"
}

# Step 1: Git Pull Force
print_status "Step 1: Performing git pull force..."
echo "Current branch: $(git branch --show-current)"
echo "Current commit: $(git rev-parse --short HEAD)"

# Prompt for confirmation
read -p "⚠️  This will force pull and overwrite local changes. Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_error "Operation cancelled by user"
    exit 1
fi

# Save current branch
CURRENT_BRANCH=$(git branch --show-current)

# Force pull
git fetch origin
git reset --hard origin/$CURRENT_BRANCH
print_success "Git force pull completed"

# Step 2: Kill API.py processes
print_status "Step 2: Killing API.py processes..."
kill_process "api.py"
kill_process "python.*api.py"
kill_process "uvicorn"

# Step 3: Kill Frontend processes
print_status "Step 3: Killing Frontend processes..."
kill_process "nuxt"
kill_process "npm"
kill_process "node"

# Step 4: Delete file locks and node_modules
print_status "Step 4: Cleaning up locks and dependencies..."

# Remove package locks
if [ -f "package-lock.json" ]; then
    rm package-lock.json
    print_success "Removed package-lock.json"
fi

if [ -f "yarn.lock" ]; then
    rm yarn.lock
    print_success "Removed yarn.lock"
fi

if [ -f "pnpm-lock.yaml" ]; then
    rm pnpm-lock.yaml
    print_success "Removed pnpm-lock.yaml"
fi

# Remove node_modules
if [ -d "node_modules" ]; then
    print_status "Removing node_modules directory..."
    rm -rf node_modules
    print_success "Removed node_modules"
fi

# Remove .nuxt cache
if [ -d ".nuxt" ]; then
    rm -rf .nuxt
    print_success "Removed .nuxt cache"
fi

# Remove .output
if [ -d ".output" ]; then
    rm -rf .output
    print_success "Removed .output"
fi

# Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
print_success "Cleaned Python cache files"

# Step 5: Install dependencies
print_status "Step 5: Installing fresh dependencies..."
npm install
print_success "npm install completed"

# Step 6: Build project
print_status "Step 6: Building project..."
npm run build
print_success "npm run build completed"

# Step 7: Check for .env file
print_status "Step 7: Checking environment configuration..."
if [ ! -f ".env" ]; then
    print_warning ".env file not found!"
    if [ -f ".env.example" ]; then
        print_status "Copying .env.example to .env..."
        cp .env.example .env
        print_warning "Please edit .env file with your actual credentials:"
        print_warning "  - CODEGEN_TOKEN=sk-your-token-here"
        print_warning "  - CODEGEN_ORG_ID=your-org-id-here"
    else
        print_error ".env.example not found! Please create .env manually."
    fi
else
    print_success ".env file exists"
fi

# Step 8: Start services
print_status "Step 8: Starting services..."

# Check if Python dependencies are installed
print_status "Checking Python dependencies..."
if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
    print_warning "Python dependencies missing. Installing..."
    if [ -f "backend/requirements.txt" ]; then
        pip3 install -r backend/requirements.txt
    else
        pip3 install fastapi uvicorn python-multipart
    fi
    print_success "Python dependencies installed"
fi

# Start API in background
print_status "Starting API server (backend/api.py)..."
cd backend
nohup python3 api.py > ../api.log 2>&1 &
API_PID=$!
cd ..
print_success "API server started (PID: $API_PID)"

# Wait a moment for API to start
sleep 3

# Check if API is running
if kill -0 $API_PID 2>/dev/null; then
    print_success "API server is running on port 8002"
else
    print_error "API server failed to start. Check api.log for details."
    cat api.log
    exit 1
fi

# Step 9: Start frontend development server
print_status "Step 9: Starting frontend development server..."
print_status "Frontend will start on http://localhost:3001"
print_status "API is running on http://localhost:8002"

echo ""
echo "🎉 CPR Full Refresher Upgrade Complete!"
echo "=============================================="
echo "✅ Git force pulled"
echo "✅ All processes killed"
echo "✅ Dependencies cleaned and reinstalled"
echo "✅ Project built successfully"
echo "✅ API server started (PID: $API_PID)"
echo ""
echo "🌐 Starting frontend development server..."
echo "   Frontend: http://localhost:3001"
echo "   API:      http://localhost:8002"
echo ""
echo "📝 Logs:"
echo "   API logs: tail -f api.log"
echo "   Frontend logs: will appear below"
echo ""
echo "🛑 To stop services:"
echo "   kill $API_PID  # Stop API"
echo "   Ctrl+C         # Stop frontend"
echo ""

# Start frontend (this will run in foreground)
npm run dev

