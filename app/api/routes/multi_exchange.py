"""
Multi-exchange endpoints for cross-exchange analytics and price comparison
"""

from fastapi import APIRouter, HTTPException, Request, Body, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Dict, List
from datetime import datetime, timezone
import logging

from app.core.dependencies import get_market_agent

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger("CryptoPredictAPI")

@router.get("/health", tags=["Multi-Exchange"])
@limiter.limit("30/minute")
async def get_exchange_health(
    request: Request,
    market_agent = Depends(get_market_agent)
):
    """
    Get health status of all registered cryptocurrency exchanges.
    
    Returns information about:
    - Exchange availability and response times
    - Number of healthy vs unhealthy exchanges
    - Last health check timestamps
    - Exchange configurations
    """
    try:
        health_data = await market_agent.get_exchange_health()
        return health_data
    except Exception as e:
        logger.error(f"Exchange health error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get exchange health: {str(e)}")

@router.post("/best-prices", tags=["Multi-Exchange"])
@limiter.limit("20/minute")
async def find_best_prices(
    request: Request, 
    symbols_request: Dict[str, List[str]] = Body(...),
    market_agent = Depends(get_market_agent)
):
    """
    Find the best prices across all exchanges for multiple cryptocurrency symbols.
    
    Useful for:
    - Arbitrage opportunity detection
    - Price comparison across exchanges
    - Finding the best exchange for trading
    
    Request body should contain a "symbols" field with a list of trading symbols.
    Example: {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]}
    """
    try:
        if "symbols" not in symbols_request or not symbols_request["symbols"]:
            raise HTTPException(status_code=400, detail="Symbols list is required")
            
        if len(symbols_request["symbols"]) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 symbols allowed per request")
            
        # Find best prices across exchanges
        results = await market_agent.find_best_prices(symbols_request["symbols"])
        
        return results
    except Exception as e:
        logger.error(f"Best prices error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to find best prices: {str(e)}")

@router.get("/coverage", tags=["Multi-Exchange"])
@limiter.limit("10/minute")
async def get_exchange_coverage(request: Request):
    """
    Get information about exchange coverage and capabilities.
    
    Returns:
    - List of supported exchanges
    - Exchange priorities and configurations
    - Estimated number of trading pairs per exchange
    - Exchange specialties (derivatives, spot, etc.)
    """
    try:
        coverage_info = {
            "status": "success",
            "exchanges": {
                "binance": {
                    "priority": 1,
                    "specialty": "Primary exchange with highest liquidity",
                    "estimated_pairs": 600,
                    "features": ["spot", "futures", "options"],
                    "rate_limit": "1200 requests/minute"
                },
                "kucoin": {
                    "priority": 2,
                    "specialty": "Early altcoin discovery and emerging tokens",
                    "estimated_pairs": 800,
                    "features": ["spot", "futures", "margin"],
                    "rate_limit": "100 requests/minute"
                },
                "bybit": {
                    "priority": 3,
                    "specialty": "Derivatives and Asian market focus",
                    "estimated_pairs": 400,
                    "features": ["spot", "derivatives", "funding_rates"],
                    "rate_limit": "120 requests/minute"
                },
                "gateio": {
                    "priority": 4,
                    "specialty": "Comprehensive coverage and new listings",
                    "estimated_pairs": 1200,
                    "features": ["spot", "margin", "new_listings"],
                    "rate_limit": "200 requests/minute"
                },
                "bitget": {
                    "priority": 5,
                    "specialty": "Copy trading and emerging markets",
                    "estimated_pairs": 500,
                    "features": ["spot", "futures", "copy_trading"],
                    "rate_limit": "150 requests/minute"
                },
                "okx": {
                    "priority": 6,
                    "specialty": "Professional trading and derivatives",
                    "estimated_pairs": 400,
                    "features": ["spot", "futures", "options", "margin"],
                    "rate_limit": "300 requests/minute"
                }
            },
            "total_estimated_pairs": 3900,
            "capabilities": [
                "Multi-exchange price comparison",
                "Arbitrage opportunity detection", 
                "Intelligent failover routing",
                "Cross-exchange analytics",
                "Real-time health monitoring"
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return coverage_info
    except Exception as e:
        logger.error(f"Exchange coverage error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get exchange coverage: {str(e)}")

@router.post("/arbitrage", tags=["Multi-Exchange"])
@limiter.limit("15/minute")
async def find_arbitrage_opportunities(
    request: Request,
    symbols_request: Dict[str, List[str]] = Body(...),
    market_agent = Depends(get_market_agent)
):
    """
    Find arbitrage opportunities across exchanges for specified symbols.
    
    Analyzes price differences between exchanges to identify potential
    arbitrage opportunities with profit calculations.
    
    Request body should contain a "symbols" field with trading symbols.
    Example: {"symbols": ["BTCUSDT", "ETHUSDT"]}
    """
    try:
        if "symbols" not in symbols_request or not symbols_request["symbols"]:
            raise HTTPException(status_code=400, detail="Symbols list is required")
            
        if len(symbols_request["symbols"]) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 symbols allowed for arbitrage analysis")
        
        # Get best prices data which includes arbitrage information
        price_data = await market_agent.find_best_prices(symbols_request["symbols"])
        
        # Extract arbitrage opportunities
        arbitrage_opportunities = []
        
        for symbol_data in price_data.get("results", []):
            symbol = symbol_data.get("symbol")
            exchanges = symbol_data.get("exchanges", {})
            
            if len(exchanges) < 2:
                continue
                
            # Find min and max prices
            prices = [(name, data["price"]) for name, data in exchanges.items() 
                     if data.get("price") and data["price"] > 0]
            
            if len(prices) < 2:
                continue
                
            prices.sort(key=lambda x: x[1])  # Sort by price
            min_exchange, min_price = prices[0]
            max_exchange, max_price = prices[-1]
            
            spread_percent = ((max_price - min_price) / min_price) * 100
            
            # Only include opportunities with >0.1% spread
            if spread_percent > 0.1:
                arbitrage_opportunities.append({
                    "symbol": symbol,
                    "buy_exchange": min_exchange,
                    "sell_exchange": max_exchange,
                    "buy_price": min_price,
                    "sell_price": max_price,
                    "spread_percent": round(spread_percent, 4),
                    "potential_profit_per_unit": round(max_price - min_price, 6)
                })
        
        # Sort by spread percentage (highest first)
        arbitrage_opportunities.sort(key=lambda x: x["spread_percent"], reverse=True)
        
        return {
            "arbitrage_opportunities": arbitrage_opportunities,
            "total_opportunities": len(arbitrage_opportunities),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "Prices are real-time but may change rapidly. Always verify prices before executing trades."
        }
        
    except Exception as e:
        logger.error(f"Arbitrage analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze arbitrage opportunities: {str(e)}")

@router.get("/summary", tags=["Multi-Exchange"])
@limiter.limit("20/minute")
async def get_exchange_summary(
    request: Request,
    market_agent = Depends(get_market_agent)
):
    """
    Get a comprehensive summary of all exchange data and capabilities.
    
    Returns aggregated information about:
    - Total trading pairs across all exchanges
    - Exchange health status summary
    - Feature capabilities matrix
    - Performance metrics
    """
    try:
        # Get exchange health data
        health_data = await market_agent.get_exchange_health()
        
        # Calculate summary statistics
        total_exchanges = len(health_data.get("exchanges", {}))
        healthy_exchanges = sum(1 for ex in health_data.get("exchanges", {}).values() 
                               if ex.get("status") == "healthy")
        
        # Get coverage info
        coverage_response = await get_exchange_coverage(request)
        coverage_info = coverage_response if isinstance(coverage_response, dict) else {}
        
        summary = {
            "overview": {
                "total_exchanges": total_exchanges,
                "healthy_exchanges": healthy_exchanges,
                "unhealthy_exchanges": total_exchanges - healthy_exchanges,
                "total_estimated_pairs": coverage_info.get("total_estimated_pairs", 0),
                "health_percentage": round((healthy_exchanges / total_exchanges * 100), 2) if total_exchanges > 0 else 0
            },
            "exchange_details": health_data.get("exchanges", {}),
            "capabilities": coverage_info.get("capabilities", []),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Exchange summary error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get exchange summary: {str(e)}") 