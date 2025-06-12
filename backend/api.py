"""
Enhanced Backend API server using official Codegen SDK
Provides comprehensive chat interface integration with real-time streaming
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

# Import the official Codegen SDK
try:
    from codegen import Agent
    CODEGEN_AVAILABLE = True
except ImportError:
    CODEGEN_AVAILABLE = False
    print("Warning: Codegen SDK not available. Install with: pip install codegen")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Request/Response Models
class TaskRequest(BaseModel):
    prompt: str = Field(..., description="The prompt to send to the Codegen agent")
    stream: bool = Field(default=True, description="Whether to stream the response")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation context")

class TaskResponse(BaseModel):
    result: Optional[str] = Field(None, description="The task result")
    status: str = Field(..., description="Task status")
    task_id: Optional[str] = Field(None, description="Unique task identifier")
    web_url: Optional[str] = Field(None, description="Web URL for the task")
    thread_id: Optional[str] = Field(None, description="Thread ID")

class TaskStatusResponse(BaseModel):
    status: str = Field(..., description="Current task status")
    result: Optional[str] = Field(None, description="Task result if completed")
    task_id: str = Field(..., description="Task identifier")
    web_url: Optional[str] = Field(None, description="Web URL for the task")
    progress: Optional[Dict[str, Any]] = Field(None, description="Progress information")

class HealthResponse(BaseModel):
    status: str
    codegen_available: bool
    version: str
    timestamp: str

# Configuration
class CodegenConfig(BaseModel):
    org_id: str
    token: str
    base_url: Optional[str] = None

class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8887
    log_level: str = "info"
    cors_origins: list = ["*"]

def get_codegen_config() -> CodegenConfig:
    """Get Codegen configuration from environment variables"""
    return CodegenConfig(
        org_id=os.getenv("CODEGEN_ORG_ID", "323"),
        token=os.getenv("CODEGEN_TOKEN", "sk-ce027fa7-3c8d-4beb-8c86-ed8ae982ac99"),
        base_url=os.getenv("CODEGEN_BASE_URL")
    )

def get_server_config() -> ServerConfig:
    """Get server configuration from environment variables"""
    return ServerConfig(
        host=os.getenv("SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("SERVER_PORT", "8887")),
        log_level=os.getenv("LOG_LEVEL", "info"),
        cors_origins=os.getenv("CORS_ORIGINS", "*").split(",")
    )

# Initialize FastAPI app
app = FastAPI(
    title="Codegen AI Chat Dashboard API",
    description="Backend API for Codegen AI agent chat interface",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
server_config = get_server_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=server_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize default Codegen configuration
default_codegen_config = get_codegen_config()

# Store active tasks and agents (in production, use Redis or database)
active_tasks: Dict[str, Any] = {}
agent_instances: Dict[str, Agent] = {}

def get_or_create_agent(org_id: str, token: str, base_url: Optional[str] = None) -> Agent:
    """Get or create a Codegen agent instance"""
    if not CODEGEN_AVAILABLE:
        raise HTTPException(status_code=500, detail="Codegen SDK not available")
    
    agent_key = f"{org_id}:{token}"
    
    if agent_key not in agent_instances:
        try:
            kwargs = {"org_id": org_id, "token": token}
            if base_url:
                kwargs["base_url"] = base_url
            
            agent_instances[agent_key] = Agent(**kwargs)
            logger.info(f"Created new agent instance for org_id: {org_id}")
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to create agent: {str(e)}")
    
    return agent_instances[agent_key]

async def stream_task_updates(task, task_id: str, thread_id: Optional[str] = None):
    """Stream task status updates to the client"""
    try:
        max_retries = 120  # 10 minutes with 5-second intervals
        retry_count = 0
        last_status = None
        
        while retry_count < max_retries:
            try:
                # Refresh task status
                task.refresh()
                current_status = task.status.lower() if task.status else "unknown"
                
                # Only send update if status changed or it's the first update
                if current_status != last_status or retry_count == 0:
                    update_data = {
                        "status": current_status,
                        "task_id": task_id,
                        "timestamp": datetime.now().isoformat(),
                        "retry_count": retry_count
                    }
                    
                    if thread_id:
                        update_data["thread_id"] = thread_id
                    
                    # Include web_url if available
                    if hasattr(task, 'web_url') and task.web_url:
                        update_data["web_url"] = task.web_url
                    
                    yield f"data: {json.dumps(update_data)}\n\n"
                    last_status = current_status
                
                # Check if task is complete
                if current_status == "completed":
                    # Try multiple ways to get the result
                    result_content = None
                    
                    # Method 1: Direct result attribute
                    if hasattr(task, 'result') and task.result:
                        result_content = task.result
                    
                    # Method 2: Check if there's a summary or output attribute
                    elif hasattr(task, 'summary') and task.summary:
                        result_content = task.summary
                    
                    # Method 3: Check for output attribute
                    elif hasattr(task, 'output') and task.output:
                        result_content = task.output
                    
                    # Method 4: Use web_url as fallback with message
                    elif hasattr(task, 'web_url') and task.web_url:
                        result_content = f"Task completed successfully. View details at: {task.web_url}"
                    
                    # Method 5: Generic completion message
                    else:
                        result_content = "Task completed successfully."
                    
                    result_data = {
                        "status": "completed",
                        "result": result_content,
                        "task_id": task_id,
                        "timestamp": datetime.now().isoformat(),
                        "web_url": getattr(task, 'web_url', None)
                    }
                    
                    if thread_id:
                        result_data["thread_id"] = thread_id
                    
                    yield f"data: {json.dumps(result_data)}\n\n"
                    yield "data: [DONE]\n\n"
                    break
                    
                elif current_status == "failed":
                    error_msg = getattr(task, 'error', None) or getattr(task, 'failure_reason', None) or 'Task failed with unknown error'
                    error_data = {
                        "status": "failed",
                        "error": error_msg,
                        "task_id": task_id,
                        "timestamp": datetime.now().isoformat(),
                        "web_url": getattr(task, 'web_url', None)
                    }
                    
                    if thread_id:
                        error_data["thread_id"] = thread_id
                    
                    yield f"data: {json.dumps(error_data)}\n\n"
                    yield "data: [DONE]\n\n"
                    break
                    
                elif current_status in ["pending", "active", "running", "queued", "in_progress"]:
                    # Continue polling
                    await asyncio.sleep(5)
                    retry_count += 1
                else:
                    # Unknown status, continue polling but log it
                    logger.warning(f"Unknown task status: {current_status} for task {task_id}")
                    await asyncio.sleep(5)
                    retry_count += 1
                    
            except Exception as e:
                logger.error(f"Error refreshing task {task_id}: {e}")
                error_data = {
                    "status": "error",
                    "error": f"Failed to refresh task: {str(e)}",
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                await asyncio.sleep(5)
                retry_count += 1
        
        # Timeout handling
        if retry_count >= max_retries:
            # Before timing out, try one final refresh to get the result
            try:
                task.refresh()
                if task.status and task.status.lower() == "completed":
                    result_content = getattr(task, 'result', None) or getattr(task, 'summary', None) or f"Task completed. View at: {getattr(task, 'web_url', 'N/A')}"
                    final_data = {
                        "status": "completed",
                        "result": result_content,
                        "task_id": task_id,
                        "timestamp": datetime.now().isoformat(),
                        "web_url": getattr(task, 'web_url', None)
                    }
                    yield f"data: {json.dumps(final_data)}\n\n"
                    yield "data: [DONE]\n\n"
                    return
            except Exception as e:
                logger.error(f"Final refresh attempt failed for task {task_id}: {e}")
            
            timeout_data = {
                "status": "timeout",
                "error": "Task polling timeout after 10 minutes. Task may still be running.",
                "task_id": task_id,
                "timestamp": datetime.now().isoformat(),
                "web_url": getattr(task, 'web_url', None)
            }
            yield f"data: {json.dumps(timeout_data)}\n\n"
            yield "data: [DONE]\n\n"
            
    except Exception as e:
        logger.error(f"Error in streaming task {task_id}: {e}")
        final_error = {
            "status": "error",
            "error": f"Streaming error: {str(e)}",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        }
        yield f"data: {json.dumps(final_error)}\n\n"
        yield "data: [DONE]\n\n"
    finally:
        # Clean up
        active_tasks.pop(task_id, None)
        logger.info(f"Cleaned up task {task_id}")

@app.post("/api/v1/run-task", response_model=TaskResponse)
async def run_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
    x_org_id: Optional[str] = Header(None, alias="X-Org-ID"),
    x_token: Optional[str] = Header(None, alias="X-Token"),
    x_base_url: Optional[str] = Header(None, alias="X-Base-URL")
):
    """
    Run a Codegen task with dynamic credentials
    Supports both streaming and non-streaming responses
    """
    try:
        # Use credentials from headers if provided, otherwise use default config
        org_id = x_org_id or default_codegen_config.org_id
        token = x_token or default_codegen_config.token
        base_url = x_base_url or default_codegen_config.base_url
        
        if not org_id or not token:
            raise HTTPException(
                status_code=400, 
                detail="Missing org_id or token. Provide via headers or environment variables."
            )
        
        logger.info(f"Running task for org_id: {org_id}, prompt length: {len(request.prompt)}")
        
        # Get or create agent instance
        agent = get_or_create_agent(org_id, token, base_url)
        
        # Run the task using official SDK
        task = agent.run(prompt=request.prompt)
        task_id = str(task.id) if task.id else f"task_{datetime.now().timestamp()}"
        
        logger.info(f"Created task with ID: {task_id}, Status: {task.status}")
        
        # Store task for status tracking
        active_tasks[task_id] = {
            "task": task,
            "created_at": datetime.now(),
            "thread_id": request.thread_id,
            "org_id": org_id
        }
        
        if request.stream:
            # Return streaming response
            return StreamingResponse(
                stream_task_updates(task, task_id, request.thread_id),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"  # Disable nginx buffering
                }
            )
        else:
            # For non-streaming, wait for completion with timeout
            max_wait_time = 300  # 5 minutes
            poll_interval = 5
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                await asyncio.sleep(poll_interval)
                task.refresh()
                status = task.status.lower() if task.status else "unknown"
                elapsed_time += poll_interval
                
                logger.debug(f"Task {task_id} status: {status} (elapsed: {elapsed_time}s)")
                
                if status == "completed":
                    result = getattr(task, 'result', 'Task completed successfully.')
                    return TaskResponse(
                        result=result,
                        status=status,
                        task_id=task_id,
                        web_url=getattr(task, 'web_url', None),
                        thread_id=request.thread_id
                    )
                elif status == "failed":
                    error_msg = getattr(task, 'error', 'Task failed with unknown error')
                    raise HTTPException(status_code=500, detail=f"Task failed: {error_msg}")
            
            # Timeout for non-streaming
            raise HTTPException(
                status_code=408, 
                detail=f"Task timeout after {max_wait_time} seconds - task may still be running"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running task: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/v1/task/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get detailed status of a specific task"""
    try:
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task_info = active_tasks[task_id]
        task = task_info["task"]
        
        # Refresh task status
        task.refresh()
        
        return TaskStatusResponse(
            status=task.status.lower() if task.status else "unknown",
            result=getattr(task, 'result', None) if task.status and task.status.lower() == "completed" else None,
            task_id=task_id,
            web_url=getattr(task, 'web_url', None),
            progress={
                "created_at": task_info["created_at"].isoformat(),
                "thread_id": task_info.get("thread_id"),
                "org_id": task_info.get("org_id")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status for {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving task status: {str(e)}")

@app.get("/api/v1/tasks")
async def list_active_tasks():
    """List all active tasks"""
    try:
        tasks_summary = []
        for task_id, task_info in active_tasks.items():
            task = task_info["task"]
            tasks_summary.append({
                "task_id": task_id,
                "status": task.status.lower() if task.status else "unknown",
                "created_at": task_info["created_at"].isoformat(),
                "thread_id": task_info.get("thread_id"),
                "org_id": task_info.get("org_id"),
                "web_url": getattr(task, 'web_url', None)
            })
        
        return {
            "active_tasks": tasks_summary,
            "total_count": len(tasks_summary)
        }
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/task/{task_id}/debug")
async def debug_task(task_id: str):
    """Debug endpoint to inspect task attributes"""
    try:
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task_info = active_tasks[task_id]
        task = task_info["task"]
        
        # Refresh task status
        task.refresh()
        
        # Get all available attributes
        task_attributes = {}
        for attr in dir(task):
            if not attr.startswith('_'):
                try:
                    value = getattr(task, attr)
                    if not callable(value):
                        task_attributes[attr] = str(value)
                except:
                    task_attributes[attr] = "Unable to access"
        
        return {
            "task_id": task_id,
            "attributes": task_attributes,
            "status": getattr(task, 'status', 'unknown'),
            "has_result": hasattr(task, 'result'),
            "has_summary": hasattr(task, 'summary'),
            "has_output": hasattr(task, 'output'),
            "has_web_url": hasattr(task, 'web_url'),
            "web_url": getattr(task, 'web_url', None)
        }
        
    except Exception as e:
        logger.error(f"Error debugging task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/task/{task_id}")
async def cancel_task(task_id: str):
    """Cancel/remove a task from tracking"""
    try:
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Remove from active tasks
        removed_task = active_tasks.pop(task_id)
        
        return {
            "message": f"Task {task_id} removed from tracking",
            "task_id": task_id,
            "was_created_at": removed_task["created_at"].isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check endpoint"""
    return HealthResponse(
        status="healthy",
        codegen_available=CODEGEN_AVAILABLE,
        version="2.0.0",
        timestamp=datetime.now().isoformat()
    )

@app.get("/api/v1/config")
async def get_config():
    """Get current configuration (without sensitive data)"""
    return {
        "codegen_available": CODEGEN_AVAILABLE,
        "default_org_id": default_codegen_config.org_id,
        "server_config": {
            "host": server_config.host,
            "port": server_config.port,
            "cors_origins": server_config.cors_origins
        },
        "active_tasks_count": len(active_tasks),
        "agent_instances_count": len(agent_instances)
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info("Starting Codegen AI Chat Dashboard API v2.0.0")
    logger.info(f"Codegen SDK Available: {CODEGEN_AVAILABLE}")
    logger.info(f"Default Org ID: {default_codegen_config.org_id}")
    logger.info(f"Server Config: {server_config.host}:{server_config.port}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("Shutting down Codegen AI Chat Dashboard API")
    # Clean up active tasks and agents
    active_tasks.clear()
    agent_instances.clear()

if __name__ == "__main__":
    server_config = get_server_config()
    uvicorn.run(
        app,
        host=server_config.host,
        port=server_config.port,
        log_level=server_config.log_level,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    )