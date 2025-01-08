![Banner Image](icons/banner.png)

# Pebble Crypto Backend
This is the backend service for the **Pebble Crypto** app, a cryptocurrency signals platform built using **FastAPI**.

## Project Structure

```
pebble_crypto_backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints.py
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   ├── models/
│   │   ├── market.py
│   │   ├── pair.py
│   │   └── signal.py
│   ├── routers/
│   │   ├── market.py
│   │   ├── pairs.py
│   │   └── signals.py
│   ├── services/
│   │   ├── binance.py
│   │   └── coingecko.py
│   └── utils/
│       ├── cache.py
│       ├── fetch.py
│       └── signals.py
├── tests/
│   ├── test_market.py
│   ├── test_pairs.py
│   ├── test_services.py
│   └── test_signals.py
├── .gitignore                 # Git-related files (hidden)
├── requirements.txt           # Dependencies
└── venv/                      # Virtual environment (ignore this folder when viewing files)
 
```

## Setup

To set up the backend, follow the instructions below.

### Prerequisites

- Python 3.9 or higher
- Pip (Python package manager)

### Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/chumbacash/pebble-crypto-backend.git
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
   ```

### Disclaimer:

This repository is created by Chumbacash and is intended for personal projects only. Use it at your own risk. Nothing in this repository constitutes financial advice.

Happy Day friends🎇🎉
