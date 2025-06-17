"""
Market advisor endpoints for trading recommendations and analysis
"""

from fastapi import APIRouter, HTTPException, Request, Body, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Dict, List, Optional
from datetime import datetime, timezone
import logging

from app.core.dependencies import (
    get_market_advisor, get_market_comparison_analyzer
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger("CryptoPredictAPI")

@router.post("/recommendations", tags=["Market Advisor"])
@limiter.limit("30/minute")
async def get_trading_recommendations(
    request: Request,
    symbols_request: Dict[str, List[str]] = Body(...),
    market_advisor = Depends(get_market_advisor)
):
    """
    Get comprehensive trading recommendations for multiple cryptocurrency symbols.
    
    Analyzes market conditions and provides actionable trading advice including:
    - Buy/Hold/Sell recommendations
    - Risk assessment
    - Entry and exit points
    - Position sizing suggestions
    
    Request body should contain a "symbols" field with trading symbols.
    Example: {"symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]}
    """
    try:
        if "symbols" not in symbols_request or not symbols_request["symbols"]:
            raise HTTPException(status_code=400, detail="Symbols list is required")
            
        if len(symbols_request["symbols"]) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 symbols allowed per request")
        
        # Get trading recommendations from market advisor
        recommendations = await market_advisor.get_trading_recommendations(symbols_request["symbols"])
        
        return {
            "recommendations": recommendations,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "symbols_analyzed": len(symbols_request["symbols"]),
            "disclaimer": "Trading recommendations are for informational purposes only. Always do your own research before making investment decisions."
        }
        
    except Exception as e:
        logger.error(f"Trading recommendations error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate trading recommendations: {str(e)}")

@router.post("/analysis/correlation", tags=["Market Advisor"])
@limiter.limit("20/minute")
async def analyze_correlation(
    request: Request,
    symbols_request: Dict[str, List[str]] = Body(...),
    market_analyzer = Depends(get_market_comparison_analyzer)
):
    """
    Analyze price correlations between multiple cryptocurrency symbols.
    
    Provides:
    - Correlation matrix between all symbol pairs
    - Statistical significance of correlations
    - Recommendations based on correlation patterns
    - Diversification insights
    
    Request body should contain a "symbols" field with trading symbols.
    Example: {"symbols": ["BTCUSDT", "ETHUSDT", "LINKUSDT", "ADAUSDT"]}
    """
    try:
        if "symbols" not in symbols_request or not symbols_request["symbols"]:
            raise HTTPException(status_code=400, detail="Symbols list is required")
            
        if len(symbols_request["symbols"]) < 2:
            raise HTTPException(status_code=400, detail="Minimum 2 symbols required for correlation analysis")
            
        if len(symbols_request["symbols"]) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 symbols allowed for correlation analysis")
        
        # Perform correlation analysis
        correlation_data = await market_analyzer.analyze_correlations(symbols_request["symbols"])
        
        return {
            "correlation_analysis": correlation_data,
            "symbols_analyzed": symbols_request["symbols"],
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "interpretation": {
                "high_correlation": "> 0.7 suggests similar price movements",
                "medium_correlation": "0.3 - 0.7 suggests moderate relationship",
                "low_correlation": "< 0.3 suggests little relationship",
                "negative_correlation": "< 0 suggests opposite price movements"
            }
        }
        
    except Exception as e:
        logger.error(f"Correlation analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze correlations: {str(e)}")

@router.post("/analysis/risk", tags=["Market Advisor"])
@limiter.limit("25/minute")
async def assess_portfolio_risk(
    request: Request,
    portfolio_request: Dict = Body(...),
    market_advisor = Depends(get_market_advisor)
):
    """
    Assess portfolio risk for a collection of cryptocurrency holdings.
    
    Analyzes:
    - Overall portfolio volatility
    - Risk/reward ratios
    - Diversification effectiveness
    - Value at Risk (VaR) calculations
    - Risk-adjusted performance metrics
    
    Request body format:
    {
        "portfolio": {
            "BTCUSDT": {"weight": 0.4, "amount": 1000},
            "ETHUSDT": {"weight": 0.3, "amount": 750},
            "SOLUSDT": {"weight": 0.3, "amount": 500}
        },
        "timeframe": "30d"
    }
    """
    try:
        if "portfolio" not in portfolio_request or not portfolio_request["portfolio"]:
            raise HTTPException(status_code=400, detail="Portfolio data is required")
            
        portfolio = portfolio_request["portfolio"]
        timeframe = portfolio_request.get("timeframe", "30d")
        
        # Validate portfolio format
        total_weight = sum(holding.get("weight", 0) for holding in portfolio.values())
        if abs(total_weight - 1.0) > 0.01:  # Allow small rounding errors
            raise HTTPException(status_code=400, detail="Portfolio weights must sum to 1.0")
        
        # Perform risk assessment
        risk_analysis = await market_advisor.assess_portfolio_risk(portfolio, timeframe)
        
        return {
            "risk_assessment": risk_analysis,
            "portfolio_summary": {
                "total_symbols": len(portfolio),
                "timeframe": timeframe,
                "total_weight": round(total_weight, 3)
            },
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "risk_levels": {
                "low": "< 15% volatility",
                "medium": "15-30% volatility", 
                "high": "30-50% volatility",
                "very_high": "> 50% volatility"
            }
        }
        
    except Exception as e:
        logger.error(f"Portfolio risk assessment error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to assess portfolio risk: {str(e)}")

@router.get("/market-overview", tags=["Market Advisor"])
@limiter.limit("15/minute")
async def get_market_overview(
    request: Request,
    top_n: int = 20,
    market_advisor = Depends(get_market_advisor)
):
    """
    Get a comprehensive overview of the cryptocurrency market.
    
    Provides:
    - Top N cryptocurrencies by market performance
    - Overall market sentiment indicators
    - Sector performance analysis
    - Key market trends and patterns
    - Trading volume analysis
    
    Parameters:
    - top_n: Number of top cryptocurrencies to include (default: 20, max: 50)
    """
    try:
        if top_n < 5 or top_n > 50:
            raise HTTPException(status_code=400, detail="top_n must be between 5 and 50")
        
        # Get market overview from advisor
        market_overview = await market_advisor.get_market_overview(top_n)
        
        return {
            "market_overview": market_overview,
            "analysis_parameters": {
                "top_symbols": top_n,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            },
            "market_insights": {
                "sentiment_indicators": "Fear & Greed Index, Social sentiment, News sentiment",
                "technical_indicators": "RSI, MACD, Moving averages across timeframes",
                "volume_analysis": "24h volume trends and breakdowns",
                "correlation_insights": "Cross-asset correlation patterns"
            }
        }
        
    except Exception as e:
        logger.error(f"Market overview error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get market overview: {str(e)}")

@router.post("/signals", tags=["Market Advisor"])
@limiter.limit("20/minute")
async def get_trading_signals(
    request: Request,
    signals_request: Dict = Body(...),
    market_advisor = Depends(get_market_advisor)
):
    """
    Generate trading signals for specified cryptocurrency symbols.
    
    Analyzes multiple indicators to provide:
    - Entry/exit signals
    - Signal strength and confidence
    - Stop-loss and take-profit recommendations
    - Multi-timeframe signal confirmation
    
    Request body format:
    {
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "timeframes": ["1h", "4h", "1d"],
        "signal_types": ["technical", "momentum", "volume"]
    }
    """
    try:
        if "symbols" not in signals_request or not signals_request["symbols"]:
            raise HTTPException(status_code=400, detail="Symbols list is required")
            
        symbols = signals_request["symbols"]
        timeframes = signals_request.get("timeframes", ["1h", "4h", "1d"])
        signal_types = signals_request.get("signal_types", ["technical", "momentum", "volume"])
        
        if len(symbols) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 symbols allowed for signal generation")
        
        # Generate trading signals
        trading_signals = await market_advisor.generate_trading_signals(
            symbols, timeframes, signal_types
        )
        
        return {
            "trading_signals": trading_signals,
            "analysis_parameters": {
                "symbols": symbols,
                "timeframes": timeframes,
                "signal_types": signal_types,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            },
            "signal_interpretation": {
                "strong_buy": "Multiple confirming signals across timeframes",
                "buy": "Positive signals with some confirmation",
                "hold": "Mixed or neutral signals",
                "sell": "Negative signals with some confirmation", 
                "strong_sell": "Multiple negative signals across timeframes"
            }
        }
        
    except Exception as e:
        logger.error(f"Trading signals error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate trading signals: {str(e)}") 