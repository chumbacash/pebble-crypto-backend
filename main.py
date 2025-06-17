"""
Pebble Crypto Analytics API - Production Entry Point
Root application entry point that imports the modular FastAPI app
"""

import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the modular FastAPI app
from app.main import app

# Export the app for ASGI servers
__all__ = ["app"]

# Configure for development and production
if __name__ == "__main__":
    # Get configuration from environment variables
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    reload = os.getenv("RELOAD", "true").lower() == "true"
    workers = int(os.getenv("WORKERS", 1))
    
    print(f"🚀 Starting Pebble Crypto Analytics API on {host}:{port}")
    print(f"🔧 Configuration: reload={reload}, workers={workers}")
    print(f"📚 API Documentation: http://{host}:{port}/docs")
    print(f"🔍 Alternative docs: http://{host}:{port}/redoc")
    
    # Run the server
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level="info"
    )