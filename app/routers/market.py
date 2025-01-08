from fastapi import APIRouter
from app.services.binance import get_market_data

router = APIRouter()

@router.get("/{pair}")
async def market_data(pair: str):
    """
    Fetch market data for a specific trading pair.
    """
    data = await get_market_data(pair)
    return {"pair": pair, "market_data": data}
