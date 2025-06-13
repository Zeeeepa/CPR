#!/usr/bin/env python3
"""
Test script for CPR backend API
Tests task creation and streaming with actual Codegen API
"""

import os
import sys
import time
import json
import requests
import subprocess
from datetime import datetime

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8002")
url = f"{BACKEND_URL}/api/v1/run-task"
org_id = os.getenv("CODEGEN_ORG_ID", "123")
token = os.getenv("CODEGEN_TOKEN", "sk-test-token")

if not org_id or not token:
    print("Error: CODEGEN_ORG_ID and CODEGEN_TOKEN environment variables must be set")
    sys.exit(1)

def test_streaming():
    """Test the streaming functionality"""
    print("\n🚀 Testing SSE streaming...\n")
    
    # 1. Start a task
    print("Starting task...")
    response = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "X-Organization-ID": org_id,
            "X-API-Token": token
        },
        json={
            "prompt": "List all files in the current directory",
            "stream": True
        }
    )
    
    if not response.ok:
        print(f"Error starting task: {response.status_code}")
        print(response.text)
        return
    
    data = response.json()
    task_id = data.get("task_id")
    if not task_id:
        print("No task ID returned")
        return
        
    print(f"Task started with ID: {task_id}")
    
    # 2. Connect to SSE stream
    print("\nConnecting to SSE stream...")
    stream_url = f"http://localhost:8002/api/v1/task/{task_id}/stream"
    
    # Use curl to test SSE stream (easier than using Python for SSE)
    import subprocess
    
    cmd = [
        "curl", "-N", 
        stream_url
    ]
    
    print("\nReceiving events:")
    print("-" * 50)
    
    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for a short time to get some output
    try:
        stdout, stderr = process.communicate(timeout=10)
        
        if stderr:
            print(f"Error: {stderr}")
        
        if stdout:
            print("Received data from stream:")
            for line in stdout.splitlines():
                if line.strip():
                    print(f"  {line}")
        else:
            print("No data received from stream")
            
    except subprocess.TimeoutExpired:
        process.terminate()
        stdout, stderr = process.communicate()
        print("Stream timeout (this is expected for long-running tasks)")
        if stdout:
            print("Received data so far:")
            for line in stdout.splitlines():
                if line.strip():
                    print(f"  {line}")
    
    print("-" * 50)

def test_connection():
    """Test connection to backend API and Codegen API"""
    print("\n" + "=" * 60)
    print("Testing connection to backend API and Codegen API...")
    print("=" * 60)
    
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
            print(f"Status: {data.get('status', 'unknown')}")
            if data.get("status") != "success":
                print(f"Error: {data.get('error', 'Unknown error')}")
                return False
            return True
        else:
            print(f"Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    if test_connection():
        test_streaming()
    else:
        print("\n⚠️ Connection test failed. Skipping streaming test.")
        sys.exit(1)
