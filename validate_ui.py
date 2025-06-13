#!/usr/bin/env python3
"""
UI Validation Script for CPR (Codegen PR) Application
Tests the frontend build, backend API, and integration points
"""

import os
import sys
import json
import time
import subprocess
import requests
from pathlib import Path

def run_command(cmd, cwd=None, timeout=30):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"

def check_file_exists(filepath):
    """Check if a file exists"""
    return Path(filepath).exists()

def validate_environment():
    """Validate environment setup"""
    print("🔍 Validating Environment Setup...")
    
    # Check if .env file exists
    if not check_file_exists('.env'):
        print("❌ .env file not found")
        return False
    
    # Check if required files exist
    required_files = [
        'package.json',
        'nuxt.config.ts',
        'app.vue',
        'pages/index.vue',
        'components/ChatMessage.vue',
        'components/SettingsModal.vue',
        'backend/api.py',
        'backend/requirements.txt'
    ]
    
    for file in required_files:
        if not check_file_exists(file):
            print(f"❌ Required file missing: {file}")
            return False
    
    print("✅ Environment setup validated")
    return True

def validate_frontend_build():
    """Validate frontend build process"""
    print("🏗️ Validating Frontend Build...")
    
    # Check if node_modules exists
    if not check_file_exists('node_modules'):
        print("📦 Installing dependencies...")
        success, stdout, stderr = run_command("npm install", timeout=120)
        if not success:
            print(f"❌ npm install failed: {stderr}")
            return False
    
    # Test build process
    print("🔨 Testing build process...")
    success, stdout, stderr = run_command("npm run build", timeout=120)
    if not success:
        print(f"❌ Build failed: {stderr}")
        return False
    
    # Check if build output exists
    if not check_file_exists('.output'):
        print("❌ Build output directory not found")
        return False
    
    print("✅ Frontend build validated")
    return True

def validate_backend_setup():
    """Validate backend setup"""
    print("🐍 Validating Backend Setup...")
    
    # Test Python imports
    success, stdout, stderr = run_command(
        "cd backend && python -c 'import api; print(\"Backend imports OK\")'",
        timeout=30
    )
    if not success:
        print(f"❌ Backend import failed: {stderr}")
        return False
    
    print("✅ Backend setup validated")
    return True

def validate_ui_components():
    """Validate UI components structure"""
    print("🎨 Validating UI Components...")
    
    # Check main page structure
    with open('pages/index.vue', 'r') as f:
        content = f.read()
        
    # Check for key UI elements
    ui_elements = [
        'New Thread',
        'Agent Dashboard',
        'Connected',
        'Disconnected',
        'ChatMessage',
        'SettingsModal',
        'textarea',
        'Send'
    ]
    
    for element in ui_elements:
        if element not in content:
            print(f"❌ UI element missing: {element}")
            return False
    
    # Check ChatMessage component
    with open('components/ChatMessage.vue', 'r') as f:
        chat_content = f.read()
        
    chat_elements = [
        'message.role',
        'message.content',
        'message.timestamp',
        'message.status',
        'steps'
    ]
    
    for element in chat_elements:
        if element not in chat_content:
            print(f"❌ ChatMessage element missing: {element}")
            return False
    
    print("✅ UI components validated")
    return True

def validate_api_structure():
    """Validate API structure"""
    print("🔌 Validating API Structure...")
    
    with open('backend/api.py', 'r') as f:
        api_content = f.read()
    
    # Check for key API endpoints and features
    api_elements = [
        'FastAPI',
        'TaskRequest',
        'TaskResponse',
        'run_task',
        'test_connection',
        'CORS',
        'codegen',
        'Agent'
    ]
    
    for element in api_elements:
        if element not in api_content:
            print(f"❌ API element missing: {element}")
            return False
    
    print("✅ API structure validated")
    return True

def validate_configuration():
    """Validate configuration files"""
    print("⚙️ Validating Configuration...")
    
    # Check package.json
    with open('package.json', 'r') as f:
        package_data = json.load(f)
    
    required_deps = [
        'nuxt',
        '@nuxtjs/tailwindcss',
        '@heroicons/vue',
        'marked',
        'uuid'
    ]
    
    dependencies = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}
    
    for dep in required_deps:
        if dep not in dependencies:
            print(f"❌ Missing dependency: {dep}")
            return False
    
    # Check nuxt.config.ts
    if not check_file_exists('nuxt.config.ts'):
        print("❌ nuxt.config.ts not found")
        return False
    
    print("✅ Configuration validated")
    return True

def validate_styling():
    """Validate styling setup"""
    print("🎨 Validating Styling Setup...")
    
    # Check if Tailwind config exists
    if not check_file_exists('tailwind.config.js'):
        print("❌ tailwind.config.js not found")
        return False
    
    # Check if CSS assets exist
    if not check_file_exists('assets'):
        print("❌ assets directory not found")
        return False
    
    print("✅ Styling setup validated")
    return True

def create_deployment_script():
    """Create a simple deployment script for testing"""
    print("📝 Creating deployment script...")
    
    deployment_script = """#!/bin/bash
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
"""
    
    with open('deploy.sh', 'w') as f:
        f.write(deployment_script)
    
    # Make it executable
    os.chmod('deploy.sh', 0o755)
    
    print("✅ Deployment script created: deploy.sh")

def main():
    """Main validation function"""
    print("🔍 CPR UI Validation Starting...")
    print("=" * 50)
    
    validation_steps = [
        ("Environment", validate_environment),
        ("Frontend Build", validate_frontend_build),
        ("Backend Setup", validate_backend_setup),
        ("UI Components", validate_ui_components),
        ("API Structure", validate_api_structure),
        ("Configuration", validate_configuration),
        ("Styling", validate_styling)
    ]
    
    results = []
    
    for step_name, step_func in validation_steps:
        try:
            result = step_func()
            results.append((step_name, result))
            if not result:
                print(f"❌ {step_name} validation failed")
            print()
        except Exception as e:
            print(f"❌ {step_name} validation error: {e}")
            results.append((step_name, False))
            print()
    
    # Create deployment script
    create_deployment_script()
    
    # Summary
    print("=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for step_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{step_name:20} {status}")
        if result:
            passed += 1
    
    print("=" * 50)
    print(f"📈 Results: {passed}/{total} validations passed")
    
    if passed == total:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("🚀 The CPR UI is ready for deployment!")
        print()
        print("📋 Next Steps:")
        print("1. Set real CODEGEN_TOKEN and CODEGEN_ORG_ID in .env")
        print("2. Run ./deploy.sh to start the application")
        print("3. Open http://localhost:3001 to test the UI")
        print("4. Test connection and message functionality")
        return True
    else:
        print("⚠️  Some validations failed. Please fix the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
