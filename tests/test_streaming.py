"""
Integration tests for SSE streaming functionality
"""

import asyncio
import json
import os
from typing import AsyncGenerator
import pytest
from fastapi.testclient import TestClient
from sse_starlette.sse import EventSourceResponse

from backend.api import app, active_tasks

# Test client
client = TestClient(app)

# Mock environment variables
os.environ["CODEGEN_ORG_ID"] = "test_org"
os.environ["CODEGEN_TOKEN"] = "test_token"

@pytest.mark.asyncio
async def test_task_streaming_flow():
    """Test the complete task streaming flow"""
    # 1. Start a task
    response = client.post(
        "/api/v1/run-task",
        headers={
            "X-Organization-ID": "test_org",
            "X-API-Token": "test_token"
        },
        json={
            "prompt": "Test prompt",
            "stream": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    task_id = data["task_id"]
    
    # 2. Connect to SSE stream
    with client.websocket_connect(f"/api/v1/task/{task_id}/stream") as websocket:
        # Collect all events
        events = []
        done = False
        
        while not done:
            data = websocket.receive_text()
            if not data:
                break
                
            # Parse SSE event
            if data.startswith("data: "):
                event_data = data[6:].strip()
                if event_data == "[DONE]":
                    done = True
                else:
                    try:
                        event = json.loads(event_data)
                        events.append(event)
                    except json.JSONDecodeError:
                        continue
        
        # Validate events
        assert len(events) > 0
        
        # Check for step updates
        steps = [e for e in events if "current_step" in e]
        assert len(steps) > 0
        
        # Check for completion
        completion = [e for e in events if e["status"] == "completed"]
        assert len(completion) == 1
        assert "result" in completion[0]
        
        # Verify task cleanup
        assert task_id not in active_tasks

@pytest.mark.asyncio
async def test_task_error_handling():
    """Test error handling in streaming"""
    # 1. Start a task that will fail
    response = client.post(
        "/api/v1/run-task",
        headers={
            "X-Organization-ID": "test_org",
            "X-API-Token": "invalid_token"  # This should cause an error
        },
        json={
            "prompt": "Test prompt",
            "stream": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    task_id = data["task_id"]
    
    # 2. Connect to SSE stream
    with client.websocket_connect(f"/api/v1/task/{task_id}/stream") as websocket:
        events = []
        done = False
        
        while not done:
            data = websocket.receive_text()
            if not data:
                break
                
            if data.startswith("data: "):
                event_data = data[6:].strip()
                if event_data == "[DONE]":
                    done = True
                else:
                    try:
                        event = json.loads(event_data)
                        events.append(event)
                    except json.JSONDecodeError:
                        continue
        
        # Validate error handling
        assert len(events) > 0
        errors = [e for e in events if e["status"] in ["error", "failed"]]
        assert len(errors) > 0
        assert "error" in errors[0]
        
        # Verify task cleanup
        assert task_id not in active_tasks

@pytest.mark.asyncio
async def test_client_disconnect_handling():
    """Test handling of client disconnections"""
    # 1. Start a task
    response = client.post(
        "/api/v1/run-task",
        headers={
            "X-Organization-ID": "test_org",
            "X-API-Token": "test_token"
        },
        json={
            "prompt": "Test prompt",
            "stream": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    task_id = data["task_id"]
    
    # 2. Connect and immediately disconnect
    with client.websocket_connect(f"/api/v1/task/{task_id}/stream") as websocket:
        # Receive one message then disconnect
        data = websocket.receive_text()
        assert data.startswith("data: ")
    
    # Wait a bit for cleanup
    await asyncio.sleep(0.1)
    
    # Verify task cleanup after disconnect
    assert task_id not in active_tasks

@pytest.mark.asyncio
async def test_heartbeat_events():
    """Test heartbeat events are sent"""
    # 1. Start a task
    response = client.post(
        "/api/v1/run-task",
        headers={
            "X-Organization-ID": "test_org",
            "X-API-Token": "test_token"
        },
        json={
            "prompt": "Test prompt",
            "stream": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    task_id = data["task_id"]
    
    # 2. Connect to SSE stream
    with client.websocket_connect(f"/api/v1/task/{task_id}/stream") as websocket:
        heartbeats = 0
        start_time = asyncio.get_event_loop().time()
        
        # Listen for 6 seconds to catch at least one heartbeat
        while asyncio.get_event_loop().time() - start_time < 6:
            data = websocket.receive_text()
            if data == ": heartbeat\n\n":
                heartbeats += 1
            
            if data.startswith("data: ") and data[6:].strip() == "[DONE]":
                break
        
        # Should have received at least one heartbeat
        assert heartbeats > 0

def test_invalid_task_id():
    """Test accessing stream with invalid task ID"""
    response = client.get("/api/v1/task/invalid_id/stream")
    assert response.status_code == 404
    assert "Task not found" in response.json()["detail"]

