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
        if base_url:
            kwargs["base_url"] = base_url
            
        agent = Agent(**kwargs)
        
        # Send message to Codegen
        task = agent.create_task(content)
        
        # Update message with task ID
        messages[message_id]["task_id"] = task.task_id
        
        # Poll for task completion
        max_attempts = 30
        for attempt in range(max_attempts):
            # Get task status
            task_status = agent.get_task_status(task.task_id)
            
            # Check if task is completed
            if task_status.get("status") == "completed" or task_status.get("result"):
                # Update message with response
                messages[message_id]["status"] = "completed"
                messages[message_id]["response"] = task_status.get("result")
                messages[message_id]["completed_at"] = datetime.now().isoformat()
                return
            
            # Wait before checking again
            await asyncio.sleep(2)
        
        # If we get here, the task timed out
        messages[message_id]["status"] = "timeout"
        messages[message_id]["response"] = "Task timed out"
        messages[message_id]["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        # Update message with error
        messages[message_id]["status"] = "failed"
        messages[message_id]["response"] = f"Error: {str(e)}"
        messages[message_id]["completed_at"] = datetime.now().isoformat()

