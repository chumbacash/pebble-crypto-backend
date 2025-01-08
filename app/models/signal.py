from pydantic import BaseModel

class Signal(BaseModel):
    symbol: str
    timeframe: str
    action: str  # BUY, SELL, HOLD
