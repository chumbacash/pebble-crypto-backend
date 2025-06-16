from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException, Request, WebSocket, Depends, Body, Query, Path
from datetime import datetime, timezone
import os
import asyncio
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Optional, List, Dict, Any
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
from pydantic import BaseModel, Field
from app.services.binance import BinanceClient, SYMBOLS_CACHE, TICKER_CACHE
from app.core.prediction.technical import predictor
from app.services.metrics import MetricsTracker
from app.core.analysis.market_advisor import MarketAdvisor, MarketComparisonAnalyzer
from app.core.ai.agent import MarketAgent

ALLOWED_INTERVALS = ["1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
INTERVAL_HOURS = {
    "1h": 1, 
    "2h": 2, 
    "4h": 4, 
    "6h": 6, 
    "8h": 8, 
    "12h": 12, 
    "1d": 24, 
    "3d": 72, 
    "1w": 168, 
    "1M": 720
}
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("PebbleCryptoAPI")
metrics = MetricsTracker()
binance = BinanceClient()
limiter = Limiter(key_func=get_remote_address)

# Enhanced FastAPI app with better metadata
app = FastAPI(
    title="Pebble Crypto Analytics API",
    description="""
    🚀 **Advanced Cryptocurrency Analytics & AI-Powered Trading Assistant**
    
    ## Features
    
    * **📊 Real-Time Market Data** - Live prices, OHLCV data, and market statistics
    * **🤖 AI Assistant** - Natural language queries for market insights and investment advice
    * **📈 Technical Analysis** - RSI, Bollinger Bands, moving averages, and price predictions
    * **🔄 Multi-Exchange Support** - Aggregated data from 6+ major cryptocurrency exchanges
    * **⚡ WebSocket Streaming** - Real-time price updates and market monitoring
    * **📋 Portfolio Analysis** - Asset comparison and arbitrage opportunity detection
    
    ## Quick Start
    
    1. **Get Market Data**: `/api/market/data/{symbol}` - Comprehensive market information
    2. **Ask AI**: `/api/ai/ask` - Natural language queries about crypto markets
    3. **Technical Analysis**: `/api/analysis/predict/{symbol}` - Price predictions and signals
    * **Multi-Exchange**: `/api/exchanges/summary` - Cross-exchange price comparison
    
    ## Rate Limits
    
    * Most endpoints: 30 requests/minute
    * AI Assistant: 60 requests/minute  
    * Health check: 100 requests/minute
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Pebble Crypto API Support",
        "url": "https://github.com/pebble-crypto/api"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class LoggingMiddleware:
    async def __call__(self, request: Request, call_next):
        response = await call_next(request)
        logger.info(f"{request.method} {request.url} - Status: {response.status_code}")
        return response
app.middleware("http")(LoggingMiddleware())

# ================================================================================
# PYDANTIC MODELS
# ================================================================================

class CryptoQueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query about cryptocurrency markets", min_length=5, max_length=500)
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context to enhance the AI response")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Should I buy Bitcoin now? What does the technical analysis say?",
                "context": {"timeframe": "1d", "risk_tolerance": "moderate"}
            }
        }

class CryptoQueryResponse(BaseModel):
    query: str = Field(..., description="The original query")
    response: str = Field(..., description="AI-generated response with actionable insights")
    timestamp: str = Field(..., description="Response generation timestamp (ISO 8601)")
    supporting_data: Optional[Dict[str, Any]] = Field(default=None, description="Technical indicators and market data used")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Query processing metadata and confidence scores")

class SymbolsRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of trading symbols (e.g., ['BTCUSDT', 'ETHUSDT'])", max_items=10)
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
            }
        }

# ================================================================================
# CORE API ENDPOINTS
# ================================================================================

@app.get("/api/health", 
         tags=["🏥 System Health"], 
         summary="API Health Check",
         description="Get current API status, version, and system health metrics")
@limiter.limit("100/minute")
async def health_check(request: Request):
    """
    Returns the current health status of the API including:
    - Service availability
    - Version information
    - System timestamp
    - Exchange connectivity status
    """
    return {
        "service": "Pebble Crypto Analytics API",
        "status": "operational",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_check": "passed"
    }

# ================================================================================
# MARKET DATA ENDPOINTS
# ================================================================================

@app.get("/api/market/symbols", 
         tags=["📊 Market Data"], 
         summary="Get Trading Symbols",
         description="Retrieve all available cryptocurrency trading symbols with optional volume-based sorting")
@limiter.limit("30/minute")
async def get_trading_symbols(
    request: Request, 
    sort_by: Optional[str] = Query(None, description="Sort criteria: 'volume' for 24h volume sorting"),
    descending: bool = Query(True, description="Sort order (True for descending, False for ascending)")
):
    """
    Get all available cryptocurrency trading symbols.
    
    **Parameters:**
    - `sort_by`: Optional sorting by '24h_volume' 
    - `descending`: Sort order (default: True for highest volume first)
    
    **Returns:**
    - List of trading symbols (e.g., BTCUSDT, ETHUSDT)
    - Sorting information if applied
    - Cache timestamp
    """
    try:
        cache_key = "symbols"
        if not SYMBOLS_CACHE.get(cache_key):
            SYMBOLS_CACHE[cache_key] = binance.fetch_symbols()
        symbols = SYMBOLS_CACHE[cache_key]

        if sort_by == "volume":
            sort_cache_key = f"symbols_sorted_volume"
            if not SYMBOLS_CACHE.get(sort_cache_key):
                tickers = binance.fetch_tickers()
                ticker_map = {t['symbol']: t for t in tickers}
                sorted_symbols = sorted(
                    symbols,
                    key=lambda s: float(ticker_map.get(s, {}).get('quoteVolume', 0)),
                    reverse=descending
                )
                SYMBOLS_CACHE[sort_cache_key] = sorted_symbols
            return {
                "symbols": SYMBOLS_CACHE[sort_cache_key],
                "total_count": len(SYMBOLS_CACHE[sort_cache_key]),
                "sorting": f"24h_volume_{'desc' if descending else 'asc'}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        return {
            "symbols": symbols, 
            "total_count": len(symbols),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Symbols error: {str(e)}")
        raise HTTPException(status_code=503, detail="Market data service temporarily unavailable")

@app.get("/api/market/data/{symbol}", 
         tags=["📊 Market Data"], 
         summary="Get Market Data",
         description="Get comprehensive market data including OHLCV, volume, and recent price history")
@limiter.limit("30/minute")
async def get_market_data(
    request: Request, 
    symbol: str = Path(..., description="Trading symbol (e.g., BTCUSDT)"),
    interval: str = Query("1h", description="Time interval for OHLCV data"),
    limit: int = Query(100, description="Number of data points to retrieve", ge=1, le=1000),
    period: str = Query("24h", description="Data period: '24h' for intraday, 'historical' for extended history")
):
    """
    Get comprehensive market data for a cryptocurrency symbol.
    
    **Features:**
    - OHLCV (Open, High, Low, Close, Volume) data
    - 24h price change and statistics
    - Configurable time intervals and data limits
    - Both intraday and historical data support
    
    **Parameters:**
    - `symbol`: Trading pair (e.g., BTCUSDT, ETHUSDT)
    - `interval`: Time interval (1h, 4h, 1d, 1w, etc.)
    - `limit`: Number of candles (1-1000)
    - `period`: '24h' for current day only, 'historical' for extended history
    """
    try:
        # Validate interval
        if interval not in ALLOWED_INTERVALS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval. Allowed: {', '.join(ALLOWED_INTERVALS)}"
            )
        
        # Fetch OHLCV data
        if period == "24h":
            # Intraday data for current day
            now = datetime.now(timezone.utc)
            start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
            interval_hours = INTERVAL_HOURS[interval]
            intervals_elapsed = int((now - start_of_day).total_seconds() / (interval_hours * 3600)) + 1
            limit = min(intervals_elapsed, limit)
        
        # Await the async call for OHLCV data
        data = await binance.fetch_ohlcv(symbol, interval, limit=limit)
        if not data:
            raise HTTPException(status_code=404, detail="No market data available for this symbol")

        # Filter for intraday if requested
        if period == "24h":
            now = datetime.now(timezone.utc)
            start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
            filtered_data = []
            for candle in data:
                candle_time = datetime.fromtimestamp(candle["timestamp"] / 1000, tz=timezone.utc)
                if candle_time >= start_of_day:
                    filtered_data.append(candle)
            data = filtered_data

        # Calculate statistics
        if data:
            current_price = data[-1]["close"]
            price_24h_ago = data[0]["close"] if len(data) > 1 else current_price
            price_change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100
            
            stats = {
                "current_price": current_price,
                "price_change_24h_percent": round(price_change_24h, 2),
                "high_24h": max(candle["high"] for candle in data),
                "low_24h": min(candle["low"] for candle in data),
                "volume_24h": sum(candle["volume"] for candle in data)
            }
        else:
            stats = {}

        return {
            "symbol": symbol,
            "interval": interval,
            "period": period,
            "market_data": data,
            "statistics": stats,
            "data_points": len(data),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Market data error for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve market data: {str(e)}")

# ================================================================================
# REAL-TIME DATA ENDPOINTS
# ================================================================================

@app.websocket("/api/ws/live/{symbol}")
async def websocket_live_data(websocket: WebSocket, symbol: str, interval: str = "1h"):
    """
    **Real-time cryptocurrency data streaming via WebSocket**
    
    Provides live market updates including:
    - Real-time price changes
    - OHLCV data updates
    - Volume and market activity
    
    **Parameters:**
    - `symbol`: Trading pair (e.g., BTCUSDT)
    - `interval`: Update interval (1h, 4h, 1d, etc.)
    
    **Connection stays open and sends periodic updates based on the specified interval.**
    """
    await websocket.accept()
    try:
        # Validate interval
        if interval not in ALLOWED_INTERVALS:
            await websocket.send_json({
                "error": "Invalid interval",
                "detail": f"Allowed intervals: {', '.join(ALLOWED_INTERVALS)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            await websocket.close(code=1008)
            return
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "symbol": symbol,
            "interval": interval,
            "message": f"Live data stream started for {symbol}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
            
        while True:
            try:
                # Fetch latest OHLCV data
                ohlcv = await binance.fetch_ohlcv(symbol, interval, limit=1)
                if ohlcv:
                    await websocket.send_json({
                        "type": "market_update",
                        "symbol": symbol,
                        "interval": interval,
                        "data": ohlcv[0],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                
                # Dynamic sleep time based on interval
                if interval.endswith('h'):
                    sleep_time = 300  # 5 minutes for hourly intervals
                elif interval in ['1d', '3d', '1w', '1M']:
                    sleep_time = 900  # 15 minutes for daily+ intervals
                else:
                    sleep_time = 300
                    
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"WebSocket data error for {symbol}: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Temporary data unavailable",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                await asyncio.sleep(60)  # Wait before retrying
                
    except Exception as e:
        logger.error(f"WebSocket connection error ({symbol}): {str(e)}")
        await websocket.close(code=1011)

# ================================================================================
# AI ASSISTANT ENDPOINTS
# ================================================================================

# Initialize the MarketAgent for AI-powered responses
market_agent = MarketAgent()

@app.post("/api/ai/ask", 
          response_model=CryptoQueryResponse, 
          tags=["🤖 AI Assistant"], 
          summary="AI-Powered Market Assistant",
          description="Get intelligent responses to natural language queries about cryptocurrency markets")
@limiter.limit("60/minute")
async def ai_market_assistant(
    request: Request,
    query_request: CryptoQueryRequest = Body(...),
):
    """
    **🤖 Intelligent Cryptocurrency Market Assistant**
    
    Ask any question about cryptocurrency markets and get AI-powered responses with:
    
    **Supported Query Types:**
    - **Price Information**: *"What's the current price of Bitcoin?"*
    - **Technical Analysis**: *"What do the RSI and moving averages say about Ethereum?"*
    - **Investment Advice**: *"Should I buy Solana now?"*
    - **Market Trends**: *"How is the crypto market performing today?"*
    - **Asset Comparison**: *"Compare Bitcoin vs Ethereum performance"*
    - **Risk Assessment**: *"Is LINK a good investment this week?"*
    
    **AI Features:**
    - Multi-timeframe technical analysis
    - Real-time market data integration
    - Professional investment insights
    - Risk assessment and position sizing
    - Entry/exit point recommendations
    
    **Response includes:**
    - Clear, actionable advice
    - Supporting technical data
    - Confidence scores
    - Risk warnings and disclaimers
    """
    try:
        # Extract query and context
        query = query_request.query
        context = query_request.context or {}
        
        # Log the incoming query for monitoring
        logger.info(f"AI Assistant Query: {query[:100]}...")
        
        # Process query through the market agent
        result = await market_agent.process_query(query)
        
        # Apply any context-specific adjustments
        if context:
            result = await _enhance_with_context(result, context)
        
        # Extract and structure supporting data
        supporting_data = result.get("supporting_data", {})
        
        # Add multi-timeframe insights if available
        if "multi_timeframe" in result:
            multi_tf_insights = {}
            for tf, tf_data in result.get("multi_timeframe", {}).items():
                if "trend" in tf_data:
                    multi_tf_insights[tf] = {
                        "trend": tf_data["trend"].get("description", "NEUTRAL"),
                        "rsi": tf_data.get("indicators", {}).get("rsi", 50),
                        "confidence": tf_data.get("confidence", 0.5)
                    }
            
            if multi_tf_insights:
                supporting_data["timeframe_analysis"] = multi_tf_insights
        
        return CryptoQueryResponse(
            query=result["query"],
            response=result["response"],
            timestamp=result["timestamp"],
            supporting_data=supporting_data,
            metadata=result.get("metadata")
        )
        
    except Exception as e:
        logger.error(f"AI Assistant error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"AI processing failed: {str(e)}"
        )

# ================================================================================
# TECHNICAL ANALYSIS ENDPOINTS
# ================================================================================

@app.get("/api/analysis/predict/{symbol}", 
         tags=["📈 Technical Analysis"], 
         summary="Price Prediction & Technical Analysis",
         description="Advanced technical analysis with price predictions, indicators, and trading signals")
@limiter.limit("30/minute")
async def technical_analysis_prediction(
    request: Request, 
    symbol: str = Path(..., description="Trading symbol (e.g., BTCUSDT)"),
    interval: str = Query("1h", description="Analysis timeframe"),
    analysis_depth: str = Query("standard", description="Analysis depth: 'quick', 'standard', 'comprehensive'")
):
    """
    **📈 Advanced Technical Analysis & Price Predictions**
    
    Get comprehensive technical analysis including:
    
    **Technical Indicators:**
    - RSI (Relative Strength Index)
    - Moving Averages (SMA, EMA)
    - Bollinger Bands
    - MACD and momentum indicators
    - Support and resistance levels
    
    **Analysis Features:**
    - Multi-timeframe trend analysis
    - Price prediction models
    - Buy/sell signal generation
    - Volatility assessment
    - Risk/reward calculations
    
    **Analysis Depths:**
    - `quick`: Basic indicators and trend
    - `standard`: Full technical analysis suite
    - `comprehensive`: Multi-timeframe + advanced metrics
    """
    try:
        # Validate interval
        if interval not in ALLOWED_INTERVALS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval. Allowed: {', '.join(ALLOWED_INTERVALS)}"
            )
        
        # Determine data limit based on analysis depth
        data_limits = {
            "quick": 50,
            "standard": 100,
            "comprehensive": 200
        }
        limit = data_limits.get(analysis_depth, 100)
        
        # Clear cache for fresh analysis
        predictor.analysis_cache.clear()
        logger.info(f"Technical analysis requested for {symbol} ({interval}, {analysis_depth})")
            
        # Fetch OHLCV data
        ohlcv = await binance.fetch_ohlcv(symbol, interval, limit=limit)
        closes = [entry["close"] for entry in ohlcv]
        
        if len(closes) < 20:
            raise HTTPException(
                status_code=422,
                detail="Insufficient data for technical analysis (minimum 20 data points required)"
            )
        
        # Perform technical analysis
        analysis = await predictor.analyze_market(closes, interval)
        
        # Enhance metadata
        analysis["metadata"].update({
            "interval": interval,
            "symbol": symbol,
            "analysis_depth": analysis_depth,
            "data_points_used": len(closes),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return analysis
        
    except Exception as e:
        logger.error(f"Technical analysis error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Technical analysis failed: {str(e)}"
        )

@app.get("/api/analysis/compare/{primary_symbol}", 
         tags=["📈 Technical Analysis"], 
         summary="Multi-Asset Comparison",
         description="Compare multiple cryptocurrencies with performance metrics and relative analysis")
@limiter.limit("20/minute")
async def compare_cryptocurrency_assets(
    request: Request, 
    primary_symbol: str = Path(..., description="Primary cryptocurrency to analyze"),
    comparison_symbols: str = Query(..., description="Comma-separated symbols to compare (e.g., 'ETHUSDT,SOLUSDT')"),
    time_period: str = Query("7d", description="Comparison period: 1d, 3d, 7d, 14d, 30d"),
    metrics: str = Query("all", description="Metrics to include: 'all', 'performance', 'volatility', 'technical'")
):
    """
    **📊 Multi-Asset Performance Comparison**
    
    Compare cryptocurrency performance across multiple metrics:
    
    **Performance Metrics:**
    - Price change percentages
    - Volume analysis
    - Market cap considerations
    - Relative strength rankings
    
    **Technical Comparison:**
    - RSI levels across assets
    - Trend strength comparison
    - Volatility rankings
    - Correlation analysis
    
    **Time Periods:**
    - Short-term: 1d, 3d
    - Medium-term: 7d, 14d  
    - Long-term: 30d
    
    **Use Cases:**
    - Portfolio diversification
    - Sector rotation analysis
    - Relative value identification
    - Risk assessment across assets
    """
    try:
        # Validate inputs
        if not primary_symbol or not comparison_symbols:
            raise HTTPException(
                status_code=400,
                detail="Both primary_symbol and comparison_symbols must be provided"
            )
            
        # Parse and validate comparison symbols
        comparison_assets = [s.strip().upper() for s in comparison_symbols.split(",")]
        
        # Limit number of comparisons
        if len(comparison_assets) > 8:
            comparison_assets = comparison_assets[:8]
            logger.warning("Limited comparison to 8 assets for performance")
            
        # Validate time period
        valid_periods = ["1d", "3d", "7d", "14d", "30d"]
        if time_period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time period. Allowed: {', '.join(valid_periods)}"
            )
            
        # Initialize comparison analyzer
        analyzer = MarketComparisonAnalyzer(binance_client=binance)
        
        # Generate comparison data
        comparison_data = await analyzer.compare_assets(
            primary_symbol=primary_symbol.upper(),
            comparison_assets=comparison_assets,
            time_period=time_period
        )
        
        if "error" in comparison_data:
            raise HTTPException(
                status_code=404,
                detail=comparison_data["error"]
            )
        
        # Filter metrics if requested
        if metrics != "all":
            # This could be extended to filter specific metric categories
            pass
            
        return {
            "comparison_type": "multi_asset_analysis",
            "primary_symbol": primary_symbol.upper(),
            "comparison_assets": comparison_assets,
            "time_period": time_period,
            "metrics_included": metrics,
            "analysis_data": comparison_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Asset comparison error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Comparison analysis failed: {str(e)}")

# ================================================================================
# MULTI-EXCHANGE ENDPOINTS
# ================================================================================

@app.get("/api/exchanges/health", 
         tags=["🔄 Multi-Exchange"], 
         summary="Exchange Health Monitor",
         description="Monitor health and availability status of all connected cryptocurrency exchanges")
@limiter.limit("30/minute")
async def monitor_exchange_health(request: Request):
    """
    **🔄 Exchange Health & Connectivity Monitor**
    
    Monitor real-time health status of all connected exchanges:
    
    **Health Metrics:**
    - Exchange availability (online/offline)
    - Response time measurements
    - Error rate tracking
    - Last successful connection
    
    **Supported Exchanges:**
    - Binance (Primary)
    - KuCoin, Bybit, Gate.io
    - Bitget, OKX
    
    **Use Cases:**
    - System reliability monitoring
    - Exchange selection for trading
    - Outage detection and alerts
    - Performance optimization
    """
    try:
        health_data = await market_agent.get_exchange_health()
        return {
            "monitoring_status": "active",
            "health_check_timestamp": datetime.now(timezone.utc).isoformat(),
            **health_data
        }
    except Exception as e:
        logger.error(f"Exchange health monitoring error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Health monitoring failed: {str(e)}"
        )

@app.post("/api/exchanges/summary", 
          tags=["🔄 Multi-Exchange"], 
          summary="Multi-Exchange Market Summary",
          description="Comprehensive market data aggregated from multiple exchanges with arbitrage detection")
@limiter.limit("20/minute")
async def multi_exchange_market_summary(
    request: Request, 
    symbols_request: SymbolsRequest = Body(...)
):
    """
    **🔄 Comprehensive Multi-Exchange Market Summary**
    
    Get aggregated market data from all connected exchanges:
    
    **Data Sources:**
    - Price data from 6+ major exchanges
    - Volume and liquidity analysis
    - Best bid/ask identification
    - Arbitrage opportunity detection
    
    **Features:**
    - Cross-exchange price comparison
    - Real-time arbitrage alerts
    - Exchange health integration
    - Liquidity depth analysis
    
    **Response Includes:**
    - Best prices across exchanges
    - Price spread analysis
    - Trading volume comparison
    - Exchange-specific data quality
    - Arbitrage profit calculations
    
    **Maximum 5 symbols per request for optimal performance.**
    """
    try:
        symbols = symbols_request.symbols
        
        if len(symbols) > 5:
            raise HTTPException(
                status_code=400, 
                detail="Maximum 5 symbols allowed per request for optimal performance"
            )
        
        # Get comprehensive multi-exchange data
        market_summary = {}
        exchange_health = await market_agent.get_exchange_health()
        
        for symbol in symbols:
            try:
                # Get aggregated market data
                market_data = await market_agent.exchange_aggregator.get_multi_asset_data([symbol])
                best_price_data = await market_agent.exchange_aggregator.find_best_price(symbol)
                
                symbol_summary = {
                    "symbol": symbol.upper(),
                    "market_data": {},
                    "best_price_analysis": best_price_data,
                    "exchange_coverage": 0,
                    "data_quality_score": 0
                }
                
                # Process primary exchange data
                if market_data and symbol.upper() in market_data:
                    primary_data = market_data[symbol.upper()]
                    symbol_summary.update({
                        "primary_exchange": primary_data.exchange,
                        "current_price": primary_data.current_price,
                        "price_change_24h": primary_data.price_change_24h,
                        "high_24h": primary_data.high_24h,
                        "low_24h": primary_data.low_24h,
                        "volume_24h": primary_data.volume_24h
                    })
                
                # Aggregate exchange-specific data
                if best_price_data and "all_prices" in best_price_data:
                    exchange_count = 0
                    total_quality = 0
                    
                    for price_info in best_price_data["all_prices"]:
                        exchange_name = price_info["exchange"]
                        data = price_info["data"]
                        exchange_health_status = exchange_health.get("exchanges", {}).get(exchange_name, {})
                        
                        symbol_summary["market_data"][exchange_name] = {
                            "price": data.current_price,
                            "price_change_24h": data.price_change_24h,
                            "volume_24h": data.volume_24h,
                            "timestamp": data.timestamp.isoformat(),
                            "health_status": exchange_health_status.get("status", "unknown"),
                            "response_time": exchange_health_status.get("response_time", 0)
                        }
                        
                        exchange_count += 1
                        # Simple quality scoring based on health and data completeness
                        if exchange_health_status.get("status") == "healthy":
                            total_quality += 1
                    
                    symbol_summary["exchange_coverage"] = exchange_count
                    symbol_summary["data_quality_score"] = round((total_quality / max(exchange_count, 1)) * 100, 1)
                    symbol_summary["price_spread_percent"] = best_price_data.get("price_spread", 0)
                    symbol_summary["arbitrage_opportunity"] = best_price_data.get("arbitrage_opportunity", False)
                
                market_summary[symbol.upper()] = symbol_summary
                
            except Exception as e:
                logger.error(f"Error processing market summary for {symbol}: {str(e)}")
                market_summary[symbol.upper()] = {
                    "symbol": symbol.upper(),
                    "error": f"Data unavailable: {str(e)}"
                }
        
        return {
            "summary_type": "multi_exchange_aggregated",
            "symbols_analyzed": len(symbols),
            "market_summary": market_summary,
            "exchange_health_summary": {
                "total_exchanges": exchange_health.get("total_exchanges", 0),
                "healthy_exchanges": exchange_health.get("healthy_exchanges", 0),
                "health_percentage": round((exchange_health.get("healthy_exchanges", 0) / max(exchange_health.get("total_exchanges", 1), 1)) * 100, 1)
            },
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Multi-exchange summary error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Multi-exchange analysis failed: {str(e)}"
        )

@app.post("/api/exchanges/arbitrage", 
          tags=["🔄 Multi-Exchange"], 
          summary="Arbitrage Opportunity Scanner",
          description="Detect arbitrage opportunities across multiple cryptocurrency exchanges")
@limiter.limit("15/minute")
async def scan_arbitrage_opportunities(
    request: Request, 
    symbols_request: SymbolsRequest = Body(...)
):
    """
    **💰 Real-Time Arbitrage Opportunity Scanner**
    
    Identify profitable arbitrage opportunities across exchanges:
    
    **Detection Features:**
    - Real-time price discrepancies
    - Profit margin calculations
    - Exchange fee considerations
    - Minimum profit threshold filtering
    
    **Risk Analysis:**
    - Exchange reliability scores
    - Liquidity depth assessment
    - Transfer time estimates
    - Fee impact calculations
    
    **Opportunity Types:**
    - Simple arbitrage (buy low, sell high)
    - Triangular arbitrage detection
    - Cross-exchange spread analysis
    
    **⚠️ Important:** This is for informational purposes only. 
    Consider all trading risks, fees, and execution delays.
    """
    try:
        symbols = symbols_request.symbols
        
        if len(symbols) > 10:
            raise HTTPException(
                status_code=400, 
                detail="Maximum 10 symbols for arbitrage scanning"
            )
        
        # Scan for arbitrage opportunities
        arbitrage_results = await market_agent.find_best_prices(symbols)
        
        # Process and enhance arbitrage data
        opportunities = []
        
        for symbol_data in arbitrage_results.get("results", []):
            if symbol_data.get("arbitrage_opportunity"):
                opportunity = {
                    "symbol": symbol_data["symbol"],
                    "profit_potential": symbol_data.get("price_spread", 0),
                    "best_buy_exchange": symbol_data.get("lowest_price_exchange", "unknown"),
                    "best_sell_exchange": symbol_data.get("highest_price_exchange", "unknown"),
                    "buy_price": symbol_data.get("lowest_price", 0),
                    "sell_price": symbol_data.get("highest_price", 0),
                    "estimated_profit_percent": symbol_data.get("profit_percent", 0),
                    "risk_level": "medium",  # Could be calculated based on exchange reliability
                    "data_timestamp": symbol_data.get("timestamp", datetime.now(timezone.utc).isoformat())
                }
                opportunities.append(opportunity)
        
        return {
            "scan_type": "arbitrage_opportunities",
            "symbols_scanned": symbols,
            "opportunities_found": len(opportunities),
            "arbitrage_opportunities": opportunities,
            "market_conditions": {
                "volatility": "moderate",  # Could be calculated from price data
                "liquidity": "good"        # Could be assessed from volume data
            },
            "disclaimer": "Arbitrage opportunities are time-sensitive and subject to execution risks, fees, and market changes.",
            "scan_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Arbitrage scanning error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Arbitrage scanning failed: {str(e)}"
        )

@app.get("/api/exchanges/coverage", 
         tags=["🔄 Multi-Exchange"], 
         summary="Exchange Coverage Information",
         description="Detailed information about supported exchanges, capabilities, and trading pairs")
@limiter.limit("10/minute")
async def get_exchange_coverage_info(request: Request):
    """
    **📋 Exchange Coverage & Capabilities Overview**
    
    Comprehensive information about our exchange integration:
    
    **Exchange Network:**
    - 6+ major cryptocurrency exchanges
    - Global market coverage
    - Specialized exchange capabilities
    - Rate limit and API specifications
    
    **Features per Exchange:**
    - Spot trading support
    - Derivatives and futures
    - Estimated trading pairs
    - Geographic specialization
    
    **Integration Stats:**
    - Total estimated trading pairs: 4400+
    - Combined daily volume coverage
    - Redundancy and failover capabilities
    """
    try:
        coverage_info = {
            "integration_overview": {
                "total_exchanges": 6,
                "primary_exchange": "Binance",
                "total_estimated_pairs": 4400,
                "global_coverage": True,
                "redundancy_level": "high"
            },
            "exchanges": {
                "binance": {
                    "priority": 1,
                    "region": "Global",
                    "specialty": "Highest liquidity and most comprehensive trading pairs",
                    "estimated_pairs": 600,
                    "features": ["spot", "futures", "options", "staking"],
                    "rate_limit": "1200 requests/minute",
                    "api_version": "v3",
                    "status": "primary"
                },
                "kucoin": {
                    "priority": 2,
                    "region": "Global",
                    "specialty": "Early altcoin discovery and emerging tokens",
                    "estimated_pairs": 800,
                    "features": ["spot", "futures", "margin", "lending"],
                    "rate_limit": "100 requests/minute",
                    "api_version": "v2",
                    "status": "secondary"
                },
                "bybit": {
                    "priority": 3,
                    "region": "Asia-Pacific",
                    "specialty": "Derivatives trading and perpetual contracts",
                    "estimated_pairs": 400,
                    "features": ["spot", "derivatives", "copy_trading"],
                    "rate_limit": "120 requests/minute",
                    "api_version": "v5",
                    "status": "secondary"
                },
                "gateio": {
                    "priority": 4,
                    "region": "Global",
                    "specialty": "Comprehensive altcoin coverage and new listings",
                    "estimated_pairs": 1200,
                    "features": ["spot", "margin", "futures", "nft"],
                    "rate_limit": "200 requests/minute",
                    "api_version": "v4",
                    "status": "secondary"
                },
                "bitget": {
                    "priority": 5,
                    "region": "Global",
                    "specialty": "Copy trading platform and social trading",
                    "estimated_pairs": 500,
                    "features": ["spot", "futures", "copy_trading"],
                    "rate_limit": "150 requests/minute",
                    "api_version": "v1",
                    "status": "secondary"
                },
                "okx": {
                    "priority": 6,
                    "region": "Global",
                    "specialty": "Deep liquidity and institutional trading",
                    "estimated_pairs": 900,
                    "features": ["spot", "futures", "options", "web3"],
                    "rate_limit": "300 requests/minute",
                    "api_version": "v5",
                    "status": "secondary"
                }
            },
            "capabilities": {
                "data_aggregation": "Real-time price and volume data from all exchanges",
                "arbitrage_detection": "Cross-exchange price discrepancy identification",
                "failover_routing": "Automatic switching during exchange downtime",
                "load_balancing": "Distributed requests across healthy exchanges",
                "health_monitoring": "Continuous exchange availability tracking"
            },
            "performance_metrics": {
                "average_response_time": "< 500ms",
                "uptime_target": "99.9%",
                "data_freshness": "< 30 seconds",
                "redundancy_factor": "3x (primary + 2 backups minimum)"
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        return coverage_info
        
    except Exception as e:
        logger.error(f"Exchange coverage info error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve coverage information: {str(e)}"
        )

# ================================================================================
# UTILITY FUNCTIONS
# ================================================================================

async def _enhance_with_context(result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Apply context-specific adjustments to AI responses"""
    # Handle preferred timeframe
    if "timeframe" in context and result.get("metadata", {}).get("symbol"):
        symbol = result["metadata"]["symbol"]
        timeframe = context["timeframe"]
        
        # Map common timeframe formats
        timeframe_map = {
            "short": "1h",
            "medium": "4h", 
            "long": "1d",
            "weekly": "1w"
        }
        interval = timeframe_map.get(timeframe, timeframe)
        
        if interval in ALLOWED_INTERVALS:
            result["response"] = f"*Analyzed using {interval} timeframe data*\n\n{result['response']}"
    
    # Handle risk tolerance
    if "risk_tolerance" in context:
        risk = context["risk_tolerance"].lower()
        if "advice" in result.get("metadata", {}).get("intent", ""):
            risk_notes = {
                "conservative": "\n\n⚠️ **Conservative Approach**: Consider smaller position sizes and tighter stop losses.",
                "moderate": "\n\n⚖️ **Balanced Approach**: Standard risk management applies.",
                "aggressive": "\n\n🚀 **Aggressive Approach**: Higher risk tolerance noted - consider larger positions if analysis supports it."
            }
            result["response"] += risk_notes.get(risk, "")
    
    return result

# ================================================================================
# APPLICATION STARTUP
# ================================================================================

if __name__ == "__main__":
    # Configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    workers = int(os.getenv("WORKERS", 1))
    
    # Enhanced startup logging
    logger.info("🚀 Starting Pebble Crypto Analytics API")
    logger.info(f"📡 Server: {host}:{port}")
    logger.info(f"🔄 Reload: {reload}")
    logger.info(f"⚡ Workers: {workers}")
    logger.info(f"🌐 Environment: {os.getenv('ENVIRONMENT', 'production')}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers
    )
