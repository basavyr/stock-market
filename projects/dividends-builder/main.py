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


def get_stock_data(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Check if we got a valid response with essential fields
        if not info or "currentPrice" not in info:
            return None

        dividend_yield = info.get("dividendYield")
        current_price = info.get("currentPrice")

        if dividend_yield is None:
            return 0.0, 0.0

        # Apply 1e-2 multiplier as the yield is provided in percentage (e.g., 0.4 for 0.4%)
        annual_dividend_per_share = round(
            current_price * dividend_yield * 1e-2, 2)
        return dividend_yield, annual_dividend_per_share

    except Exception:
        return None


def main():
    portfolio = get_portfolio()
    total_ada = 0

    for stock in portfolio:
        ticker = stock['Symbol']
        quantity = float(stock['Quantity'])

        stock_data = get_stock_data(ticker)

        if stock_data is None:
            print(f"Stock: {ticker: <6} | Error retrieving data")
            continue

        div_yield, annual_dividend_per_share = stock_data
        annual_revenue = round(annual_dividend_per_share * quantity, 2)
        total_ada += annual_revenue

        print(f"Stock: {ticker: <6} | Quantity: {quantity: >8.2f} | "
              f"Yield: {div_yield: >5.2f}% | "
              f"Anually: {annual_dividend_per_share: >6.2f} $/share | "
              f"Total: {annual_revenue: >10.2f} $")

    print("-" * 80)
    print(
        f"Total Portfolio Annual Dividend Amount (ADA): {total_ada: >10.2f} $")


if __name__ == "__main__":
    main()
