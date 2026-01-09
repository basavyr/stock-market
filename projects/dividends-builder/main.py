import yfinance as yf

import os
import csv

PORTFOLIO_PATH = os.getenv("PORTFOLIO_PATH", None)
assert PORTFOLIO_PATH is not None, "PORTFOLIO_PATH environment variable is not set"


def get_portfolio():
    with open(PORTFOLIO_PATH, 'r', encoding='utf-8') as reader:
        data = reader.readlines()
        portfolio = csv.DictReader(data[4:])
        return portfolio


def get_stock_dividend(ticker: str):
    info = yf.Ticker(ticker).info
    dividend_yield = info.get("dividendYield")
    if dividend_yield is None:
        return 0
    dividend_yield = dividend_yield * 1e-2
    annual_dividend_revenue = float(info.get("currentPrice")*dividend_yield)
    return round(annual_dividend_revenue, 2)  # per share


def main():
    portfolio = get_portfolio()
    for stock in portfolio:
        ticker = stock['Symbol']
        print(f'Stock: {ticker}')
        quantity = float(stock['Quantity'])
        annual_dividend = get_stock_dividend(ticker)
        usd_per_share = annual_dividend
        usd_per_stock = round(usd_per_share*quantity, 2)
        print(
            f'Anually {usd_per_share} $ | {usd_per_stock} $ per {quantity} shares')


if __name__ == "__main__":
    main()
