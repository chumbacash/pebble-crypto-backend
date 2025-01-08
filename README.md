# Pebble Crypto Backend

This is the backend service for the **Pebble Crypto** app, a cryptocurrency signals platform built using **FastAPI**.

## Project Structure

```
pebble_crypto_backend/
├── app/
│   ├── main.py         # FastAPI app entry point
│   ├── routers/        # API routes
│   │   ├── pairs.py    # Pairs endpoint logic
│   │   ├── market.py   # Market data endpoint logic
│   │   ├── signals.py  # Signal generation logic
│   ├── services/       # External API services
│   │   ├── binance.py  # Binance API integration
│   │   ├── coingecko.py # CoinGecko API integration (optional)
│   ├── utils/          # Utility functions
│   └── models/         # Data models
├── tests/              # Test cases
└── requirements.txt    # Dependencies
```

## Setup

To set up the backend, follow the instructions below.

### Prerequisites

- Python 3.9 or higher
- Pip (Python package manager)

### Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/your-username/pebble_crypto_backend.git
   cd pebble_crypto_backend

2. Setup a virtual environment:

   ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

3. Install dependecies:
   
   ```bash
   pip install -r requirements.txt

Running the Application:
To start the development server:

    ```bash
    uvicorn app.main:app --reload
