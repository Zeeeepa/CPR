"""
Thread Management API for Codegen SDK
Provides endpoints for thread creation, message sending, and response retrieval
"""

import asyncio
import logging
import os
import json
import uuid
import time
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator, List
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks, Request, APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get Codegen credentials from environment
org_id = os.getenv("CODEGEN_ORG_ID")
token = os.getenv("CODEGEN_TOKEN")

# Print environment variables for debugging
print(f"Environment variables loaded: CODEGEN_ORG_ID={org_id}, CODEGEN_TOKEN={token[:10] if token else None}...")

# Import the official Codegen SDK
try:
    from codegen.agents.agent import Agent, AgentTask
    CODEGEN_AVAILABLE = True
except ImportError:
    CODEGEN_AVAILABLE = False
    print("Warning: Codegen SDK not available. Install with: pip install codegen")

# Define models for API requests and responses
class ThreadCreate(BaseModel):
    name: Optional[str] = None
    
class ThreadResponse(BaseModel):
    thread_id: str
    name: Optional[str] = None
    created_at: str
    
class MessageCreate(BaseModel):
    content: str
    thread_id: str
    
class MessageResponse(BaseModel):
    message_id: str
    thread_id: str
    task_id: Optional[str] = None
    status: str = "pending"
    created_at: str
    
class MessageStatusResponse(BaseModel):
    message_id: str
    thread_id: str
    task_id: Optional[str] = None
    status: str
    content: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    
class ThreadListResponse(BaseModel):
    threads: List[ThreadResponse]
    
class MessageListResponse(BaseModel):
    messages: List[MessageStatusResponse]

# Create router for thread management
router = APIRouter(prefix="/api/v1/threads", tags=["threads"])

# In-memory storage for threads and messages (in production, use a database)
threads = {}
messages = {}

# Thread management endpoints
@router.post("/", response_model=ThreadResponse)
async def create_thread(
    thread_data: ThreadCreate,
    x_organization_id: Optional[str] = Header(None),
    x_token: Optional[str] = Header(None),
    x_base_url: Optional[str] = Header(None)
):
    """Create a new thread"""
    # Use headers or environment variables
    org_id_to_use = x_organization_id or org_id
    token_to_use = x_token or token
    base_url_to_use = x_base_url
    
    if not org_id_to_use or not token_to_use:
        raise HTTPException(status_code=400, detail="Missing organization ID or token")
    
    # Generate thread ID
    thread_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    # Create thread object
    thread = {
        "thread_id": thread_id,
        "name": thread_data.name or f"Thread {thread_id[:8]}",
        "created_at": created_at,
        "messages": []
    }
    
    # Store thread
    threads[thread_id] = thread
    
    return ThreadResponse(
        thread_id=thread_id,
        name=thread.get("name"),
        created_at=created_at
    )

@router.get("/", response_model=ThreadListResponse)
async def list_threads(
    x_organization_id: Optional[str] = Header(None),
    x_token: Optional[str] = Header(None)
):
    """List all threads"""
    # Use headers or environment variables
    org_id_to_use = x_organization_id or org_id
    token_to_use = x_token or token
    
    if not org_id_to_use or not token_to_use:
        raise HTTPException(status_code=400, detail="Missing organization ID or token")
    
    thread_list = []
    for thread_id, thread in threads.items():
        thread_list.append(ThreadResponse(
            thread_id=thread_id,
            name=thread.get("name"),
            created_at=thread.get("created_at")
        ))
    
    return ThreadListResponse(threads=thread_list)

@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    x_organization_id: Optional[str] = Header(None),
    x_token: Optional[str] = Header(None)
):
    """Get a specific thread"""
    # Use headers or environment variables
    org_id_to_use = x_organization_id or org_id
    token_to_use = x_token or token
    
    if not org_id_to_use or not token_to_use:
        raise HTTPException(status_code=400, detail="Missing organization ID or token")
    
    if thread_id not in threads:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    thread = threads[thread_id]
    
    return ThreadResponse(
        thread_id=thread_id,
        name=thread.get("name"),
        created_at=thread.get("created_at")
    )

@router.post("/{thread_id}/messages", response_model=MessageResponse)
async def create_message(
    thread_id: str,
    message_data: MessageCreate,
    background_tasks: BackgroundTasks,
    x_organization_id: Optional[str] = Header(None),
    x_token: Optional[str] = Header(None),
    x_base_url: Optional[str] = Header(None)
):
    """Create a new message in a thread"""
    # Use headers or environment variables
    org_id_to_use = x_organization_id or org_id
    token_to_use = x_token or token
    base_url_to_use = x_base_url
    
    if not org_id_to_use or not token_to_use:
        raise HTTPException(status_code=400, detail="Missing organization ID or token")
    
    if thread_id not in threads:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Generate message ID
    message_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    # Create message object
    message = {
        "message_id": message_id,
        "thread_id": thread_id,
        "content": message_data.content,
        "status": "pending",
        "created_at": created_at,
        "completed_at": None,
        "task_id": None,
        "response": None
    }
    
    # Store message
    messages[message_id] = message
    threads[thread_id]["messages"].append(message_id)
    
    # Process message in background
    background_tasks.add_task(
        process_message,
        message_id=message_id,
        content=message_data.content,
        org_id=org_id_to_use,
        token=token_to_use,
        base_url=base_url_to_use
    )
    
    return MessageResponse(
        message_id=message_id,
        thread_id=thread_id,
        task_id=None,
        status="pending",
        created_at=created_at
    )

@router.get("/{thread_id}/messages", response_model=MessageListResponse)
async def list_messages(
    thread_id: str,
    x_organization_id: Optional[str] = Header(None),
    x_token: Optional[str] = Header(None)
):
    """List all messages in a thread"""
    # Use headers or environment variables
    org_id_to_use = x_organization_id or org_id
    token_to_use = x_token or token
    
    if not org_id_to_use or not token_to_use:
        raise HTTPException(status_code=400, detail="Missing organization ID or token")
    
    if thread_id not in threads:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    message_list = []
    for message_id in threads[thread_id]["messages"]:
        if message_id in messages:
            message = messages[message_id]
            message_list.append(MessageStatusResponse(
                message_id=message_id,
                thread_id=thread_id,
                task_id=message.get("task_id"),
                status=message.get("status"),
                content=message.get("response"),
                created_at=message.get("created_at"),
                completed_at=message.get("completed_at")
            ))
    
    return MessageListResponse(messages=message_list)

@router.get("/{thread_id}/messages/{message_id}", response_model=MessageStatusResponse)
async def get_message(
    thread_id: str,
    message_id: str,
    x_organization_id: Optional[str] = Header(None),
    x_token: Optional[str] = Header(None)
):
    """Get a specific message"""
    # Use headers or environment variables
    org_id_to_use = x_organization_id or org_id
    token_to_use = x_token or token
    
    if not org_id_to_use or not token_to_use:
        raise HTTPException(status_code=400, detail="Missing organization ID or token")
    
    if thread_id not in threads:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    if message_id not in messages:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message = messages[message_id]
    
    if message.get("thread_id") != thread_id:
        raise HTTPException(status_code=404, detail="Message not found in this thread")
    
    return MessageStatusResponse(
        message_id=message_id,
        thread_id=thread_id,
        task_id=message.get("task_id"),
        status=message.get("status"),
        content=message.get("response"),
        created_at=message.get("created_at"),
        completed_at=message.get("completed_at")
    )

# Helper function to process messages using Codegen SDK
async def process_message(message_id: str, content: str, org_id: str, token: str, base_url: Optional[str] = None):
    """Process a message using Codegen SDK"""
    # ... existing error handling for CODEGEN_AVAILABLE ...
    if not CODEGEN_AVAILABLE:
        # Update message with error
        messages[message_id]["status"] = "failed"
        messages[message_id]["response"] = "Codegen SDK not available"
        messages[message_id]["completed_at"] = datetime.now().isoformat()
        return
    
    try:
        # Update message status
        messages[message_id]["status"] = "processing"
        
        # Initialize Agent with proper parameters
        kwargs = {"org_id": org_id, "token": token}
        if base_url and base_url != "default":
            kwargs["base_url"] = base_url
            
        agent = Agent(**kwargs)
        
        # Send message to Codegen
        try:
            # Try to use the run method
            task = agent.run(content)
            
            # Store task ID if available
            task_id = None
            if hasattr(task, 'id') and task.id is not None:
                task_id = str(task.id)
            elif hasattr(task, 'agent_run_id') and task.agent_run_id is not None:
                task_id = str(task.agent_run_id)
            elif hasattr(task, 'run_id') and task.run_id is not None:
                task_id = str(task.run_id)
            
            if task_id:
                messages[message_id]["task_id"] = task_id
            
            # Store web URL if available
            if hasattr(task, 'web_url') and task.web_url:
                messages[message_id]["web_url"] = task.web_url
            
            # Wait for task to complete with timeout
            max_retries = 60  # 5 minutes with 5-second intervals
            for _ in range(max_retries):
                # Refresh task to get latest status
                task.refresh()
                
                # Get current status
                status = task.status.lower() if hasattr(task, 'status') and task.status else "unknown"
                
                # If task is completed, extract the result
                if status in ["completed", "complete"]:
                    # Extract result
                    result = None
                    if hasattr(task, 'result') and task.result:
                        if isinstance(task.result, str):
                            result = task.result
                        elif isinstance(task.result, dict):
                            result = task.result.get('content') or task.result.get('response') or str(task.result)
                    
                    # If no result but we have web_url, use that
                    if not result and hasattr(task, 'web_url') and task.web_url:
                        result = f"Task completed successfully. View details at: {task.web_url}"
                        messages[message_id]["web_url"] = task.web_url
                    
                    # Update message with result
                    messages[message_id]["status"] = "completed"
                    messages[message_id]["response"] = result
                    messages[message_id]["completed_at"] = datetime.now().isoformat()
                    return
                
                # If task failed, update with error
                elif status == "failed":
                    error = getattr(task, 'error', "Unknown error")
                    messages[message_id]["status"] = "failed"
                    messages[message_id]["response"] = f"Error: {error}"
                    messages[message_id]["completed_at"] = datetime.now().isoformat()
                    return
                
                # Wait before next check
                await asyncio.sleep(5)
            
            # If we reach here, task timed out
            messages[message_id]["status"] = "timeout"
            messages[message_id]["response"] = "Task timed out after 5 minutes"
            messages[message_id]["completed_at"] = datetime.now().isoformat()
            
        except Exception as e:
            # If run method fails
            messages[message_id]["status"] = "failed"
            messages[message_id]["response"] = f"Error: {str(e)}"
            messages[message_id]["completed_at"] = datetime.now().isoformat()
    except Exception as e:
        # Update message with error
        messages[message_id]["status"] = "failed"
        messages[message_id]["response"] = f"Error: {str(e)}"
        messages[message_id]["completed_at"] = datetime.now().isoformat()
