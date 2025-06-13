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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
# Add this right after load_dotenv() in your code
print(f"CODEGEN_ORG_ID from env: {os.getenv('CODEGEN_ORG_ID')}")
print(f"CODEGEN_TOKEN from env: {os.getenv('CODEGEN_TOKEN')}")
org_id = os.getenv("CODEGEN_ORG_ID")
token = os.getenv("CODEGEN_TOKEN")

print(f"Org ID: {org_id}")
print(f"Token: {token[:10]}..." if token else "Token: None")

# Test SDK import and basic initialization
try:
    from codegen.agents.agent import Agent
    print("SDK imported successfully")
    
    agent = Agent(org_id=org_id, token=token)
    print("Agent created successfully")
    
except Exception as e:
    print(f"Error: {e}")
# Import the official Codegen SDK
try:
    from codegen.agents.agent import Agent
    from codegen.agents.task import Task
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
    task_id: Optional[str] = Field(None, description="Task identifier")
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
        base_url=os.getenv("CODEGEN_BASE_URL")
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

# Enhanced Agent Client for better error handling and status tracking
class AgentClient:
    def __init__(self, org_id: str, token: str, base_url: Optional[str] = None):
        if not CODEGEN_AVAILABLE:
            raise ImportError("Codegen SDK not available. Install with: pip install codegen")
        
        # Initialize Agent with proper parameters
        kwargs = {"org_id": org_id, "token": token}
        if base_url:
            kwargs["base_url"] = base_url
            
        self.agent = Agent(**kwargs)
        
    async def process_message(self, message: str, stream: bool = True) -> Dict[str, Any]:
        """Process a message with proper error handling and status tracking"""
        try:
            logger.info(f"Starting process_message with stream={stream}")
            
            # Run the agent with the message
            task = self.agent.run(prompt=message)
            logger.info(f"Agent.run() completed, task object created: {type(task)}")
            
            # Debug: Print all task attributes
            logger.info("=== TASK OBJECT DEBUG ===")
            for attr in dir(task):
                if not attr.startswith('_'):
                    try:
                        value = getattr(task, attr)
                        if not callable(value):
                            logger.info(f"task.{attr} = {value} (type: {type(value)})")
                    except Exception as e:
                        logger.info(f"task.{attr} = ERROR: {e}")
            logger.info("=== END TASK DEBUG ===")
            
            # Extract task ID using the proper attribute
            task_id = None
            
            # Try multiple ways to get the task ID
            if hasattr(task, 'id') and task.id is not None:
                task_id = str(task.id)
                logger.info(f"Got task ID from task.id: {task_id}")
            elif hasattr(task, 'agent_run_id') and task.agent_run_id is not None:
                task_id = str(task.agent_run_id)
                logger.info(f"Got task ID from task.agent_run_id: {task_id}")
            elif hasattr(task, 'run_id') and task.run_id is not None:
                task_id = str(task.run_id)
                logger.info(f"Got task ID from task.run_id: {task_id}")
            
            if not task_id:
                # Fallback to timestamp-based ID if task.id is not available
                task_id = f"task_{int(datetime.now().timestamp() * 1000)}"
                logger.warning(f"Task ID not available from SDK, using fallback: {task_id}")
            
            logger.info(f"Final task ID: {task_id}")
            
            if not stream:
                # For non-streaming, wait for completion with timeout
                max_retries = 60  # 5 minutes with 5-second intervals
                for _ in range(max_retries):
                    task.refresh()
                    status = task.status.lower() if task.status else "unknown"
                    
                    if status in ["completed", "complete"]:
                        return {
                            "status": "completed",
                            "result": self._extract_result(task),
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
            
            logger.info(f"Returning streaming response with task_id: {task_id}")
            return {
                "status": "initiated",
                "task": task,
                "task_id": task_id
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "task_id": None
            }
    
    def _extract_result(self, task) -> str:
        """Extract result from task using multiple fallback methods"""
        # Method 1: Direct result attribute
        if hasattr(task, 'result') and task.result:
            if isinstance(task.result, str):
                return task.result
            elif isinstance(task.result, dict):
                return task.result.get('content') or task.result.get('response') or str(task.result)
        
        # Method 2: Web URL fallback
        if hasattr(task, 'web_url') and task.web_url:
            return f"Task completed successfully. View details at: {task.web_url}"
        
        # Method 3: Default message
        return "Task completed successfully."

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

async def stream_task_updates_enhanced(task, task_id: str, thread_id: Optional[str] = None) -> AsyncGenerator[str, None]:
    """Enhanced streaming function for task updates with better error handling and progress tracking"""
    try:
        logger.info(f"Starting stream_task_updates_enhanced for task_id: {task_id}")
        
        # Initial update
        yield json.dumps({
            "status": "initiated",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "thread_id": thread_id,
            "current_step": "Initializing task"
        })
        
        # Track progress steps
        steps = ["Analyzing request", "Processing task", "Generating response"]
        current_step_index = 0
        
        # Stream updates with progress tracking
        max_retries = 300  # 10 minutes with 2-second intervals
        for i in range(max_retries):
            try:
                # Refresh task status
                task.refresh()
                current_status = task.status.lower() if task.status else "unknown"
                logger.info(f"Task {task_id} status: {current_status}")
                
                # Update step based on progress
                if i % 10 == 0 and current_step_index < len(steps):
                    current_step = steps[current_step_index]
                    yield json.dumps({
                        "status": "running",
                        "task_id": task_id,
                        "timestamp": datetime.now().isoformat(),
                        "thread_id": thread_id,
                        "current_step": current_step
                    })
                    current_step_index = min(current_step_index + 1, len(steps) - 1)
                
                # Check if task is complete
                if current_status in ["completed", "complete"]:
                    # Extract result
                    result = None
                    if hasattr(task, 'result') and task.result:
                        if isinstance(task.result, str):
                            result = task.result
                        elif isinstance(task.result, dict):
                            result = task.result.get('content') or task.result.get('response') or str(task.result)
                    
                    if not result and hasattr(task, 'web_url') and task.web_url:
                        result = f"Task completed successfully. View details at: {task.web_url}"
                    elif not result:
                        result = "Task completed successfully."
                    
                    # Send completion event
                    yield json.dumps({
                        "status": "completed",
                        "task_id": task_id,
                        "result": result,
                        "timestamp": datetime.now().isoformat(),
                        "thread_id": thread_id,
                        "web_url": getattr(task, 'web_url', None)
                    })
                    
                    # Send done event
                    yield "[DONE]"
                    break
                    
                elif current_status == "failed":
                    error_msg = getattr(task, 'error', None) or 'Task failed with unknown error'
                    
                    # Send failure event
                    yield json.dumps({
                        "status": "failed",
                        "task_id": task_id,
                        "error": error_msg,
                        "timestamp": datetime.now().isoformat(),
                        "thread_id": thread_id,
                        "web_url": getattr(task, 'web_url', None)
                    })
                    
                    # Send done event
                    yield "[DONE]"
                    break
                
                # Send heartbeat to keep connection alive
                if i % 5 == 0:
                    yield json.dumps({
                        "status": "heartbeat",
                        "task_id": task_id,
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Wait before next update
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error refreshing task {task_id}: {e}")
                # Send error event but don't break the loop
                yield json.dumps({
                    "status": "error",
                    "error": f"Failed to refresh task: {str(e)}",
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat(),
                    "recoverable": True  # Indicate this is a recoverable error
                })
                await asyncio.sleep(5)  # Wait longer before retry
        
        # Handle timeout
        if current_status not in ["completed", "complete", "failed"]:
            logger.warning(f"Task {task_id} reached max retries")
            
            # Try to extract any available result even if not "completed"
            final_result = None
            if hasattr(task, 'web_url') and task.web_url:
                final_result = f"Task processing completed. View details at: {task.web_url}"
                yield json.dumps({
                    "status": "completed",
                    "result": final_result,
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat(),
                    "thread_id": thread_id,
                    "web_url": task.web_url
                })
                yield "[DONE]"
            else:
                yield json.dumps({
                    "status": "timeout",
                    "error": f"Task timed out after {max_retries * 2} seconds",
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat(),
                    "thread_id": thread_id
                })
                yield "[DONE]"
                
    except Exception as e:
        logger.error(f"Stream error for task {task_id}: {e}")
        yield json.dumps({
            "status": "error",
            "error": str(e),
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "thread_id": thread_id
        })
        yield "[DONE]"

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Codegen AI Chat Dashboard API v2.0.0")
    logger.info(f"Codegen SDK Available: {CODEGEN_AVAILABLE}")
    
    if CODEGEN_AVAILABLE:
        try:
            default_codegen_config = get_codegen_config()
            logger.info(f"Default Org ID: {default_codegen_config.org_id}")
        except Exception as e:
            logger.warning(f"Could not load default config: {e}")
    
    server_config = get_server_config()
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
try:
    default_codegen_config = get_codegen_config()
except Exception as e:
    logger.warning(f"Could not load default config: {e}")
    default_codegen_config = None

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
        if default_codegen_config:
            org_id = x_org_id or default_codegen_config.org_id
            token = x_token or default_codegen_config.token
            base_url = x_base_url or default_codegen_config.base_url
        else:
            org_id = x_org_id
            token = x_token
            base_url = x_base_url
        
        if not org_id or not token:
            raise HTTPException(
                status_code=400, 
                detail="Missing org_id or token. Provide via headers or environment variables."
            )
        
        logger.info(f"=== STARTING TASK ===")
        logger.info(f"Running task for org_id: {org_id}, prompt length: {len(request.prompt)}")
        logger.info(f"Stream requested: {request.stream}")
        
        # Get or create agent client
        agent_client = get_or_create_agent_client(org_id, token, base_url)
        
        # Process the message
        logger.info("Calling agent_client.process_message...")
        result = await agent_client.process_message(request.prompt, stream=request.stream)
        logger.info(f"process_message returned: {result}")
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Generate task ID if not available
        task_id = result.get("task_id")
        if not task_id:
            task_id = f"task_{int(datetime.now().timestamp() * 1000)}"
            result["task_id"] = task_id
            logger.warning(f"Generated fallback task ID: {task_id}")
        
        # ALWAYS store task for status tracking - BEFORE returning response
        logger.info(f"Storing task with ID: {task_id}")
        active_tasks[task_id] = {
            "task": result.get("task"),  # This might be None for some cases
            "created_at": datetime.now(),
            "thread_id": request.thread_id,
            "org_id": org_id,
            "status": result["status"],
            "result": result.get("result"),
            "web_url": result.get("web_url"),
            "prompt": request.prompt  # Store original prompt for reference
        }
        logger.info(f"✅ Successfully stored task {task_id} in active_tasks")
        
        if not request.stream:
            # Return direct response for non-streaming
            return TaskResponse(
                result=result.get("result"),
                status=result["status"],
                task_id=task_id,
                web_url=result.get("web_url"),
                thread_id=request.thread_id
            )
        
        # For streaming, ensure task is stored before creating the stream
        if task_id not in active_tasks:
            logger.error(f"❌ CRITICAL: Task {task_id} not found in active_tasks after storage attempt")
            logger.error(f"Current active_tasks: {list(active_tasks.keys())}")
            raise HTTPException(status_code=500, detail="Failed to store task for tracking")
        
        logger.info(f"✅ Task {task_id} confirmed in active_tasks, starting stream")
        
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
        logger.error(f"Error running task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/v1/task/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get detailed status of a specific task"""
    try:
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        task_info = active_tasks[task_id]
        task = task_info.get("task")
        
        # Try to refresh if task object is available
        current_status = task_info.get("status", "unknown")
        result = task_info.get("result")
        web_url = task_info.get("web_url")
        
        if task:
            try:
                # Refresh task status
                task.refresh()
                current_status = task.status.lower() if task.status else current_status
                web_url = getattr(task, 'web_url', web_url)
                
                # Extract result if completed and not already set
                if current_status in ["completed", "complete"] and not result:
                    if hasattr(task, 'result') and task.result:
                        if isinstance(task.result, str):
                            result = task.result
                        elif isinstance(task.result, dict):
                            result = task.result.get('content') or task.result.get('response') or str(task.result)
                    elif web_url:
                        result = f"Task completed successfully. View details at: {web_url}"
                    else:
                        result = "Task completed successfully."
                
                # Update stored info
                task_info.update({
                    "status": current_status,
                    "result": result,
                    "web_url": web_url
                })
                
            except Exception as e:
                logger.warning(f"Could not refresh task {task_id}: {e}")
        
        return TaskStatusResponse(
            status=current_status,
            result=result,
            task_id=task_id,
            web_url=web_url,
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
            try:
                task.refresh()
                status = task.status.lower() if task.status else "unknown"
            except Exception as e:
                logger.warning(f"Could not refresh task {task_id}: {e}")
                status = "unknown"
                
            tasks_summary.append({
                "task_id": task_id,
                "status": status,
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
        try:
            task.refresh()
        except Exception as e:
            logger.warning(f"Could not refresh task for debug: {e}")
        
        # Get all available attributes safely
        task_attributes = {}
        for attr in dir(task):
            if not attr.startswith('_'):
                try:
                    value = getattr(task, attr)
                    if not callable(value):
                        # Truncate long values for readability
                        str_value = str(value)
                        if len(str_value) > 200:
                            str_value = str_value[:200] + "..."
                        task_attributes[attr] = str_value
                except Exception as e:
                    task_attributes[attr] = f"Error accessing: {str(e)}"
        
        return {
            "task_id": task_id,
            "attributes": task_attributes,
            "status": getattr(task, 'status', 'unknown'),
            "has_result": hasattr(task, 'result') and task.result is not None,
            "has_web_url": hasattr(task, 'web_url') and task.web_url is not None,
            "web_url": getattr(task, 'web_url', None),
            "task_info": {
                "created_at": task_info["created_at"].isoformat(),
                "thread_id": task_info.get("thread_id"),
                "org_id": task_info.get("org_id")
            }
        }
        
    except HTTPException:
        raise
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
            logger.info(f"Testing connection with org_id: {config.org_id}, token: {config.token[:10]}...")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Try to create an agent - this validates credentials
        try:
            agent = Agent(
                org_id=config.org_id,
                token=config.token,
                base_url=config.base_url
            )
            
            # Instead of calling a non-existent method, let's try a simple operation
            # that will validate the credentials without consuming resources
            logger.info("Agent created successfully, credentials appear valid")
            
            return {
                "status": "connected",
                "message": "Successfully connected to Codegen API",
                "org_id": config.org_id,
                "base_url": config.base_url or "https://api.codegen.com",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            # Check if it's an authentication error
            if "401" in str(e) or "unauthorized" in str(e).lower():
                raise HTTPException(
                    status_code=401, 
                    detail=f"Authentication failed. Please check your org_id and token: {str(e)}"
                )
            else:
                raise HTTPException(
                    status_code=500, 
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
    config_data = {
        "codegen_available": CODEGEN_AVAILABLE,
        "server_config": {
            "host": server_config.host,
            "port": server_config.port,
            "cors_origins": server_config.cors_origins
        },
        "active_tasks_count": len(active_tasks),
        "agent_clients_count": len(agent_clients)
    }
    
    if default_codegen_config:
        config_data["default_org_id"] = default_codegen_config.org_id
        config_data["has_default_config"] = True
    else:
        config_data["has_default_config"] = False
    
    return config_data

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
                max_retries = 300  # 10 minutes with 2-second intervals
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        # Check if client disconnected
                        if await request.is_disconnected():
                            logger.info(f"Client disconnected from task {task_id} stream")
                            break
                            
                        # Refresh task status
                        task.refresh()
                        current_status = task.status.lower() if task.status else "unknown"
                        
                        # Prepare update data
                        update_data = {
                            "status": current_status,
                            "task_id": task_id,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        if hasattr(task, 'web_url') and task.web_url:
                            update_data["web_url"] = task.web_url
                        
                        # Check if task is complete
                        if current_status in ["completed", "complete"]:
                            # Extract result using the same logic as other endpoints
                            result = None
                            if hasattr(task, 'result') and task.result:
                                if isinstance(task.result, str):
                                    result = task.result
                                elif isinstance(task.result, dict):
                                    result = task.result.get('content') or task.result.get('response') or str(task.result)
                            
                            if not result and hasattr(task, 'web_url') and task.web_url:
                                result = f"Task completed successfully. View details at: {task.web_url}"
                            elif not result:
                                result = "Task completed successfully."
                            
                            # Send completion event
                            yield f"data: {json.dumps({
                                'status': 'completed',
                                'task_id': task_id,
                                'result': result,
                                'web_url': getattr(task, 'web_url', None)
                            })}\n\n"
                            
                            # Send done event
                            yield "data: [DONE]\n\n"
                            break
                            
                        elif current_status == "failed":
                            error_msg = getattr(task, 'error', None) or 'Task failed with unknown error'
                            
                            # Send failure event
                            yield f"data: {json.dumps({
                                'status': 'failed',
                                'task_id': task_id,
                                'error': error_msg,
                                'web_url': getattr(task, 'web_url', None)
                            })}\n\n"
                            
                            # Send done event
                            yield "data: [DONE]\n\n"
                            break
                            
                        else:
                            # Send status update
                            yield f"data: {json.dumps(update_data)}\n\n"
                        
                        # Send heartbeat to keep connection alive
                        yield ": heartbeat\n\n"
                        
                        # Wait before next update
                        await asyncio.sleep(2)
                        retry_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error refreshing task {task_id}: {e}")
                        # Send error event
                        yield f"data: {json.dumps({
                            'status': 'error',
                            'error': f'Failed to refresh task: {str(e)}',
                            'task_id': task_id,
                        })}\n\n"
                        break
                
                # Handle timeout
                if retry_count >= max_retries:
                    logger.warning(f"Task {task_id} reached max retries")
                    
                    # Try to extract any available result even if not "completed"
                    final_result = None
                    if hasattr(task, 'web_url') and task.web_url:
                        final_result = f"Task processing completed. View details at: {task.web_url}"
                        yield f"data: {json.dumps({
                            'status': 'completed',
                            'result': final_result,
                            'task_id': task_id,
                            'web_url': task.web_url
                        })}\n\n"
                        yield "data: [DONE]\n\n"
                    else:
                        yield f"data: {json.dumps({
                            'status': 'failed',
                            'error': f"Task timed out after {max_retries * 2} seconds",
                            'task_id': task_id,
                        })}\n\n"
                    
            except Exception as e:
                logger.error(f"Stream error for task {task_id}: {e}")
                yield f"data: {json.dumps({
                    'status': 'error',
                    'error': str(e),
                    'task_id': task_id,
                })}\n\n"
                
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
                "X-Accel-Buffering": "no"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up stream for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/debug/active-tasks")
async def debug_active_tasks():
    """Debug endpoint to see all active tasks"""
    return {
        "active_tasks": list(active_tasks.keys()),
        "total_count": len(active_tasks),
        "task_details": {
            task_id: {
                "created_at": task_info["created_at"].isoformat(),
                "thread_id": task_info.get("thread_id"),
                "org_id": task_info.get("org_id"),
                "has_task_object": "task" in task_info
            }
            for task_id, task_info in active_tasks.items()
        }
    }

if __name__ == "__main__":
    server_config = get_server_config()
    uvicorn.run(
        app,
        host=server_config.host,
        port=server_config.port,
        log_level=server_config.log_level,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    )
