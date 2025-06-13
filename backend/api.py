"""
Enhanced Backend API server using official Codegen SDK
Provides comprehensive chat interface integration with real-time streaming
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn
from contextlib import asynccontextmanager

# Import the official Codegen SDK
try:
    from codegen.agents.agent import Agent
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
    port: int = 8002
    log_level: str = "info"
    cors_origins: list = ["*"]

def get_codegen_config() -> CodegenConfig:
    """Get Codegen configuration from environment variables"""
    org_id = os.getenv("CODEGEN_ORG_ID")
    token = os.getenv("CODEGEN_TOKEN")
    
    if not org_id:
        raise ValueError("CODEGEN_ORG_ID environment variable is required")
    if not token:
        raise ValueError("CODEGEN_TOKEN environment variable is required")
    
    return CodegenConfig(
        org_id=org_id,
        token=token,
        base_url=os.getenv("CODEGEN_BASE_URL")  # Don't use default base_url, let SDK use its default
    )

def get_server_config() -> ServerConfig:
    """Get server configuration from environment variables"""
    return ServerConfig(
        host=os.getenv("SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("SERVER_PORT", "8002")),
        log_level=os.getenv("LOG_LEVEL", "info"),
        cors_origins=os.getenv("CORS_ORIGINS", "*").split(",")
    )

# Store active tasks and agent clients
active_tasks: Dict[str, Any] = {}
agent_clients: Dict[str, Agent] = {}

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Codegen AI Chat Dashboard API v2.0.0")
    logger.info(f"Codegen SDK Available: {CODEGEN_AVAILABLE}")
    logger.info(f"Default Org ID: {default_codegen_config.org_id}")
    logger.info(f"Server Config: {server_config.host}:{server_config.port}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Codegen AI Chat Dashboard API")
    active_tasks.clear()
    agent_clients.clear()

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Codegen AI Chat Dashboard API",
    description="Backend API for Codegen AI agent chat interface",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
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

# Enhanced Agent Client for better error handling and status tracking
class AgentClient:
    def __init__(self, org_id: str, token: str, base_url: Optional[str] = None):
        if not CODEGEN_AVAILABLE:
            raise ImportError("Codegen SDK not available. Install with: pip install codegen")
        
        kwargs = {"org_id": org_id, "token": token}
        if base_url:
            kwargs["base_url"] = base_url
            
        self.agent = Agent(**kwargs)
        
    async def process_message(self, message: str, stream: bool = True) -> Dict[str, Any]:
        """Process a message with proper error handling and status tracking"""
        try:
            # Run the agent with the message
            task = self.agent.run(prompt=message)
            task_id = str(task.id) if task.id else f"task_{datetime.now().timestamp()}"
            
            if not stream:
                # For non-streaming, wait for completion
                max_retries = 60  # 5 minutes with 5-second intervals
                for _ in range(max_retries):
                    task.refresh()
                    status = task.status.lower() if task.status else "unknown"
                    
                    if status in ["completed", "complete"]:
                        return {
                            "status": "completed",
                            "result": getattr(task, 'result', None),
                            "task_id": task_id,
                            "web_url": getattr(task, 'web_url', None)
                        }
                    elif status == "failed":
                        return {
                            "status": "failed",
                            "error": getattr(task, 'error', "Unknown error"),
                            "task_id": task_id
                        }
                    
                    await asyncio.sleep(5)
                
                return {
                    "status": "timeout",
                    "error": "Task timed out",
                    "task_id": task_id
                }
            
            return {
                "status": "initiated",
                "task": task,
                "task_id": task_id
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "status": "error",
                "error": str(e),
                "task_id": None
            }

def get_or_create_agent_client(org_id: str, token: str, base_url: Optional[str] = None) -> AgentClient:
    """Get or create an AgentClient instance"""
    if not CODEGEN_AVAILABLE:
        raise HTTPException(status_code=500, detail="Codegen SDK not available")
    
    client_key = f"{org_id}:{token}"
    
    if client_key not in agent_clients:
        try:
            agent_clients[client_key] = AgentClient(org_id, token, base_url)
            logger.info(f"Created new agent client for org_id: {org_id}")
        except Exception as e:
            logger.error(f"Failed to create agent client: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to create agent client: {str(e)}")
    
    return agent_clients[client_key]

async def stream_task_updates(task, task_id: str, thread_id: Optional[str] = None) -> AsyncGenerator[str, None]:
    """Stream task status updates to the client with enhanced error handling"""
    try:
        max_retries = 900  # 30 minutes with 2-second intervals
        retry_count = 0
        last_step = None
        
        while retry_count < max_retries:
            try:
                # Refresh task status
                task.refresh()
                current_status = task.status.lower() if task.status else "unknown"
                
                # Extract step information
                current_step = None
                try:
                    # Try to get step information from task.result or task.summary
                    if hasattr(task, 'result') and isinstance(task.result, dict):
                        current_step = task.result.get('current_step')
                    elif hasattr(task, 'summary') and isinstance(task.summary, dict):
                        current_step = task.summary.get('current_step')
                except Exception as e:
                    logger.warning(f"Could not extract step info: {e}")
                
                # Prepare update data
                update_data = {
                    "status": current_status,
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat()
                }
                
                if thread_id:
                    update_data["thread_id"] = thread_id
                
                if hasattr(task, 'web_url') and task.web_url:
                    update_data["web_url"] = task.web_url
                
                # Only send step update if it has changed
                if current_step and current_step != last_step:
                    update_data["current_step"] = current_step
                    last_step = current_step
                
                # Check if task is complete
                if current_status == "completed":
                    result = (
                        getattr(task, 'result', None) or
                        getattr(task, 'summary', None) or
                        getattr(task, 'output', None) or
                        (f"Task completed successfully. View details at: {task.web_url}" if hasattr(task, 'web_url') else None) or
                        "Task completed successfully."
                    )
                    
                    # Send completion event
                    yield f"data: {json.dumps({
                        'status': 'completed',
                        'task_id': task_id,
                        'result': result,
                        'web_url': getattr(task, 'web_url', None)
                    })}\\n\\n"
                    
                    # Send done event
                    yield "data: [DONE]\\n\\n"
                    break
                    
                elif current_status == "failed":
                    error_msg = getattr(task, 'error', None) or getattr(task, 'failure_reason', None) or 'Task failed with unknown error'
                    
                    # Send failure event
                    yield f"data: {json.dumps({
                        'status': 'failed',
                        'task_id': task_id,
                        'error': error_msg,
                        'web_url': getattr(task, 'web_url', None)
                    })}\\n\\n"
                    
                    # Send done event
                    yield "data: [DONE]\\n\\n"
                    break
                    
                elif current_status != "unknown":
                    # Send status update
                    yield f"data: {json.dumps(update_data)}\\n\\n"
                
                # Send heartbeat every 5 seconds to keep connection alive
                yield ": heartbeat\\n\\n"
                
                # Wait before next update
                await asyncio.sleep(2)
                retry_count += 1
                
            except Exception as e:
                logger.error(f"Error refreshing task {task_id}: {e}")
                # Send error event
                yield f"data: {json.dumps({
                    'status': 'error',
                    'error': f"Failed to refresh task: {str(e)}",
                    'task_id': task_id,
                })}\\n\\n"
                break
        
        # Handle timeout
        if retry_count >= max_retries:
            logger.error(f"Task {task_id} timed out after {max_retries * 2} seconds")
            yield f"data: {json.dumps({
                'status': 'failed',
                'error': f"Task timed out after {max_retries * 2} seconds",
                'task_id': task_id,
            })}\\n\\n"
            
    except Exception as e:
        logger.error(f"Stream error for task {task_id}: {e}")
        yield f"data: {json.dumps({
            'status': 'error',
            'error': str(e),
            'task_id': task_id,
        })}\\n\\n"
        
    finally:
        # Clean up task
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
        
        # Get or create agent client
        agent_client = get_or_create_agent_client(org_id, token, base_url)
        
        # Process the message
        result = await agent_client.process_message(request.prompt, stream=request.stream)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["error"])
        
        if not request.stream:
            # Return direct response for non-streaming
            return TaskResponse(
                result=result.get("result"),
                status=result["status"],
                task_id=result["task_id"],
                web_url=result.get("web_url"),
                thread_id=request.thread_id
            )
        
        # Store task for status tracking
        task_id = result["task_id"]
        active_tasks[task_id] = {
            "task": result["task"],
            "created_at": datetime.now(),
            "thread_id": request.thread_id,
            "org_id": org_id
        }
        
        # Return streaming response with proper SSE headers
        return StreamingResponse(
            stream_task_updates(result["task"], task_id, request.thread_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Content-Type": "text/event-stream",
                "Transfer-Encoding": "chunked"
            }
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

@app.post("/api/v1/test-connection")
async def test_connection():
    """Test connection to Codegen API"""
    try:
        if not CODEGEN_AVAILABLE:
            raise HTTPException(status_code=500, detail="Codegen SDK not available")
        
        # Try to get configuration
        try:
            config = get_codegen_config()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Try to create an agent and test connection
        try:
            agent = Agent(
                org_id=config.org_id,
                token=config.token,
                base_url=config.base_url
            )
            
            # Test with a simple status check - this will validate credentials
            status = agent.get_status()
            
            return {
                "status": "connected",
                "message": "Successfully connected to Codegen API",
                "org_id": config.org_id,
                "base_url": config.base_url,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            raise HTTPException(
                status_code=401, 
                detail=f"Failed to connect to Codegen API: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in connection test: {e}")
        raise HTTPException(status_code=500, detail=f"Connection test error: {str(e)}")

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
        "agent_clients_count": len(agent_clients)
    }

@app.get("/api/v1/task/{task_id}/stream")
async def stream_task_events(
    task_id: str,
    request: Request,
    background_tasks: BackgroundTasks
) -> StreamingResponse:
    """Stream task events using Server-Sent Events (SSE)"""
    try:
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail="Task not found")
            
        task_info = active_tasks[task_id]
        task = task_info["task"]
        
        async def event_generator():
            try:
                max_retries = 150  # 5 minutes with 2-second intervals
                retry_count = 0
                last_step = None
                
                while retry_count < max_retries:
                    try:
                        # Check if client disconnected
                        if await request.is_disconnected():
                            logger.info(f"Client disconnected from task {task_id} stream")
                            break
                            
                        # Refresh task status
                        task.refresh()
                        current_status = task.status.lower() if task.status else "unknown"
                        logger.info(f"Task {task_id} status: {current_status}")
                        
                        # Debug: Log all task attributes to understand completion states
                        debug_info = {
                            'status': task.status,
                            'has_result': hasattr(task, 'result') and task.result is not None,
                            'has_output': hasattr(task, 'output') and task.output is not None,
                            'has_web_url': hasattr(task, 'web_url') and task.web_url is not None,
                        }
                        logger.debug(f"Task {task_id} debug info: {debug_info}")
                        
                        # Extract step information from multiple sources
                        current_step = None
                        try:
                            # Method 1: Try to get step from result
                            if hasattr(task, 'result') and isinstance(task.result, dict):
                                current_step = task.result.get('current_step') or task.result.get('step') or task.result.get('action')
                            
                            # Method 2: Try to get step from summary
                            if not current_step and hasattr(task, 'summary') and isinstance(task.summary, dict):
                                current_step = task.summary.get('current_step') or task.summary.get('step') or task.summary.get('action')
                            
                            # Method 3: Try to get step from status or other attributes
                            if not current_step:
                                for attr_name in ['current_action', 'current_step', 'step', 'action', 'phase']:
                                    if hasattr(task, attr_name):
                                        attr_value = getattr(task, attr_name)
                                        if attr_value and isinstance(attr_value, str):
                                            current_step = attr_value
                                            break
                            
                            # Method 4: Infer step from status
                            if not current_step and current_status:
                                status_to_step = {
                                    'pending': 'Task queued',
                                    'running': 'Processing request',
                                    'in_progress': 'Executing task',
                                    'active': 'Agent working',
                                    'processing': 'Analyzing input',
                                    'executing': 'Running commands',
                                    'finalizing': 'Completing task'
                                }
                                current_step = status_to_step.get(current_status, f"Status: {current_status}")
                                
                        except Exception as e:
                            logger.warning(f"Could not extract step info: {e}")
                            # Fallback step based on status
                            if current_status in ['running', 'in_progress', 'active']:
                                current_step = f"Processing ({current_status})"
                        
                        # Prepare update data
                        update_data = {
                            "status": current_status,
                            "task_id": task_id,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        if hasattr(task, 'web_url') and task.web_url:
                            update_data["web_url"] = task.web_url
                        
                        # Only send step update if it has changed
                        if current_step and current_step != last_step:
                            update_data["current_step"] = current_step
                            last_step = current_step
                            logger.info(f"Task {task_id} step: {current_step}")
                        
                        # Check if task is complete - expanded completion detection
                        is_completed = (
                            current_status in ["completed", "complete", "finished", "done", "success", "successful"] or
                            (hasattr(task, 'web_url') and task.web_url and current_status not in ["pending", "running", "in_progress", "active", "processing", "executing"]) or
                            (hasattr(task, 'result') and task.result and current_status not in ["pending", "running", "in_progress", "active", "processing", "executing"])
                        )
                        
                        if is_completed:
                            # Try multiple ways to get the result
                            result = None
                            
                            # Method 1: Try to get result directly
                            if hasattr(task, 'result') and task.result:
                                if isinstance(task.result, dict):
                                    result = task.result.get('content') or task.result.get('response') or str(task.result)
                                else:
                                    result = str(task.result)
                            
                            # Method 2: Try to get summary
                            if not result and hasattr(task, 'summary') and task.summary:
                                if isinstance(task.summary, dict):
                                    result = task.summary.get('content') or task.summary.get('response') or str(task.summary)
                                else:
                                    result = str(task.summary)
                            
                            # Method 3: Try to get output
                            if not result and hasattr(task, 'output') and task.output:
                                result = str(task.output)
                            
                            # Method 4: Try to get response from messages
                            if not result and hasattr(task, 'messages') and task.messages:
                                try:
                                    # Get the last assistant message
                                    for msg in reversed(task.messages):
                                        if hasattr(msg, 'role') and msg.role == 'assistant' and hasattr(msg, 'content'):
                                            result = msg.content
                                            break
                                except Exception as e:
                                    logger.warning(f"Could not extract from messages: {e}")
                            
                            # Method 5: Try to get any text content from task attributes
                            if not result:
                                for attr_name in ['content', 'response', 'text', 'answer']:
                                    if hasattr(task, attr_name):
                                        attr_value = getattr(task, attr_name)
                                        if attr_value and isinstance(attr_value, str) and len(attr_value.strip()) > 0:
                                            result = attr_value
                                            break
                            
                            # Fallback with web URL
                            if not result:
                                if hasattr(task, 'web_url') and task.web_url:
                                    result = f"Task completed successfully. View full details at: {task.web_url}"
                                else:
                                    result = "Task completed successfully."
                            
                            logger.info(f"Task {task_id} completed with result: {result[:200]}...")
                            
                            # Debug: Log all task attributes for debugging
                            debug_attrs = {}
                            for attr in ['result', 'summary', 'output', 'content', 'response', 'messages']:
                                if hasattr(task, attr):
                                    attr_val = getattr(task, attr)
                                    debug_attrs[attr] = str(attr_val)[:100] if attr_val else None
                            logger.debug(f"Task {task_id} attributes: {debug_attrs}")
                            
                            # Send completion event
                            yield f"data: {json.dumps({
                                'status': 'completed',
                                'task_id': task_id,
                                'result': result,
                                'web_url': getattr(task, 'web_url', None)
                            })}\\n\\n"
                            
                            # Send done event
                            yield "data: [DONE]\\n\\n"
                            break
                            
                        elif current_status == "failed":
                            error_msg = getattr(task, 'error', None) or getattr(task, 'failure_reason', None) or 'Task failed with unknown error'
                            logger.error(f"Task {task_id} failed: {error_msg}")
                            
                            # Send failure event
                            yield f"data: {json.dumps({
                                'status': 'failed',
                                'task_id': task_id,
                                'error': error_msg,
                                'web_url': getattr(task, 'web_url', None)
                            })}\\n\\n"
                            
                            # Send done event
                            yield "data: [DONE]\\n\\n"
                            break
                            
                        elif current_status != "unknown":
                            # Send status update
                            yield f"data: {json.dumps(update_data)}\\n\\n"
                        
                        # Send heartbeat every 5 seconds to keep connection alive
                        yield ": heartbeat\\n\\n"
                        
                        # Check for early completion indicators every 30 seconds
                        if retry_count > 0 and retry_count % 15 == 0:  # Every 30 seconds (15 * 2 seconds)
                            if hasattr(task, 'web_url') and task.web_url and current_status not in ["pending", "running"]:
                                logger.info(f"Task {task_id} appears complete (has web_url), forcing completion check")
                                # Force completion on next iteration
                                continue
                        
                        # Wait before next update
                        await asyncio.sleep(2)
                        retry_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error refreshing task {task_id}: {e}")
                        # Send error event
                        yield f"data: {json.dumps({
                            'status': 'error',
                            'error': f"Failed to refresh task: {str(e)}",
                            'task_id': task_id,
                        })}\\n\\n"
                        break
                
                # Handle timeout - but first check if we can extract any result
                if retry_count >= max_retries:
                    logger.warning(f"Task {task_id} reached max retries, checking for any available result...")
                    
                    # Try to extract result even if status isn't "completed"
                    final_result = None
                    if hasattr(task, 'web_url') and task.web_url:
                        final_result = f"Task processing completed. View full details at: {task.web_url}"
                    elif hasattr(task, 'result') and task.result:
                        if isinstance(task.result, dict):
                            final_result = task.result.get('content') or task.result.get('response') or str(task.result)
                        else:
                            final_result = str(task.result)
                    
                    if final_result:
                        logger.info(f"Task {task_id} forced completion with result")
                        yield f"data: {json.dumps({
                            'status': 'completed',
                            'result': final_result,
                            'task_id': task_id,
                            'web_url': getattr(task, 'web_url', None)
                        })}\\n\\n"
                        yield "data: [DONE]\\n\\n"
                    else:
                        logger.error(f"Task {task_id} timed out after {max_retries * 2} seconds with no result")
                        yield f"data: {json.dumps({
                            'status': 'failed',
                            'error': f"Task timed out after {max_retries * 2} seconds",
                            'task_id': task_id,
                        })}\\n\\n"
                    
            except Exception as e:
                logger.error(f"Stream error for task {task_id}: {e}")
                yield f"data: {json.dumps({
                    'status': 'error',
                    'error': str(e),
                    'task_id': task_id,
                })}\\n\\n"
                
            finally:
                # Clean up task
                active_tasks.pop(task_id, None)
                logger.info(f"Cleaned up task {task_id}")
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable proxy buffering
            }
        )
        
    except Exception as e:
        logger.error(f"Error setting up stream for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    server_config = get_server_config()
    uvicorn.run(
        app,
        host=server_config.host,
        port=server_config.port,
        log_level=server_config.log_level,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    )
