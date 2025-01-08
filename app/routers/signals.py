from fastapi import APIRouter
from app.services.binance import get_market_data
from app.utils.signals import generate_signal

router = APIRouter()

@router.get("/{pair}")
async def generate_signals(pair: str, timeframe: str = "1h"):
    """
    Generate trading signals for a pair in a given timeframe.
    """
    market_data = await get_market_data(pair, timeframe)
    signal = generate_signal(market_data)
    return {"pair": pair, "timeframe": timeframe, "signal": signal}
