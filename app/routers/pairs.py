from fastapi import APIRouter
from app.services.binance import get_trading_pairs

router = APIRouter()

@router.get("/")
async def list_pairs():
    """
    Endpoint to get available trading pairs.
    """
    pairs = await get_trading_pairs()
    return {"pairs": pairs}
