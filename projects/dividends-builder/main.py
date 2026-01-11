import yfinance as yf
from tqdm import tqdm

import os
import csv
import logging

# Suppress yfinance internal HTTP error logging
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

PORTFOLIO_PATH = os.getenv("PORTFOLIO_PATH", None)
assert PORTFOLIO_PATH is not None, "PORTFOLIO_PATH environment variable is not set"


def get_portfolio():
    """
    Parses the portfolio CSV file and returns a list of stock holdings.

    The function dynamically detects if the file starts with metadata and skips 
    the first 4 lines if necessary.

    Returns:
        list: A list of dictionaries, where each dictionary represents a stock holding.
    """
    with open(PORTFOLIO_PATH, 'r', encoding='utf-8') as reader:
        lines = reader.readlines()

        # Determine if we need to skip the first 4 lines
        # We assume the header contains 'Symbol'
        if len(lines) > 4 and 'Symbol' not in lines[0]:
            portfolio = csv.DictReader(lines[4:])
        else:
            portfolio = csv.DictReader(lines)

        return list(portfolio)


def get_stock_data(ticker: str):
    """
    Fetches real-time price and dividend yield data for a given stock ticker.

    Args:
        ticker (str): The stock symbol (e.g., 'AAPL').

    Returns:
        tuple: (dividend_yield, annual_dividend_per_share) if successful.
        None: If the data cannot be retrieved or essential fields are missing.
    """
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


def process_portfolio(portfolio):
    """
    Fetches dividend data for all stocks in the portfolio.

    Args:
        portfolio (list): A list of dictionaries representing stock holdings.

    Returns:
        tuple: (all_stock_data, total_ada_full) where all_stock_data is a list of 
               processed stock info and total_ada_full is the cumulative ADA.
    """
    all_stock_data = []
    total_ada_full = 0

    print("Fetching dividend data for the entire portfolio...")
    for stock in tqdm(portfolio, desc="Progress", unit="stock"):
        ticker = stock['Symbol']
        quantity = float(stock['Quantity'])

        stock_data = get_stock_data(ticker)

        if stock_data is None:
            continue

        div_yield, annual_dividend_per_share = stock_data
        annual_revenue = round(annual_dividend_per_share * quantity, 2)

        all_stock_data.append({
            'ticker': ticker,
            'quantity': quantity,
            'yield': div_yield,
            'annual_dividend_per_share': annual_dividend_per_share,
            'annual_revenue': annual_revenue
        })
        total_ada_full += annual_revenue

    return all_stock_data, total_ada_full


def filter_portfolio_by_threshold(all_stocks, threshold=15.0):
    """
    Filters the processed stock data based on an annual dividend threshold.

    Args:
        all_stocks (list): A list of dictionaries with processed stock info.
        threshold (float): The minimum annual revenue required.

    Returns:
        tuple: (filtered_stocks, total_ada_filtered)
    """
    filtered_stocks = [
        s for s in all_stocks if s['annual_revenue'] >= threshold]
    total_ada_filtered = sum(s['annual_revenue'] for s in filtered_stocks)
    return filtered_stocks, total_ada_filtered


def main():
    """
    Main execution flow: 
    1. Loads the portfolio.
    2. Fetches data for all stocks.
    3. Prints total ADA for the entire portfolio.
    4. Filters and prints reports for stocks above the threshold.
    5. Prints the filtered total ADA.
    """
    portfolio = get_portfolio()

    # Process the entire portfolio first
    all_stocks, total_ada_full = process_portfolio(portfolio)

    print("-" * 80)
    print(
        f"Total Portfolio Annual Dividend Amount (ADA): {total_ada_full: >10.2f} $")
    print("-" * 80)

    # Default threshold for filtering
    threshold = 15.0
    filtered_stocks, total_ada_filtered = filter_portfolio_by_threshold(
        all_stocks, 0)

    print(f"\nFiltered Portfolio (Annual dividend >= {threshold} USD):\n")

    if not filtered_stocks:
        print("No stocks meet the specified dividend threshold.")
    else:
        for idx, stock in enumerate(filtered_stocks):
            print(f"{(idx+1): >2}: {stock['ticker']: <6} | Quantity: {stock['quantity']: >8.2f} | "
                  f"Yield: {stock['yield']: >5.2f}% | "
                  f"Anually: {stock['annual_dividend_per_share']: >6.2f} $/share | "
                  f"Total: {stock['annual_revenue']: >10.2f} $")

    print("-" * 80)
    print(
        f"Total Filtered Portfolio Annual Dividend Amount: {total_ada_filtered: >10.2f} $")


if __name__ == "__main__":
    main()
