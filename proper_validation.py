#!/usr/bin/env python3
"""
PROPER validation using the actual task flow as specified by the user.
"""

import requests
import time
import json

def test_actual_task_flow():
    """Test the actual task creation and completion flow"""
    print("🧪 Testing ACTUAL task flow with proper validation...")
    
    # Step 1: Create a task with correct headers
    url = "http://localhost:8002/api/v1/run-task"
    headers = {
        "Content-Type": "application/json",
        "X-Org-ID": "123456",  # Use numeric org_id
        "X-Token": "test-token",
        "X-Base-URL": "https://api.codegen.com"
    }
    data = {"prompt": "Hello, this is a test message"}
    
    try:
        print("📤 Creating task...")
        response = requests.post(url, headers=headers, json=data, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code != 200:
            print(f"❌ Task creation failed with status {response.status_code}")
            return False
            
        task_data = response.json()
        task_id = task_data.get('task_id')
        
        if not task_id:
            print("❌ No task_id returned")
            return False
            
        print(f"✅ Task created with ID: {task_id}")
        
        # Step 2: Check task status (task.refresh() equivalent)
        status_url = f"http://localhost:8002/api/v1/task/{task_id}/status"
        
        print("🔄 Checking task status...")
        for attempt in range(10):  # Check up to 10 times
            try:
                status_response = requests.get(status_url, timeout=5)
                if status_response.status_code == 200:
                    task_status = status_response.json()
                    print(f"📊 Task status: {task_status}")
                    
                    # task.refresh() equivalent - print current status
                    current_status = task_status.get('status', 'unknown')
                    print(f"task.status = '{current_status}'")
                    
                    # Once task is complete, access the result
                    if current_status == "completed":
                        result = task_status.get('result', 'No result available')
                        print(f"✅ Task completed!")
                        print(f"task.result = {result}")
                        return True
                    elif current_status == "failed":
                        print(f"❌ Task failed: {task_status.get('error', 'Unknown error')}")
                        return False
                    else:
                        print(f"⏳ Task still {current_status}, waiting...")
                        time.sleep(2)
                else:
                    print(f"❌ Status check failed: {status_response.status_code}")
                    print(f"Response: {status_response.text}")
                    
            except Exception as e:
                print(f"❌ Status check error: {e}")
                
        print("⏰ Task did not complete within timeout")
        return False
        
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    print("🚀 PROPER Task Flow Validation")
    print("=" * 50)
    
    success = test_actual_task_flow()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 VALIDATION PASSED: Task flow works correctly!")
    else:
        print("❌ VALIDATION FAILED: Task flow is broken!")
        
    return success

if __name__ == "__main__":
    main()

