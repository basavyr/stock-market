import yfinance as yf
from tqdm import tqdm
import os
import csv
import logging
import argparse

# Suppress yfinance internal HTTP error logging
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

WISHLIST_PATH = os.path.join(os.path.dirname(__file__), "wishlist.csv")


def get_portfolio():
    """
    Parses the portfolio CSV file and returns a list of stock holdings.

    The function dynamically detects the header row by searching for the "Symbol"
    field, allowing it to handle variable metadata lines (e.g., from IBKR Flex Queries).

    Returns:
        list: A list of dictionaries, where each dictionary represents a stock holding.
    """
    portfolio_path = os.getenv("PORTFOLIO_PATH", None)
    if portfolio_path is None:
        print("\nError: PORTFOLIO_PATH environment variable is not set. Portfolio analysis cannot proceed.")
        return None

    with open(portfolio_path, 'r', encoding='utf-8') as reader:
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
    for stock in tqdm(portfolio, desc="Calculating Portfolio Dividends", unit="stock", leave=False):
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


def process_wishlist(holdings=None):
    """
    Parses wishlist.csv and calculates required shares and investment to reach 
    target Annual Dividend Income (ADI), accounting for current holdings if provided.

    Args:
        holdings (dict, optional): A dictionary mapping ticker symbols to current quantities.
    """
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
            target_adi_str = row['TARGET_ADI'].strip().rstrip('.')
            target_adi = float(target_adi_str)
            wishlist.append({'stock': stock, 'target_adi': target_adi})

    results = []
    for item in tqdm(wishlist, desc="Calculating Target Investments", unit="stock", leave=False):
        ticker = item['stock']
        data = get_stock_data(ticker)
        if data is None:
            continue

        div_yield, div_per_share, current_price = data

        current_quantity = holdings.get(ticker, 0.0) if holdings else 0.0
        target_adi = item['target_adi']

        if div_per_share == 0:
            # Cannot reach target ADI if the stock pays no dividends
            delta_shares = 0.0 if target_adi <= 0 else float('-inf')
            required_to_buy = float('inf') if target_adi > 0 else 0.0
            total_cost = float('inf') if target_adi > 0 else 0.0
        else:
            total_target_shares = target_adi / div_per_share
            delta_shares = round(current_quantity - total_target_shares, 4)
            required_to_buy = round(max(0, -delta_shares), 4)
            total_cost = round(required_to_buy * current_price, 2)

        results.append({
            'stock': ticker,
            'target_adi': target_adi,
            'owned_shares': current_quantity,
            'delta_shares': delta_shares,
            'required_buy': required_to_buy,
            'total_cost': total_cost,
            'current_price': current_price,
            'yield': div_yield,
            'is_in_portfolio': (ticker in holdings) if holdings else False
        })

    # Calculate total target Annual Dividend Income (ADI)
    total_target_adi = sum(row['target_adi'] for row in results)

    analysis_title = "WISHLIST GAP ANALYSIS (ADI)" if holdings else "WISHLIST TARGET PLANNING (ADI)"

    print("\n" + "=" * 40)
    print(f"    {analysis_title}")
    print("=" * 40)
    print(
        f"Goal: Reach a Total Annual Dividend Income (ADI) of {total_target_adi:,.2f} $")
    print("-" * 112)
    print(f"{'#': >3} | {'Stock (Yield)': <16} | {'Target ADI': <12} | {'Owned': <10} | {'Delta': <10} | {'Price': <10} | {'Total Cost': <12}")
    print("-" * 112)

    for idx, row in enumerate(results):
        delta_str = f"{row['delta_shares']: >10.2f}" if row['delta_shares'] != float(
            '-inf') else "  N/A"
        cost_str = f"{row['total_cost']: >10.2f} $" if row['total_cost'] != float(
            'inf') else "  N/A"

        # Highlight if already in portfolio
        marker = "*" if row['is_in_portfolio'] else " "
        stock_yield_str = f"{marker} {row['stock']} ({row['yield']:.2f}%)"

        print(
            f"{(idx+1): >2}: | {stock_yield_str: <16} | {row['target_adi']: >10.2f} $ | {row['owned_shares']: >10.2f} | {delta_str} | {row['current_price']: >8.2f} $ | {cost_str}")
    # Calculate total required investment
    total_investment = sum(row['total_cost']
                           for row in results if row['total_cost'] != float('inf'))

    print("-" * 112)
    print(
        f"Total Required Investment to reach ADI goals ({total_target_adi:,.2f} $): {total_investment:,.2f} $")
    print("Delta = Owned - Target. Negative delta indicates missing shares needed to reach the target.")
    if holdings:
        print("(*) indicates stock already present in your portfolio.")
    print("-" * 112)


def main():
    """
    Main execution flow:
    - Parses command-line arguments to determine which workflow to run.
    - Honors --portfolio and --wishlist flags. Runs both if no flags are provided.
    """
    parser = argparse.ArgumentParser(
        description="Calculate Annual Dividend Income (ADI) for your portfolio and wishlist.")
    parser.add_argument("--portfolio", action="store_true",
                        help="Run only the portfolio analysis.")
    parser.add_argument("--wishlist", action="store_true",
                        help="Run only the wishlist target planning.")

    args = parser.parse_args()

    # If no flags are provided, default to running both
    run_all = not (args.portfolio or args.wishlist)
    holdings = None

    if args.portfolio or run_all:
        portfolio = get_portfolio()
        if portfolio:
            all_stocks, total_adi_full = process_portfolio(portfolio)
            # Build a holdings lookup for Gap Analysis
            holdings = {s['ticker']: s['quantity'] for s in all_stocks}

            print(
                f"\nPortfolio Annual Dividend Income (ADI): {total_adi_full: >10.2f} $")
            print("-" * 90)

            # ... rest of portfolio processing ...
            threshold = 15.0
            filtered_stocks, total_adi_filtered = filter_portfolio_by_threshold(
                all_stocks, threshold)

            print(f"Primary Dividend Sources (ADI >= {threshold} USD):\n")
            print(
                f"{'#': >3} | {'Stock (Yield)': <16} | {'Quantity': <10} | {'Div/Share': <17} | {'Annual Total': <15}")
            print("-" * 90)

            if not filtered_stocks:
                print("No stocks meet the specified dividend threshold.")
            else:
                for idx, stock in enumerate(filtered_stocks):
                    stock_yield_str = f"{stock['ticker']} ({stock['yield']:.2f}%)"
                    print(f"{(idx+1): >2}: | {stock_yield_str: <16} | {stock['quantity']: >10.2f} | "
                          f"{stock['annual_dividend_per_share']: >9.2f} $/share | "
                          f"{stock['annual_revenue']: >12.2f} $")

            print("-" * 90)
            print(
                f"Total ADI from Primary Sources: {total_adi_filtered: >41.2f} $")
            print("-" * 90)

    if args.wishlist or run_all:
        # Pass holdings data only if gaps can be calculated
        process_wishlist(holdings=holdings)


if __name__ == "__main__":
    main()
