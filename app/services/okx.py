"""
OKX API Client
Provides standardized interface for OKX cryptocurrency exchange data
One of the world's largest crypto exchanges with deep liquidity
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

OKX_API = os.getenv("OKX_API", "https://www.okx.com/api/v5")
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

class OKXClient:
    """OKX API client with support for spot, futures, and options trading"""
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type(requests.HTTPError)
    )
    def fetch_symbols(self) -> List[str]:
        """Synchronously fetch all trading symbols from OKX"""
        try:
            cache_key = "all_symbols"
            if cache_key in SYMBOLS_CACHE:
                return SYMBOLS_CACHE[cache_key]
                
            symbols = []
            
            # Fetch spot symbols
            response = requests.get(f"{OKX_API}/public/instruments", 
                                  params={"instType": "SPOT"}, 
                                  headers=HEADERS)
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == "0":  # OKX success code
                spot_symbols = [s["instId"] for s in data["data"] if s["state"] == "live"]
                symbols.extend(spot_symbols)
            
            # Fetch perpetual futures symbols
            try:
                futures_response = requests.get(f"{OKX_API}/public/instruments", 
                                              params={"instType": "SWAP"}, 
                                              headers=HEADERS)
                futures_response.raise_for_status()
                
                futures_data = futures_response.json()
                if futures_data.get("code") == "0":
                    futures_symbols = [s["instId"] for s in futures_data["data"] if s["state"] == "live"]
                    symbols.extend(futures_symbols)
            except Exception as e:
                logger.warning(f"Could not fetch OKX futures symbols: {str(e)}")
            
            # Store in cache with timestamp
            SYMBOLS_CACHE[cache_key] = symbols
            SYMBOLS_CACHE["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Successfully fetched {len(symbols)} OKX trading symbols")
            return symbols
            
        except Exception as e:
            logger.error(f"OKX symbols fetch error: {str(e)}")
            # If we've cached symbols before, return those instead of failing
            if "all_symbols" in SYMBOLS_CACHE:
                logger.warning("Using cached OKX symbols due to API error")
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
                f"{OKX_API}/public/instruments",
                params={"instType": "SPOT", "instId": symbol},
                headers=HEADERS
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == "0" and data.get("data"):
                return {**data["data"][0], "product_type": "spot"}
            
            # Try futures/swap
            try:
                futures_response = requests.get(
                    f"{OKX_API}/public/instruments",
                    params={"instType": "SWAP", "instId": symbol},
                    headers=HEADERS
                )
                futures_response.raise_for_status()
                
                futures_data = futures_response.json()
                if futures_data.get("code") == "0" and futures_data.get("data"):
                    return {**futures_data["data"][0], "product_type": "swap"}
            except Exception:
                pass
            
            return None
        except Exception as e:
            logger.error(f"OKX symbol details fetch error for {symbol}: {str(e)}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.HTTPError, requests.Timeout))
    )
    async def fetch_ohlcv(self, symbol: str, interval: str = "1h", limit: int = 100) -> List[Dict]:
        """Fetch OHLCV (candlestick) data for a symbol"""
        async with CACHE_LOCK:
            okx_symbol = self._convert_symbol_format(symbol)
            cache_key = f"okx_{okx_symbol}_{interval}_{limit}"
            if cache_key in OHLCV_CACHE:
                return OHLCV_CACHE[cache_key]
            
            try:
                # Convert interval to OKX format
                okx_interval = self._convert_interval(interval)
                
                # OKX uses the same endpoint for all instrument types
                params = {
                    "instId": okx_symbol,
                    "bar": okx_interval,
                    "limit": limit
                }
                
                response = await asyncio.to_thread(
                    requests.get,
                    f"{OKX_API}/market/candles",
                    params=params,
                    headers=HEADERS,
                    timeout=10
                )
                response.raise_for_status()
                
                data = response.json()
                if data.get("code") == "0" and data.get("data"):
                    raw_data = data["data"]
                    
                    # Convert OKX format to standard format
                    ohlcv = []
                    for entry in raw_data:
                        # OKX format: [timestamp, open, high, low, close, volume, volumeCcy, volumeCcyQuote, confirm]
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
                    raise Exception(f"OKX API error: {data.get('msg', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"OKX OHLCV fetch error for {symbol}: {str(e)}")
                raise

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type(requests.HTTPError)
    )
    def fetch_tickers(self) -> List[dict]:
        """Synchronously fetch 24h ticker data for all symbols"""
        try:
            cache_key = 'okx_tickers'
            if cache_key in TICKER_CACHE:
                return TICKER_CACHE[cache_key]
                
            tickers = []
            
            # Fetch spot tickers
            response = requests.get(f"{OKX_API}/market/tickers", 
                                  params={"instType": "SPOT"}, 
                                  headers=HEADERS)
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == "0":
                for ticker in data["data"]:
                    try:
                        tickers.append({
                            "symbol": ticker["instId"],
                            "price": float(ticker["last"]) if ticker["last"] else 0,
                            "priceChange": float(ticker["open24h"]) - float(ticker["last"]) if ticker["open24h"] and ticker["last"] else 0,
                            "priceChangePercent": float(ticker["open24hPc"]) if ticker["open24hPc"] else 0,
                            "high": float(ticker["high24h"]) if ticker["high24h"] else 0,
                            "low": float(ticker["low24h"]) if ticker["low24h"] else 0,
                            "volume": float(ticker["vol24h"]) if ticker["vol24h"] else 0,
                            "quoteVolume": float(ticker["volCcy24h"]) if ticker["volCcy24h"] else 0,
                            "product_type": "spot"
                        })
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error processing spot ticker for {ticker.get('instId', 'unknown')}: {str(e)}")
                        continue
            
            # Fetch swap/futures tickers
            try:
                futures_response = requests.get(f"{OKX_API}/market/tickers", 
                                              params={"instType": "SWAP"}, 
                                              headers=HEADERS)
                futures_response.raise_for_status()
                
                futures_data = futures_response.json()
                if futures_data.get("code") == "0":
                    for ticker in futures_data["data"]:
                        try:
                            tickers.append({
                                "symbol": ticker["instId"],
                                "price": float(ticker["last"]) if ticker["last"] else 0,
                                "priceChange": float(ticker["open24h"]) - float(ticker["last"]) if ticker["open24h"] and ticker["last"] else 0,
                                "priceChangePercent": float(ticker["open24hPc"]) if ticker["open24hPc"] else 0,
                                "high": float(ticker["high24h"]) if ticker["high24h"] else 0,
                                "low": float(ticker["low24h"]) if ticker["low24h"] else 0,
                                "volume": float(ticker["vol24h"]) if ticker["vol24h"] else 0,
                                "quoteVolume": float(ticker["volCcy24h"]) if ticker["volCcy24h"] else 0,
                                "product_type": "swap"
                            })
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Error processing swap ticker for {ticker.get('instId', 'unknown')}: {str(e)}")
                            continue
            except Exception as e:
                logger.warning(f"Could not fetch OKX futures tickers: {str(e)}")
            
            TICKER_CACHE[cache_key] = tickers
            TICKER_CACHE['last_updated'] = datetime.now(timezone.utc).isoformat()
            
            return tickers
                
        except Exception as e:
            logger.error(f"OKX tickers fetch error: {str(e)}")
            # If we've cached tickers before, return those instead of failing
            if 'okx_tickers' in TICKER_CACHE:
                logger.warning("Using cached OKX tickers due to API error")
                return TICKER_CACHE['okx_tickers']
            raise
            
    async def fetch_tickers_async(self) -> List[dict]:
        """Asynchronously fetch 24h ticker data"""
        return await asyncio.to_thread(self.fetch_tickers)
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get ticker data for a specific symbol"""
        try:
            okx_symbol = self._convert_symbol_format(symbol)
            response = await asyncio.to_thread(
                requests.get,
                f"{OKX_API}/market/ticker",
                params={"instId": okx_symbol},
                headers=HEADERS,
                timeout=5
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == "0" and data.get("data"):
                ticker_data = data["data"][0]
                
                return {
                    "symbol": symbol,
                    "price": float(ticker_data.get("last", 0)) if ticker_data.get("last") else 0,
                    "bid": float(ticker_data.get("bidPx", 0)) if ticker_data.get("bidPx") else 0,
                    "ask": float(ticker_data.get("askPx", 0)) if ticker_data.get("askPx") else 0,
                    "high24h": float(ticker_data.get("high24h", 0)) if ticker_data.get("high24h") else 0,
                    "low24h": float(ticker_data.get("low24h", 0)) if ticker_data.get("low24h") else 0,
                    "volume24h": float(ticker_data.get("vol24h", 0)) if ticker_data.get("vol24h") else 0,
                    "priceChangePercent": float(ticker_data.get("open24hPc", 0)) if ticker_data.get("open24hPc") else 0,
                    "product_type": "spot"
                }
            
            return None
                
        except Exception as e:
            logger.error(f"OKX ticker fetch error for {symbol}: {str(e)}")
            return None
    
    async def get_order_book(self, symbol: str, depth: int = 20) -> Optional[Dict]:
        """Get order book data for liquidity analysis"""
        try:
            response = await asyncio.to_thread(
                requests.get,
                f"{OKX_API}/market/books",
                params={"instId": symbol, "sz": depth},
                headers=HEADERS,
                timeout=5
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == "0" and data.get("data"):
                book_data = data["data"][0]
                
                return {
                    "bids": [[float(bid[0]), float(bid[1])] for bid in book_data.get("bids", [])],
                    "asks": [[float(ask[0]), float(ask[1])] for ask in book_data.get("asks", [])],
                    "timestamp": int(book_data.get("ts", 0)),
                    "exchange": "okx"
                }
            
            return None
                
        except Exception as e:
            logger.error(f"OKX order book fetch error for {symbol}: {str(e)}")
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
            logger.error(f"OKX symbol search error: {str(e)}")
            return []
    
    def _convert_interval(self, interval: str) -> str:
        """Convert standard interval to OKX format"""
        interval_map = {
            "1m": "1m",
            "3m": "3m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1H",
            "2h": "2H",
            "4h": "4H",
            "6h": "6H",
            "12h": "12H",
            "1d": "1D",
            "3d": "3D",
            "1w": "1W",
            "1M": "1M"
        }
        return interval_map.get(interval, "1H")

    def _convert_symbol_format(self, symbol: str) -> str:
        """Convert generic symbols like BTCUSDT to OKX format BTC-USDT (dash separated)."""
        # If the symbol already contains a dash, assume it's correct
        if "-" in symbol:
            return symbol.upper()

        symbol = symbol.upper()
        suffixes = [
            "USDT", "USDC", "BTC", "ETH", "BNB", "USD", "EUR", "GBP"
        ]
        for suff in suffixes:
            if symbol.endswith(suff):
                base = symbol[:-len(suff)]
                return f"{base}-{suff}"
        # Fallback – return original if no known suffix found
        return symbol 