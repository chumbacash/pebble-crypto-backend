from fastapi import APIRouter
from app.services.binance import fetch_trading_pairs

router = APIRouter()

@router.get("/trading-pairs")
async def get_trading_pairs():
    """
    Endpoint to fetch and return trading pairs from Binance.
    """
    pairs = await fetch_trading_pairs()
    return {"trading_pairs": pairs}
