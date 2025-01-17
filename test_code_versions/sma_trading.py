# Dependencies
import requests
import numpy as np
from time import sleep # Introduce a Delay

# Set up the session and API key
s = requests.Session()
s.headers.update({'X-API-key': 'KOTLAQPL'})  # Make sure you use YOUR API Key

# Global variables
MAX_GROSS_EXPOSURE = 250000
MAX_NET_EXPOSURE = 250000
ORDER_LIMIT = 1000 # Change based on Market Condition
MOVING_AVERAGE_PERIOD = 10
CHECK_INTERVAL = 5  # Check every 5 bars

# Function to get the latest market tick
def get_tick():
    resp = s.get('http://localhost:9999/v1/case')
    if resp.ok:
        case = resp.json()
        return case['tick'], case['status']

# Function to get the bid and ask price for a given ticker
def get_bid_ask(ticker):
    payload = {'ticker': ticker}
    resp = s.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        best_bid = book['bids'][0]['price'] if book['bids'] else None
        best_ask = book['asks'][0]['price'] if book['asks'] else None
        return best_bid, best_ask

# Function to get the time and sales data for a ticker (Historical Data)
def get_time_sales(ticker):
    payload = {'ticker': ticker}
    resp = s.get('http://localhost:9999/v1/securities/tas', params=payload)
    if resp.ok:
        return [item['price'] for item in resp.json()]
    return []

# Function to compute the Simple Moving Average (SMA)
def compute_sma(prices, period=MOVING_AVERAGE_PERIOD):
    if len(prices) < period:
        return None
    return np.mean(prices[-period:])

# Function to calculate gross and net exposure
def calculate_exposure(positions):
    gross_exposure = sum(abs(pos['position']) for pos in positions.values())
    net_exposure = sum(pos['position'] for pos in positions.values())
    return gross_exposure, net_exposure

# Function to place orders
def place_order(ticker, action, price):
    resp = s.post('http://localhost:9999/v1/orders', params={
        'ticker': ticker,
        'type': 'LIMIT',
        'quantity': ORDER_LIMIT,
        'price': price,
        'action': action
    })
    if resp.ok:
        print(f"Placed {action} order for {ticker} at {price}")
    else:
        print(f"Failed to place {action} order: {resp.text}")

# Main trading logic
def main():
    tick, status = get_tick()
    ticker_list = ['OWL', 'DUCK', 'DOVE', 'CROW']  # Add tickers as needed
    last_traded_ticks = {ticker: 0 for ticker in ticker_list}
    current_position = None  # None means no position, 'long' means bought and holding
    current_ticker = None  # Track the ticker of the current open position

    while status == 'ACTIVE':

        # Retrieves all open positions and calculates the gross and net exposures
        positions = {pos['ticker']: pos for pos in s.get('http://localhost:9999/v1/securities').json()}
        gross_exposure, net_exposure = calculate_exposure(positions)
        print(f"Gross Exposure: {gross_exposure}, Net Exposure: {net_exposure}")

        for ticker in ticker_list:
            # Skips when not enough time has passed since the last trade
            if tick < last_traded_ticks[ticker] + CHECK_INTERVAL:
                print(f"Skipping {ticker} as it hasn't reached CHECK_INTERVAL")
                continue
            
            prices = get_time_sales(ticker)
            if len(prices) < MOVING_AVERAGE_PERIOD:
                print(f"Not enough data for {ticker}. Skipping...")
                continue

            sma = compute_sma(prices)
            if sma is None:
                print(f"SMA is None for {ticker}, skipping...")
                continue

            best_bid, best_ask = get_bid_ask(ticker)
            if not best_bid or not best_ask:
                print(f"No bid/ask data for {ticker}. Skipping...")
                continue

            # Debugging prints
            print(f"{ticker} | SMA: {sma}, Best Bid: {best_bid}, Best Ask: {best_ask}")
            print(f"Current Position: {current_position}")

            # Check for buy condition: only buy if no position is currently held
            if current_position is None and best_bid > sma and gross_exposure < MAX_GROSS_EXPOSURE:
                print(f"Buy Condition Met for {ticker}")
                place_order(ticker, 'BUY', best_bid)
                current_position = 'long'  # We now hold a long position
                current_ticker = ticker  # Set the ticker we bought
                last_traded_ticks[ticker] = tick

            # Check for sell condition: only sell if we hold the current position
            elif current_position == 'long' and ticker == current_ticker and best_bid < sma and net_exposure > -MAX_NET_EXPOSURE:
                print(f"Sell Condition Met for {ticker}")
                place_order(ticker, 'SELL', best_ask)
                current_position = None  # We no longer hold a position
                current_ticker = None  # Reset current position ticker
                last_traded_ticks[ticker] = tick

        tick, status = get_tick()
        sleep(1)  # Wait a second before the next iteration

if __name__ == '__main__':
    main()
