"""
Shared dependencies for FastAPI application
Provides dependency injection for common services and clients
"""

import os
import logging
from functools import lru_cache
from typing import Dict, Any

from app.services.binance import BinanceClient
from app.services.metrics import MetricsTracker
from app.core.ai.agent import MarketAgent
from app.core.analysis.market_advisor import MarketAdvisor, MarketComparisonAnalyzer
from app.core.prediction.technical import predictor

logger = logging.getLogger("CryptoPredictAPI")

# Initialize logger configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

@lru_cache()
def get_settings() -> Dict[str, Any]:
    """Get application settings from environment variables"""
    return {
        "binance_api": os.getenv("BINANCE_API", "https://api.binance.com/api/v3"),
        "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "cache_ttl": int(os.getenv("CACHE_TTL", "300")),
        "host": os.getenv("HOST", "0.0.0.0"),
        "port": int(os.getenv("PORT", 8000)),
        "allowed_origins": os.getenv("ALLOWED_ORIGINS", "*").split(","),
        "api_rate_limit": os.getenv("API_RATE_LIMIT", "100/hour"),
        "metrics_interval": int(os.getenv("METRICS_INTERVAL", "300"))
    }

@lru_cache()
def get_binance_client() -> BinanceClient:
    """Get singleton Binance client instance"""
    return BinanceClient()

@lru_cache()
def get_metrics_tracker() -> MetricsTracker:
    """Get singleton metrics tracker instance"""
    return MetricsTracker()

@lru_cache()
def get_market_agent() -> MarketAgent:
    """Get singleton market agent instance"""
    return MarketAgent()

@lru_cache()
def get_market_advisor() -> MarketAdvisor:
    """Get singleton market advisor instance"""
    return MarketAdvisor()

@lru_cache()
def get_market_comparison_analyzer() -> MarketComparisonAnalyzer:
    """Get singleton market comparison analyzer instance"""
    binance_client = get_binance_client()
    return MarketComparisonAnalyzer(binance_client=binance_client)

@lru_cache()
def get_predictor():
    """Get singleton technical predictor instance"""
    return predictor

def get_allowed_intervals() -> list:
    """Get list of allowed trading intervals"""
    return ["1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]

def get_interval_hours() -> Dict[str, int]:
    """Get mapping of intervals to hours"""
    return {
        "1h": 1, "2h": 2, "4h": 4, "6h": 6, "8h": 8, "12h": 12, 
        "1d": 24, "3d": 72, "1w": 168, "1M": 720
    } 