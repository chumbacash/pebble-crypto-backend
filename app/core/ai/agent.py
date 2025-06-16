# AI agent orchestration module

import logging
from typing import Dict, List, Any, Optional, Union
import json
import re
from datetime import datetime, timezone
import asyncio
import numpy as np
import math

from app.core.ai.gemini_client import GeminiInsightsGenerator
from app.core.ai.llm_symbol_extractor import LLMSymbolExtractor
from app.services.binance import BinanceClient
from app.services.kucoin import KuCoinClient
from app.services.bybit import BybitClient
from app.services.gateio import GateIOClient
from app.services.bitget import BitgetClient
from app.services.okx import OKXClient
from app.services.exchange_aggregator import ExchangeAggregator
from app.core.indicators.advanced import BollingerBands, AverageTrueRange
from app.core.indicators.order_book import OrderBookDepthAnalyzer
from app.core.prediction.technical import predictor
from app.core.analysis.market_advisor import MarketAdvisor
from app.core.ai.multi_llm_router import MultiLLMRouter

logger = logging.getLogger("CryptoPredictAPI")

class MarketAgent:
    """
    AI-powered agent that orchestrates data collection, analysis, and natural language
    responses for cryptocurrency market questions.
    Enhanced with multi-exchange support for comprehensive market coverage.
    """
    
    def __init__(self):
        """Initialize the market agent with multi-exchange capabilities and multi-LLM routing"""
        # Initialize Multi-LLM Router for intelligent query distribution
        self.llm_router = MultiLLMRouter()
        
        # Initialize AI insights generator (optional)
        try:
            self.gemini = GeminiInsightsGenerator()
            self.gemini_available = True
            # Register Gemini with the LLM router
            self.llm_router.register_provider("gemini", self.gemini)
        except Exception as e:
            logger.warning(f"Gemini AI not available: {str(e)}")
            self.gemini = None
            self.gemini_available = False
        
        # Initialize LLM symbol extractor
        self.llm_extractor = LLMSymbolExtractor()
        
        # Try to register additional LLM providers
        self._setup_additional_llm_providers()
        
        # Initialize exchange clients
        self.binance = BinanceClient()
        self.kucoin = KuCoinClient()
        self.bybit = BybitClient()
        self.gateio = GateIOClient()
        self.bitget = BitgetClient()
        self.okx = OKXClient()
        
        # Initialize exchange aggregator
        self.exchange_aggregator = ExchangeAggregator()
        
        # Register all exchanges with the aggregator
        self._register_exchanges()
        
        # Initialize indicators and analyzers
        self.bb_indicator = BollingerBands()
        self.atr_indicator = AverageTrueRange()
        self.order_book_analyzer = OrderBookDepthAnalyzer()
        self.market_advisor = MarketAdvisor()
        
        self.valid_symbols = []
        self.last_symbols_update = None
        
        # Initialize valid symbols asynchronously
        # Initialize valid symbols (will be updated in background)
        self.valid_symbols = set()
        
        # Start background tasks if event loop is running
        try:
            asyncio.create_task(self._update_valid_symbols())
        except RuntimeError:
            # No event loop running, will update symbols on first query
            pass
        
    def _setup_additional_llm_providers(self):
        """Setup additional LLM providers if available"""
        try:
            # Try to initialize OpenRouter (if credentials available)
            from app.services.openrouter_client import OpenRouterClient
            openrouter = OpenRouterClient()
            if openrouter.is_available():
                self.llm_router.register_provider("openrouter", openrouter)
                logger.info("OpenRouter LLM provider registered")
        except Exception as e:
            logger.debug(f"OpenRouter not available: {str(e)}")
        
        try:
            # Try to initialize Anthropic (if credentials available)
            from app.services.anthropic_client import AnthropicClient
            anthropic = AnthropicClient()
            if anthropic.is_available():
                self.llm_router.register_provider("anthropic", anthropic)
                logger.info("Anthropic LLM provider registered")
        except Exception as e:
            logger.debug(f"Anthropic not available: {str(e)}")
        
    def _register_exchanges(self):
        """Register all exchange clients with the aggregator"""
        try:
            self.exchange_aggregator.register_exchange("binance", self.binance)
            self.exchange_aggregator.register_exchange("kucoin", self.kucoin)
            self.exchange_aggregator.register_exchange("bybit", self.bybit)
            self.exchange_aggregator.register_exchange("gateio", self.gateio)
            self.exchange_aggregator.register_exchange("bitget", self.bitget)
            self.exchange_aggregator.register_exchange("okx", self.okx)
            logger.info("Successfully registered all exchanges with aggregator")
        except Exception as e:
            logger.error(f"Error registering exchanges: {str(e)}")
        
    def _sanitize_nan_values(self, data):
        """Replace NaN values with None for JSON serialization"""
        if isinstance(data, dict):
            return {k: self._sanitize_nan_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_nan_values(item) for item in data]
        elif isinstance(data, float) and (np.isnan(data) or np.isinf(data)):
            return None
        elif isinstance(data, np.ndarray):
            return self._sanitize_nan_values(data.tolist())
        elif isinstance(data, np.integer):
            return int(data)
        elif isinstance(data, np.floating):
            return None if math.isnan(float(data)) or math.isinf(float(data)) else float(data)
        else:
            return data
        
    async def _update_valid_symbols(self):
        """Update the list of valid trading symbols"""
        try:
            self.valid_symbols = await self.binance.fetch_symbols_async()
            self.last_symbols_update = datetime.now(timezone.utc)
            logger.info(f"Updated valid symbols: {len(self.valid_symbols)} symbols loaded")
        except Exception as e:
            logger.error(f"Failed to update valid symbols: {str(e)}")
            # Fallback to common symbols
            self.valid_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT"]
        
    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Enhanced query processing implementing Anthropic's effective agent patterns:
        
        🎯 ROUTING: Smart query classification and complexity assessment
        ⚡ PARALLELIZATION: Multi-asset data collection with sectioning
        🔍 TRANSPARENCY: Explicit reasoning steps and confidence scoring
        📊 EVALUATOR: Response quality assessment and optimization
        
        Based on: https://www.anthropic.com/engineering/building-effective-agents
        """
        try:
            # Ensure we have valid symbols
            if not self.valid_symbols:
                try:
                    self.valid_symbols = await asyncio.to_thread(self.binance.fetch_symbols)
                    logger.info(f"Initialized valid symbols list with {len(self.valid_symbols)} symbols")
                except Exception as e:
                    logger.warning(f"Could not fetch symbols: {e}. Using fallback major symbols.")
                    # Add default major symbols as fallback
                    self.valid_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT"]
            
            # 1. Extract query information using LLM-powered extraction
            query_info = await self.llm_extractor.extract_query_info(query, self.valid_symbols)
            
            # 2. Identify required data sources
            data_sources = self._determine_data_sources(query_info)
            
            # 3. Collect data
            data = await self._collect_data(query_info, data_sources)
            
            # Store the symbol for response formatting
            data["symbol"] = query_info.get("primary_symbol")
            
            # 4. Generate a response
            response = await self._generate_response(query, query_info, data)
            
            # 5. Filter data for supporting info
            supporting_data = self._filter_supporting_data(data)
            
            # 6. Get the multi-timeframe data for additional context and remove OHLCV to reduce size
            multi_timeframe = data.get("multi_timeframe", {})
            filtered_multi_timeframe = {}
            
            # Create a filtered version of multi_timeframe data without the OHLCV arrays
            for tf, tf_data in multi_timeframe.items():
                filtered_tf_data = tf_data.copy()
                # Remove OHLCV data (which is the largest part)
                if "ohlcv" in filtered_tf_data:
                    del filtered_tf_data["ohlcv"]
                filtered_multi_timeframe[tf] = filtered_tf_data
            
            # 7. Format & return the result
            result = {
                "query": query,
                "response": response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "supporting_data": supporting_data,
                "metadata": {
                    "symbol": query_info.get("primary_symbol"),
                    "interval": query_info.get("interval", "1h"),
                    "data_sources": data_sources
                }
            }
            
            # Add filtered multi-timeframe data if available
            if filtered_multi_timeframe:
                result["multi_timeframe"] = filtered_multi_timeframe
            
            # Sanitize data to remove NaN values before returning
            sanitized_result = self._sanitize_nan_values(result)
            
            return sanitized_result
            
        except Exception as e:
            logger.error(f"Query processing error: {str(e)}")
            # Return a graceful error response
            return {
                "query": query,
                "response": f"I'm sorry, I couldn't process that query: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "supporting_data": {},
                "metadata": {"error": str(e)}
            }
    
    # Note: _extract_query_info method removed - now using LLM-based extraction
    # via self.llm_extractor.extract_query_info() for much more intelligent
    # symbol detection and query understanding
    
    def _determine_data_sources(self, query_info: Dict[str, Any]) -> List[str]:
        """Determine which data sources are needed based on the query intent"""
        intent = query_info.get("intent", "general")
        
        # Default data source for all queries
        sources = ["price_data"]
        
        intent_to_source_map = {
            "price": ["price_data"],
            "trend": ["price_data", "technical_indicators"],
            "volatility": ["price_data", "technical_indicators", "atr"],
            "levels": ["price_data", "technical_indicators", "support_resistance"],
            "prediction": ["price_data", "technical_indicators", "prediction"],
            "volume": ["price_data", "volume_data"],
            "order_book": ["price_data", "order_book"],
            "indicators": ["price_data", "technical_indicators"],
            "analysis": ["price_data", "technical_indicators", "prediction", "ai_insights"],
            "advice": ["price_data", "technical_indicators", "prediction", "ai_insights"],
            "general": ["price_data", "technical_indicators", "ai_insights"]
        }
        
        return intent_to_source_map.get(intent, sources)
    
    async def _collect_data(self, query_info: Dict[str, Any], 
                           data_sources: List[str]) -> Dict[str, Any]:
        """Collect data from various sources based on the query requirements"""
        symbols = query_info.get("symbols", [])
        primary_symbol = query_info.get("primary_symbol")
        interval = query_info.get("interval", "1h")
        query_type = query_info.get("query_type", "single_asset")
        
        # Return empty data if no symbols are specified
        if not symbols:
            return {"error": "No cryptocurrency symbol detected in the query"}
        
        data = {
            "symbols": symbols,
            "primary_symbol": primary_symbol,
            "interval": interval,
            "query_type": query_type
        }
        
        try:
            # Route to appropriate collection method based on query type
            if query_type == "single_asset":
                return await self._collect_single_asset_data(primary_symbol, interval, data_sources, data)
            elif query_type == "multi_asset":
                return await self._collect_multi_asset_data(symbols, interval, data_sources, data)
            elif query_type == "comparison":
                return await self._collect_comparison_data(symbols, interval, data_sources, data)
            elif query_type == "portfolio":
                return await self._collect_portfolio_data(symbols, interval, data_sources, data)
            else:
                # Default to single asset
                return await self._collect_single_asset_data(primary_symbol, interval, data_sources, data)
                
        except Exception as e:
            logger.error(f"Data collection error: {str(e)}")
            return {"error": f"Failed to collect data: {str(e)}"}
    
    async def _collect_single_asset_data(self, symbol: str, interval: str, 
                                       data_sources: List[str], base_data: Dict[str, Any]) -> Dict[str, Any]:
        """Collect data for a single asset using multi-exchange aggregator"""
        data = base_data.copy()
        
        try:
            # Get market data from exchange aggregator first
            market_data = await self.exchange_aggregator.get_market_data(
                symbol, 
                preferred_exchanges=["binance", "kucoin", "bybit"],
                fallback_enabled=True
            )
            
            if market_data:
                data["exchange_used"] = market_data.exchange
                data["current_price"] = market_data.current_price
                
                # Try to get arbitrage data across exchanges
                try:
                    arbitrage_data = await self.exchange_aggregator.find_best_price(symbol)
                    if arbitrage_data:
                        data["arbitrage"] = arbitrage_data
                except Exception as e:
                    logger.debug(f"Could not get arbitrage data for {symbol}: {str(e)}")
            
            # Collect price data from multiple timeframes for better insights
            timeframes = ["1h", "4h", "1d", "1w"]
            multi_timeframe_data = {}
            
            for tf in timeframes:
                try:
                    # Try to fetch OHLCV data from primary exchange first, then fallback
                    ohlcv = None
                    for exchange_name in ["binance", "kucoin", "bybit", "gateio"]:
                        try:
                            exchange_client = getattr(self, exchange_name)
                            ohlcv = await exchange_client.fetch_ohlcv(symbol, tf, limit=100)
                            if ohlcv:
                                break
                        except Exception as e:
                            logger.debug(f"Failed to get {tf} data from {exchange_name}: {str(e)}")
                            continue
                    if ohlcv:
                        # Calculate basic metrics for this timeframe
                        closes = [entry["close"] for entry in ohlcv]
                        highs = [entry["high"] for entry in ohlcv]
                        lows = [entry["low"] for entry in ohlcv]
                        volumes = [entry["volume"] for entry in ohlcv]
                        
                        # Store data for this timeframe
                        multi_timeframe_data[tf] = {
                            "ohlcv": ohlcv,
                            "current_price": closes[-1],
                            "price_change": (closes[-1] - closes[0]) / closes[0] 
                                           if len(closes) > 0 else None,
                            "high": max(highs) if highs else None,
                            "low": min(lows) if lows else None,
                            "volume_avg": sum(volumes) / len(volumes) if volumes else None,
                            "volatility": np.std(np.diff(closes) / closes[:-1]) * 100 
                                         if len(closes) > 1 else None,
                        }
                        
                        # Calculate technical indicators for this timeframe
                        if "technical_indicators" in data_sources:
                            try:
                                # Calculate and store indicators
                                bb_data = self.bb_indicator.calculate(closes)
                                bb_signal = self.bb_indicator.get_signal(closes)
                                
                                # Calculate RSI
                                try:
                                    # Here we're calculating RSI for this specific timeframe
                                    rsi_values = []
                                    for i in range(1, len(closes)):
                                        diff = closes[i] - closes[i-1]
                                        if diff > 0:
                                            rsi_values.append((diff, 0))
                                        else:
                                            rsi_values.append((0, abs(diff)))
                                    
                                    if rsi_values:
                                        avg_gain = sum(gain for gain, _ in rsi_values) / len(rsi_values)
                                        avg_loss = sum(loss for _, loss in rsi_values) / len(rsi_values)
                                        
                                        if avg_loss == 0:
                                            rsi = 100
                                        else:
                                            rs = avg_gain / avg_loss
                                            rsi = 100 - (100 / (1 + rs))
                                    else:
                                        rsi = 50  # neutral
                                except Exception:
                                    rsi = 50  # fallback
                                
                                # Calculate SMAs
                                sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else closes[-1]
                                sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else closes[-1]
                                
                                # Store indicators
                                multi_timeframe_data[tf]["indicators"] = {
                                    "rsi": rsi,
                                    "sma_20": sma_20,
                                    "sma_50": sma_50,
                                    "sma_20_diff": ((closes[-1] - sma_20) / sma_20) * 100,
                                    "sma_50_diff": ((closes[-1] - sma_50) / sma_50) * 100,
                                    "bb_upper": bb_data.get("upper", closes[-1] * 1.02),
                                    "bb_lower": bb_data.get("lower", closes[-1] * 0.98),
                                    "bb_signal": bb_signal
                                }
                                
                                # Determine trend
                                if sma_20 > sma_50:
                                    trend_direction = "BULLISH"
                                    if (sma_20 - sma_50) / sma_50 > 0.05:
                                        trend_desc = "STRONG BULLISH"
                                    else:
                                        trend_desc = "MODERATE BULLISH"
                                else:
                                    trend_direction = "BEARISH"
                                    if (sma_50 - sma_20) / sma_20 > 0.05:
                                        trend_desc = "STRONG BEARISH"
                                    else:
                                        trend_desc = "MODERATE BEARISH"
                                
                                multi_timeframe_data[tf]["trend"] = {
                                    "direction": trend_direction,
                                    "description": trend_desc
                                }
                                
                            except Exception as e:
                                logger.error(f"Technical indicators error for {tf}: {str(e)}")
                                continue
                        
                except Exception as e:
                    logger.error(f"Error fetching {tf} data for {symbol}: {str(e)}")
                    continue
            
            # Store multi-timeframe data
            data["multi_timeframe"] = multi_timeframe_data
            
            # Create primary timeframe data for backward compatibility
            if interval in multi_timeframe_data:
                primary_data = multi_timeframe_data[interval]
                data["price_data"] = {
                    "current_price": primary_data["current_price"],
                    "price_change_24h": primary_data.get("price_change"),
                    "high_24h": primary_data["high"],
                    "low_24h": primary_data["low"],
                    "volume": primary_data["volume_avg"]
                }
                
                if "indicators" in primary_data:
                    data["technical_indicators"] = primary_data["indicators"]
            
            # Add ATR data if requested
            if "atr" in data_sources and interval in multi_timeframe_data:
                primary_data = multi_timeframe_data[interval]
                closes = [entry["close"] for entry in primary_data["ohlcv"]]
                highs = [entry["high"] for entry in primary_data["ohlcv"]]
                lows = [entry["low"] for entry in primary_data["ohlcv"]]
                
                atr_data = self.atr_indicator.calculate(highs, lows, closes)
                data["atr"] = atr_data
            
            return data
            
        except Exception as e:
            logger.error(f"Single asset data collection error for {symbol}: {str(e)}")
            return {"error": f"Failed to collect data for {symbol}: {str(e)}"}
    
    async def _collect_multi_asset_data(self, symbols: List[str], interval: str, 
                                      data_sources: List[str], base_data: Dict[str, Any]) -> Dict[str, Any]:
        """Collect data for multiple assets in parallel using exchange aggregator"""
        data = base_data.copy()
        
        try:
            # Use exchange aggregator's parallel multi-asset capability
            multi_asset_data = await self.exchange_aggregator.get_multi_asset_data(
                symbols, 
                strategy="parallel"
            )
            
            # Also collect detailed data for each asset in parallel
            tasks = []
            for symbol in symbols:
                task = self._collect_single_asset_data(symbol, interval, data_sources, {"symbol": symbol})
                tasks.append(task)
            
            # Execute all data collection tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            assets_data = {}
            successful_symbols = []
            
            for i, result in enumerate(results):
                symbol = symbols[i]
                if isinstance(result, Exception):
                    logger.error(f"Error collecting data for {symbol}: {str(result)}")
                    assets_data[symbol] = {"error": str(result)}
                elif isinstance(result, dict) and "error" not in result:
                    assets_data[symbol] = result
                    successful_symbols.append(symbol)
                else:
                    assets_data[symbol] = result
            
            data["assets"] = assets_data
            data["successful_symbols"] = successful_symbols
            
            # Create aggregated view for multi-asset analysis
            if successful_symbols:
                # Calculate portfolio-level metrics
                total_volume = 0
                portfolio_volatility = []
                
                for symbol in successful_symbols:
                    asset_data = assets_data[symbol]
                    if "price_data" in asset_data:
                        price_data = asset_data["price_data"]
                        total_volume += price_data.get("volume", 0)
                        
                        # Collect volatility data
                        if interval in asset_data.get("multi_timeframe", {}):
                            tf_data = asset_data["multi_timeframe"][interval]
                            volatility = tf_data.get("volatility")
                            if volatility:
                                portfolio_volatility.append(volatility)
                
                data["portfolio_metrics"] = {
                    "total_volume": total_volume,
                    "avg_volatility": sum(portfolio_volatility) / len(portfolio_volatility) if portfolio_volatility else 0,
                    "num_assets": len(successful_symbols)
                }
            
            return data
            
        except Exception as e:
            logger.error(f"Multi-asset data collection error: {str(e)}")
            return {"error": f"Failed to collect multi-asset data: {str(e)}"}
    
    async def _collect_comparison_data(self, symbols: List[str], interval: str, 
                                     data_sources: List[str], base_data: Dict[str, Any]) -> Dict[str, Any]:
        """Collect data optimized for comparison analysis"""
        # Use multi-asset collection as base
        data = await self._collect_multi_asset_data(symbols, interval, data_sources, base_data)
        
        # Add comparison-specific metrics
        if "assets" in data and len(data.get("successful_symbols", [])) > 1:
            comparison_metrics = {}
            successful_symbols = data["successful_symbols"]
            
            # Performance comparison
            performance_data = {}
            for symbol in successful_symbols:
                asset_data = data["assets"][symbol]
                if "price_data" in asset_data:
                    price_change = asset_data["price_data"].get("price_change_24h", 0)
                    performance_data[symbol] = price_change
            
            # Sort by performance
            sorted_performance = sorted(performance_data.items(), key=lambda x: x[1] or 0, reverse=True)
            
            comparison_metrics["performance_ranking"] = sorted_performance
            comparison_metrics["best_performer"] = sorted_performance[0] if sorted_performance else None
            comparison_metrics["worst_performer"] = sorted_performance[-1] if sorted_performance else None
            
            data["comparison_metrics"] = comparison_metrics
        
        return data
    
    async def _collect_portfolio_data(self, symbols: List[str], interval: str, 
                                    data_sources: List[str], base_data: Dict[str, Any]) -> Dict[str, Any]:
        """Collect data optimized for portfolio analysis"""
        # Use multi-asset collection as base
        data = await self._collect_multi_asset_data(symbols, interval, data_sources, base_data)
        
        # Add portfolio-specific analysis
        if "assets" in data and len(data.get("successful_symbols", [])) > 1:
            portfolio_analysis = {}
            successful_symbols = data["successful_symbols"]
            
            # Correlation analysis (simplified)
            correlations = {}
            price_series = {}
            
            # Collect price series for correlation
            for symbol in successful_symbols:
                asset_data = data["assets"][symbol]
                if interval in asset_data.get("multi_timeframe", {}):
                    tf_data = asset_data["multi_timeframe"][interval]
                    closes = [entry["close"] for entry in tf_data.get("ohlcv", [])]
                    if len(closes) > 10:  # Need sufficient data
                        price_series[symbol] = closes
            
            # Calculate simple correlation (if we have multiple assets with sufficient data)
            if len(price_series) >= 2:
                symbols_list = list(price_series.keys())
                for i, symbol1 in enumerate(symbols_list):
                    for symbol2 in symbols_list[i+1:]:
                        try:
                            # Simple correlation calculation
                            series1 = np.array(price_series[symbol1])
                            series2 = np.array(price_series[symbol2])
                            
                            # Ensure same length
                            min_len = min(len(series1), len(series2))
                            series1 = series1[-min_len:]
                            series2 = series2[-min_len:]
                            
                            correlation = np.corrcoef(series1, series2)[0, 1]
                            correlations[f"{symbol1}_vs_{symbol2}"] = correlation
                        except Exception as e:
                            logger.error(f"Correlation calculation error: {str(e)}")
                            continue
            
            portfolio_analysis["correlations"] = correlations
            portfolio_analysis["diversification_score"] = self._calculate_diversification_score(correlations)
            
            data["portfolio_analysis"] = portfolio_analysis
        
        return data
    
    def _calculate_diversification_score(self, correlations: Dict[str, float]) -> float:
        """Calculate a simple diversification score based on correlations"""
        if not correlations:
            return 0.5  # neutral score
        
        # Lower average correlation = better diversification
        avg_correlation = sum(abs(corr) for corr in correlations.values()) / len(correlations)
        
        # Convert to 0-1 score (lower correlation = higher score)
        diversification_score = max(0, 1 - avg_correlation)
        
        return diversification_score
    
    async def _generate_response(self, query: str, query_info: Dict[str, Any], 
                                data: Dict[str, Any]) -> str:
        """Generate a natural language response to the query based on collected data"""
        # Check for errors
        if "error" in data:
            return f"Sorry, I couldn't answer that. {data['error']}"
            
        # Handle no symbol case
        if not query_info.get("primary_symbol"):
            # Suggest some popular symbols when no crypto is detected
            return "I need a specific cryptocurrency symbol to answer this question. Try asking about popular cryptocurrencies like BTC, ETH, SOL, BNB, XRP, ADA, or DOGE."
        
        query_type = query_info.get("query_type", "single_asset")
        
        # Route to appropriate response generator
        if query_type == "single_asset":
            return await self._generate_single_asset_response(query, query_info, data)
        elif query_type == "multi_asset":
            return await self._generate_multi_asset_response(query, query_info, data)
        elif query_type == "comparison":
            return await self._generate_comparison_response(query, query_info, data)
        elif query_type == "portfolio":
            return await self._generate_portfolio_response(query, query_info, data)
        else:
            return await self._generate_single_asset_response(query, query_info, data)
    
    async def _generate_single_asset_response(self, query: str, query_info: Dict[str, Any], 
                                            data: Dict[str, Any]) -> str:
        """Generate response for single asset queries"""
        symbol = query_info.get("primary_symbol", "")
        intent = query_info.get("intent", "general")
        
        # Extract key data points
        price_data = data.get("price_data", {})
        current_price = price_data.get("current_price")
        price_change = price_data.get("price_change_24h")
        
        if not current_price:
            return f"I couldn't retrieve current price data for {symbol}. Please try again later."
        
        # Build response based on intent
        response_parts = []
        
        # Price information
        if intent in ["price", "general"]:
            change_text = ""
            if price_change is not None:
                change_pct = price_change * 100
                direction = "up" if change_pct > 0 else "down"
                change_text = f" (${change_pct:.2f}% {direction} in the last period)"
            
            response_parts.append(f"{symbol} is currently trading at ${current_price:.4f}{change_text}.")
        
        # Technical analysis
        if intent in ["trend", "analysis", "indicators"] and "technical_indicators" in data:
            indicators = data["technical_indicators"]
            rsi = indicators.get("rsi")
            sma_20_diff = indicators.get("sma_20_diff")
            
            if rsi:
                if rsi > 70:
                    rsi_signal = "overbought"
                elif rsi < 30:
                    rsi_signal = "oversold"
                else:
                    rsi_signal = "neutral"
                
                response_parts.append(f"The RSI is {rsi:.1f}, indicating {rsi_signal} conditions.")
            
            if sma_20_diff:
                if sma_20_diff > 2:
                    trend_signal = "strong upward trend"
                elif sma_20_diff < -2:
                    trend_signal = "strong downward trend"
                else:
                    trend_signal = "sideways movement"
                
                response_parts.append(f"Price is showing {trend_signal} relative to the 20-period moving average.")
        
        # Volatility analysis
        if intent == "volatility" and "multi_timeframe" in data:
            interval = query_info.get("interval", "1h")
            if interval in data["multi_timeframe"]:
                volatility = data["multi_timeframe"][interval].get("volatility")
                if volatility:
                    if volatility > 5:
                        vol_desc = "high volatility"
                    elif volatility < 2:
                        vol_desc = "low volatility"
                    else:
                        vol_desc = "moderate volatility"
                    
                    response_parts.append(f"{symbol} is experiencing {vol_desc} with a volatility of {volatility:.2f}%.")
        
        # Prediction/advice - Use Enhanced Investment Advisor
        if intent in ["prediction", "advice"]:
            try:
                from .enhanced_investment_advisor import EnhancedInvestmentAdvisor
                advisor = EnhancedInvestmentAdvisor()
                enhanced_advice = advisor.generate_investment_advice(query, data, query_info)
                response_parts.append(enhanced_advice)
            except Exception as e:
                logger.error(f"Enhanced investment advisor failed: {str(e)}")
                response_parts.append("Based on current technical indicators, please consider your risk tolerance and do your own research before making any trading decisions.")
        
        return " ".join(response_parts) if response_parts else f"Here's the current information for {symbol}: ${current_price:.4f}."
    
    async def _generate_multi_asset_response(self, query: str, query_info: Dict[str, Any], 
                                           data: Dict[str, Any]) -> str:
        """Generate response for multi-asset queries"""
        symbols = query_info.get("symbols", [])
        successful_symbols = data.get("successful_symbols", [])
        
        if not successful_symbols:
            return f"I couldn't retrieve data for the requested cryptocurrencies: {', '.join(symbols)}."
        
        response_parts = []
        response_parts.append(f"Here's the current information for {len(successful_symbols)} cryptocurrencies:")
        
        # Individual asset summaries
        assets_data = data.get("assets", {})
        for symbol in successful_symbols:
            asset_data = assets_data.get(symbol, {})
            price_data = asset_data.get("price_data", {})
            
            current_price = price_data.get("current_price")
            price_change = price_data.get("price_change_24h")
            
            if current_price:
                change_text = ""
                if price_change is not None:
                    change_pct = price_change * 100
                    direction = "↑" if change_pct > 0 else "↓"
                    change_text = f" ({direction}{abs(change_pct):.2f}%)"
                
                response_parts.append(f"• {symbol}: ${current_price:.4f}{change_text}")
        
        # Portfolio-level insights
        if "portfolio_metrics" in data:
            portfolio_metrics = data["portfolio_metrics"]
            avg_volatility = portfolio_metrics.get("avg_volatility", 0)
            
            if avg_volatility > 0:
                response_parts.append(f"\nPortfolio average volatility: {avg_volatility:.2f}%")
        
        return "\n".join(response_parts)
    
    async def _generate_comparison_response(self, query: str, query_info: Dict[str, Any], 
                                          data: Dict[str, Any]) -> str:
        """Generate response for comparison queries"""
        symbols = query_info.get("symbols", [])
        
        if "comparison_metrics" not in data:
            return await self._generate_multi_asset_response(query, query_info, data)
        
        comparison_metrics = data["comparison_metrics"]
        performance_ranking = comparison_metrics.get("performance_ranking", [])
        
        if not performance_ranking:
            return "I couldn't compare the performance of the requested cryptocurrencies."
        
        response_parts = []
        response_parts.append("Here's how these cryptocurrencies are performing:")
        
        for i, (symbol, performance) in enumerate(performance_ranking):
            if performance is not None:
                performance_pct = performance * 100
                direction = "↑" if performance_pct > 0 else "↓"
                rank_text = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
                
                response_parts.append(f"{rank_text} {symbol}: {direction}{abs(performance_pct):.2f}%")
        
        # Highlight best and worst performers
        best_performer = comparison_metrics.get("best_performer")
        worst_performer = comparison_metrics.get("worst_performer")
        
        if best_performer and worst_performer and len(performance_ranking) > 1:
            best_symbol, best_perf = best_performer
            worst_symbol, worst_perf = worst_performer
            
            if best_perf and worst_perf:
                response_parts.append(f"\n{best_symbol} is the top performer, while {worst_symbol} is lagging behind.")
        
        return "\n".join(response_parts)
    
    async def _generate_portfolio_response(self, query: str, query_info: Dict[str, Any], 
                                         data: Dict[str, Any]) -> str:
        """Generate response for portfolio-related queries"""
        # Start with multi-asset response
        base_response = await self._generate_multi_asset_response(query, query_info, data)
        
        if "portfolio_analysis" not in data:
            return base_response
        
        portfolio_analysis = data["portfolio_analysis"]
        diversification_score = portfolio_analysis.get("diversification_score", 0)
        correlations = portfolio_analysis.get("correlations", {})
        
        response_parts = [base_response]
        
        # Diversification insights
        if diversification_score > 0:
            if diversification_score > 0.7:
                div_desc = "well-diversified"
            elif diversification_score > 0.4:
                div_desc = "moderately diversified"
            else:
                div_desc = "highly correlated"
            
            response_parts.append(f"\nPortfolio Analysis: Your selection appears to be {div_desc} (diversification score: {diversification_score:.2f}).")
        
        # Correlation insights
        if correlations:
            high_correlations = [(pair, corr) for pair, corr in correlations.items() if abs(corr) > 0.7]
            if high_correlations:
                response_parts.append("Note: Some assets show high correlation, which may reduce diversification benefits.")
        
        return "\n".join(response_parts)
    
    def _filter_supporting_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter and prepare supporting data for the response"""
        filtered_data = {}
        
        # Include key metrics but exclude raw OHLCV data to reduce response size
        if "price_data" in data:
            filtered_data["price_data"] = data["price_data"]
        
        if "technical_indicators" in data:
            filtered_data["technical_indicators"] = data["technical_indicators"]
        
        if "portfolio_metrics" in data:
            filtered_data["portfolio_metrics"] = data["portfolio_metrics"]
        
        if "comparison_metrics" in data:
            filtered_data["comparison_metrics"] = data["comparison_metrics"]
        
        # Include summary of successful symbols
        if "successful_symbols" in data:
            filtered_data["successful_symbols"] = data["successful_symbols"]
        
        return filtered_data
    
    async def get_exchange_health(self) -> Dict[str, Any]:
        """Get health status of all registered exchanges"""
        try:
            health_data = await self.exchange_aggregator.get_exchange_health()
            return {
                "status": "success",
                "exchanges": health_data,
                "total_exchanges": len(health_data),
                "healthy_exchanges": len([e for e in health_data.values() if e.get("status") == "healthy"]),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting exchange health: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def find_best_prices(self, symbols: List[str]) -> Dict[str, Any]:
        """Find best prices across all exchanges for multiple symbols"""
        try:
            results = {}
            tasks = []
            
            for symbol in symbols:
                task = self.exchange_aggregator.find_best_price(symbol)
                tasks.append((symbol, task))
            
            # Execute all price comparison tasks in parallel
            price_results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            for i, result in enumerate(price_results):
                symbol = tasks[i][0]
                if isinstance(result, Exception):
                    results[symbol] = {"error": str(result)}
                else:
                    results[symbol] = result
            
            return {
                "status": "success",
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error finding best prices: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
