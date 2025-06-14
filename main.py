"""
Main entry point for the backend API server
This file should be run from the project root directory
"""

import os
import sys
import uvicorn

# Add the current directory to sys.path to allow importing backend as a module
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    # Import the app from backend.api
    from backend.api import app
    
    uvicorn.run(
        "backend.api:app",
        host=os.getenv("SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("SERVER_PORT", 8002)),
        reload=True
    )

