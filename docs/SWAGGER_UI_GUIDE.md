# 📖 Using the Swagger UI (`/docs`) for Pebble Crypto Analytics API

> **File reference:** The Swagger (OpenAPI) interface is wired up in `app/main.py` via the `docs_url="/docs"` and `redoc_url="/redoc"` parameters when the `FastAPI` instance is created.
>
> This guide walks you through opening that interface, understanding its layout, and interacting with **every public endpoint** without writing a single line of code.

---

## 1. Prerequisites

1. Python ≥ 3.8
2. Project dependencies installed

```bash
# from the repo root
pip install -r requirements.txt
```

3. Run the API locally (hot-reload is fine):

```bash
uvicorn main:app --reload --port 8000
```

When you see `🚀 Pebble Crypto Analytics API v0.4.0 starting up…` in the console the service is live.

---

## 2. Open the Swagger UI

Visit:

```
http://localhost:8000/docs
```

You'll land on an **interactive Swagger UI** generated from the OpenAPI schema that `FastAPI` builds automatically from our route definitions.

*If you prefer ReDoc's minimalist look, use* `http://localhost:8000/redoc`.

---

## 3. UI Orientation

| UI Zone | What It Shows |
|---------|---------------|
| **Top Bar** | API title, version and a search field. |
| **Tag Sections** | Endpoints are grouped by the `tags=[…]` we pass in `app/main.py`.  Each tag is a collapsible section. |
| **Path Row** | A single endpoint (HTTP method + path). Click to expand for full details. |
| **"Try it out" Button** | Turns the row into an editable form so you can supply parameters / body and execute live requests. |
| **Response Pane** | Shows the actual request sent & the JSON response, status code, headers, etc. |

> **Tip:** Because we enabled CORS for `*` and there's no auth by default, you can call everything directly from the browser.

---

## 4. Testing Each Endpoint

Below you'll find a quick-start checklist for every tag.  In the UI simply:
1. Expand the **tag**.
2. Click the **path row**.
3. Press **Try it out**.
4. Fill in any parameters.
5. Hit **Execute** and observe the response.

### 4.1 Health
| Path | Purpose | Notes |
|------|---------|-------|
| `GET /api/health` | Liveness/readiness probe | Returns version, uptime, cache stats, etc. |

### 4.2 Market Data
| Path | Purpose |
|------|---------|
| `GET /api/market/symbols` | List all tradable symbols (≈ 1,400+) |
| `GET /api/market/data/{symbol}` | Raw market snapshot incl. OHLCV & indicators |

*Parameters*: `interval`, `limit`, `include_indicators` (boolean)

### 4.3 Technical Analysis
| Path | Purpose | Example Params |
|------|---------|----------------|
| `GET /api/analysis/predict/{symbol}` | ML-based price prediction | `interval=1h` |
| `GET /api/analysis/compare/{primary_symbol}` | Multi-asset comparison | `comparison_symbols=ETHUSDT,SOLUSDT`,  `time_period=7d` |

### 4.4 AI Assistant
| Path | Method | Body |
|------|--------|------|
| `/api/ai/ask` | **POST** | `{ "query": "Should I buy Bitcoin now?", "context": {"timeframe":"1d"} }` |

After pressing **Execute** you'll receive a full natural-language answer plus metadata (confidence, risk, etc.).

### 4.5 Multi-Exchange
| Path | Purpose |
|------|---------|
| `GET /api/exchanges/health` | Real-time status for Binance, KuCoin, Bybit, Gate.io, Bitget, OKX |
| `GET /api/exchanges/coverage` | Exchange + symbol coverage matrix |
| `POST /api/exchanges/summary` | Aggregated market summary (top gainers/losers). Body optional. |
| `POST /api/exchanges/arbitrage` | Detect arbitrage across exchanges. Body: `{ "symbols": ["BTCUSDT","ETHUSDT"] }` |

### 4.6 Market Advisor
| Path | Purpose |
|------|---------|
| `GET /api/advisor/market-overview` | AI-curated macro market overview | Query param: `top_n` (default 10) |

### 4.7 WebSocket (Docs Only)
Swagger can't open WS connections, but you can still inspect the schema.

| Path | Description |
|------|-------------|
| `GET /api/ws/live/{symbol}` | Real-time OHLCV updates. e.g. `ws://localhost:8000/api/ws/live/BTCUSDT?interval=1h` |

---

## 5. Saving & Sharing Requests
Swagger UI auto-generates the **curl** command for each executed request.  Copy it into your CLI test scripts or documentation.

---

## 6. Troubleshooting
| Issue | Fix |
|-------|-----|
| `CORS` errors | Ensure you're browsing from `localhost` (same host) or whitelist your origin in `.env` → `ALLOWED_ORIGINS`. |
| 5xx response | Check the backend logs in the terminal.  The stack trace pinpoints the failing exchange/provider. |
| "Network Error" in UI | Backend not running or wrong port. Verify `uvicorn` is active. |

---

## 7. Going Beyond Swagger
* **ReDoc** (`/redoc`) offers a static read-only doc view.
* Download **OpenAPI JSON** (`/openapi.json`) to generate client SDKs with tools like `openapi-generator` or `swagger-codegen`.

---

### 📬 Feedback
Found a doc bug or have a UI suggestion?  Open an issue or reach the team at **api@pebblecrypto.com**.

Enjoy effortless testing! 🚀 