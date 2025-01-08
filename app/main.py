from fastapi import FastAPI
from app.routers import pairs, market, signals

app = FastAPI(
    title="Pebble Crypto Backend",
    description="API backend for Pebble Crypto app.",
    version="1.0.0",
)

# Include routes
app.include_router(pairs.router, prefix="/pairs", tags=["Pairs"])
app.include_router(market.router, prefix="/market", tags=["Market"])
app.include_router(signals.router, prefix="/signals", tags=["Signals"])
