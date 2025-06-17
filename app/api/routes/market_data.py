"""
Market data endpoints for cryptocurrency information
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Optional
from datetime import datetime, timezone
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.dependencies import (
    get_binance_client, get_allowed_intervals, get_interval_hours, get_settings
)
from app.services.binance import BinanceClient, SYMBOLS_CACHE

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.get("/symbols", tags=["Market Data"])
@limiter.limit("30/minute")
async def get_active_symbols(
    request: Request, 
    sort_by: Optional[str] = None, 
    descending: bool = True,
    quote_asset: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 500,
    binance: BinanceClient = Depends(get_binance_client)
):
    """
    Get list of available trading symbols.
    
    - **sort_by**: Sort by 'volume' or 'name'
    - **descending**: Sort in descending order if True
    - **quote_asset**: Filter by quote asset (e.g., 'USDT', 'BTC')
    - **search**: Search for specific symbols
    - **limit**: Maximum number of symbols to return
    """
    try:
        cache_key = "symbols"
        if not SYMBOLS_CACHE.get(cache_key):
            SYMBOLS_CACHE[cache_key] = binance.fetch_symbols()
        symbols = SYMBOLS_CACHE[cache_key]
        
        # Filter by quote asset if specified
        if quote_asset:
            quote_upper = quote_asset.upper()
            symbols = [s for s in symbols if s.endswith(quote_upper)]
        
        # Filter by search term if specified
        if search:
            search_upper = search.upper()
            symbols = [s for s in symbols if search_upper in s]

        # Sort by volume if requested
        if sort_by == "volume":
            sort_cache_key = f"symbols_sorted_volume_{quote_asset or ''}_{search or ''}"
            if not SYMBOLS_CACHE.get(sort_cache_key):
                tickers = binance.fetch_tickers()
                ticker_map = {t['symbol']: t for t in tickers}
                sorted_symbols = sorted(
                    symbols,
                    key=lambda s: float(ticker_map.get(s, {}).get('quoteVolume', 0)),
                    reverse=descending
                )
                SYMBOLS_CACHE[sort_cache_key] = sorted_symbols
            symbols = SYMBOLS_CACHE[sort_cache_key]
        # Sort by name if requested
        elif sort_by == "name":
            symbols = sorted(symbols, reverse=descending)
        
        # Apply limit
        symbols = symbols[:limit]
            
        return {
            "symbols": symbols,
            "total_count": len(symbols),
            "filter_applied": bool(quote_asset or search),
            "quote_asset": quote_asset,
            "sorting": f"{sort_by or 'none'}_{'desc' if descending else 'asc'}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

@router.get("/intraday/{symbol}", tags=["Market Data"])
@limiter.limit("30/minute")
async def get_intraday_data(
    request: Request, 
    symbol: str, 
    interval: str = "1h",
    binance: BinanceClient = Depends(get_binance_client),
    allowed_intervals: list = Depends(get_allowed_intervals),
    interval_hours: dict = Depends(get_interval_hours)
):
    """
    Returns intraday data for the given symbol based on the specified interval for the current day.
    Data points are fetched from midnight (UTC) until the current time.
    """
    try:
        symbol = symbol.upper()
        cache_key = "symbols"
        if not SYMBOLS_CACHE.get(cache_key):
            SYMBOLS_CACHE[cache_key] = binance.fetch_symbols()
        valid_symbols = SYMBOLS_CACHE[cache_key]
        
        if symbol not in valid_symbols:
            raise HTTPException(
                status_code=404,
                detail=f"Symbol {symbol} not found. Please check available symbols with /symbols endpoint."
            )
            
        if interval not in allowed_intervals:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval. Allowed values: {', '.join(allowed_intervals)}"
            )
            
        now = datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        interval_hours_val = interval_hours[interval]
        intervals_elapsed = int((now - start_of_day).total_seconds() / (interval_hours_val * 3600)) + 1
        limit = min(intervals_elapsed, 500)
        
        data = await binance.fetch_ohlcv(symbol, interval, limit=limit)
        if not data:
            raise HTTPException(status_code=404, detail="No intraday data available")
            
        intraday = []
        for candle in data:
            candle_time = datetime.fromtimestamp(candle["timestamp"] / 1000, tz=timezone.utc)
            if candle_time >= start_of_day:
                intraday.append(candle)
                
        return {
            "symbol": symbol,
            "interval": interval,
            "intraday_data": intraday,
            "time_updated": now.isoformat(),
            "intervals_elapsed": intervals_elapsed,
            "candles_returned": len(intraday)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Intraday data retrieval failed: {str(e)}")

@router.get("/historical/{symbol}", tags=["Market Data"])
@limiter.limit("20/minute")
async def get_historical_data(
    request: Request, 
    symbol: str, 
    interval: str = "1h", 
    limit: int = 100,
    binance: BinanceClient = Depends(get_binance_client),
    allowed_intervals: list = Depends(get_allowed_intervals)
):
    """
    Returns historical data for the given symbol and interval.
    Allows specifying the number of candles to retrieve.
    """
    try:
        symbol = symbol.upper()
        cache_key = "symbols"
        if not SYMBOLS_CACHE.get(cache_key):
            SYMBOLS_CACHE[cache_key] = binance.fetch_symbols()
        valid_symbols = SYMBOLS_CACHE[cache_key]
        
        if symbol not in valid_symbols:
            raise HTTPException(
                status_code=404,
                detail=f"Symbol {symbol} not found. Please check available symbols with /symbols endpoint."
            )
            
        if interval not in allowed_intervals:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval. Allowed values: {', '.join(allowed_intervals)}"
            )
            
        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 1000"
            )
            
        data = await binance.fetch_ohlcv(symbol, interval, limit=limit)
        if not data:
            raise HTTPException(status_code=404, detail="No historical data available")
            
        return {
            "symbol": symbol,
            "interval": interval,
            "historical_data": data,
            "time_updated": datetime.now(timezone.utc).isoformat(),
            "candles_returned": len(data)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Historical data retrieval failed: {str(e)}")

@router.get("/symbol/{symbol}/info", tags=["Market Data"])
@limiter.limit("30/minute")
async def get_symbol_info(
    request: Request, 
    symbol: str,
    binance: BinanceClient = Depends(get_binance_client)
):
    """
    Get detailed information about a specific trading symbol.
    """
    try:
        symbol = symbol.upper()
        cache_key = "symbols"
        if not SYMBOLS_CACHE.get(cache_key):
            SYMBOLS_CACHE[cache_key] = binance.fetch_symbols()
        valid_symbols = SYMBOLS_CACHE[cache_key]
        
        if symbol not in valid_symbols:
            raise HTTPException(
                status_code=404,
                detail=f"Symbol {symbol} not found. Please check available symbols with /symbols endpoint."
            )
        
        # Extract base and quote assets
        base_asset = ""
        quote_asset = ""
        
        # Check common quote assets
        common_quotes = ["USDT", "BTC", "ETH", "BNB", "BUSD", "USDC", "EUR", "TRY", "TUSD", "FDUSD"]
        for quote in common_quotes:
            if symbol.endswith(quote):
                quote_asset = quote
                base_asset = symbol[:-len(quote)]
                break
        
        if not base_asset:
            # Fallback for unknown quote assets
            base_asset = symbol[:-4] if len(symbol) > 4 else symbol
            quote_asset = symbol[-4:] if len(symbol) > 4 else ""
        
        # Get current ticker data
        ticker_data = await binance.get_ticker(symbol)
        
        return {
            "symbol": symbol,
            "base_asset": base_asset,
            "quote_asset": quote_asset,
            "symbol_info": {
                "is_trading": True,
                "current_price": ticker_data.get("price") if ticker_data else None,
                "price_change_24h": ticker_data.get("priceChangePercent") if ticker_data else None,
                "volume_24h": ticker_data.get("volume24h") if ticker_data else None,
                "high_24h": ticker_data.get("high24h") if ticker_data else None,
                "low_24h": ticker_data.get("low24h") if ticker_data else None
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Symbol info retrieval failed: {str(e)}")

@router.get("/coins", tags=["Market Data"])
@limiter.limit("10/minute")
async def get_coins_with_trading_pairs(
    request: Request,
    min_quote_assets: int = 1,
    include_volume: bool = False,
    binance: BinanceClient = Depends(get_binance_client)
):
    """
    Get a list of unique coins/tokens with their available trading pairs.
    Groups symbols by base asset and shows available quote assets.
    """
    try:
        cache_key = "symbols"
        if not SYMBOLS_CACHE.get(cache_key):
            SYMBOLS_CACHE[cache_key] = binance.fetch_symbols()
        symbols = SYMBOLS_CACHE[cache_key]
        
        # Get ticker data if volume is requested
        tickers = []
        if include_volume:
            tickers = binance.fetch_tickers()
            ticker_map = {t['symbol']: t for t in tickers}
        
        # Group symbols by base asset
        coins = {}
        common_quotes = ["USDT", "BTC", "ETH", "BNB", "BUSD", "USDC", "EUR", "TRY", "TUSD", "FDUSD"]
        
        for symbol in symbols:
            # Find the quote asset
            quote_asset = None
            for quote in common_quotes:
                if symbol.endswith(quote):
                    quote_asset = quote
                    base_asset = symbol[:-len(quote)]
                    break
            
            if not quote_asset:
                continue  # Skip symbols with unrecognized quote assets
            
            if base_asset not in coins:
                coins[base_asset] = {
                    "base_asset": base_asset,
                    "quote_assets": [],
                    "trading_pairs": [],
                    "pair_count": 0
                }
                
                if include_volume:
                    coins[base_asset]["total_volume"] = 0
            
            coins[base_asset]["quote_assets"].append(quote_asset)
            coins[base_asset]["trading_pairs"].append(symbol)
            coins[base_asset]["pair_count"] += 1
            
            if include_volume and symbol in ticker_map:
                volume = float(ticker_map[symbol].get('quoteVolume', 0))
                coins[base_asset]["total_volume"] += volume
        
        # Filter by minimum quote assets
        filtered_coins = {
            base: data for base, data in coins.items() 
            if len(set(data["quote_assets"])) >= min_quote_assets
        }
        
        # Convert to list and sort by pair count
        coins_list = list(filtered_coins.values())
        coins_list.sort(key=lambda x: x["pair_count"], reverse=True)
        
        return {
            "coins": coins_list,
            "total_unique_coins": len(coins_list),
            "filter_applied": {
                "min_quote_assets": min_quote_assets,
                "include_volume": include_volume
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Coins data retrieval failed: {str(e)}")

@router.get("/volatility/comparison", tags=["Market Data"])
@limiter.limit("10/minute")
async def compare_volatility(
    request: Request,
    symbols: Optional[str] = None,
    top: Optional[int] = 20,
    interval: str = "1h",
    sort: str = "desc",
    binance: BinanceClient = Depends(get_binance_client),
    allowed_intervals: list = Depends(get_allowed_intervals)
):
    """
    Compare volatility across multiple cryptocurrency symbols.
    Can analyze specific symbols or top N symbols by volume.
    """
    try:
        if interval not in allowed_intervals:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval. Allowed values: {', '.join(allowed_intervals)}"
            )
        
        # Determine which symbols to analyze
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(',')]
        else:
            # Get top symbols by volume
            cache_key = "symbols"
            if not SYMBOLS_CACHE.get(cache_key):
                SYMBOLS_CACHE[cache_key] = binance.fetch_symbols()
            all_symbols = SYMBOLS_CACHE[cache_key]
            
            # Get tickers and sort by volume
            tickers = binance.fetch_tickers()
            ticker_map = {t['symbol']: t for t in tickers}
            sorted_symbols = sorted(
                all_symbols,
                key=lambda s: float(ticker_map.get(s, {}).get('quoteVolume', 0)),
                reverse=True
            )
            symbol_list = sorted_symbols[:top]
        
        # Calculate volatility for each symbol
        volatility_data = []
        
        for symbol in symbol_list[:50]:  # Limit to 50 symbols max
            try:
                ohlcv = await binance.fetch_ohlcv(symbol, interval, limit=24)  # 24 periods
                if len(ohlcv) < 10:  # Need at least 10 data points
                    continue
                
                closes = [float(candle["close"]) for candle in ohlcv]
                
                # Calculate volatility (standard deviation of returns)
                returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
                volatility = (sum(r**2 for r in returns) / len(returns))**0.5 * 100  # As percentage
                
                # Get current price info
                current_price = closes[-1]
                price_change = ((closes[-1] - closes[0]) / closes[0]) * 100
                
                volatility_data.append({
                    "symbol": symbol,
                    "volatility_percent": round(volatility, 4),
                    "current_price": current_price,
                    "price_change_percent": round(price_change, 2),
                    "data_points": len(closes)
                })
                
            except Exception as e:
                # Skip symbols that fail
                continue
        
        # Sort by volatility
        reverse_sort = sort.lower() == "desc"
        volatility_data.sort(key=lambda x: x["volatility_percent"], reverse=reverse_sort)
        
        return {
            "volatility_comparison": volatility_data,
            "analysis_params": {
                "interval": interval,
                "symbols_analyzed": len(volatility_data),
                "sort_order": sort,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Volatility comparison failed: {str(e)}")
