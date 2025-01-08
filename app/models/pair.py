from pydantic import BaseModel

class Pair(BaseModel):
    symbol: str
    base: str
    quote: str
