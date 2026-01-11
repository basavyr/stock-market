import yfinance as yf
from tqdm import tqdm

import os
import csv
import logging

# Suppress yfinance internal HTTP error logging
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

PORTFOLIO_PATH = os.getenv("PORTFOLIO_PATH", None)
assert PORTFOLIO_PATH is not None, "PORTFOLIO_PATH environment variable is not set"


WISHLIST_PATH = os.path.join(os.path.dirname(__file__), "wishlist.csv")


def get_portfolio():
    """
    Parses the portfolio CSV file and returns a list of stock holdings.

    The function dynamically detects the header row by searching for the "Symbol"
    field, allowing it to handle variable metadata lines (e.g., from IBKR Flex Queries).

    Returns:
        list: A list of dictionaries, where each dictionary represents a stock holding.
    """
    with open(PORTFOLIO_PATH, 'r', encoding='utf-8') as reader:
        lines = reader.readlines()

        # Find the index of the header row containing 'Symbol'
        header_row_idx = 0
        for i, line in enumerate(lines):
            if 'Symbol' in line:
                header_row_idx = i
                break

        # Parse starting from the detected header row
        portfolio = csv.DictReader(lines[header_row_idx:])
        return list(portfolio)


def get_stock_data(ticker: str):
    """
    Fetches real-time price and dividend yield data for a given stock ticker.

    Args:
        ticker (str): The stock symbol (e.g., 'AAPL').

    Returns:
        tuple: (dividend_yield, annual_dividend_per_share, current_price) if successful.
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
            return 0.0, 0.0, current_price

        # Apply 1e-2 multiplier as the yield is provided in percentage (e.g., 0.4 for 0.4%)
        annual_dividend_per_share = round(
            current_price * dividend_yield * 1e-2, 2)
        return dividend_yield, annual_dividend_per_share, current_price

    except Exception:
        return None


def process_portfolio(portfolio):
    """
    Fetches dividend data for all stocks in the portfolio.

    Args:
        portfolio (list): A list of dictionaries representing stock holdings.

    Returns:
        tuple: (all_stock_data, total_adi_full) where all_stock_data is a list of
               processed stock info and total_adi_full is the cumulative Annual Dividend Income (ADI).
    """
    all_stock_data = []
    total_adi_full = 0
    print("\n" + "=" * 40)
    print("      PORTFOLIO ANALYSIS (ADI)")
    print("=" * 40)
    for stock in tqdm(portfolio, desc="Fetching market data", unit="stock", leave=False):
        ticker = stock['Symbol']
        quantity = float(stock['Quantity'])

        stock_data = get_stock_data(ticker)

        if stock_data is None:
            continue

        div_yield, annual_dividend_per_share, _ = stock_data
        annual_revenue = round(annual_dividend_per_share * quantity, 2)

        all_stock_data.append({
            'ticker': ticker,
            'quantity': quantity,
            'yield': div_yield,
            'annual_dividend_per_share': annual_dividend_per_share,
            'annual_revenue': annual_revenue
        })
        total_adi_full += annual_revenue

    return all_stock_data, total_adi_full


def filter_portfolio_by_threshold(all_stocks, threshold=15.0):
    """
    Filters the processed stock data based on an annual dividend threshold.

    Args:
        all_stocks (list): A list of dictionaries with processed stock info.
        threshold (float): The minimum annual revenue required.

    Returns:
        tuple: (filtered_stocks, total_adi_filtered)
    """
    filtered_stocks = [
        s for s in all_stocks if s['annual_revenue'] >= threshold]
    total_adi_filtered = sum(s['annual_revenue'] for s in filtered_stocks)
    return filtered_stocks, total_adi_filtered


def process_wishlist():
    """
    Parses wishlist.csv and calculates required shares and investment to reach 
    target Annual Dividend Income (ADI).
    """
    assert WISHLIST_PATH is not None, "WISHLIST_PATH environment variable is not set"
    if not os.path.exists(WISHLIST_PATH):
        print(
            f"\nWishlist file not found at {WISHLIST_PATH}. Skipping wishlist analysis.")
        return

    wishlist = []
    with open(WISHLIST_PATH, 'r', encoding='utf-8') as reader:
        # Handling potential trailing commas or dots as mentioned by the user
        data = csv.DictReader(reader, skipinitialspace=True)
        for row in data:
            stock = row['STOCK'].strip()
            # Remove any non-numeric characters like trailing dots
            target_tda_str = row['TARGET_TDA'].strip().rstrip('.')
            target_tda = float(target_tda_str)
            wishlist.append({'stock': stock, 'target_tda': target_tda})

    results = []
    for item in tqdm(wishlist, desc="Processing targets", unit="stock", leave=False):
        data = get_stock_data(item['stock'])
        if data is None:
            continue

        div_yield, div_per_share, current_price = data

        if div_per_share == 0:
            # Cannot reach target if no dividends are paid
            required_shares = float('inf')
            total_cost = float('inf')
        else:
            required_shares = round(item['target_tda'] / div_per_share, 4)
            total_cost = round(required_shares * current_price, 2)

        results.append({
            'stock': item['stock'],
            'target_tda': item['target_tda'],
            'required_shares': required_shares,
            'total_cost': total_cost,
            'current_price': current_price,
            'yield': div_yield
        })

    # Calculate total target Annual Dividend Income (ADI)
    total_target_adi = sum(row['target_tda'] for row in results)

    print("\n" + "=" * 40)
    print("    WISHLIST TARGET PLANNING (ADI)")
    print("=" * 40)
    print(
        f"Goal: Reach a Total Annual Dividend Income (ADI) of {total_target_adi:,.2f} $")
    print("-" * 110)
    print(f"{'#': >3} | {'Stock (Yield)': <16} | {'Target ADI': <12} | {'Req. Shares': <12} | {'Current Price': <14} | {'Total Cost': <12}")
    print("-" * 110)

    for idx, row in enumerate(results):
        shares_str = f"{row['required_shares']:.4f}" if row['required_shares'] != float(
            'inf') else "N/A"
        cost_str = f"{row['total_cost']:,} $" if row['total_cost'] != float(
            'inf') else "N/A (No Div)"

        # Combine Stock and Yield: AAPL (0.40%)
        stock_yield_str = f"{row['stock']} ({row['yield']:.2f}%)"

        print(
            f"{(idx+1): >2}: | {stock_yield_str: <16} | {row['target_tda']: >10.2f} $ | {shares_str: >12} | {row['current_price']: >12.2f} $ | {cost_str: >12}")

    # Calculate total required investment
    total_investment = sum(row['total_cost']
                           for row in results if row['total_cost'] != float('inf'))

    print("-" * 110)
    print(
        f"Total Required Investment to reach ADI goals: {total_investment:,.2f} $")
    print("-" * 110)


def main():
    """
    Main execution flow:
    1. Loads the portfolio.
    2. Fetches data for all stocks.
    3. Prints total ADA for the entire portfolio.
    4. Filters and prints reports for stocks above the threshold.
    5. Prints the filtered total ADA.
    6. Processes and prints wishlist analysis.
    """
    portfolio = get_portfolio()

    # Process the entire portfolio first
    skip_portfolio = False
    if not skip_portfolio:
        all_stocks, total_adi_full = process_portfolio(portfolio)

        print(
            f"\nPortfolio Annual Dividend Income (ADI): {total_adi_full: >10.2f} $")
        print("-" * 90)

        # Default threshold for filtering
        threshold = 15.0
        filtered_stocks, total_adi_filtered = filter_portfolio_by_threshold(
            all_stocks, threshold)

        print(f"High Earner Report (ADI >= {threshold} USD):\n")
        print(f"{'#': >3} | {'Stock (Yield)': <16} | {'Quantity': <10} | {'Div/Share': <12} | {'Annual Total': <15}")
        print("-" * 90)

        if not filtered_stocks:
            print("No stocks meet the specified dividend threshold.")
        else:
            for idx, stock in enumerate(filtered_stocks):
                stock_yield_str = f"{stock['ticker']} ({stock['yield']:.2f}%)"
                print(f"{(idx+1): >2}: | {stock_yield_str: <16} | {stock['quantity']: >10.2f} | "
                      f"{stock['annual_dividend_per_share']: >9.2f} $/sh | "
                      f"{stock['annual_revenue']: >12.2f} $")

        print("-" * 90)
        print(f"Total ADI from High Earners: {total_adi_filtered: >41.2f} $")
        print("-" * 90)

    # Wishlist Analysis
    process_wishlist()


if __name__ == "__main__":
    main()
