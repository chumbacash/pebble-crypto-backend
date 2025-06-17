"""
AI agent endpoints for natural language cryptocurrency queries
"""

from fastapi import APIRouter, HTTPException, Request, Body, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import logging

from app.core.dependencies import get_market_agent, get_allowed_intervals

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger("CryptoPredictAPI")

# Pydantic models for AI query endpoint
class CryptoQueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query about cryptocurrency markets")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional context to enhance the AI response")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "What is the current price of Bitcoin and should I buy it now?",
                "context": {"preferred_timeframe": "1d", "risk_tolerance": "moderate"}
            }
        }

class CryptoQueryResponse(BaseModel):
    query: str = Field(..., description="The original query")
    response: str = Field(..., description="AI-generated response to the query")
    timestamp: str = Field(..., description="When the response was generated")
    supporting_data: Optional[Dict[str, Any]] = Field(default=None, description="Supporting data used to generate the response")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata about the query processing")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "What is the current price of Bitcoin and should I buy it now?",
                "response": "Bitcoin (BTCUSDT) is currently trading at $50,123.45, up 2.3% in the last 24 hours. Technical indicators show a bullish trend with RSI at 58. Based on current volatility and market conditions, consider dollar-cost averaging rather than a single large purchase. Always do your own research and consider your risk tolerance before investing.",
                "timestamp": "2024-10-08T12:34:56.789Z",
                "supporting_data": {
                    "current_price": 50123.45,
                    "price_change_24h": 0.023,
                    "rsi": 58
                },
                "metadata": {
                    "symbol": "BTCUSDT",
                    "interval": "1d",
                    "data_sources": ["price_data", "technical_indicators", "ai_insights"]
                }
            }
        }

@router.post("/ask", response_model=CryptoQueryResponse, tags=["AI Assistant"])
@limiter.limit("60/minute")
async def process_crypto_query(
    request: Request,
    query_request: CryptoQueryRequest = Body(...),
    market_agent = Depends(get_market_agent),
    allowed_intervals: list = Depends(get_allowed_intervals)
):
    """
    Process a natural language query about cryptocurrency markets and return an AI-powered response.
    
    This endpoint can handle a wide variety of questions including but not limited to:
    - Price information (e.g., "What's the current price of ETH?")
    - Trend analysis (e.g., "What's the trend for Solana?")
    - Volatility assessment (e.g., "How volatile is LINK today?")
    - Investment advice (e.g., "Should I buy SOL now?")
    - Technical indicators (e.g., "What does the RSI say about Bitcoin?")
    - Market comparison (e.g., "How is ADA performing compared to DOT?")
    
    The AI will analyze relevant data sources and provide a comprehensive response with supporting information.
    """
    try:
        # Extract query and context
        query = query_request.query
        context = query_request.context or {}
        
        # Log the incoming query
        logger.info(f"Processing query: {query}")
        
        # Process query through the market agent
        result = await market_agent.process_query(query)
        
        # Apply any context-specific adjustments to the response
        if context:
            result = await _enhance_with_context(result, context, allowed_intervals)
        
        # Extract supporting data with multi-timeframe insights
        supporting_data = result.get("supporting_data", {})
        
        # Add multi-timeframe data if available
        if "multi_timeframe" in result:
            # Only include essential data from multi-timeframe analysis
            multi_tf_insights = {}
            for tf, tf_data in result.get("multi_timeframe", {}).items():
                if "trend" in tf_data:
                    multi_tf_insights[tf] = {
                        "trend": tf_data["trend"].get("description", "NEUTRAL"),
                        "rsi": tf_data.get("indicators", {}).get("rsi", 50),
                        "volatility": tf_data.get("volatility")
                    }
            
            # Add to supporting data if we have insights
            if multi_tf_insights:
                supporting_data["timeframe_analysis"] = multi_tf_insights
        
        # Return the structured response
        return CryptoQueryResponse(
            query=result["query"],
            response=result["response"],
            timestamp=result["timestamp"],
            supporting_data=supporting_data,
            metadata=result.get("metadata")
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process query: {str(e)}"
        )

async def _enhance_with_context(result: Dict[str, Any], context: Dict[str, Any], allowed_intervals: list) -> Dict[str, Any]:
    """Apply context-specific adjustments to the AI response"""
    # Handle preferred timeframe if provided
    if "preferred_timeframe" in context and result.get("metadata", {}).get("symbol"):
        symbol = result["metadata"]["symbol"]
        timeframe = context["preferred_timeframe"]
        
        # Map common timeframe formats to API intervals
        timeframe_map = {
            "short": "1h",
            "medium": "4h",
            "long": "1d",
            "very_long": "1w"
        }
        interval = timeframe_map.get(timeframe, timeframe)
        
        # Only adjust if the interval is valid
        if interval in allowed_intervals:
            # Add timeframe-specific context to the response
            if "I've analyzed" not in result["response"]:
                result["response"] = f"I've analyzed {symbol} using {interval} timeframe data. {result['response']}"
    
    # Handle risk tolerance if provided
    if "risk_tolerance" in context:
        risk_tolerance = context["risk_tolerance"].lower()
        if "advice" in result.get("metadata", {}).get("intent", ""):
            # Add risk tolerance context if it's an advice-seeking query
            if risk_tolerance == "high":
                result["response"] += "\n\nNote: Based on your high risk tolerance, you might consider more aggressive entry/exit points than suggested above."
            elif risk_tolerance == "low":
                result["response"] += "\n\nNote: Given your low risk tolerance, consider using tighter stop losses and taking smaller positions than suggested above."
    
    return result

# Legacy endpoint support (the old simple ask endpoint)
@router.post("/ask-simple", tags=["AI Agent"])
@limiter.limit("10/minute")
async def ask_agent(
    request: Request, 
    query: Dict[str, str] = Body(...),
    market_agent = Depends(get_market_agent)
):
    """
    Simple AI agent endpoint for backward compatibility.
    
    Examples:
    - "What is the current price of BTC?"
    - "What is the trend for Ethereum?"
    - "Should I buy SOL now?"
    - "How volatile is LINK today?"
    
    Request body should contain a "question" field with the natural language query.
    """
    try:
        if "question" not in query or not query["question"].strip():
            raise HTTPException(status_code=400, detail="Question is required")
            
        # Process the query
        response = await market_agent.process_query(query["question"])
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

# Multi-exchange endpoints have been moved to app/api/routes/multi_exchange.py
