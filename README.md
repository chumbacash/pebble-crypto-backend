<<<<<<< HEAD
![Banner Image](static/images/20250109_094420_0000.png )
=======
# 🚀 Pebble Crypto Analytics API
>>>>>>> 10e0e2c (update commit)

![Banner Image](static/images/20250109_094420_0000.png)

> **Advanced Cryptocurrency Analytics & AI-Powered Trading Assistant**
> 
> A production-ready FastAPI backend providing real-time market data, AI-powered analysis, and multi-exchange integration for cryptocurrency trading and analytics.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![API Status](https://img.shields.io/badge/API-Production%20Ready-brightgreen.svg)](http://localhost:8000/docs)

## 📋 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [API Documentation](#-api-documentation)
- [Installation](#-installation)
- [Usage Examples](#-usage-examples)
- [Project Structure](#-project-structure)
- [Development](#-development)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [License](#-license)

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

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### 1. Clone and Install
```bash
git clone https://github.com/your-org/pebble-crypto-backend.git
cd pebble-crypto-backend

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit configuration (optional - works with defaults)
nano .env
```

### 3. Run the API
```bash
# Start the development server
uvicorn main:app --reload --port 8000

# Verify it's running
curl http://localhost:8000/api/health
```

### 4. Explore the API
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health

## 📚 API Documentation

### 🏥 **System Health**
```http
GET /api/health
```
Get API status, version, and system health metrics.

### 📊 **Market Data**
```http
GET /api/market/symbols                    # Get all trading symbols
GET /api/market/data/{symbol}              # Comprehensive market data
```

### 🤖 **AI Assistant** 
```http
POST /api/ai/ask
Content-Type: application/json

{
  "query": "Should I buy Bitcoin now? What does the technical analysis say?",
  "context": {"timeframe": "1d", "risk_tolerance": "moderate"}
}
```

### 📈 **Technical Analysis**
```http
GET /api/analysis/predict/{symbol}         # Price predictions & signals
GET /api/analysis/compare/{primary_symbol} # Multi-asset comparison
```

### 🔄 **Multi-Exchange**
```http
GET /api/exchanges/health                  # Exchange status monitoring
POST /api/exchanges/summary                # Market data aggregation
POST /api/exchanges/arbitrage              # Arbitrage opportunities
GET /api/exchanges/coverage                # Exchange information
```

### ⚡ **Real-Time Data**
```javascript
// WebSocket connection
const ws = new WebSocket('ws://localhost:8000/api/ws/live/BTCUSDT?interval=1h');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Live update:', data);
};
```

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

### Multi-Exchange Arbitrage Detection
```python
# Find arbitrage opportunities
response = requests.post('http://localhost:8000/api/exchanges/arbitrage', json={
    "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
})

opportunities = response.json()
for opportunity in opportunities.get('arbitrage_opportunities', []):
    print(f"{opportunity['symbol']}: {opportunity['profit_potential']:.2f}% profit potential")
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

## 🔧 Development

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run with auto-reload
uvicorn main:app --reload --port 8000

# Run in development mode with detailed logging
export ENVIRONMENT=development
uvicorn main:app --reload --log-level debug
```

### Code Quality
```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy app/

# Security check
bandit -r app/
```

### Adding New Features
1. Create feature branch: `git checkout -b feature/new-feature`
2. Implement changes in the appropriate `app/` subdirectory
3. Add comprehensive tests in `tests/`
4. Update API documentation
5. Submit pull request

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

- **Documentation**: Visit http://localhost:8000/docs for interactive API documentation
- **Issues**: Report bugs and request features on our [GitHub Issues](https://github.com/your-org/pebble-crypto-backend/issues)
- **Discussions**: Join our [GitHub Discussions](https://github.com/your-org/pebble-crypto-backend/discussions) for community support

## 🎯 Roadmap

- [ ] **Advanced ML Models**: Integration of machine learning prediction models
- [ ] **Social Sentiment Analysis**: Twitter and Reddit sentiment integration  
- [ ] **Portfolio Management**: Advanced portfolio optimization tools
- [ ] **Mobile API**: React Native/Flutter optimized endpoints
- [ ] **Enterprise Features**: Multi-tenant support and advanced analytics

---

<<<<<<< HEAD
**For the most up-to-date information, always check:**
1. 📚 `/docs` folder for detailed documentation
2. 🧪 `/tests` folder for current functionality verification  
3. 🔄 Recent commits for breaking changes
4. 📊 API documentation at `http://localhost:8000/docs`
=======
**Made with ❤️ by the Pebble Crypto Team**

*For the latest updates and detailed API documentation, visit http://localhost:8000/docs*
>>>>>>> 10e0e2c (update commit)
