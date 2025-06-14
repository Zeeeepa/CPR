"""
Main entry point for the backend API server
"""

import os
import sys
import uvicorn

# Add the parent directory to sys.path to allow importing backend as a module
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Now we can import from backend
from backend.api import app

if __name__ == "__main__":
    uvicorn.run(
        "backend.api:app",
        host=os.getenv("SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("SERVER_PORT", 8002)),
        reload=True
    )

