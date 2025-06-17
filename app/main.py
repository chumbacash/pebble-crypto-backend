"""
Pebble Crypto Analytics API - Modular FastAPI Application
Main application entry point using APIRouter for bigger applications architecture
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import logging

# Import route modules
from app.api.routes import health, market_data, predictions, ai_agent, websockets, multi_exchange, market_advisor
from app.core.dependencies import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("CryptoPredictAPI")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    # Get settings
    settings = get_settings()
    
    # Create FastAPI app with metadata
    app = FastAPI(
        title="Pebble Crypto Analytics API",
        description="""
        Advanced cryptocurrency analytics API powered by AI and multi-exchange data aggregation.
        
        ## Features
        
        * **Multi-Exchange Integration**: 6+ cryptocurrency exchanges
        * **AI-Powered Analysis**: Natural language queries with intelligent responses
        * **Technical Analysis**: Advanced indicators and price predictions
        * **Real-time Data**: WebSocket streams for live market data
        * **Market Advisory**: Trading recommendations and portfolio analysis
        * **Cross-Exchange Analytics**: Arbitrage detection and price comparison
        
        ## Data Sources
        
        - Binance (Primary)
        - KuCoin
        - Bybit  
        - Gate.io
        - Bitget
        - OKX
        
        ## Rate Limits
        
        - Standard endpoints: 100 requests/hour
        - AI endpoints: 60 requests/minute
        - WebSocket connections: Unlimited
        
        For production access and higher limits, contact the API team.
        """,
        version="0.4.0",
        contact={
            "name": "Pebble Crypto API Team",
            "email": "api@pebblecrypto.com",
        },
        license_info={
            "name": "MIT",
        },
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add rate limiting middleware
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings["allowed_origins"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Include route modules with proper prefixes and tags
    app.include_router(
        health.router,
        prefix="/api",
        tags=["Health"]
    )
    
    app.include_router(
        market_data.router,
        prefix="/api/market",
        tags=["Market Data"]
    )
    
    app.include_router(
        predictions.router,
        prefix="/api/analysis",
        tags=["Technical Analysis"]
    )
    
    app.include_router(
        ai_agent.router,
        prefix="/api/ai",
        tags=["AI Assistant"]
    )
    
    app.include_router(
        multi_exchange.router,
        prefix="/api/exchanges",
        tags=["Multi-Exchange"]
    )
    
    app.include_router(
        market_advisor.router,
        prefix="/api/advisor",
        tags=["Market Advisor"]
    )
    
    app.include_router(
        websockets.router,
        prefix="/api/ws",
        tags=["WebSocket"]
    )
    
    # Add root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """
        Root endpoint providing API information and quick status check.
        """
        return {
            "name": "Pebble Crypto Analytics API",
            "version": "0.4.0", 
            "status": "online",
            "description": "Advanced cryptocurrency analytics with AI-powered insights",
            "features": [
                "Multi-exchange data aggregation",
                "AI-powered market analysis", 
                "Technical indicators and predictions",
                "Real-time WebSocket streams",
                "Trading recommendations",
                "Cross-exchange arbitrage detection"
            ],
            "endpoints": {
                "health": "/api/health",
                "market_data": "/api/market/*",
                "predictions": "/api/analysis/*", 
                "ai_assistant": "/api/ai/*",
                "exchanges": "/api/exchanges/*",
                "advisor": "/api/advisor/*",
                "websockets": "/api/ws/*",
                "documentation": "/docs"
            },
            "supported_exchanges": [
                "Binance", "KuCoin", "Bybit", "Gate.io", "Bitget", "OKX"
            ]
        }
    
    # Add startup event
    @app.on_event("startup")
    async def startup_event():
        logger.info("🚀 Pebble Crypto Analytics API v0.4.0 starting up...")
        logger.info("📊 Multi-exchange integration: 6 exchanges")
        logger.info("🤖 AI-powered analysis: Available")
        logger.info("📈 Technical indicators: 20+ indicators")
        logger.info("⚡ Real-time WebSocket: Available")
        logger.info("✅ Startup complete - API ready for requests")
    
    # Add shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("🔄 Pebble Crypto Analytics API shutting down...")
        logger.info("✅ Shutdown complete")
    
    return app

# Create the application instance
app = create_app() 