"""
Price prediction endpoints using technical analysis
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

from app.core.dependencies import (
    get_binance_client, get_predictor, get_allowed_intervals
)
from app.services.binance import BinanceClient

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger("CryptoPredictAPI")

@router.get("/predict/{symbol}", tags=["Predictions"])
@limiter.limit("30/minute")
async def predict_price(
    request: Request, 
    symbol: str, 
    interval: str = "1h",
    binance: BinanceClient = Depends(get_binance_client),
    predictor = Depends(get_predictor),
    allowed_intervals: list = Depends(get_allowed_intervals)
):
    """
    Generate price predictions and technical analysis for a cryptocurrency symbol.
    
    Returns comprehensive analysis including:
    - Price predictions with confidence intervals
    - Technical indicators (RSI, MACD, Moving Averages)
    - Market trends and volatility assessment
    - Trading signals and recommendations
    
    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        interval: Time interval for analysis (1h, 4h, 1d, etc.)
    """
    try:
        # Debug logging for interval
        logger.info(f"Predict endpoint called with interval: {interval}")
        
        # Validate interval
        if interval not in allowed_intervals:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval. Allowed values: {', '.join(allowed_intervals)}"
            )
            
        # Clear the cache to ensure fresh analysis
        predictor.analysis_cache.clear()
        logger.info(f"Cache cleared for fresh analysis with interval: {interval}")
            
        # Await the async call for OHLCV data
        ohlcv = await binance.fetch_ohlcv(symbol, interval, limit=100)
        closes = [entry["close"] for entry in ohlcv]
        
        if len(closes) < 50:
            raise HTTPException(
                status_code=422,
                detail="Need at least 50 data points for analysis"
            )
            
        # Await the async analyze_market call
        analysis = await predictor.analyze_market(closes, interval)
        
        # Force the interval in the response
        analysis["metadata"]["interval"] = interval
        analysis["metadata"]["symbol"] = symbol
        
        return analysis
        
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Analysis failed: " + str(e)
        )
