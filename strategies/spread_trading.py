'''
Spread Trading and Mean Reversion

The strategy failed to deliver optimistic results during case simulations in high-liquidity market conditions. 
This underperformance can be attributed to several factors:

Reduced Volatility: In high-liquidity markets, price fluctuations tend to be minimal, compressing the spreads
and limiting profit opportunities for spread trading strategies.

Tighter Competition: High liquidity often attracts more participants, increasing competition for favorable 
bid/ask prices and making it harder to execute trades at advantageous levels.

Mean Reversion Limitations: In highly liquid conditions, price movements may not deviate significantly 
from the mean, reducing the frequency and profitability of mean reversion opportunities.

Execution Challenges: The tighter spreads and rapid price adjustments in liquid markets can result in 
slippage or missed trades, further impacting the strategy effectiveness.
'''

import requests
from time import sleep

s = requests.Session()
s.headers.update({'X-API-key': 'EDKSMGPU'})  # Replace with your API key

# Global constants
MAX_LONG_EXPOSURE = 300000
MAX_SHORT_EXPOSURE = -100000
ORDER_LIMIT = 5000

MEAN_REVERSION_THRESHOLD = 0.015  # Adjusted for OWL (1.5%)
GROSS_LIMIT = 250000
NET_LIMIT = 250000

VOLATILITY_SPREADS = {
    'OWL': (0.001, 0.002),  # Tighter spreads: 0.1% to 0.2% of price
    'CROW': (0.002, 0.004),  # Moderate spreads: 0.2% to 0.4% of price
    'DOVE': (0.005, 0.01),   # Wider spreads: 0.5% to 1% of price
    'DUCK': (0.003, 0.005)   # Intermediate spreads: 0.3% to 0.5% of price
}

REBATE_MARKET = ['CROW', 'DOVE']  # Favorable for market orders
REBATE_LIMIT = ['OWL', 'DUCK']    # Favorable for limit orders

def get_tick():
    """Fetch the current tick and status of the trading case."""
    resp = s.get('http://localhost:9999/v1/case')
    if resp.ok:
        case = resp.json()
        return case['tick'], case['status']

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

def get_last_price(ticker):
    """Fetch the last traded price for a given ticker."""
    payload = {'ticker': ticker}
    resp = s.get('http://localhost:9999/v1/securities/tas', params=payload)
    if resp.ok:
        trades = resp.json()
        if trades:
            return trades[-1]['price']
    return None

def get_position():
    """Fetch the current positions for all tickers."""
    resp = s.get('http://localhost:9999/v1/securities')
    if resp.ok:
        book = resp.json()
        return {item['ticker']: item['position'] for item in book}

def calculate_gross_exposure(positions):
    """Calculate the gross exposure from current positions."""
    return sum(abs(pos) for pos in positions.values())

def calculate_net_exposure(positions):
    """Calculate the net exposure from current positions."""
    return sum(positions.values())

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

def calculate_spread_adjustment(price, spread_range):
    """Calculate adjusted bid/ask prices based on volatility spreads."""
    lower_bound, upper_bound = spread_range
    spread = (upper_bound - lower_bound) / 2
    return lower_bound * price, upper_bound * price

def deleverage_positions(positions):
    """Reduce positions when approaching exposure limits."""
    for ticker, position in positions.items():
        if position > 0:  # Long position
            place_market_order(ticker, min(position, ORDER_LIMIT), 'SELL')
        elif position < 0:  # Short position
            place_market_order(ticker, min(abs(position), ORDER_LIMIT), 'BUY')

def main():
    """Main trading logic implementing market-making, mean reversion, and risk controls."""
    tick, status = get_tick()
    ticker_list = ['OWL', 'CROW', 'DOVE', 'DUCK']

    while status == 'ACTIVE':
        positions = get_position()

        # Calculate gross and net exposures
        gross_exposure = calculate_gross_exposure(positions)
        net_exposure = calculate_net_exposure(positions)

        # Deleverage when near limits
        if gross_exposure >= GROSS_LIMIT * 0.9 or abs(net_exposure) >= NET_LIMIT * 0.9:
            deleverage_positions(positions)
            sleep(1)
            tick, status = get_tick()
            continue

        for ticker in ticker_list:
            position = positions.get(ticker, 0)
            best_bid_price, best_ask_price = get_bid_ask(ticker)
            last_price = get_last_price(ticker)

            if not best_bid_price or not best_ask_price:
                continue

            # Spread adjustment
            spread_range = VOLATILITY_SPREADS[ticker]
            adjusted_bid_price, adjusted_ask_price = calculate_spread_adjustment(
                (best_bid_price + best_ask_price) / 2, spread_range)

            # Calculate quantities
            remaining_long_exposure = MAX_LONG_EXPOSURE - position
            remaining_short_exposure = position - MAX_SHORT_EXPOSURE

            buy_quantity = min(ORDER_LIMIT, remaining_long_exposure)
            sell_quantity = min(ORDER_LIMIT, remaining_short_exposure)

            if ticker in REBATE_LIMIT:  # OWL and DUCK
                if buy_quantity > 0:
                    place_limit_order(ticker, buy_quantity, adjusted_bid_price, 'BUY')
                if sell_quantity > 0:
                    place_limit_order(ticker, sell_quantity, adjusted_ask_price, 'SELL')

            elif ticker in REBATE_MARKET:  # CROW and DOVE
                if buy_quantity > 0:
                    place_market_order(ticker, buy_quantity, 'BUY')
                if sell_quantity > 0:
                    place_market_order(ticker, sell_quantity, 'SELL')

            # Mean reversion for OWL
            if ticker == 'OWL' and last_price:
                mean_price = (best_bid_price + best_ask_price) / 2
                deviation = (last_price - mean_price) / mean_price

                if abs(deviation) > MEAN_REVERSION_THRESHOLD:
                    action = 'BUY' if deviation < 0 else 'SELL'
                    quantity = buy_quantity if action == 'BUY' else sell_quantity
                    place_market_order(ticker, quantity, action)

            sleep(0.75)  # To respect API limits

        tick, status = get_tick()

if __name__ == '__main__':
    main()
