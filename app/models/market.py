from pydantic import BaseModel

class MarketData(BaseModel):
    symbol: str
    high: float
    low: float
    close: float
    volume: float
    timeframe: str
