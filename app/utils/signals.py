def generate_signal(market_data):
    """
    Simple signal generation logic based on moving averages.
    """
    close_prices = [float(entry[4]) for entry in market_data]  # Closing prices
    short_ma = sum(close_prices[-7:]) / 7  # 7-period moving average
    long_ma = sum(close_prices) / len(close_prices)  # Full-period moving average

    if short_ma > long_ma:
        return "BUY"
    elif short_ma < long_ma:
        return "SELL"
    else:
        return "HOLD"
