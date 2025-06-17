"""
Health check routes for the FastAPI application
"""

from fastapi import APIRouter, Request, Depends
from datetime import datetime, timezone
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.dependencies import get_settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.get("/health", tags=["Health"])
@limiter.limit("100/minute")
async def health_check(request: Request, settings: dict = Depends(get_settings)):
    """
    Health check endpoint to verify API status and version
    """
    return {
        "name": "Pebble Crypto API",
        "status": "online",
        "version": "0.4.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "host": settings["host"],
            "port": settings["port"]
        }
    } 