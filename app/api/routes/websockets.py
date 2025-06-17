"""
WebSocket endpoints for real-time cryptocurrency data streaming
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
import asyncio
import json
import logging
from typing import Dict, Set
from datetime import datetime, timezone

from app.core.dependencies import get_binance_client

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger("CryptoPredictAPI")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, symbol: str):
        await websocket.accept()
        if symbol not in self.active_connections:
            self.active_connections[symbol] = set()
        self.active_connections[symbol].add(websocket)
        logger.info(f"WebSocket connected for {symbol}. Total connections: {len(self.active_connections[symbol])}")

    def disconnect(self, websocket: WebSocket, symbol: str):
        if symbol in self.active_connections:
            self.active_connections[symbol].discard(websocket)
            if not self.active_connections[symbol]:
                del self.active_connections[symbol]
        logger.info(f"WebSocket disconnected for {symbol}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def broadcast(self, symbol: str, message: str):
        if symbol in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[symbol]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to connection: {e}")
                    disconnected.add(connection)
            
            # Remove disconnected connections
            self.active_connections[symbol] -= disconnected

manager = ConnectionManager()

@router.websocket("/live/{symbol}")
async def websocket_live_data(
    websocket: WebSocket, 
    symbol: str,
    binance=Depends(get_binance_client)
):
    """
    WebSocket endpoint for real-time price updates for a specific cryptocurrency symbol.
    
    Provides:
    - Real-time price updates every 1-2 seconds
    - 24h price change information
    - Volume data
    - Timestamp information
    
    Usage:
    - Connect to: ws://localhost:8000/api/ws/live/BTCUSDT
    - Replace BTCUSDT with your desired trading pair
    """
    symbol = symbol.upper()
    await manager.connect(websocket, symbol)
    
    try:
        # Send initial connection confirmation
        await manager.send_personal_message(json.dumps({
            "type": "connection",
            "symbol": symbol,
            "status": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": f"Connected to live data stream for {symbol}"
        }), websocket)
        
        # Start data streaming loop
        while True:
            try:
                # Get current ticker data
                ticker_data = await binance.get_ticker(symbol)
                
                if ticker_data:
                    # Format the data for WebSocket
                    stream_data = {
                        "type": "price_update",
                        "symbol": symbol,
                        "price": ticker_data.get("price"),
                        "price_change_24h": ticker_data.get("priceChangePercent"),
                        "volume_24h": ticker_data.get("volume24h"),
                        "high_24h": ticker_data.get("high24h"),
                        "low_24h": ticker_data.get("low24h"),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Send data to this specific connection
                    await manager.send_personal_message(json.dumps(stream_data), websocket)
                else:
                    # Send error message if no data available
                    error_data = {
                        "type": "error",
                        "symbol": symbol,
                        "message": "No ticker data available",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    await manager.send_personal_message(json.dumps(error_data), websocket)
                
                # Wait before next update (1 second intervals)
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in live data stream for {symbol}: {e}")
                error_data = {
                    "type": "error",
                    "symbol": symbol,
                    "message": f"Stream error: {str(e)}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await manager.send_personal_message(json.dumps(error_data), websocket)
                await asyncio.sleep(5)  # Wait longer on errors
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, symbol)
        logger.info(f"WebSocket disconnected for {symbol}")
    except Exception as e:
        logger.error(f"WebSocket error for {symbol}: {e}")
        manager.disconnect(websocket, symbol)

@router.websocket("/multi")
async def websocket_multi_symbol(
    websocket: WebSocket,
    binance=Depends(get_binance_client)
):
    """
    WebSocket endpoint for real-time data on multiple symbols.
    
    Send a JSON message to subscribe to multiple symbols:
    {"action": "subscribe", "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]}
    
    Send a JSON message to unsubscribe:
    {"action": "unsubscribe", "symbols": ["BTCUSDT"]}
    """
    await websocket.accept()
    subscribed_symbols: Set[str] = set()
    
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Connected to multi-symbol stream. Send subscription messages to start receiving data."
        }))
        
        async def data_sender():
            """Background task to send data for subscribed symbols"""
            while True:
                if subscribed_symbols:
                    for symbol in list(subscribed_symbols):  # Create a copy to avoid modification during iteration
                        try:
                            ticker_data = await binance.get_ticker(symbol)
                            
                            if ticker_data:
                                stream_data = {
                                    "type": "price_update",
                                    "symbol": symbol,
                                    "price": ticker_data.get("price"),
                                    "price_change_24h": ticker_data.get("priceChangePercent"),
                                    "volume_24h": ticker_data.get("volume24h"),
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }
                                await websocket.send_text(json.dumps(stream_data))
                                
                        except Exception as e:
                            logger.error(f"Error getting data for {symbol}: {e}")
                            continue
                            
                await asyncio.sleep(2)  # Update every 2 seconds for multi-symbol
        
        # Start the data sender task
        data_task = asyncio.create_task(data_sender())
        
        try:
            # Listen for subscription messages
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    action = message.get("action")
                    symbols = message.get("symbols", [])
                    
                    if action == "subscribe":
                        for symbol in symbols:
                            symbol = symbol.upper()
                            subscribed_symbols.add(symbol)
                        
                        await websocket.send_text(json.dumps({
                            "type": "subscription",
                            "action": "subscribed",
                            "symbols": list(subscribed_symbols),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }))
                        
                    elif action == "unsubscribe":
                        for symbol in symbols:
                            symbol = symbol.upper()
                            subscribed_symbols.discard(symbol)
                            
                        await websocket.send_text(json.dumps({
                            "type": "subscription",
                            "action": "unsubscribed",
                            "symbols": list(subscribed_symbols),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }))
                        
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "Invalid action. Use 'subscribe' or 'unsubscribe'",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }))
                        
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }))
                    
        finally:
            # Cancel the data sender task when connection closes
            data_task.cancel()
            
    except WebSocketDisconnect:
        logger.info("Multi-symbol WebSocket disconnected")
    except Exception as e:
        logger.error(f"Multi-symbol WebSocket error: {e}")

@router.get("/connections", tags=["WebSocket"])
@limiter.limit("20/minute")
async def get_websocket_stats(request: Request):
    """
    Get statistics about active WebSocket connections.
    
    Returns information about:
    - Total active connections
    - Connections per symbol
    - Connection timestamps
    """
    try:
        stats = {
            "total_symbols": len(manager.active_connections),
            "total_connections": sum(len(connections) for connections in manager.active_connections.values()),
            "connections_by_symbol": {
                symbol: len(connections) for symbol, connections in manager.active_connections.items()
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"WebSocket stats error: {e}")
        return {
            "error": "Failed to get WebSocket statistics",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
