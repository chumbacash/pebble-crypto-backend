"""
Exchange Aggregator Service
Orchestrates data collection from multiple cryptocurrency exchanges
Following Anthropic's agent design patterns for reliability and performance
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("CryptoPredictAPI")

class ExchangeStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive" 
    ERROR = "error"
    MAINTENANCE = "maintenance"

@dataclass
class ExchangeConfig:
    """Configuration for each exchange"""
    name: str
    priority: int  # Lower number = higher priority
    rate_limit: int  # requests per minute
    timeout: int  # seconds
    retry_attempts: int
    status: ExchangeStatus = ExchangeStatus.ACTIVE

@dataclass
class MarketData:
    """Standardized market data structure"""
    symbol: str
    exchange: str
    timestamp: datetime
    current_price: float
    price_change_24h: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    volume_24h: Optional[float] = None
    market_cap: Optional[float] = None
    
class ExchangeAggregator:
    """
    Aggregates data from multiple cryptocurrency exchanges
    Implements failover, load balancing, and data validation
    """
    
    def __init__(self):
        self.exchanges = {}
        self.exchange_configs = {}
        self.last_health_check = {}
        self._initialize_exchange_configs()
    
    def _initialize_exchange_configs(self):
        """Initialize exchange configurations with priorities and limits"""
        self.exchange_configs = {
            "binance": ExchangeConfig(
                name="binance",
                priority=1,  # Highest priority
                rate_limit=1200,  # requests per minute
                timeout=5,
                retry_attempts=3
            ),
            "kucoin": ExchangeConfig(
                name="kucoin", 
                priority=2,
                rate_limit=100,
                timeout=10,
                retry_attempts=3
            ),
            "bybit": ExchangeConfig(
                name="bybit",
                priority=3,
                rate_limit=120,
                timeout=8,
                retry_attempts=3
            ),
            "gateio": ExchangeConfig(
                name="gateio",
                priority=4,
                rate_limit=200,
                timeout=10,
                retry_attempts=2
            ),
            "bitget": ExchangeConfig(
                name="bitget",
                priority=5,
                rate_limit=150,
                timeout=10,
                retry_attempts=2
            ),
            "okx": ExchangeConfig(
                name="okx",
                priority=6,
                rate_limit=300,  # OKX has good rate limits
                timeout=8,
                retry_attempts=3
            )
        }
    
    def register_exchange(self, name: str, exchange_client):
        """Register an exchange client with the aggregator"""
        if name in self.exchange_configs:
            self.exchanges[name] = exchange_client
            logger.info(f"Registered exchange: {name}")
        else:
            logger.warning(f"Unknown exchange configuration: {name}")
    
    async def get_market_data(self, symbol: str, 
                            preferred_exchanges: Optional[List[str]] = None,
                            fallback_enabled: bool = True) -> Optional[MarketData]:
        """
        Get market data for a symbol with intelligent exchange selection
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            preferred_exchanges: List of preferred exchanges to try first
            fallback_enabled: Whether to fallback to other exchanges on failure
        """
        
        # Determine exchange priority order
        exchange_order = self._get_exchange_priority_order(preferred_exchanges)
        
        # Try exchanges in priority order
        for exchange_name in exchange_order:
            if exchange_name not in self.exchanges:
                continue
                
            config = self.exchange_configs[exchange_name]
            if config.status != ExchangeStatus.ACTIVE:
                continue
            
            try:
                # Attempt to get data from this exchange
                data = await self._fetch_from_exchange(exchange_name, symbol)
                if data:
                    logger.debug(f"Successfully retrieved {symbol} data from {exchange_name}")
                    return data
                    
            except Exception as e:
                logger.warning(f"Failed to get {symbol} from {exchange_name}: {str(e)}")
                
                # Update exchange status if needed
                await self._handle_exchange_error(exchange_name, e)
                
                if not fallback_enabled:
                    break
                    
                continue
        
        logger.error(f"Failed to retrieve {symbol} data from all available exchanges")
        return None
    
    async def get_multi_asset_data(self, symbols: List[str],
                                 strategy: str = "parallel") -> Dict[str, MarketData]:
        """
        Get data for multiple assets using different strategies
        
        Args:
            symbols: List of trading symbols
            strategy: "parallel" (all at once) or "sequential" (one by one)
        """
        
        if strategy == "parallel":
            return await self._get_multi_asset_parallel(symbols)
        else:
            return await self._get_multi_asset_sequential(symbols)
    
    async def _get_multi_asset_parallel(self, symbols: List[str]) -> Dict[str, MarketData]:
        """Get multiple assets in parallel for maximum speed"""
        tasks = []
        for symbol in symbols:
            task = self.get_market_data(symbol)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        data = {}
        for i, result in enumerate(results):
            symbol = symbols[i]
            if isinstance(result, MarketData):
                data[symbol] = result
            elif isinstance(result, Exception):
                logger.error(f"Error getting {symbol}: {str(result)}")
            
        return data
    
    async def _get_multi_asset_sequential(self, symbols: List[str]) -> Dict[str, MarketData]:
        """Get multiple assets sequentially to respect rate limits"""
        data = {}
        
        for symbol in symbols:
            try:
                result = await self.get_market_data(symbol)
                if result:
                    data[symbol] = result
                    
                # Small delay to respect rate limits
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error getting {symbol}: {str(e)}")
                continue
        
        return data
    
    async def find_best_price(self, symbol: str, 
                            operation: str = "buy") -> Optional[Dict[str, Any]]:
        """
        Find the best price across all exchanges for a given symbol
        
        Args:
            symbol: Trading symbol
            operation: "buy" (lowest ask) or "sell" (highest bid)
        """
        
        # Get data from all available exchanges
        exchange_data = {}
        tasks = []
        
        for exchange_name in self.exchanges.keys():
            if self.exchange_configs[exchange_name].status == ExchangeStatus.ACTIVE:
                task = self._fetch_from_exchange(exchange_name, symbol)
                tasks.append((exchange_name, task))
        
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        # Process results
        prices = []
        for i, result in enumerate(results):
            exchange_name = tasks[i][0]
            if isinstance(result, MarketData):
                prices.append({
                    "exchange": exchange_name,
                    "price": result.current_price,
                    "data": result
                })
        
        if not prices:
            return None
        
        # Find best price based on operation
        if operation == "buy":
            best = min(prices, key=lambda x: x["price"])
        else:  # sell
            best = max(prices, key=lambda x: x["price"])
        
        return {
            "best_exchange": best["exchange"],
            "best_price": best["price"],
            "all_prices": prices,
            "price_spread": max(p["price"] for p in prices) - min(p["price"] for p in prices),
            "arbitrage_opportunity": len(prices) > 1
        }
    
    async def get_exchange_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all registered exchanges"""
        health_status = {}
        
        for exchange_name, exchange_client in self.exchanges.items():
            try:
                # Simple health check - try to get a common symbol
                start_time = datetime.now()
                test_data = await self._fetch_from_exchange(exchange_name, "BTCUSDT")
                response_time = (datetime.now() - start_time).total_seconds()
                
                health_status[exchange_name] = {
                    "status": "healthy" if test_data else "degraded",
                    "response_time": response_time,
                    "last_check": datetime.now().isoformat(),
                    "config": self.exchange_configs[exchange_name].__dict__
                }
                
            except Exception as e:
                health_status[exchange_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "last_check": datetime.now().isoformat(),
                    "config": self.exchange_configs[exchange_name].__dict__
                }
        
        return health_status
    
    def _get_exchange_priority_order(self, preferred: Optional[List[str]] = None) -> List[str]:
        """Get exchanges in priority order"""
        if preferred:
            # Start with preferred exchanges, then add others by priority
            remaining = [name for name in self.exchanges.keys() if name not in preferred]
            remaining.sort(key=lambda x: self.exchange_configs[x].priority)
            return preferred + remaining
        else:
            # Sort by priority
            return sorted(self.exchanges.keys(), 
                         key=lambda x: self.exchange_configs[x].priority)
    
    async def _fetch_from_exchange(self, exchange_name: str, symbol: str) -> Optional[MarketData]:
        """Fetch data from a specific exchange (to be implemented per exchange)"""
        exchange_client = self.exchanges[exchange_name]
        config = self.exchange_configs[exchange_name]
        
        try:
            # Attempt to fetch data with timeout
            data = await asyncio.wait_for(
                self._call_exchange_api(exchange_client, symbol),
                timeout=config.timeout
            )
            
            if data:
                # Map exchange-specific field names to standardized MarketData structure
                current_price = data.get("price", 0)
                
                # Map 24h price change (percentage or absolute)
                price_change_24h = None
                if "priceChangePercent" in data:
                    # Convert percentage to absolute change
                    price_change_24h = (float(data["priceChangePercent"]) / 100) * current_price
                elif "priceChange" in data:
                    price_change_24h = data["priceChange"]
                
                # Map 24h high/low
                high_24h = data.get("high24h") or data.get("high") or None
                low_24h = data.get("low24h") or data.get("low") or None
                
                # Map 24h volume
                volume_24h = data.get("volume24h") or data.get("volume") or data.get("vol") or None
                
                return MarketData(
                    symbol=symbol,
                    exchange=exchange_name,
                    timestamp=datetime.now(timezone.utc),
                    current_price=float(current_price) if current_price else 0,
                    price_change_24h=float(price_change_24h) if price_change_24h else None,
                    high_24h=float(high_24h) if high_24h else None,
                    low_24h=float(low_24h) if low_24h else None,
                    volume_24h=float(volume_24h) if volume_24h else None
                )
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {symbol} from {exchange_name}")
        except Exception as e:
            logger.error(f"Error fetching {symbol} from {exchange_name}: {str(e)}")
            
        return None
    
    async def _call_exchange_api(self, exchange_client, symbol: str) -> Optional[Dict[str, Any]]:
        """Call the exchange API with proper method detection and enhanced data fetching"""
        
        exchange_type = type(exchange_client).__name__
        
        # Special handling for each exchange type
        if exchange_type == 'OKXClient':
            try:
                result = await exchange_client.get_ticker(symbol)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"Error calling get_ticker on OKX: {str(e)}")
        
        elif exchange_type == 'KuCoinClient':
            # For KuCoin, try to get full 24h ticker data instead of just level1
            try:
                # Get all tickers and find our symbol
                all_tickers = await exchange_client.fetch_tickers_async()
                kucoin_symbol = exchange_client._convert_symbol_format(symbol)
                
                for ticker in all_tickers:
                    if ticker['symbol'] == kucoin_symbol:
                        return {
                            "symbol": symbol,
                            "price": ticker['price'],
                            "priceChangePercent": ticker['priceChangePercent'],
                            "high24h": ticker['high'],
                            "low24h": ticker['low'],
                            "volume24h": ticker['volume']
                        }
                
                # Fallback to level1 if not found in tickers
                result = await exchange_client.get_ticker(symbol)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"Error getting KuCoin ticker data: {str(e)}")
        
        else:
            # Try standard method names for other exchanges
            ticker_methods = ['get_ticker', 'fetch_ticker', 'ticker']
            
            for method_name in ticker_methods:
                if hasattr(exchange_client, method_name):
                    try:
                        method = getattr(exchange_client, method_name)
                        if asyncio.iscoroutinefunction(method):
                            result = await method(symbol)
                        else:
                            result = await asyncio.to_thread(method, symbol)
                        
                        if result:
                            return result
                    except Exception as e:
                        logger.debug(f"Error calling {method_name} on {exchange_type}: {str(e)}")
                        continue
        
        logger.warning(f"Failed to get ticker data from {exchange_type} for {symbol}")
        return None
    
    async def _handle_exchange_error(self, exchange_name: str, error: Exception):
        """Handle exchange errors and update status if needed"""
        config = self.exchange_configs[exchange_name]
        
        # For now, just log the error
        # In production, you might want to:
        # - Temporarily disable the exchange after multiple failures
        # - Send alerts to monitoring systems
        # - Implement circuit breaker pattern
        
        logger.warning(f"Exchange {exchange_name} error: {str(error)}")
        
        # Update last error time
        self.last_health_check[exchange_name] = {
            "timestamp": datetime.now(),
            "status": "error",
            "error": str(error)
        } 