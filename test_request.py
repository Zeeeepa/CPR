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
                timestamp = datetime.fromisoformat(data["timestamp"]).strftime("%H:%M:%S")
                
                if "current_step" in data:
                    print(f"\n[{timestamp}] Step: {data['current_step']}")
                elif data["status"] == "completed":
                    print(f"\n[{timestamp}] Completed: {data['result']}")
                elif data["status"] == "failed":
                    print(f"\n[{timestamp}] Failed: {data['error']}")
                else:
                    print(f"\n[{timestamp}] Status: {data['status']}")
                
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

if __name__ == "__main__":
    test_streaming()
