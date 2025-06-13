"""
Enhanced Backend API server using official Codegen SDK
Provides comprehensive chat interface integration with real-time streaming
"""

import asyncio
import logging
import os
import json
import uuid
import time
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator, List
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
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

# Mock data for testing
MOCK_MODE = False
active_tasks = {}

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
    from codegen.agents.agent import Agent, AgentTask
    CODEGEN_AVAILABLE = True
except ImportError:
    CODEGEN_AVAILABLE = False
    print("Warning: Codegen SDK not available. Install with: pip install codegen")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define request and response models
class TaskRequest(BaseModel):
    prompt: str
    stream: bool = True
    thread_id: Optional[str] = None

class TaskResponse(BaseModel):
    status: str
    task_id: str
    result: Optional[str] = None
    web_url: Optional[str] = None
    thread_id: Optional[str] = None

class TaskStatusResponse(BaseModel):
    status: str
    task_id: str
    result: Optional[str] = None
    web_url: Optional[str] = None
    thread_id: Optional[str] = None
    created_at: Optional[str] = None

class CodegenConfig(BaseModel):
    org_id: str
    token: str
    base_url: Optional[str] = None

# Create FastAPI app
app = FastAPI(
    title="Codegen Chat API",
    description="API for interacting with Codegen AI agents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Define the get_codegen_config function
def get_codegen_config() -> CodegenConfig:
    """Get Codegen configuration from environment variables"""
    org_id = os.getenv("CODEGEN_ORG_ID")
    token = os.getenv("CODEGEN_TOKEN")
    base_url = os.getenv("CODEGEN_BASE_URL")
    
    if not org_id or not token:
        raise ValueError("Missing CODEGEN_ORG_ID or CODEGEN_TOKEN environment variables")
    
    return CodegenConfig(
        org_id=org_id,
        token=token,
        base_url=base_url
    )

# Enhanced Agent Client for better error handling and status tracking
class AgentClient:
    def __init__(self, org_id: str, token: str, base_url: Optional[str] = None):
        self.org_id = org_id
        self.token = token
        self.base_url = base_url
        
        # In mock mode, we don't need the actual SDK
        if not MOCK_MODE:
            try:
                from codegen.agents.agent import Agent, AgentTask
                
                # Initialize Agent with proper parameters
                kwargs = {"org_id": org_id, "token": token}
                if base_url:
                    kwargs["base_url"] = base_url
                    
                self.agent = Agent(**kwargs)
            except ImportError:
                raise ImportError("Codegen SDK not available. Install with: pip install codegen")
        
    async def process_message(self, message: str, stream: bool = True) -> Dict[str, Any]:
        """Process a message with proper error handling and status tracking"""
        try:
            logger.info(f"Starting process_message with stream={stream}")
            
            if MOCK_MODE:
                # Create a mock task ID
                task_id = f"mock-task-{uuid.uuid4()}"
                
                # Store task in active_tasks
                active_tasks[task_id] = {
                    "status": "initiated",
                    "message": message,
                    "created_at": datetime.now().isoformat(),
                    "web_url": f"https://codegen.com/tasks/{task_id}"
                }
                
                logger.info(f"Created mock task with ID: {task_id}")
                
                return {
                    "status": "initiated",
                    "task_id": task_id,
                    "task": None  # No actual task object in mock mode
                }
            
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

# Global agent client cache
agent_clients = {}

def get_or_create_agent_client(org_id: str, token: str, base_url: Optional[str] = None) -> AgentClient:
    """Get or create an agent client for the given credentials"""
    client_key = f"{org_id}:{token}:{base_url or 'default'}"
    
    if client_key not in agent_clients:
        agent_clients[client_key] = AgentClient(org_id, token, base_url)
    
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
        
        # In mock mode, simulate streaming updates
        if MOCK_MODE:
            # Simulate processing steps
            for step in steps:
                await asyncio.sleep(1)  # Simulate processing time
                
                yield json.dumps({
                    "status": "running",
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat(),
                    "thread_id": thread_id,
                    "current_step": step
                })
            
            # Simulate completion
            await asyncio.sleep(1)
            
            # Generate a mock response based on the message
            message = active_tasks.get(task_id, {}).get("message", "")
            if "list" in message.lower() and "file" in message.lower():
                result = "Here are the files in the current directory:\n\n```\nREADME.md\npackage.json\ntsconfig.json\napp.vue\npages/\ncomponents/\nassets/\npublic/\n```"
            elif "help" in message.lower():
                result = "I'm here to help! You can ask me questions about the codebase, request changes, or get assistance with any development tasks."
            else:
                result = f"I've processed your request: '{message}'\n\nIs there anything specific you'd like me to explain or help with?"
            
            # Update active_tasks
            active_tasks[task_id]["status"] = "completed"
            active_tasks[task_id]["result"] = result
            
            # Send completion event
            yield json.dumps({
                "status": "completed",
                "task_id": task_id,
                "timestamp": datetime.now().isoformat(),
                "thread_id": thread_id,
                "result": result,
                "web_url": f"https://codegen.com/tasks/{task_id}"
            })
            
            # Send done event
            yield "[DONE]"
            return
        
        # For real mode with SDK
        if not task:
            logger.warning(f"No task object provided for task_id: {task_id}")
            
            # Send a few updates to show progress
            for step in steps:
                await asyncio.sleep(1)
                
                yield json.dumps({
                    "status": "running",
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat(),
                    "thread_id": thread_id,
                    "current_step": step
                })
            
            # Send completion with error
            yield json.dumps({
                "status": "completed",
                "task_id": task_id,
                "timestamp": datetime.now().isoformat(),
                "thread_id": thread_id,
                "result": "Task completed, but no response was received from the agent. Please try again.",
                "error": "No task object available"
            })
            
            # Send done event
            yield "[DONE]"
            return
        
        # Real task processing with SDK
        max_retries = 60  # 5 minutes with 5-second intervals
        for i in range(max_retries):
            try:
                # Refresh task status
                task.refresh()
                
                # Get current status
                status = task.status.lower() if task.status else "unknown"
                logger.info(f"Task {task_id} status: {status} (attempt {i+1}/{max_retries})")
                
                # Send status update
                yield json.dumps({
                    "status": status,
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat(),
                    "thread_id": thread_id,
                    "current_step": steps[min(current_step_index, len(steps) - 1)]
                })
                
                # Update step index periodically
                if i > 0 and i % 5 == 0 and current_step_index < len(steps) - 1:
                    current_step_index += 1
                
                # Check if task is completed
                if status in ["completed", "complete"]:
                    # Extract result
                    result = None
                    web_url = None
                    
                    # Try to get result from task
                    if hasattr(task, 'result') and task.result:
                        if isinstance(task.result, str):
                            result = task.result
                        elif isinstance(task.result, dict):
                            result = task.result.get('content') or task.result.get('response') or str(task.result)
                    
                    # Try to get web URL
                    if hasattr(task, 'web_url') and task.web_url:
                        web_url = task.web_url
                    
                    # If no result, use default message
                    if not result:
                        result = "Task completed successfully."
                        if web_url:
                            result += f" View details at: {web_url}"
                    
                    # Update active_tasks
                    if task_id in active_tasks:
                        active_tasks[task_id]["status"] = "completed"
                        active_tasks[task_id]["result"] = result
                        active_tasks[task_id]["web_url"] = web_url
                    
                    # Send completion event
                    yield json.dumps({
                        "status": "completed",
                        "task_id": task_id,
                        "timestamp": datetime.now().isoformat(),
                        "thread_id": thread_id,
                        "result": result,
                        "web_url": web_url
                    })
                    
                    # Send done event
                    yield "[DONE]"
                    return
                
                # Check if task failed
                elif status in ["failed", "error"]:
                    # Get error message
                    error_message = "Task failed"
                    if hasattr(task, 'error') and task.error:
                        error_message = str(task.error)
                    
                    # Update active_tasks
                    if task_id in active_tasks:
                        active_tasks[task_id]["status"] = "failed"
                        active_tasks[task_id]["error"] = error_message
                    
                    # Send failure event
                    yield json.dumps({
                        "status": "failed",
                        "task_id": task_id,
                        "timestamp": datetime.now().isoformat(),
                        "thread_id": thread_id,
                        "error": error_message
                    })
                    
                    # Send done event
                    yield "[DONE]"
                    return
                
                # Wait before next check
                await asyncio.sleep(5)
            
            except Exception as e:
                logger.error(f"Error refreshing task {task_id}: {e}", exc_info=True)
                
                # Send error update but continue trying
                yield json.dumps({
                    "status": "running",
                    "task_id": task_id,
                    "timestamp": datetime.now().isoformat(),
                    "thread_id": thread_id,
                    "current_step": f"Retrying after error: {str(e)[:50]}..."
                })
                
                await asyncio.sleep(5)
        
        # If we get here, task timed out
        logger.warning(f"Task {task_id} timed out after {max_retries} attempts")
        
        # Update active_tasks
        if task_id in active_tasks:
            active_tasks[task_id]["status"] = "timeout"
            active_tasks[task_id]["error"] = "Task timed out"
        
        # Send timeout event
        yield json.dumps({
            "status": "timeout",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "thread_id": thread_id,
            "error": "Task timed out after 5 minutes"
        })
        
        # Send done event
        yield "[DONE]"
    
    except Exception as e:
        logger.error(f"Error in stream_task_updates_enhanced: {e}", exc_info=True)
        
        # Send error event
        yield json.dumps({
            "status": "error",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "thread_id": thread_id,
            "error": str(e)
        })
        
        # Send done event
        yield "[DONE]"

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load configuration and initialize resources
    logger.info("Starting up API server...")
    
    # Yield control to the application
    yield
    
    # Shutdown: Clean up resources
    logger.info("Shutting down API server...")
    
    # Clean up active tasks
    active_tasks.clear()
    
    # Clean up agent clients
    agent_clients.clear()

# Apply lifespan context manager
app.router.lifespan_context = lifespan

# Helper function to get Codegen configuration
def get_codegen_config() -> CodegenConfig:
    """Get Codegen configuration from environment variables"""
    org_id = os.getenv("CODEGEN_ORG_ID")
    token = os.getenv("CODEGEN_TOKEN")
    base_url = os.getenv("CODEGEN_BASE_URL")
    
    if not org_id or not token:
        raise ValueError("Missing CODEGEN_ORG_ID or CODEGEN_TOKEN environment variables")
    
    return CodegenConfig(
        org_id=org_id,
        token=token,
        base_url=base_url
    )

# Try to load default config
try:
    default_codegen_config = get_codegen_config()
    logger.info(f"Loaded default config with org_id: {default_codegen_config.org_id}")
except Exception as e:
    logger.warning(f"Could not load default config: {e}")
    default_codegen_config = None

@app.post("/api/v1/run-task")
async def run_task(
    request: Request,
    task_request: TaskRequest,
    background_tasks: BackgroundTasks,
    x_organization_id: Optional[str] = Header(None),
    x_token: Optional[str] = Header(None),
    x_base_url: Optional[str] = Header(None)
):
    """Run a task with the Codegen API"""
    try:
        # Use provided credentials or fallback to environment variables
        org_id_to_use = x_organization_id or os.getenv("CODEGEN_ORG_ID")
        token_to_use = x_token or os.getenv("CODEGEN_TOKEN")
        base_url = x_base_url or os.getenv("CODEGEN_BASE_URL")
        
        if not org_id_to_use or not token_to_use:
            raise HTTPException(
                status_code=400,
                detail="Missing organization ID or token"
            )
        
        # In mock mode, create a mock task
        if MOCK_MODE:
            # Create a mock task ID
            task_id = f"mock-task-{uuid.uuid4()}"
            
            # Store task in active_tasks
            active_tasks[task_id] = {
                "status": "running",
                "message": task_request.prompt,
                "created_at": datetime.now().isoformat(),
                "thread_id": task_request.thread_id,
                "web_url": f"https://codegen.com/tasks/{task_id}"
            }
            
            logger.info(f"Created mock task with ID: {task_id}")
            
            # For streaming, return task ID immediately
            if task_request.stream:
                return {
                    "status": "initiated",
                    "task_id": task_id,
                    "message": "Task started successfully"
                }
            
            # For non-streaming, simulate a delay and return a result
            await asyncio.sleep(2)
            
            # Generate a mock response based on the message
            if "list" in task_request.prompt.lower() and "file" in task_request.prompt.lower():
                result = "Here are the files in the current directory:\n\n```\nREADME.md\npackage.json\ntsconfig.json\napp.vue\npages/\ncomponents/\nassets/\npublic/\n```"
            elif "help" in task_request.prompt.lower():
                result = "I'm here to help! You can ask me questions about the codebase, request changes, or get assistance with any development tasks."
            else:
                result = f"I've processed your request: '{task_request.prompt}'\n\nIs there anything specific you'd like me to explain or help with?"
            
            # Update active_tasks
            active_tasks[task_id]["status"] = "completed"
            active_tasks[task_id]["result"] = result
            
            return {
                "status": "completed",
                "task_id": task_id,
                "result": result,
                "web_url": f"https://codegen.com/tasks/{task_id}"
            }
        
        # Get or create agent client
        client = get_or_create_agent_client(org_id_to_use, token_to_use, base_url)
        
        # Process the message
        result = await client.process_message(
            message=task_request.prompt,
            stream=task_request.stream
        )
        
        # Check for errors
        if result.get("status") == "error":
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Unknown error")
            )
        
        # Get task ID
        task_id = result.get("task_id")
        if not task_id:
            raise HTTPException(
                status_code=500,
                detail="No task ID returned from agent"
            )
        
        # Store task in active_tasks
        active_tasks[task_id] = {
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "thread_id": task_request.thread_id,
            "web_url": None
        }
        
        # For streaming, return task ID immediately
        if task_request.stream:
            return {
                "status": "initiated",
                "task_id": task_id,
                "message": "Task started successfully"
            }
        
        # For non-streaming, wait for completion
        # This is handled in process_message for non-streaming requests
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running task: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/api/v1/task/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get the status of a task"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task_info = active_tasks[task_id]
    
    # In mock mode, simulate task completion after a delay
    if MOCK_MODE and task_info.get("status") == "running":
        # Check if task has been running for more than 5 seconds
        created_at = datetime.fromisoformat(task_info.get("created_at")) if isinstance(task_info.get("created_at"), str) else task_info.get("created_at")
        if created_at and (datetime.now() - created_at).total_seconds() > 5:
            # Generate a mock response based on the message
            message = task_info.get("message", "")
            if "list" in message.lower() and "file" in message.lower():
                result = "Here are the files in the current directory:\n\n```\nREADME.md\npackage.json\ntsconfig.json\napp.vue\npages/\ncomponents/\nassets/\npublic/\n```"
            elif "help" in message.lower():
                result = "I'm here to help! You can ask me questions about the codebase, request changes, or get assistance with any development tasks."
            else:
                result = f"I've processed your request: '{message}'\n\nIs there anything specific you'd like me to explain or help with?"
            
            # Update task info
            task_info["status"] = "completed"
            task_info["result"] = result
    
    return TaskStatusResponse(
        status=task_info.get("status", "unknown"),
        task_id=task_id,
        result=task_info.get("result"),
        web_url=task_info.get("web_url"),
        thread_id=task_info.get("thread_id"),
        created_at=task_info.get("created_at")
    )

@app.get("/api/v1/tasks")
async def list_tasks():
    """List all active tasks"""
    return {
        "tasks": [
            {
                "task_id": task_id,
                "status": info.get("status", "unknown"),
                "created_at": info.get("created_at"),
                "thread_id": info.get("thread_id")
            }
            for task_id, info in active_tasks.items()
        ]
    }

@app.get("/api/v1/task/{task_id}/stream")
async def stream_task(
    task_id: str,
    request: Request
):
    """Stream task updates"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task_info = active_tasks[task_id]
    task = task_info.get("task")
    thread_id = task_info.get("thread_id")
    
    # Use enhanced streaming function
    return StreamingResponse(
        stream_task_updates_enhanced(task, task_id, thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/v1/test-connection")
async def test_connection(
    request: Request,
    x_organization_id: Optional[str] = Header(None),
    x_token: Optional[str] = Header(None),
    x_base_url: Optional[str] = Header(None)
):
    """Test connection to the Codegen API"""
    try:
        # Use provided credentials or fallback to environment variables
        org_id_to_use = x_organization_id or os.getenv("CODEGEN_ORG_ID")
        token_to_use = x_token or os.getenv("CODEGEN_TOKEN")
        base_url = x_base_url or os.getenv("CODEGEN_BASE_URL")
        
        if not org_id_to_use or not token_to_use:
            return JSONResponse(
                status_code=400,
                content={"detail": "Missing organization ID or token"}
            )
        
        if MOCK_MODE:
            # In mock mode, just return success
            return {
                "status": "success",
                "message": "Connection successful (MOCK MODE)",
                "org_id": org_id_to_use,
                "base_url": base_url or "default"
            }
            
        # Create agent client to test connection
        client = get_or_create_agent_client(org_id_to_use, token_to_use, base_url)
        
        # If we get here, connection was successful
        return {
            "status": "success",
            "message": "Connection successful",
            "org_id": org_id_to_use,
            "base_url": base_url or "default"
        }
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)}
        )

@app.get("/api/v1/config")
async def get_config():
    """Get current configuration"""
    try:
        config = get_codegen_config()
        return {
            "org_id": config.org_id,
            "base_url": config.base_url or "default",
            "token_prefix": config.token[:5] + "..." if config.token else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Codegen Chat API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

# Run the server if executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host=os.getenv("SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("SERVER_PORT", 8002)),
        reload=True
    )
