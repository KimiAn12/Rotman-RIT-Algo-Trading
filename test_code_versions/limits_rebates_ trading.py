'''
This strategy was primarily implemented within the spread trading algorithm.

Below is a straightforward concept Ive coded to test its viability. 
'''

import requests
from time import sleep

# Create a session for API requests
s = requests.Session()
s.headers.update({'X-API-key': 'EDKSMGPU'})  # Replace with your actual API key

# Constants
ORDER_QUANTITY = 100  # Set a fixed order quantity (adjust as needed)
REBATE_MARKET = ['CROW', 'DOVE']  # Favorable for market orders
REBATE_LIMIT = ['OWL', 'DUCK']    # Favorable for limit orders

def get_bid_ask(ticker):
    """Fetch the best bid and ask prices for a given ticker."""
    payload = {'ticker': ticker}
    resp = s.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        bid_price = book['bids'][0]['price'] if book['bids'] else None
        ask_price = book['asks'][0]['price'] if book['asks'] else None
        return bid_price, ask_price
    return None, None

def place_limit_order(ticker, quantity, price, action):
    """Place a limit order for the given ticker."""
    s.post('http://localhost:9999/v1/orders', params={
        'ticker': ticker,
        'type': 'LIMIT',
        'quantity': quantity,
        'price': price,
        'action': action
    })

def place_market_order(ticker, quantity, action):
    """Place a market order for the given ticker."""
    s.post('http://localhost:9999/v1/orders', params={
        'ticker': ticker,
        'type': 'MARKET',
        'quantity': quantity,
        'action': action
    })

def main():
    """Main trading loop to place orders for rebates."""
    ticker_list = ['OWL', 'CROW', 'DOVE', 'DUCK']

    while True:
        for ticker in ticker_list:
            best_bid_price, best_ask_price = get_bid_ask(ticker)

            if not best_bid_price or not best_ask_price:
                continue

            if ticker in REBATE_LIMIT:  # OWL and DUCK
                # Place limit orders at the best bid and ask prices
                place_limit_order(ticker, ORDER_QUANTITY, best_bid_price, 'BUY')
                place_limit_order(ticker, ORDER_QUANTITY, best_ask_price, 'SELL')

            elif ticker in REBATE_MARKET:  # CROW and DOVE
                # Place market orders to buy and sell instantly
                place_market_order(ticker, ORDER_QUANTITY, 'BUY')
                place_market_order(ticker, ORDER_QUANTITY, 'SELL')

        sleep(0.5)  # Short delay to prevent overwhelming the API

if __name__ == '__main__':
    main()
