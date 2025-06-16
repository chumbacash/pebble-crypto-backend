"""
FastAPI application entry point for deployment.
This module imports the main FastAPI app and configures it for cloud deployment.
"""

import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the FastAPI app from root main.py
import sys
sys.path.append('..')
from main import app

# Export the app for ASGI servers
__all__ = ["app"]

# Configure for deployment
if __name__ == "__main__":
    # Get port from environment variable (required for Render, Railway, etc.)
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    # Run the server
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,  # Disable reload in production
        workers=1,     # Single worker for basic deployment
    ) 