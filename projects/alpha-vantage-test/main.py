from dotenv import dotenv_values
import time

import requests
if __name__ == "__main__":
    config = dotenv_values(".env")
    api_key = config["API_KEY"] # API KEY tested on February 2026

    symbols = ['NVDA', 'AAPL']
    prices = []
    for symbol in symbols:
        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={api_key}'
        r = requests.get(url)
        data = r.json()
        daily_prices = data['Time Series (Daily)']
        last_day = list(daily_prices.keys())[0]
        close_price = daily_prices[last_day]['4. close']
        price = float(close_price)
        prices.append(price)
        print(f'{symbol}: {price}$')
        time.sleep(1.5)
