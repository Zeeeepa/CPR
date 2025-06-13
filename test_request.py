"""
Manual test script for SSE streaming
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from sseclient import SSEClient
import requests

# Configuration
url = "http://localhost:8002/api/v1/run-task"
org_id = os.getenv("CODEGEN_ORG_ID")
token = os.getenv("CODEGEN_TOKEN")

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
    task_id = data["task_id"]
    print(f"Task started with ID: {task_id}")
    
    # 2. Connect to SSE stream
    print("\nConnecting to SSE stream...")
    stream_url = f"http://localhost:8002/api/v1/task/{task_id}/stream"
    client = SSEClient(stream_url)
    
    try:
        print("\nReceiving events:")
        print("-" * 50)
        
        for event in client:
            if event.data == "[DONE]":
                print("\n✅ Stream completed")
                break
                
            try:
                data = json.loads(event.data)
                
                # Skip heartbeat events
                if data.get("status") == "heartbeat":
                    continue
                
                # Format timestamp if available
                timestamp = ""
                if "timestamp" in data:
                    try:
                        timestamp = datetime.fromisoformat(data["timestamp"]).strftime("%H:%M:%S")
                    except (ValueError, TypeError):
                        timestamp = "??:??:??"
                else:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                
                if "current_step" in data:
                    print(f"\n[{timestamp}] Step: {data['current_step']}")
                elif data.get("status") == "completed":
                    print(f"\n[{timestamp}] Completed: {data.get('result', 'No result provided')}")
                elif data.get("status") == "failed" or data.get("status") == "error":
                    print(f"\n[{timestamp}] Failed: {data.get('error', 'Unknown error')}")
                else:
                    print(f"\n[{timestamp}] Status: {data.get('status', 'unknown')}")
                
                if "web_url" in data and data["web_url"]:
                    print(f"View at: {data['web_url']}")
                    
            except json.JSONDecodeError:
                if event.data != "heartbeat":
                    print(f"Raw event: {event.data}")
                
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        client.close()
        print("-" * 50)

def test_connection():
    """Test the connection to the backend API"""
    print("\n🔌 Testing connection to backend API...\n")
    
    try:
        response = requests.post(
            "http://localhost:8002/api/v1/test-connection",
            headers={
                "Content-Type": "application/json",
                "X-Organization-ID": org_id,
                "X-API-Token": token
            }
        )
        
        if response.ok:
            data = response.json()
            print("✅ Connection successful!")
            print(f"Status: {data.get('status', 'unknown')}")
            print(f"Message: {data.get('message', 'No message')}")
            print(f"Organization ID: {data.get('org_id', 'Not provided')}")
            print(f"Base URL: {data.get('base_url', 'Not provided')}")
            return True
        else:
            print(f"❌ Connection failed: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Error testing connection: {e}")
        return False

if __name__ == "__main__":
    if test_connection():
        test_streaming()
    else:
        print("\n⚠️ Connection test failed. Skipping streaming test.")
        sys.exit(1)

