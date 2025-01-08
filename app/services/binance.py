import httpx

BASE_URL = "https://api.binance.com"

async def get_trading_pairs():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v3/exchangeInfo")
        data = response.json()
        pairs = [symbol["symbol"] for symbol in data["symbols"]]
        return pairs

async def get_market_data(pair: str, interval: str = "1h"):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/v3/klines?symbol={pair}&interval={interval}&limit=100"
        )
        data = response.json()
        return data
