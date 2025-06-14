#!/usr/bin/env python3
"""
Script to programmatically create a new thread and send a message to it.
This will be accessible afterwards via the user interface.
"""

import requests
import json
import argparse
import time
import uuid

def main():
    parser = argparse.ArgumentParser(description='Create a thread and send a message')
    parser.add_argument('--message', type=str, default='Hello from the command line!',
                        help='Message to send to the thread')
    parser.add_argument('--org_id', type=str, default='323',
                        help='Organization ID')
    parser.add_argument('--token', type=str, default='sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99',
                        help='API token')
    parser.add_argument('--base_url', type=str, default='default',
                        help='Base URL')
    parser.add_argument('--backend_url', type=str, default='http://localhost:8002',
                        help='Backend URL')
    
    args = parser.parse_args()
    
    # Create a unique thread ID
    thread_id = str(uuid.uuid4())
    
    # Headers for API requests
    headers = {
        'Content-Type': 'application/json',
        'X-Organization-ID': args.org_id,
        'X-Token': args.token,
        'X-Base-URL': args.base_url
    }
    
    # Create a thread by sending a message
    print(f"Creating thread with ID: {thread_id}")
    
    # Prepare the message payload
    payload = {
        'message': args.message,
        'thread_id': thread_id
    }
    
    # Send the message to create the thread
    response = requests.post(
        f"{args.backend_url}/api/v1/run-task",
        headers=headers,
        json=payload
    )
    
    if response.status_code == 200:
        data = response.json()
        task_id = data.get('task_id')
        print(f"Message sent successfully. Task ID: {task_id}")
        print(f"Thread ID: {thread_id}")
        
        # Wait for the task to complete
        print("Waiting for task to complete...")
        max_attempts = 10
        for attempt in range(max_attempts):
            status_response = requests.get(
                f"{args.backend_url}/api/v1/task/{task_id}/status",
                headers=headers
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"Status check {attempt+1}/{max_attempts}: {status_data}")
                
                # If the task has a result, it's complete
                if status_data.get('result'):
                    print("Task completed with result!")
                    print(f"Result: {status_data.get('result')}")
                    break
                
                # If the task is marked as completed
                if status_data.get('status') == 'completed':
                    print("Task marked as completed!")
                    break
            
            # Wait before checking again
            time.sleep(2)
        
        # Create a local storage entry for the thread
        print("Creating local storage entry for the thread...")
        
        # This is a simplified version of what the UI would store
        thread_data = {
            'id': thread_id,
            'name': f"Thread created at {time.strftime('%Y-%m-%d %H:%M:%S')}",
            'messages': [
                {
                    'id': str(uuid.uuid4()),
                    'role': 'user',
                    'content': args.message,
                    'sent': True,
                    'timestamp': int(time.time() * 1000)
                },
                {
                    'id': str(uuid.uuid4()),
                    'role': 'assistant',
                    'content': status_data.get('result', 'Task completed successfully.'),
                    'sent': True,
                    'taskId': task_id,
                    'timestamp': int(time.time() * 1000)
                }
            ],
            'lastActivity': time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        }
        
        print(f"Thread created successfully with ID: {thread_id}")
        print("You can now access this thread via the user interface.")
        print(f"Thread data: {json.dumps(thread_data, indent=2)}")
        
        # Note: In a real implementation, you would need to save this to the browser's localStorage
        # or to a database that the UI can access. This script just demonstrates the API calls.
        
        print("\nTo make this thread appear in the UI, you can:")
        print("1. Open the browser console in the CPR UI")
        print("2. Run the following JavaScript code:")
        print(f"""
// Get existing threads
let threads = JSON.parse(localStorage.getItem('cpr_threads') || '[]');

// Add new thread
threads.push({
  id: "{thread_id}",
  name: "Thread created at {time.strftime('%Y-%m-%d %H:%M:%S')}",
  messages: [
    {{
      id: "{str(uuid.uuid4())}",
      role: "user",
      content: "{args.message}",
      sent: true,
      timestamp: {int(time.time() * 1000)}
    }},
    {{
      id: "{str(uuid.uuid4())}",
      role: "assistant",
      content: "{status_data.get('result', 'Task completed successfully.')}",
      sent: true,
      taskId: "{task_id}",
      timestamp: {int(time.time() * 1000)}
    }}
  ],
  lastActivity: "{time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}"
});

// Save back to localStorage
localStorage.setItem('cpr_threads', JSON.stringify(threads));

// Reload the page to see the new thread
window.location.reload();
        """)
    else:
        print(f"Failed to send message. Status code: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    main()

