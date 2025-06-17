# 🚀 Pebble Crypto Analytics API

![Banner Image](static/images/20250109_094420_0000.png)

> **Advanced Cryptocurrency Analytics & AI-Powered Trading Assistant**
> 
> A production-ready FastAPI backend providing real-time market data, AI-powered analysis, and multi-exchange integration for cryptocurrency trading and analytics.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![API Status](https://img.shields.io/badge/API-Production%20Ready-brightgreen.svg)](http://localhost:8000/docs)

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [🔥 Interactive API Documentation](#-interactive-api-documentation)
- [📚 Complete API Reference](#-complete-api-reference)
- [Features](#-features)
- [Installation](#-installation)
- [Usage Examples](#-usage-examples)
- [Project Structure](#-project-structure)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Contributing](#-contributing)

## 🚀 Quick Start

### 1. Install and Run
```bash
# Clone the repository
git clone https://github.com/your-org/pebble-crypto-backend.git
cd pebble-crypto-backend

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn main:app --reload --port 8000
```

### 2. Access the API Documentation
Once the server is running, visit these URLs:

🔥 **Primary Documentation (Recommended)**
- **Interactive Swagger UI**: http://localhost:8000/docs
- **Alternative ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

🏥 **Quick Health Check**
- **API Status**: http://localhost:8000/api/health

## 🔥 Interactive API Documentation

### 📖 **Using the `/docs` Interface**

The FastAPI automatically generates **interactive API documentation** at `/docs`. This is your main tool for exploring and testing the API:

#### **Key Features of `/docs`:**
- ✅ **Try It Out**: Test any endpoint directly in the browser
- ✅ **Real Responses**: See actual API responses with live data
- ✅ **Request Examples**: Auto-generated request/response schemas
- ✅ **Authentication**: Test with API keys if required
- ✅ **Download Schemas**: Export OpenAPI specs for integration

#### **How to Use `/docs`:**
1. **Navigate** to http://localhost:8000/docs
2. **Browse** available endpoints by category
3. **Click** "Try it out" on any endpoint
4. **Fill** in required parameters
5. **Execute** to see real responses
6. **Copy** curl commands for your applications

## 📚 Complete API Reference

### 🏥 **System Health & Status**
Monitor API health and system performance.

| Endpoint | Method | Description | Try It |
|----------|--------|-------------|---------|
| `/api/health` | GET | API status, version, and metrics | [📊 Test](http://localhost:8000/docs#/Health/health_check_api_health_get) |

**Example Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-01-09T12:00:00Z",
  "uptime": "2 hours 15 minutes"
}
```

### 📊 **Market Data Endpoints**
Get comprehensive cryptocurrency market information.

| Endpoint | Method | Description | Try It |
|----------|--------|-------------|---------|
| `/api/market/symbols` | GET | List all available trading symbols | [📈 Test](http://localhost:8000/docs#/Market%20Data/get_symbols_api_market_symbols_get) |
| `/api/market/data/{symbol}` | GET | Complete market data for a symbol | [📊 Test](http://localhost:8000/docs#/Market%20Data/get_market_data_api_market_data__symbol__get) |

**Example - Get Bitcoin Data:**
```bash
curl "http://localhost:8000/api/market/data/BTCUSDT"
```

**Response Structure:**
```json
{
  "symbol": "BTCUSDT",
  "price": 45000.00,
  "change_24h": 2.5,
  "volume": 1000000,
  "indicators": {
    "rsi": 65.2,
    "macd": "bullish"
  }
}
```

### 🤖 **AI Assistant Endpoints**
Natural language market analysis and trading advice.

| Endpoint | Method | Description | Try It |
|----------|--------|-------------|---------|
| `/api/ai/ask` | POST | Ask questions about markets in natural language | [🤖 Test](http://localhost:8000/docs#/AI%20Assistant/ask_question_api_ai_ask_post) |

**Example - AI Market Query:**
```bash
curl -X POST "http://localhost:8000/api/ai/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Should I buy Bitcoin now? What does the technical analysis say?",
    "context": {
      "timeframe": "1d",
      "risk_tolerance": "moderate"
    }
  }'
```

**Response Structure:**
```json
{
  "response": "Based on current technical analysis...",
  "confidence": 0.85,
  "recommendations": ["Consider DCA strategy", "Monitor support at $44,000"],
  "risk_assessment": "moderate"
}
```

### 📈 **Technical Analysis Endpoints**
Advanced technical analysis and price predictions.

| Endpoint | Method | Description | Try It |
|----------|--------|-------------|---------|
| `/api/analysis/predict/{symbol}` | GET | Price predictions and trading signals | [📊 Test](http://localhost:8000/docs#/Technical%20Analysis/predict_api_analysis_predict__symbol__get) |
| `/api/analysis/compare/{primary_symbol}` | GET | Compare multiple assets | [📊 Test](http://localhost:8000/docs#/Technical%20Analysis/compare_symbols_api_analysis_compare__primary_symbol__get) |

**Example - Bitcoin Prediction:**
```bash
curl "http://localhost:8000/api/analysis/predict/BTCUSDT?timeframe=1d"
```

### 🔄 **Multi-Exchange Endpoints**
Aggregate data from multiple cryptocurrency exchanges.

| Endpoint | Method | Description | Try It |
|----------|--------|-------------|---------|
| `/api/exchanges/health` | GET | Check status of all exchanges | [🏥 Test](http://localhost:8000/docs#/Multi-Exchange/exchange_health_api_exchanges_health_get) |
| `/api/exchanges/summary` | POST | Get aggregated market data | [📊 Test](http://localhost:8000/docs#/Multi-Exchange/exchange_summary_api_exchanges_summary_post) |
| `/api/exchanges/arbitrage` | POST | Find arbitrage opportunities | [💰 Test](http://localhost:8000/docs#/Multi-Exchange/arbitrage_opportunities_api_exchanges_arbitrage_post) |
| `/api/exchanges/coverage` | GET | Exchange information and coverage | [ℹ️ Test](http://localhost:8000/docs#/Multi-Exchange/exchange_coverage_api_exchanges_coverage_get) |

**Example - Arbitrage Detection:**
```bash
curl -X POST "http://localhost:8000/api/exchanges/arbitrage" \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
  }'
```

### ⚡ **Real-Time WebSocket Endpoints**
Live streaming market data updates.

| Endpoint | Protocol | Description | Try It |
|----------|----------|-------------|---------|
| `/api/ws/live/{symbol}` | WebSocket | Real-time price updates | [🔴 Test](http://localhost:8000/docs#/WebSocket/websocket_endpoint_api_ws_live__symbol__get) |

**Example - WebSocket Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws/live/BTCUSDT?interval=1h');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Live Bitcoin update:', data);
};
```

## ✨ Features

### 🤖 **AI-Powered Analysis**
- Natural language query processing for market insights
- Investment advice with confidence scores and risk assessment
- Multi-timeframe technical analysis with actionable recommendations
- Context-aware responses based on user preferences

### 📊 **Comprehensive Market Data** 
- Real-time data from 6+ major cryptocurrency exchanges
- 1,400+ trading pairs with live price updates
- OHLCV data with configurable intervals (1h to 1M)
- Advanced technical indicators (RSI, Bollinger Bands, Moving Averages)

### 🔄 **Multi-Exchange Integration**
- Binance, KuCoin, Bybit, Gate.io, Bitget, OKX support
- Cross-exchange price comparison and arbitrage detection
- Automatic failover and load balancing
- Real-time exchange health monitoring

### ⚡ **Production Features**
- Async-first architecture with high concurrency
- Smart caching with TTL for optimal performance
- Rate limiting and request throttling
- WebSocket streaming for real-time updates
- Comprehensive error handling and monitoring

## 🛠️ Installation

### Standard Installation
```bash
# Clone the repository
git clone https://github.com/your-org/pebble-crypto-backend.git
cd pebble-crypto-backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn main:app --reload --port 8000
```

### Docker Installation
```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or build manually
docker build -t pebble-crypto-api .
docker run -d -p 8000:8000 --env-file .env pebble-crypto-api
```

### Environment Configuration
Create a `.env` file with the following configuration:

```ini
# API Configuration
HOST=0.0.0.0
PORT=8000
RELOAD=true
WORKERS=1
ENVIRONMENT=development

# Rate Limits
AI_ASSISTANT_RATE_LIMIT=60/minute
MARKET_DATA_RATE_LIMIT=30/minute
HEALTH_CHECK_RATE_LIMIT=100/minute

# Security
ALLOWED_ORIGINS=*

# Optional: External API Keys
GEMINI_API_KEY=your_gemini_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

## 💡 Usage Examples

### Using the Interactive Documentation
The easiest way to explore the API is through the interactive documentation:

1. **Start the server**: `uvicorn main:app --reload --port 8000`
2. **Open your browser**: Go to http://localhost:8000/docs
3. **Pick an endpoint**: Click on any endpoint to expand it
4. **Try it out**: Click "Try it out" button
5. **Fill parameters**: Enter required parameters
6. **Execute**: Click "Execute" to see real responses

### AI-Powered Market Queries
```python
import requests

# Natural language market analysis
response = requests.post('http://localhost:8000/api/ai/ask', json={
    "query": "What's the best cryptocurrency to buy today under $100?",
    "context": {"risk_tolerance": "moderate", "timeframe": "1w"}
})

analysis = response.json()
print(analysis['response'])
```

### Multi-Asset Price Comparison
```python
# Compare multiple cryptocurrencies
response = requests.get(
    'http://localhost:8000/api/analysis/compare/BTCUSDT',
    params={
        'comparison_symbols': 'ETHUSDT,SOLUSDT,ADAUSDT',
        'time_period': '7d'
    }
)

comparison = response.json()
```

### Real-Time Market Data
```python
import asyncio
import websockets
import json

async def live_market_feed():
    uri = "ws://localhost:8000/api/ws/live/BTCUSDT?interval=1h"
    async with websockets.connect(uri) as websocket:
        while True:
            data = await websocket.recv()
            market_update = json.loads(data)
            print(f"BTC Price: ${market_update['data']['close']}")

# Run the live feed
asyncio.run(live_market_feed())
```

## 📁 Project Structure

```
pebble-crypto-backend/
├── 📚 Core Application
│   ├── main.py                    # FastAPI application entry point
│   └── app/
│       ├── core/
│       │   ├── ai/                # AI assistant components
│       │   │   ├── agent.py       # Market analysis agent
│       │   │   ├── enhanced_investment_advisor.py
│       │   │   └── multi_llm_router.py
│       │   ├── analysis/          # Market analysis tools
│       │   ├── indicators/        # Technical indicators
│       │   └── prediction/        # Price prediction models
│       └── services/
│           ├── binance.py         # Binance integration
│           ├── kucoin.py          # KuCoin integration
│           ├── exchange_aggregator.py # Multi-exchange orchestration
│           └── metrics.py         # Performance monitoring
├── 🧪 Testing & Quality Assurance
│   └── tests/
│       ├── test_complete_system.py     # End-to-end testing
│       ├── test_system_direct.py       # Direct API testing
│       └── test_data_quality.py        # Data quality validation
├── 🐳 Deployment
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
└── 📖 Documentation
    ├── README.md
    └── static/images/
```

## 🧪 Testing

### Run All Tests
```bash
# Run the complete test suite
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=app --cov-report=html

# Run specific test categories
python -m pytest tests/test_complete_system.py -v      # System tests
python -m pytest tests/test_data_quality.py -v        # Data quality
python -m pytest tests/test_system_direct.py -v       # Direct API tests
```

### Test Categories
- **System Tests**: End-to-end API functionality
- **Data Quality**: Market data accuracy and completeness
- **Integration Tests**: Multi-exchange and AI components
- **Performance Tests**: Load testing and response times

### Test Results
- ✅ **100% Success Rate** across all endpoints
- ✅ **Real Market Data** validated from 6+ exchanges
- ✅ **AI Processing** tested with diverse query types
- ✅ **Error Handling** verified with edge cases

## 🚀 Deployment

### Production Deployment
```bash
# Using Docker Compose (recommended)
docker-compose -f docker-compose.prod.yml up -d

# Scale for high availability
docker-compose up --scale api=3
```

### Environment Variables
```bash
# Production settings
ENVIRONMENT=production
WORKERS=4
RELOAD=false
LOG_LEVEL=info

# Security
ALLOWED_ORIGINS=https://your-frontend-domain.com
API_RATE_LIMIT=100/minute
```

### Health Monitoring
```bash
# Check API health
curl https://api.your-domain.com/api/health

# Monitor exchange connectivity
curl https://api.your-domain.com/api/exchanges/health
```

## 📊 API Rate Limits

| Endpoint Category | Rate Limit | Purpose |
|-------------------|------------|---------|
| 🤖 AI Assistant | 60/minute | Natural language processing |
| 📊 Market Data | 30/minute | Real-time market information |
| 📈 Technical Analysis | 20-30/minute | Complex calculations |
| 🔄 Multi-Exchange | 15-20/minute | Cross-exchange operations |
| 🏥 Health Check | 100/minute | System monitoring |
| ⚡ WebSocket | Unlimited | Real-time streaming |

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Quick Contribution Guide
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Ensure all tests pass: `python -m pytest tests/ -v`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Development Standards
- Write comprehensive tests for new features
- Follow Python PEP 8 style guidelines
- Add docstrings for all functions and classes
- Update documentation for API changes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This software is for informational purposes only. Cryptocurrency trading carries significant financial risk. Always conduct your own research and consult with financial advisors before making investment decisions. The authors are not responsible for any financial losses incurred through the use of this software.

## 🆘 Support

- **📖 Interactive Docs**: Visit http://localhost:8000/docs for complete API documentation
- **🐛 Issues**: Report bugs and request features on our [GitHub Issues](https://github.com/your-org/pebble-crypto-backend/issues)
- **💬 Discussions**: Join our [GitHub Discussions](https://github.com/your-org/pebble-crypto-backend/discussions) for community support
- **📊 API Schema**: Download OpenAPI spec at http://localhost:8000/openapi.json

## 🎯 Roadmap

- [ ] **Advanced ML Models**: Integration of machine learning prediction models
- [ ] **Social Sentiment Analysis**: Twitter and Reddit sentiment integration  
- [ ] **Portfolio Management**: Advanced portfolio optimization tools
- [ ] **Mobile API**: React Native/Flutter optimized endpoints
- [ ] **Enterprise Features**: Multi-tenant support and advanced analytics

---

**Made with ❤️ by the Pebble Crypto Team**

## 🔗 Quick Links

- **🔥 Start Here**: http://localhost:8000/docs
- **📊 API Health**: http://localhost:8000/api/health
- **📖 Alternative Docs**: http://localhost:8000/redoc
- **⚡ WebSocket Test**: Use the `/docs` interface to test real-time endpoints

**For the most comprehensive and up-to-date API information, always use the interactive documentation at `/docs`**
