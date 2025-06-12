"""
Enhanced Backend API server using official Codegen SDK
Provides comprehensive chat interface integration with real-time streaming
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

# Store active tasks
active_tasks: Dict[str, Any] = {}

class AgentCallback:
    def __init__(self, task_id: str, thread_id: Optional[str] = None):
        self.task_id = task_id
        self.thread_id = thread_id
        self.queue = asyncio.Queue()
        self.completed = False
        self.error = None
        self.current_step = 0
        self.total_steps = 0

    async def on_status_change(self, status: str, result: Optional[str] = None, error: Optional[str] = None, step_info: Optional[dict] = None):
        """Handle status change events"""
        event_data = {
            "status": status,
            "task_id": self.task_id,
            "timestamp": datetime.now().isoformat()
        }
        
        if self.thread_id:
            event_data["thread_id"] = self.thread_id
            
        if result:
            event_data["result"] = result
        if error:
            event_data["error"] = error
            
        # Include step information if available
        if step_info:
            event_data.update(step_info)
            
        # Format as proper SSE event
        event_str = f"data: {json.dumps(event_data)}\n\n"
        await self.queue.put(event_str)
        
        if status in ["completed", "failed"]:
            self.completed = True
            if error:
                self.error = error
            # Send completion event
            await self.queue.put("data: [DONE]\n\n")

    async def get_events(self):
        """Get events from the queue"""
        try:
            while not self.completed or not self.queue.empty():
                try:
                    # Use timeout to prevent infinite waiting
                    event = await asyncio.wait_for(self.queue.get(), timeout=5.0)
                    yield event
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
                except Exception as e:
                    logger.error(f"Error getting events: {e}")
                    yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
                    yield "data: [DONE]\n\n"
                    break
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

async def monitor_task(task, callback: AgentCallback):
    """Monitor task status and trigger callbacks"""
    try:
        logger.info(f"Starting to monitor task {callback.task_id}")
        max_retries = 900  # 30 minutes with 2-second intervals
        retry_count = 0
        last_step = None
        
        while not callback.completed and retry_count < max_retries:
            task.refresh()
            status = task.status.lower() if task.status else "unknown"
            logger.info(f"Task {callback.task_id} status: {status}")
            
            # Extract step information from task
            current_step = None
            try:
                # Try to get step information from task.result or task.summary
                if hasattr(task, 'result') and isinstance(task.result, dict):
                    current_step = task.result.get('current_step')
                elif hasattr(task, 'summary') and isinstance(task.summary, dict):
                    current_step = task.summary.get('current_step')
            except Exception as e:
                logger.warning(f"Could not extract step info: {e}")
            
            # Only send update if step has changed
            if current_step and current_step != last_step:
                step_info = {
                    'current_step': current_step,
                    'step_number': callback.current_step + 1
                }
                await callback.on_status_change(status, step_info=step_info)
                last_step = current_step
                callback.current_step += 1
            
            if status == "completed":
                result = (
                    getattr(task, 'result', None) or 
                    getattr(task, 'summary', None) or 
                    getattr(task, 'output', None) or 
                    "Task completed successfully."
                )
                logger.info(f"Task {callback.task_id} completed with result")
                await callback.on_status_change("completed", result=result)
                break
            elif status == "failed":
                error = getattr(task, 'error', None) or getattr(task, 'failure_reason', None) or 'Task failed'
                logger.error(f"Task {callback.task_id} failed: {error}")
                await callback.on_status_change("failed", error=error)
                break
            elif status != "unknown":
                logger.info(f"Task {callback.task_id} status update: {status}")
                await callback.on_status_change(status)
            
            await asyncio.sleep(2)  # Poll every 2 seconds
            retry_count += 1
            
        if retry_count >= max_retries:
            logger.error(f"Task {callback.task_id} timed out after {max_retries * 2} seconds")
            await callback.on_status_change("failed", error="Task timed out")
            
    except Exception as e:
        logger.error(f"Error monitoring task {callback.task_id}: {e}")
        await callback.on_status_change("error", error=str(e))
    finally:
        # Clean up
        active_tasks.pop(callback.task_id, None)
        logger.info(f"Cleaned up task {callback.task_id}")

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
        
        if not CODEGEN_AVAILABLE:
            raise HTTPException(status_code=500, detail="Codegen SDK not available")
        
        logger.info(f"Running task for org_id: {org_id}, prompt: {request.prompt}")
        
        # Initialize agent
        kwargs = {"org_id": org_id, "token": token}
        if base_url:
            kwargs["base_url"] = base_url
        
        agent = Agent(**kwargs)
        logger.info("Agent initialized successfully")
        
        # Run the task
        task = agent.run(prompt=request.prompt)
        task_id = str(task.id) if task.id else f"task_{datetime.now().timestamp()}"
        logger.info(f"Created task with ID: {task_id}")
        
        # Create callback handler
        callback = AgentCallback(task_id, request.thread_id)
        
        # Store task
        active_tasks[task_id] = {
            "task": task,
            "callback": callback,
            "created_at": datetime.now()
        }
        logger.info(f"Stored task {task_id} in active_tasks")
        
        # Start monitoring in background
        background_tasks.add_task(monitor_task, task, callback)
        logger.info(f"Started monitoring task {task_id} in background")
        
        # Return streaming response
        logger.info(f"Returning streaming response for task {task_id}")
        return StreamingResponse(
            callback.get_events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
            
    except Exception as e:
        logger.error(f"Error running task: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "codegen_available": CODEGEN_AVAILABLE,
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
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
