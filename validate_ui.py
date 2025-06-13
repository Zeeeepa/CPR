#!/usr/bin/env python3
"""
Validation script for CPR application
Checks environment, backend API, and frontend
"""

import os
import sys
import time
import requests
from datetime import datetime
import subprocess
from pathlib import Path

# Configuration
BACKEND_URL = "http://localhost:8002"
FRONTEND_URL = "http://localhost:3002"  # Updated to port 3002
REQUIRED_ENV_VARS = ["CODEGEN_TOKEN", "CODEGEN_ORG_ID"]

def print_header(title):
    """Print a section header"""
    print("\n" + "=" * 60)
    print(f" {title} ".center(60, "="))
    print("=" * 60)

def print_pass(message):
    """Print a pass message with color"""
    print(f"\033[92m✓ PASS\033[0m {message}")

def print_fail(message):
    """Print a fail message with color"""
    print(f"\033[91m✗ FAIL\033[0m {message}")

def check_environment():
    """Check if required environment variables are set"""
    print_header("Environment Check")
    
    all_vars_set = True
    for var in REQUIRED_ENV_VARS:
        if var in os.environ and os.environ[var]:
            print_pass(f"Environment variable {var}")
        else:
            print_fail(f"Environment variable {var}")
            all_vars_set = False
    
    return all_vars_set

def check_backend_api():
    """Check if backend API is running"""
    print_header("Backend API Check")
    
    try:
        response = requests.get(f"{BACKEND_URL}/docs", timeout=5)
        if response.status_code == 200:
            print_pass("Backend API is running")
            return True
        else:
            print_fail(f"Backend API is running with status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_fail(f"Could not connect to {BACKEND_URL}. Is the backend running?")
        return False
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False

def test_connection():
    """Test connection to backend API and Codegen API"""
    print_header("API Connection Test")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/test-connection",
            headers={
                "X-Organization-ID": os.environ.get("CODEGEN_ORG_ID", ""),
                "X-Token": os.environ.get("CODEGEN_TOKEN", "")
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print_pass(f"Backend connection test")
            print(f"     Status: {data.get('status', 'unknown')}")
            return True
        else:
            print_fail(f"Backend connection test")
            print(f"     Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print_fail(f"Backend connection test")
        print(f"     Error: {str(e)}")
        return False

def test_task_creation():
    """Test task creation"""
    print_header("Task Creation Test")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/run-task",
            headers={
                "Content-Type": "application/json",
                "X-Organization-ID": os.environ.get("CODEGEN_ORG_ID", ""),
                "X-Token": os.environ.get("CODEGEN_TOKEN", "")
            },
            json={
                "prompt": "List all files in the current directory",
                "stream": False
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            task_id = data.get("task_id")
            if task_id:
                print_pass(f"Task creation")
                print(f"     Task ID: {task_id}")
                return task_id
            else:
                print_fail("Task creation")
                print(f"     No task ID returned")
                return None
        else:
            print_fail("Task creation")
            print(f"     Status code: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        print_fail("Task creation")
        print(f"     Error: {str(e)}")
        return None

def test_streaming():
    """Test SSE streaming for a task"""
    print_header("SSE Streaming Test")
    
    # Create a new task for streaming
    task_id = test_task_creation()
    
    if not task_id:
        print_fail("No task ID available for streaming test")
        return False
    
    try:
        # Use curl to test SSE stream
        stream_url = f"{BACKEND_URL}/api/v1/task/{task_id}/stream"
        
        cmd = [
            "curl", 
            "-N", 
            stream_url
        ]
        
        # Run curl command with timeout
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for a short time to get some output
        try:
            stdout, stderr = process.communicate(timeout=6)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
        
        if stderr and not "Total" in stderr:  # Ignore curl progress messages
            print_fail("SSE streaming")
            print(f"     Error: {stderr}")
            return False
        
        if stdout:
            print_pass("SSE streaming")
            print(f"     Received data from stream")
            return True
        else:
            print_fail("SSE streaming")
            print(f"     No data received from stream")
            return False
    except Exception as e:
        print_fail("SSE streaming")
        print(f"     Error: {str(e)}")
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
            print_pass(f"File exists: {file_path}")
        else:
            print_fail(f"File exists: {file_path}")
            all_files_exist = False
    
    return all_files_exist

def check_frontend():
    """Check if frontend is running"""
    print_header("Frontend Check")
    
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            print_pass("Frontend is running")
            return True
        else:
            print_fail(f"Frontend check failed with status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print_fail(f"Frontend check failed: {e}")
        return False

def main():
    """Main validation function"""
    print("=" * 60)
    print("================ CPR Application Validation ================")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check environment variables
    env_check_passed = check_environment()
    
    # Check backend API
    backend_running = check_backend_api()
    
    # Only proceed with API tests if backend is running
    if backend_running:
        connection_test_passed = test_connection()
        task_test_passed = test_task_creation() is not None
        stream_test_passed = test_streaming()
    else:
        connection_test_passed = False
        task_test_passed = False
        stream_test_passed = False
    
    # Check frontend
    frontend_running = check_frontend()
    
    # Check frontend files
    files_check_passed = check_frontend_files()
    
    # Print summary
    print("\n" + "=" * 60)
    print("==================== Validation Summary ====================")
    print("=" * 60)
    
    all_passed = (
        env_check_passed and 
        backend_running and 
        connection_test_passed and 
        task_test_passed and 
        stream_test_passed and
        frontend_running and
        files_check_passed
    )
    
    if all_passed:
        print("\n✅ All validation tests passed! The application is ready to use.")
        print(f"- Backend API: {BACKEND_URL}")
        print(f"- Frontend: {FRONTEND_URL}")
        return 0
    else:
        print("\n⚠️  Some validation tests failed. Please fix the issues and try again.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

