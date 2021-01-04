#! /Users/robertpoenaru/.pyenv/shims/python
import yfinance as fin
import matplotlib.pyplot as plt


def GetStockPrice(stock):
    stock_value = fin.Ticker(stock)
    current_market_price = float(stock_value.info['regularMarketDayHigh'])
    output, price = f'{stock} stock price: {current_market_price} $', current_market_price
    print(output)
    return price


shares_available = [2.22, 0.69, 1.93]
shares_to_get = [3.0, 3.0, 3.0]
stocks = ["AAPL", "MSFT", "SBUX"]
stocks_prices = list(map(GetStockPrice, stocks))


def Minus(a, b):
    return round(b-a, 3)


required_shares = list(map(Minus, shares_available, shares_to_get))

# print(stocks_prices)

total = 0.0
for stock_name, share, price in zip(stocks, required_shares, stocks_prices):
    print(f'{stock_name}: {share} shares are required @ {price} USD')
    required_amount_to_invest = share*price
    total = total+required_amount_to_invest

print(f'For 3 shares per stock, a total of {total} $ is needed')
current_total_amount = sum(
    list(map(lambda x: x[0]*x[1], zip(shares_available, stocks_prices))))
print(list(map(lambda x: x[0]*x[1], zip(shares_available, stocks_prices))))
print(f'In addition to the current: {current_total_amount}')


with open("data_stocks.dat", 'w') as out:
    lines = ['Current Portfolio Value\n']
    for stock_name, share, price, available_stock in zip(stocks, required_shares, stocks_prices, shares_available):
        line = f'Stock: {stock_name} ({available_stock} shares) | Current Capital: {round(available_stock*price,3)} | Required Investment for 3 shares hold: {round(share*price,3)}\n'
        lines.append(line)
    out.writelines(lines)
