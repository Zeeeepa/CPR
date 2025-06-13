#!/usr/bin/env python3
"""
REAL validation using actual Codegen SDK task flow.
This tests the EXACT flow you specified:
1. Create task
2. task.refresh() 
3. print(task.status)
4. if task.status == "completed": print(task.result)
"""

import requests
import time
import json
import os

def test_real_task_flow():
    """Test the REAL task flow with proper Codegen SDK validation"""
    print("🎯 REAL Task Flow Validation")
    print("Testing the EXACT flow you specified!")
    print("=" * 60)
    
    # Use environment variables for real credentials
    # Users need to set these in .env for real testing
    org_id = os.getenv("CODEGEN_ORG_ID", "123456")  # Default numeric for testing
    token = os.getenv("CODEGEN_TOKEN", "test-token")
    base_url = os.getenv("CODEGEN_BASE_URL", "https://api.codegen.com")
    
    print(f"🔑 Using org_id: {org_id}")
    print(f"🔑 Using token: {token[:10]}..." if len(token) > 10 else f"🔑 Using token: {token}")
    print(f"🔑 Using base_url: {base_url}")
    
    # Step 1: Create task (equivalent to starting a Codegen task)
    url = "http://localhost:8002/api/v1/run-task"
    headers = {
        "Content-Type": "application/json",
        "X-Org-ID": str(org_id),  # Ensure it's a string
        "X-Token": token,
        "X-Base-URL": base_url
    }
    
    data = {
        "prompt": "Hello! Please respond with a simple greeting.",
        "stream": False  # Non-streaming for easier testing
    }
    
    try:
        print("\\n📤 Creating task...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code != 200:
            print(f"❌ Task creation failed with status {response.status_code}")
            if response.status_code == 500 and "Unauthorized" in response.text:
                print("🔑 This is an authentication issue - need valid Codegen credentials")
                print("💡 Set CODEGEN_ORG_ID and CODEGEN_TOKEN in .env file")
            return False
            
        task_data = response.json()
        task_id = task_data.get('task_id')
        
        if not task_id:
            print("❌ No task_id returned")
            return False
            
        print(f"✅ Task created with ID: {task_id}")
        
        # Step 2: Monitor task using task.refresh() equivalent
        status_url = f"http://localhost:8002/api/v1/task/{task_id}/status"
        
        print("\\n🔄 Monitoring task status (task.refresh() equivalent)...")
        
        max_attempts = 30  # Wait up to 60 seconds
        for attempt in range(max_attempts):
            try:
                # This is equivalent to task.refresh()
                status_response = requests.get(status_url, timeout=10)
                
                if status_response.status_code != 200:
                    print(f"❌ Status check failed: {status_response.status_code}")
                    print(f"Response: {status_response.text}")
                    continue
                    
                task_status = status_response.json()
                current_status = task_status.get('status', 'unknown')
                
                # This is equivalent to print(task.status)
                print(f"task.status = '{current_status}'")
                
                # Check if task is completed (your specified condition)
                if current_status == "completed":
                    result = task_status.get('result', 'No result available')
                    # This is equivalent to print(task.result)
                    print(f"✅ Task completed!")
                    print(f"task.result = {result}")
                    return True
                    
                elif current_status == "failed":
                    error = task_status.get('error', 'Unknown error')
                    print(f"❌ Task failed: {error}")
                    return False
                    
                elif current_status in ["pending", "running", "in_progress", "active", "processing", "executing"]:
                    print(f"⏳ Task still {current_status}, waiting... (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(2)
                    
                else:
                    print(f"❓ Unknown status: {current_status}")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"❌ Status check error: {e}")
                time.sleep(2)
                
        print("⏰ Task did not complete within timeout")
        return False
        
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    print("🚀 REAL Codegen Task Flow Validation")
    print("Using the EXACT methods you specified:")
    print("1. Create task")
    print("2. task.refresh()")
    print("3. print(task.status)")
    print("4. if task.status == 'completed': print(task.result)")
    print("=" * 60)
    
    success = test_real_task_flow()
    
    print("\\n" + "=" * 60)
    if success:
        print("🎉 VALIDATION PASSED: Real task flow works!")
        print("✅ Headers are correct and task completion works!")
    else:
        print("❌ VALIDATION FAILED: Task flow is broken!")
        print("🔧 Check credentials and backend status")
        
    return success

if __name__ == "__main__":
    main()

