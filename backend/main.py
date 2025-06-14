"""
Main entry point for the backend API server
"""

import os
import uvicorn
from backend.api import app

if __name__ == "__main__":
    uvicorn.run(
        "backend.api:app",
        host=os.getenv("SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("SERVER_PORT", 8002)),
        reload=True
    )

