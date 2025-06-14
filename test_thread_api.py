#!/usr/bin/env python3
"""
Test script for the Thread Management API
This script tests the basic functionality of the thread management API:
1. Create a thread
2. Send a message to the thread
3. Retrieve the message response
"""

import requests
import json
import time
import argparse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description='Test Thread Management API')
    parser.add_argument('--org_id', type=str, default=os.getenv('CODEGEN_ORG_ID'),
                        help='Organization ID')
    parser.add_argument('--token', type=str, default=os.getenv('CODEGEN_TOKEN'),
                        help='API token')
    parser.add_argument('--base_url', type=str, default='default',
                        help='Base URL')
    parser.add_argument('--backend_url', type=str, default='http://localhost:8002',
                        help='Backend URL')
    parser.add_argument('--message', type=str, default='Hello from the test script!',
                        help='Message to send to the thread')
    
    args = parser.parse_args()
    
    # Validate required parameters
    if not args.org_id or not args.token:
        print("Error: Organization ID and token are required.")
        print("Set them as environment variables or provide them as arguments.")
        return
    
    # Headers for API requests
    headers = {
        'Content-Type': 'application/json',
        'X-Organization-ID': args.org_id,
        'X-Token': args.token,
        'X-Base-URL': args.base_url
    }
    
    print("=== Starting Thread API Test ===\n")
    
    # Step 1: Create a thread
    print("=== Creating Thread ===")
    thread_response = requests.post(
        f"{args.backend_url}/api/v1/threads",
        headers=headers,
        json={"name": f"Test Thread {time.strftime('%Y-%m-%d %H:%M:%S')}"}
    )
    
    if thread_response.status_code != 200:
        print(f"Error creating thread: {thread_response.status_code}")
        print(f"Response: {thread_response.text}")
        return
    
    thread_data = thread_response.json()
    thread_id = thread_data.get('thread_id')
    print(f"Thread created with ID: {thread_id}")
    print(f"Thread name: {thread_data.get('name')}")
    print(f"Created at: {thread_data.get('created_at')}")
    print()
    
    # Step 2: Send a message to the thread
    print("=== Sending Message ===")
    message_response = requests.post(
        f"{args.backend_url}/api/v1/threads/{thread_id}/messages",
        headers=headers,
        json={"content": args.message, "thread_id": thread_id}
    )
    
    if message_response.status_code != 200:
        print(f"Error sending message: {message_response.status_code}")
        print(f"Response: {message_response.text}")
        return
    
    message_data = message_response.json()
    message_id = message_data.get('message_id')
    print(f"Message sent with ID: {message_id}")
    print(f"Initial status: {message_data.get('status')}")
    print()
    
    # Step 3: Poll for message response
    print("=== Polling for Response ===")
    max_attempts = 30
    for attempt in range(max_attempts):
        print(f"Checking message status (attempt {attempt+1}/{max_attempts})...")
        
        status_response = requests.get(
            f"{args.backend_url}/api/v1/threads/{thread_id}/messages/{message_id}",
            headers=headers
        )
        
        if status_response.status_code != 200:
            print(f"Error checking message status: {status_response.status_code}")
            print(f"Response: {status_response.text}")
            time.sleep(2)
            continue
        
        status_data = status_response.json()
        print(f"Status: {status_data.get('status')}")
        
        # Check if message is completed
        if status_data.get('status') == 'completed':
            print("\n=== Message Completed ===")
            print(f"Response content: {status_data.get('content')}")
            print(f"Completed at: {status_data.get('completed_at')}")
            break
        
        # Check if message failed
        if status_data.get('status') in ['failed', 'timeout']:
            print("\n=== Message Failed ===")
            print(f"Error: {status_data.get('content')}")
            break
        
        # Wait before checking again
        time.sleep(2)
    else:
        print("\n=== Polling Timeout ===")
        print("Message did not complete within the expected time.")
    
    # Step 4: List all messages in the thread
    print("\n=== Listing All Messages ===")
    messages_response = requests.get(
        f"{args.backend_url}/api/v1/threads/{thread_id}/messages",
        headers=headers
    )
    
    if messages_response.status_code != 200:
        print(f"Error listing messages: {messages_response.status_code}")
        print(f"Response: {messages_response.text}")
    else:
        messages_data = messages_response.json()
        print(f"Found {len(messages_data.get('messages', []))} messages in thread:")
        for idx, msg in enumerate(messages_data.get('messages', []), 1):
            print(f"  {idx}. ID: {msg.get('message_id')}")
            print(f"     Status: {msg.get('status')}")
            print(f"     Content: {msg.get('content')}")
            print()
    
    print("=== Test Complete ===")
    print(f"Thread ID: {thread_id}")
    print(f"Message ID: {message_id}")
    print("\nYou can now check the UI to see if the thread and message are displayed correctly.")

if __name__ == "__main__":
    main()

