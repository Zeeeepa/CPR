#!/usr/bin/env python3
"""
Comprehensive validation script for CPR application
Tests environment setup, backend API, and frontend components
"""

import os
import sys
import json
import time
import subprocess
import requests
from datetime import datetime

# Configuration
BACKEND_URL = "http://localhost:8002"
FRONTEND_URL = "http://localhost:3001"
REQUIRED_ENV_VARS = ["CODEGEN_TOKEN", "CODEGEN_ORG_ID"]

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f" {title} ".center(60, "="))
    print("=" * 60)

def print_result(test_name, success, message=""):
    """Print a test result with color"""
    if success:
        result = "\033[92m✓ PASS\033[0m"  # Green
    else:
        result = "\033[91m✗ FAIL\033[0m"  # Red
    
    print(f"{result} {test_name}")
    if message:
        print(f"     {message}")

def check_environment():
    """Check if required environment variables are set"""
    print_header("Environment Check")
    
    all_vars_set = True
    for var in REQUIRED_ENV_VARS:
        if var in os.environ and os.environ[var]:
            print_result(f"Environment variable {var}", True)
        else:
            print_result(f"Environment variable {var}", False, 
                        f"Missing or empty. Set it in .env file or export {var}=value")
            all_vars_set = False
    
    return all_vars_set

def check_backend_running():
    """Check if backend API is running"""
    print_header("Backend API Check")
    
    try:
        response = requests.get(f"{BACKEND_URL}/docs", timeout=5)
        if response.status_code == 200:
            print_result("Backend API is running", True)
            return True
        else:
            print_result("Backend API is running", False, 
                        f"Unexpected status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_result("Backend API is running", False, 
                    f"Could not connect to {BACKEND_URL}. Is the backend running?")
        return False
    except Exception as e:
        print_result("Backend API is running", False, f"Error: {str(e)}")
        return False

def test_backend_connection():
    """Test connection to backend API and Codegen API"""
    print_header("API Connection Test")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/test-connection",
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_result("Backend connection test", True, 
                        f"Status: {data.get('status', 'unknown')}")
            return True
        else:
            print_result("Backend connection test", False, 
                        f"Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print_result("Backend connection test", False, f"Error: {str(e)}")
        return False

def test_task_creation():
    """Test creating a task via the API"""
    print_header("Task Creation Test")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/run-task",
            headers={"Content-Type": "application/json"},
            json={
                "prompt": "Echo test message for validation",
                "stream": True
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            task_id = data.get("task_id")
            if task_id:
                print_result("Task creation", True, f"Task ID: {task_id}")
                return task_id
            else:
                print_result("Task creation", False, "No task ID returned")
                return None
        else:
            print_result("Task creation", False, 
                        f"Status code: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        print_result("Task creation", False, f"Error: {str(e)}")
        return None

def test_task_status(task_id):
    """Test checking task status"""
    print_header("Task Status Test")
    
    if not task_id:
        print_result("Task status check", False, "No task ID provided")
        return False
    
    try:
        # Wait a moment for the task to be processed
        time.sleep(2)
        
        response = requests.get(
            f"{BACKEND_URL}/api/v1/task/{task_id}/status",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "unknown")
            print_result("Task status check", True, f"Status: {status}")
            return True
        else:
            print_result("Task status check", False, 
                        f"Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print_result("Task status check", False, f"Error: {str(e)}")
        return False

def test_sse_stream(task_id):
    """Test SSE streaming for a task"""
    print_header("SSE Streaming Test")
    
    if not task_id:
        print_result("SSE streaming", False, "No task ID provided")
        return False
    
    try:
        # Use curl to test SSE stream (easier than using Python for SSE)
        cmd = [
            "curl", "-N", 
            f"{BACKEND_URL}/api/v1/task/{task_id}/stream"
        ]
        
        print("Testing SSE stream (will timeout after 5 seconds)...")
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for a short time to get some output
        time.sleep(5)
        process.terminate()
        
        stdout, stderr = process.communicate()
        
        if stderr:
            print_result("SSE streaming", False, f"Error: {stderr}")
            return False
        
        if stdout:
            print_result("SSE streaming", True, "Received data from stream")
            return True
        else:
            print_result("SSE streaming", False, "No data received from stream")
            return False
    except Exception as e:
        print_result("SSE streaming", False, f"Error: {str(e)}")
        return False

def check_frontend_files():
    """Check if essential frontend files exist"""
    print_header("Frontend Files Check")
    
    essential_files = [
        "app.vue",
        "pages/index.vue",
        "components/ChatMessage.vue",
        "components/SettingsModal.vue",
        "nuxt.config.ts",
        "package.json"
    ]
    
    all_files_exist = True
    for file_path in essential_files:
        if os.path.isfile(file_path):
            print_result(f"File exists: {file_path}", True)
        else:
            print_result(f"File exists: {file_path}", False, "File not found")
            all_files_exist = False
    
    return all_files_exist

def run_validation():
    """Run all validation tests"""
    print_header("CPR Application Validation")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Check environment
    env_ok = check_environment()
    if not env_ok:
        print("\n⚠️  Environment check failed. Please set the required environment variables.")
        print("   You can create a .env file based on .env.example")
        return False
    
    # Step 2: Check if backend is running
    backend_ok = check_backend_running()
    if not backend_ok:
        print("\n⚠️  Backend API is not running. Please start it with:")
        print("   cd backend && uvicorn api:app --host 0.0.0.0 --port 8002")
        return False
    
    # Step 3: Test backend connection
    connection_ok = test_backend_connection()
    if not connection_ok:
        print("\n⚠️  Backend connection test failed. Check your API credentials.")
        return False
    
    # Step 4: Test task creation
    task_id = test_task_creation()
    if not task_id:
        print("\n⚠️  Task creation failed. Check the backend logs for details.")
        return False
    
    # Step 5: Test task status
    status_ok = test_task_status(task_id)
    
    # Step 6: Test SSE streaming
    sse_ok = test_sse_stream(task_id)
    
    # Step 7: Check frontend files
    frontend_ok = check_frontend_files()
    if not frontend_ok:
        print("\n⚠️  Some frontend files are missing. Check your project structure.")
    
    # Final result
    print_header("Validation Summary")
    all_tests_passed = env_ok and backend_ok and connection_ok and task_id and status_ok and sse_ok and frontend_ok
    
    if all_tests_passed:
        print("\n✅ All validation tests passed! The application is ready to use.")
        print("\nYou can start the application with:")
        print("   ./deploy.sh")
        return True
    else:
        print("\n⚠️  Some validation tests failed. Please fix the issues and try again.")
        return False

if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)

