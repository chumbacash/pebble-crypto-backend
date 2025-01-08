import aioredis

redis = aioredis.from_url("redis://localhost")

async def get_cached_data(key: str):
    data = await redis.get(key)
    if data:
        return data.decode("utf-8")
    return None

async def set_cached_data(key: str, value: str, expire: int = 3600):
    await redis.set(key, value, ex=expire)
