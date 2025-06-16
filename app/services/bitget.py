"""
Bitget API Client
Provides standardized interface for Bitget cryptocurrency exchange data
Focus on copy trading and emerging markets
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

BITGET_API = os.getenv("BITGET_API", "https://api.bitget.com/api/v2")
CACHE_TTL = int(os.getenv("CACHE_TTL", "300").split("#")[0].strip())

logger = logging.getLogger("CryptoPredictAPI")

# Caching setup
SYMBOLS_CACHE = TTLCache(maxsize=10, ttl=CACHE_TTL)
OHLCV_CACHE = TTLCache(maxsize=1000, ttl=300)
TICKER_CACHE = TTLCache(maxsize=5, ttl=60)
CACHE_LOCK = asyncio.Lock()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Content-Type": "application/json"
}

class BitgetClient:
    """Bitget API client with focus on copy trading and emerging markets"""
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type(requests.HTTPError)
    )
    def fetch_symbols(self) -> List[str]:
        """Synchronously fetch all trading symbols from Bitget"""
        try:
            cache_key = "all_symbols"
            if cache_key in SYMBOLS_CACHE:
                return SYMBOLS_CACHE[cache_key]
                
            symbols = []
            
            # Fetch spot symbols
            response = requests.get(f"{BITGET_API}/spot/public/symbols", headers=HEADERS)
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == "00000":  # Bitget success code
                spot_symbols = [s["symbol"] for s in data["data"] if s["status"] == "online"]
                symbols.extend(spot_symbols)
            
            # Fetch futures symbols (USDT-M)
            try:
                futures_response = requests.get(f"{BITGET_API}/mix/market/contracts", 
                                              params={"productType": "USDT-FUTURES"}, 
                                              headers=HEADERS)
                futures_response.raise_for_status()
                
                futures_data = futures_response.json()
                if futures_data.get("code") == "00000":
                    futures_symbols = [s["symbol"] for s in futures_data["data"] if s["status"] == "normal"]
                    symbols.extend(futures_symbols)
            except Exception as e:
                logger.warning(f"Could not fetch Bitget futures symbols: {str(e)}")
            
            # Store in cache with timestamp
            SYMBOLS_CACHE[cache_key] = symbols
            SYMBOLS_CACHE["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Successfully fetched {len(symbols)} Bitget trading symbols")
            return symbols
            
        except Exception as e:
            logger.error(f"Bitget symbols fetch error: {str(e)}")
            # If we've cached symbols before, return those instead of failing
            if "all_symbols" in SYMBOLS_CACHE:
                logger.warning("Using cached Bitget symbols due to API error")
                return SYMBOLS_CACHE["all_symbols"]
            raise

    async def fetch_symbols_async(self) -> List[str]:
        """Asynchronously fetch all trading symbols"""
        return await asyncio.to_thread(self.fetch_symbols)
        
    def get_symbol_details(self, symbol: str) -> Optional[Dict]:
        """Get detailed information about a specific symbol"""
        try:
            # Try spot first
            response = requests.get(
                f"{BITGET_API}/spot/public/symbols",
                headers=HEADERS
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == "00000":
                for s in data["data"]:
                    if s["symbol"] == symbol and s["status"] == "online":
                        return {**s, "product_type": "spot"}
            
            # Try futures
            try:
                futures_response = requests.get(
                    f"{BITGET_API}/mix/market/contracts",
                    params={"productType": "USDT-FUTURES"},
                    headers=HEADERS
                )
                futures_response.raise_for_status()
                
                futures_data = futures_response.json()
                if futures_data.get("code") == "00000":
                    for s in futures_data["data"]:
                        if s["symbol"] == symbol and s["status"] == "normal":
                            return {**s, "product_type": "futures"}
            except Exception:
                pass
            
            return None
        except Exception as e:
            logger.error(f"Bitget symbol details fetch error for {symbol}: {str(e)}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.HTTPError, requests.Timeout))
    )
    async def fetch_ohlcv(self, symbol: str, interval: str = "1h", limit: int = 100) -> List[Dict]:
        """Fetch OHLCV (candlestick) data for a symbol"""
        async with CACHE_LOCK:
            cache_key = f"bitget_{symbol}_{interval}_{limit}"
            if cache_key in OHLCV_CACHE:
                return OHLCV_CACHE[cache_key]
            
            try:
                # Convert interval to Bitget format
                bitget_interval = self._convert_interval(interval)
                
                # Determine if it's spot or futures
                product_type = await self._determine_product_type(symbol)
                
                if product_type == "spot":
                    endpoint = f"{BITGET_API}/spot/market/candles"
                    params = {
                        "symbol": symbol,
                        "granularity": bitget_interval,
                        "limit": limit
                    }
                else:  # futures
                    endpoint = f"{BITGET_API}/mix/market/candles"
                    params = {
                        "symbol": symbol,
                        "granularity": bitget_interval,
                        "limit": limit,
                        "productType": "USDT-FUTURES"
                    }
                
                response = await asyncio.to_thread(
                    requests.get,
                    endpoint,
                    params=params,
                    headers=HEADERS,
                    timeout=10
                )
                response.raise_for_status()
                
                data = response.json()
                if data.get("code") == "00000":
                    raw_data = data["data"]
                    
                    # Convert Bitget format to standard format
                    ohlcv = []
                    for entry in raw_data:
                        # Bitget format: [timestamp, open, high, low, close, volume, quoteVolume]
                        ohlcv.append({
                            "timestamp": int(entry[0]),
                            "open": float(entry[1]),
                            "high": float(entry[2]),
                            "low": float(entry[3]),
                            "close": float(entry[4]),
                            "volume": float(entry[5]),
                        })
                    
                    # Sort by timestamp (oldest first)
                    ohlcv.sort(key=lambda x: x["timestamp"])
                    
                    OHLCV_CACHE[cache_key] = ohlcv
                    return ohlcv
                else:
                    raise Exception(f"Bitget API error: {data.get('msg', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"Bitget OHLCV fetch error for {symbol}: {str(e)}")
                raise

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type(requests.HTTPError)
    )
    def fetch_tickers(self) -> List[dict]:
        """Fetch 24h ticker data for all symbols"""
        try:
            cache_key = 'bitget_tickers'
            if cache_key in TICKER_CACHE:
                return TICKER_CACHE[cache_key]
                
            tickers = []
            
            # Fetch spot tickers
            response = requests.get(f"{BITGET_API}/spot/market/tickers", headers=HEADERS)
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == "00000":
                spot_tickers = data["data"]
                
                # Convert to standard format
                for ticker in spot_tickers:
                    try:
                        tickers.append({
                            "symbol": ticker["symbol"],
                            "price": float(ticker["close"]) if ticker["close"] else 0,
                            "priceChange": float(ticker["change"]) if ticker["change"] else 0,
                            "priceChangePercent": float(ticker["changeUtc"]) if ticker["changeUtc"] else 0,
                            "high": float(ticker["high24h"]) if ticker["high24h"] else 0,
                            "low": float(ticker["low24h"]) if ticker["low24h"] else 0,
                            "volume": float(ticker["baseVol"]) if ticker["baseVol"] else 0,
                            "quoteVolume": float(ticker["quoteVol"]) if ticker["quoteVol"] else 0,
                            "product_type": "spot"
                        })
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error processing spot ticker for {ticker.get('symbol', 'unknown')}: {str(e)}")
                        continue
            
            # Fetch futures tickers
            try:
                futures_response = requests.get(
                    f"{BITGET_API}/mix/market/tickers",
                    params={"productType": "USDT-FUTURES"},
                    headers=HEADERS
                )
                futures_response.raise_for_status()
                
                futures_data = futures_response.json()
                if futures_data.get("code") == "00000":
                    futures_tickers = futures_data["data"]
                    
                    for ticker in futures_tickers:
                        try:
                            tickers.append({
                                "symbol": ticker["symbol"],
                                "price": float(ticker["last"]) if ticker["last"] else 0,
                                "priceChange": float(ticker["change"]) if ticker["change"] else 0,
                                "priceChangePercent": float(ticker["changeUtc"]) if ticker["changeUtc"] else 0,
                                "high": float(ticker["high24h"]) if ticker["high24h"] else 0,
                                "low": float(ticker["low24h"]) if ticker["low24h"] else 0,
                                "volume": float(ticker["baseVolume"]) if ticker["baseVolume"] else 0,
                                "quoteVolume": float(ticker["quoteVolume"]) if ticker["quoteVolume"] else 0,
                                "product_type": "futures"
                            })
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Error processing futures ticker for {ticker.get('symbol', 'unknown')}: {str(e)}")
                            continue
            except Exception as e:
                logger.warning(f"Could not fetch Bitget futures tickers: {str(e)}")
            
            TICKER_CACHE[cache_key] = tickers
            TICKER_CACHE['last_updated'] = datetime.now(timezone.utc).isoformat()
            
            return tickers
                
        except Exception as e:
            logger.error(f"Bitget tickers fetch error: {str(e)}")
            # If we've cached tickers before, return those instead of failing
            if 'bitget_tickers' in TICKER_CACHE:
                logger.warning("Using cached Bitget tickers due to API error")
                return TICKER_CACHE['bitget_tickers']
            raise
            
    async def fetch_tickers_async(self) -> List[dict]:
        """Asynchronously fetch 24h ticker data"""
        return await asyncio.to_thread(self.fetch_tickers)
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get ticker data for a specific symbol"""
        try:
            # Determine product type
            product_type = await self._determine_product_type(symbol)
            
            if product_type == "spot":
                endpoint = f"{BITGET_API}/spot/market/tickers"
                params = {"symbol": symbol}
            else:  # futures
                endpoint = f"{BITGET_API}/mix/market/tickers"
                params = {"symbol": symbol, "productType": "USDT-FUTURES"}
            
            response = await asyncio.to_thread(
                requests.get,
                endpoint,
                params=params,
                headers=HEADERS,
                timeout=5
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == "00000" and data.get("data"):
                # Bitget returns data as array for tickers endpoint
                ticker_list = data["data"]
                if isinstance(ticker_list, list) and len(ticker_list) > 0:
                    ticker_data = ticker_list[0]
                elif isinstance(ticker_list, dict):
                    ticker_data = ticker_list
                else:
                    return None
                
                if product_type == "spot":
                    return {
                        "symbol": symbol,
                        "price": float(ticker_data.get("lastPr", 0)) if ticker_data.get("lastPr") else 0,
                        "bid": float(ticker_data.get("bidPr", 0)) if ticker_data.get("bidPr") else 0,
                        "ask": float(ticker_data.get("askPr", 0)) if ticker_data.get("askPr") else 0,
                        "high24h": float(ticker_data.get("high24h", 0)) if ticker_data.get("high24h") else 0,
                        "low24h": float(ticker_data.get("low24h", 0)) if ticker_data.get("low24h") else 0,
                        "volume24h": float(ticker_data.get("baseVolume", 0)) if ticker_data.get("baseVolume") else 0,
                        "priceChangePercent": float(ticker_data.get("changeUtc24h", 0)) if ticker_data.get("changeUtc24h") else 0,
                        "product_type": "spot"
                    }
                else:  # futures
                    return {
                        "symbol": symbol,
                        "price": float(ticker_data.get("last", 0)) if ticker_data.get("last") else 0,
                        "bid": float(ticker_data.get("bidPr", 0)) if ticker_data.get("bidPr") else 0,
                        "ask": float(ticker_data.get("askPr", 0)) if ticker_data.get("askPr") else 0,
                        "high24h": float(ticker_data.get("high24h", 0)) if ticker_data.get("high24h") else 0,
                        "low24h": float(ticker_data.get("low24h", 0)) if ticker_data.get("low24h") else 0,
                        "volume24h": float(ticker_data.get("baseVolume", 0)) if ticker_data.get("baseVolume") else 0,
                        "priceChangePercent": float(ticker_data.get("changeUtc", 0)) if ticker_data.get("changeUtc") else 0,
                        "product_type": "futures"
                    }
            
            return None
                
        except Exception as e:
            logger.error(f"Bitget ticker fetch error for {symbol}: {str(e)}")
            return None
    
    async def get_copy_trading_data(self, symbol: str) -> Optional[Dict]:
        """Get copy trading statistics (Bitget specialty)"""
        try:
            # Note: This is a simplified implementation
            # Real copy trading data would require authenticated endpoints
            
            # Get basic ticker data
            ticker = await self.get_ticker(symbol)
            if not ticker:
                return None
            
            # Get order book for liquidity analysis
            depth_response = await asyncio.to_thread(
                requests.get,
                f"{BITGET_API}/spot/market/depth",
                params={"symbol": symbol, "type": "step0", "limit": "50"},
                headers=HEADERS,
                timeout=5
            )
            
            liquidity_score = None
            if depth_response.status_code == 200:
                depth_data = depth_response.json()
                if depth_data.get("code") == "00000":
                    bids = depth_data["data"]["bids"]
                    asks = depth_data["data"]["asks"]
                    
                    # Calculate simple liquidity score
                    bid_volume = sum(float(bid[1]) for bid in bids[:10])
                    ask_volume = sum(float(ask[1]) for ask in asks[:10])
                    liquidity_score = (bid_volume + ask_volume) / 2
            
            return {
                "ticker": ticker,
                "liquidity_score": liquidity_score,
                "copy_trading_available": True,  # Bitget supports copy trading
                "exchange": "bitget",
                "note": "Copy trading data requires authenticated access"
            }
            
        except Exception as e:
            logger.error(f"Bitget copy trading data fetch error for {symbol}: {str(e)}")
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
                results = [s for s in results if quote_upper in s]
                
            return results
        except Exception as e:
            logger.error(f"Bitget symbol search error: {str(e)}")
            return []
    
    async def _determine_product_type(self, symbol: str) -> str:
        """Determine if a symbol is spot or futures"""
        # Simple heuristic: check if symbol exists in spot symbols first
        try:
            response = await asyncio.to_thread(
                requests.get,
                f"{BITGET_API}/spot/public/symbols",
                headers=HEADERS,
                timeout=3
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "00000":
                    spot_symbols = [s["symbol"] for s in data["data"]]
                    if symbol in spot_symbols:
                        return "spot"
        except:
            pass
        
        # Default to futures if not found in spot
        return "futures"
    
    def _convert_interval(self, interval: str) -> str:
        """Convert standard interval to Bitget format"""
        interval_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "4h": "4h",
            "6h": "6h",
            "12h": "12h",
            "1d": "1d",
            "3d": "3d",
            "1w": "1w",
            "1M": "1M"
        }
        return interval_map.get(interval, "1h") 