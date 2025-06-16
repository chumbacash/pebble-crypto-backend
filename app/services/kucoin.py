"""
KuCoin API Client
Provides standardized interface for KuCoin cryptocurrency exchange data
"""

import requests
import asyncio
import logging
from typing import List, Dict, Optional
from cachetools import TTLCache
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

KUCOIN_API = os.getenv("KUCOIN_API", "https://api.kucoin.com/api/v1")
CACHE_TTL = int(os.getenv("CACHE_TTL", "300").split("#")[0].strip())

logger = logging.getLogger("CryptoPredictAPI")

# Caching setup
SYMBOLS_CACHE = TTLCache(maxsize=10, ttl=CACHE_TTL)
OHLCV_CACHE = TTLCache(maxsize=1000, ttl=300)
TICKER_CACHE = TTLCache(maxsize=5, ttl=60)
CACHE_LOCK = asyncio.Lock()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

class KuCoinClient:
    """KuCoin API client with caching and error handling"""
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type(requests.HTTPError)
    )
    def fetch_symbols(self) -> List[str]:
        """Synchronously fetch all trading symbols from KuCoin"""
        try:
            cache_key = "all_symbols"
            if cache_key in SYMBOLS_CACHE:
                return SYMBOLS_CACHE[cache_key]
                
            response = requests.get(f"{KUCOIN_API}/symbols", headers=HEADERS)
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == "200000":  # KuCoin success code
                symbols = [s["symbol"] for s in data["data"] if s["enableTrading"]]
                
                # Store in cache with timestamp
                SYMBOLS_CACHE[cache_key] = symbols
                SYMBOLS_CACHE["last_updated"] = datetime.now(timezone.utc).isoformat()
                
                logger.info(f"Successfully fetched {len(symbols)} KuCoin trading symbols")
                return symbols
            else:
                raise Exception(f"KuCoin API error: {data.get('msg', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"KuCoin symbols fetch error: {str(e)}")
            # If we've cached symbols before, return those instead of failing
            if "all_symbols" in SYMBOLS_CACHE:
                logger.warning("Using cached KuCoin symbols due to API error")
                return SYMBOLS_CACHE["all_symbols"]
            raise

    async def fetch_symbols_async(self) -> List[str]:
        """Asynchronously fetch all trading symbols"""
        return await asyncio.to_thread(self.fetch_symbols)
        
    def get_symbol_details(self, symbol: str) -> Optional[Dict]:
        """Get detailed information about a specific symbol"""
        try:
            # Try to get from cache first
            cache_key = "symbols_info"
            symbols_info = None
            
            if cache_key in SYMBOLS_CACHE:
                symbols_info = SYMBOLS_CACHE[cache_key]
            else:
                response = requests.get(f"{KUCOIN_API}/symbols", headers=HEADERS)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == "200000":
                    symbols_info = data["data"]
                    SYMBOLS_CACHE[cache_key] = symbols_info
                
            # Find the symbol in the symbols info
            if symbols_info:
                for s in symbols_info:
                    if s["symbol"] == symbol and s["enableTrading"]:
                        return s
            
            return None
        except Exception as e:
            logger.error(f"KuCoin symbol details fetch error for {symbol}: {str(e)}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.HTTPError, requests.Timeout))
    )
    async def fetch_ohlcv(self, symbol: str, interval: str = "1hour", limit: int = 100) -> List[Dict]:
        """Fetch OHLCV (candlestick) data for a symbol"""
        async with CACHE_LOCK:
            cache_key = f"kucoin_{symbol}_{interval}_{limit}"
            if cache_key in OHLCV_CACHE:
                return OHLCV_CACHE[cache_key]
            
            try:
                # Convert interval to KuCoin format
                kucoin_interval = self._convert_interval(interval)
                
                response = await asyncio.to_thread(
                    requests.get,
                    f"{KUCOIN_API}/market/candles",
                    params={
                        "symbol": symbol,
                        "type": kucoin_interval,
                        "startAt": int((datetime.now().timestamp() - (limit * self._interval_to_seconds(interval)))),
                        "endAt": int(datetime.now().timestamp())
                    },
                    headers=HEADERS,
                    timeout=10
                )
                response.raise_for_status()
                
                data = response.json()
                if data.get("code") == "200000":
                    raw_data = data["data"]
                    
                    # Convert KuCoin format to standard format
                    ohlcv = []
                    for entry in raw_data:
                        # KuCoin format: [time, open, close, high, low, volume, turnover]
                        ohlcv.append({
                            "timestamp": int(entry[0]) * 1000,  # Convert to milliseconds
                            "open": float(entry[1]),
                            "high": float(entry[3]),
                            "low": float(entry[4]),
                            "close": float(entry[2]),
                            "volume": float(entry[5]),
                        })
                    
                    # Sort by timestamp (oldest first)
                    ohlcv.sort(key=lambda x: x["timestamp"])
                    
                    OHLCV_CACHE[cache_key] = ohlcv
                    return ohlcv
                else:
                    raise Exception(f"KuCoin API error: {data.get('msg', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"KuCoin OHLCV fetch error for {symbol}: {str(e)}")
                raise

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type(requests.HTTPError)
    )
    def fetch_tickers(self) -> List[dict]:
        """Fetch 24h ticker data for all symbols"""
        try:
            cache_key = 'kucoin_tickers'
            if cache_key in TICKER_CACHE:
                return TICKER_CACHE[cache_key]
                
            response = requests.get(f"{KUCOIN_API}/market/allTickers", headers=HEADERS)
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == "200000":
                tickers = data["data"]["ticker"]
                
                # Convert to standard format
                standardized_tickers = []
                for ticker in tickers:
                    try:
                        # Skip tickers with missing essential data
                        if not ticker.get("last") or not ticker.get("symbol"):
                            continue
                            
                        standardized_tickers.append({
                            "symbol": ticker["symbol"],
                            "price": float(ticker["last"]) if ticker["last"] else 0,
                            "priceChange": float(ticker["changePrice"]) if ticker.get("changePrice") and ticker["changePrice"] else 0,
                            "priceChangePercent": float(ticker["changeRate"]) * 100 if ticker.get("changeRate") and ticker["changeRate"] else 0,
                            "high": float(ticker["high"]) if ticker.get("high") and ticker["high"] else 0,
                            "low": float(ticker["low"]) if ticker.get("low") and ticker["low"] else 0,
                            "volume": float(ticker["vol"]) if ticker.get("vol") and ticker["vol"] else 0,
                            "quoteVolume": float(ticker["volValue"]) if ticker.get("volValue") and ticker["volValue"] else 0,
                        })
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error processing KuCoin ticker for {ticker.get('symbol', 'unknown')}: {str(e)}")
                        continue
                
                TICKER_CACHE[cache_key] = standardized_tickers
                TICKER_CACHE['last_updated'] = datetime.now(timezone.utc).isoformat()
                
                return standardized_tickers
            else:
                raise Exception(f"KuCoin API error: {data.get('msg', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"KuCoin tickers fetch error: {str(e)}")
            # If we've cached tickers before, return those instead of failing
            if 'kucoin_tickers' in TICKER_CACHE:
                logger.warning("Using cached KuCoin tickers due to API error")
                return TICKER_CACHE['kucoin_tickers']
            raise
            
    async def fetch_tickers_async(self) -> List[dict]:
        """Asynchronously fetch 24h ticker data"""
        return await asyncio.to_thread(self.fetch_tickers)
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get ticker data for a specific symbol"""
        try:
            # Convert BTCUSDT format to BTC-USDT format for KuCoin
            kucoin_symbol = self._convert_symbol_format(symbol)
            
            response = await asyncio.to_thread(
                requests.get,
                f"{KUCOIN_API}/market/orderbook/level1",
                params={"symbol": kucoin_symbol},
                headers=HEADERS,
                timeout=5
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == "200000" and data.get("data"):
                ticker_data = data["data"]
                
                # Handle None values properly
                if not ticker_data or not ticker_data.get("price"):
                    return None
                
                return {
                    "symbol": symbol,
                    "price": float(ticker_data["price"]) if ticker_data["price"] else 0,
                    "size": float(ticker_data["size"]) if ticker_data.get("size") else 0,
                    "bid": float(ticker_data["bestBid"]) if ticker_data.get("bestBid") else 0,
                    "ask": float(ticker_data["bestAsk"]) if ticker_data.get("bestAsk") else 0,
                    "timestamp": int(ticker_data["time"]) if ticker_data.get("time") else 0
                }
            else:
                raise Exception(f"KuCoin API error: {data.get('msg', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"KuCoin ticker fetch error for {symbol}: {str(e)}")
            return None
        
    def search_symbols(self, search_term: str, quote_asset: Optional[str] = None) -> List[str]:
        """Search for symbols matching a search term and optional quote asset"""
        try:
            # Get all symbols
            all_symbols = self.fetch_symbols()
            
            # Filter by search term (case insensitive)
            search_upper = search_term.upper()
            results = [s for s in all_symbols if search_upper in s]
            
            # Further filter by quote asset if provided
            if quote_asset:
                quote_upper = quote_asset.upper()
                results = [s for s in results if s.endswith(f"-{quote_upper}")]
                
            return results
        except Exception as e:
            logger.error(f"KuCoin symbol search error: {str(e)}")
            return []
    
    def _convert_symbol_format(self, symbol: str) -> str:
        """Convert BTCUSDT format to BTC-USDT format for KuCoin"""
        # KuCoin uses dash format: BTC-USDT instead of BTCUSDT
        if "-" not in symbol:
            # Common patterns for conversion
            if symbol.endswith("USDT"):
                base = symbol[:-4]
                return f"{base}-USDT"
            elif symbol.endswith("BTC"):
                base = symbol[:-3]
                return f"{base}-BTC"
            elif symbol.endswith("ETH"):
                base = symbol[:-3]
                return f"{base}-ETH"
            elif symbol.endswith("BNB"):
                base = symbol[:-3]
                return f"{base}-BNB"
        return symbol
    
    def _convert_interval(self, interval: str) -> str:
        """Convert standard interval to KuCoin format"""
        interval_map = {
            "1m": "1min",
            "3m": "3min", 
            "5m": "5min",
            "15m": "15min",
            "30m": "30min",
            "1h": "1hour",
            "2h": "2hour",
            "4h": "4hour",
            "6h": "6hour",
            "8h": "8hour",
            "12h": "12hour",
            "1d": "1day",
            "1w": "1week"
        }
        return interval_map.get(interval, "1hour")
    
    def _interval_to_seconds(self, interval: str) -> int:
        """Convert interval string to seconds"""
        interval_seconds = {
            "1m": 60,
            "3m": 180,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "2h": 7200,
            "4h": 14400,
            "6h": 21600,
            "8h": 28800,
            "12h": 43200,
            "1d": 86400,
            "1w": 604800
        }
        return interval_seconds.get(interval, 3600) 