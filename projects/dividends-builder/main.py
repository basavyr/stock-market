import yfinance as yf
from tqdm import tqdm
import os
import csv
import logging
import argparse

# Suppress yfinance internal HTTP error logging
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

WISHLIST_PATH = os.path.join(os.path.dirname(__file__), "wishlist.csv")

# Supported portfolio data sources and their implementation status
SUPPORTED_SOURCES = {
    "ibkr": {"name": "Interactive Brokers", "filename": "ibkr.csv", "status": "Implemented", "currency": "$", "iso": "USD"},
    "xtb": {"name": "XTB", "filename": "xtb.csv", "status": "Planned", "currency": "$", "iso": "USD"},
    "tradeville": {"name": "Tradeville", "filename": "tradeville.csv", "status": "Implemented", "currency": "RON", "iso": "RON"},
    "auto": {"name": "Automatic Detection", "filename": None, "status": "Planned", "currency": "$", "iso": "USD"}
}

# Cache for exchange rates to avoid redundant API calls
EXCHANGE_RATE_CACHE = {}


def get_exchange_rate(from_currency, to_currency):
    """
    Fetches the current exchange rate between two currencies using yfinance.

    Args:
        from_currency (str): The source currency code (e.g., 'USD').
        to_currency (str): The target currency code (e.g., 'RON').

    Returns:
        float: The exchange rate (1 unit of from_currency = X units of to_currency).
    """
    if from_currency == to_currency:
        return 1.0

    pair = f"{from_currency}{to_currency}=X"
    if pair in EXCHANGE_RATE_CACHE:
        return EXCHANGE_RATE_CACHE[pair]

    try:
        # Some symbols use a simplified format in yfinance
        rate_ticker = yf.Ticker(pair)

        # history() is often more reliable than info[] for FX pairs on weekends
        hist = rate_ticker.history(period="1d")
        if not hist.empty:
            rate = hist['Close'].iloc[-1]
            EXCHANGE_RATE_CACHE[pair] = rate
            return rate

        rate = rate_ticker.info.get("regularMarketPrice")

        if rate is None:
            return 1.0

        EXCHANGE_RATE_CACHE[pair] = rate
        return rate
    except Exception:
        return 1.0


def get_portfolio(source="ibkr"):
    """
    Parses the portfolio CSV file from the specified directory and returns a list of stock holdings.

    Args:
        source (str): The data source type ('ibkr', 'xtb', 'tradeville').

    Returns:
        list: A list of dictionaries, where each dictionary represents a stock holding.
    """
    if source not in SUPPORTED_SOURCES:
        raise ValueError(f"Unknown data source: '{source}'.")

    source_info = SUPPORTED_SOURCES[source]

    # Check implementation status
    if source_info["status"] != "Implemented":
        raise NotImplementedError(
            f"Parsing for '{source}' ({source_info['name']}) data is not implemented yet.")

    portfolio_dir = os.getenv("PORTFOLIO_PATH", None)
    if portfolio_dir is None:
        print("\nError: PORTFOLIO_PATH environment variable is not set. Portfolio analysis cannot proceed.")
        return None

    if not os.path.isdir(portfolio_dir):
        print(
            f"\nError: PORTFOLIO_PATH is not a valid directory: {portfolio_dir}")
        return None

    filename = source_info["filename"]
    file_path = os.path.join(portfolio_dir, filename)

    if not os.path.exists(file_path):
        print(
            f"\nError: Portfolio file '{filename}' for source '{source}' not found in: {portfolio_dir}")
        return None

    if source == "ibkr":
        with open(file_path, 'r', encoding='utf-8') as reader:
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

    elif source == "tradeville":
        with open(file_path, 'r', encoding='utf-8') as reader:
            # Tradeville files often specify delimiter in the first line (e.g., SEP=	)
            first_line = reader.readline()
            delimiter = '\t'  # Default to tab
            if first_line.startswith('SEP='):
                delimiter = first_line.split('=')[1].strip('\n\r')
            else:
                reader.seek(0)

            reader_csv = csv.DictReader(reader, delimiter=delimiter)
            portfolio = []
            for row in reader_csv:
                # Skip cash lines or empty symbols
                ticker = row.get('simbol')
                if not ticker or ticker == 'RON':
                    continue

                # Suffix .RO for Bucharest Stock Exchange (BVB) symbols to work with yfinance
                if not ticker.endswith('.RO'):
                    ticker = f"{ticker}.RO"

                portfolio.append({
                    'Symbol': ticker,
                    'Quantity': row.get('sold', '0'),
                    'Description': row.get('nume', ''),
                    'ISIN': row.get('isin', '')
                })
            return portfolio

    return None


def get_stock_data(ticker: str):
    """
    Fetches real-time price and dividend yield data for a given stock ticker.

    Args:
        ticker (str): The stock symbol (e.g., 'AAPL').

    Returns:
        tuple: (dividend_yield, annual_dividend_per_share, current_price, currency) if successful.
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
        currency = info.get("currency", "USD")

        if dividend_yield is None:
            return 0.0, 0.0, current_price, currency

        # Calculate with full precision to avoid multiplying rounding errors during conversion
        annual_dividend_per_share = current_price * dividend_yield * 1e-2
        return dividend_yield, annual_dividend_per_share, current_price, currency

    except (AttributeError, KeyError, ValueError, TypeError):
        return None
    except Exception:
        # Catch-all for any other yfinance specific issues while remaining relatively safe
        return None


def process_portfolio(portfolio, source="IBKR", currency="$"):
    """
    Fetches dividend data for all stocks in the portfolio.

    Args:
        portfolio (list): A list of dictionaries representing stock holdings.
        source (str): Human-readable name of the portfolio source for display.
        currency (str): Currency symbol to use for display.

    Returns:
        tuple: (all_stock_data, total_adi_full) where all_stock_data is a list of
               processed stock info and total_adi_full is the cumulative Annual Dividend Income (ADI).
    """
    all_stock_data = []
    total_adi_full = 0
    print("\n" + "=" * 50)
    print(f"      {source.upper()} PORTFOLIO ANALYSIS (ADI)")
    print("=" * 50)
    for stock in tqdm(portfolio, desc="Calculating Portfolio Dividends", unit="stock", leave=False):
        ticker = stock['Symbol']
        quantity = float(stock['Quantity'])

        stock_data = get_stock_data(ticker)

        if stock_data is None:
            continue

        div_yield, annual_dividend_per_share, _, _ = stock_data
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

    The currency is detected from the 3rd column of the CSV header.
    Format: STOCK, TARGET_ADI, [CURRENCY]

    NOTE: The required investment in local currency (RON) depends only on the dividend yield, not on the exchange rate.

    Args:
        holdings (dict, optional): A dictionary mapping ticker symbols to current quantities.
    """
    if not os.path.exists(WISHLIST_PATH):
        print(
            f"\nWishlist file not found at {WISHLIST_PATH}. Skipping wishlist analysis.")
        return

    wishlist = []
    detected_currency_symbol = "$"  # Default label
    target_iso_currency = "USD"
    with open(WISHLIST_PATH, 'r', encoding='utf-8') as reader:
        # Handling potential trailing commas or dots as mentioned by the user
        data = csv.DictReader(reader, skipinitialspace=True)

        # Detect currency from the header (3rd field)
        header_fields = data.fieldnames
        if header_fields and len(header_fields) >= 3:
            raw_currency = header_fields[2].strip().upper()
            target_iso_currency = raw_currency
            if raw_currency == "USD":
                detected_currency_symbol = "$"
            else:
                detected_currency_symbol = raw_currency

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

        div_yield, div_per_share, current_price, listing_currency = data

        # Currency Conversion Logic
        rate = 1.0
        if listing_currency != target_iso_currency:
            rate = get_exchange_rate(listing_currency, target_iso_currency)
            div_per_share = div_per_share * rate
            current_price = current_price * rate

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
            'rate': rate,
            'listing_currency': listing_currency,
            'yield': div_yield,
            'is_in_portfolio': (ticker in holdings) if holdings else False
        })

    # Calculate total target Annual Dividend Income (ADI)
    total_target_adi = sum(row['target_adi'] for row in results)

    analysis_title = "WISHLIST GAP ANALYSIS (ADI)" if holdings else "WISHLIST TARGET PLANNING (ADI)"

    print("\n" + "=" * 40)
    print(f"    {analysis_title}")
    print("=" * 40)
    print("-" * 115)
    print(f"{'#': >3} | {'Stock (Yield)': <16} | {f'Target ADI ({detected_currency_symbol})': <20} | {
          'Owned': <10} | {'Delta': <10} | {f'Total Cost ({detected_currency_symbol})': <35}")
    print("-" * 115)

    for idx, row in enumerate(results):
        delta_str = f"{row['delta_shares']: >10.2f}" if row['delta_shares'] != float(
            '-inf') else "  N/A"

        if row['total_cost'] == float('inf'):
            cost_info_str = "  N/A"
        else:
            cost_info_str = f"{row['total_cost']: >10,.2f} (@{row['current_price']:,.2f}/share)"

        # Highlight if already in portfolio
        marker = "*" if row['is_in_portfolio'] else " "
        stock_yield_str = f"{marker} {row['stock']} ({row['yield']:.2f}%)"

        print(
            f"{(idx+1): >2}: | {stock_yield_str: <16} | {row['target_adi']: >18.2f} | {row['owned_shares']: >10.2f} | {delta_str} | {cost_info_str: <35}")
    # Calculate total required investment
    total_investment = sum(row['total_cost']
                           for row in results if row['total_cost'] != float('inf'))

    print("-" * 115)
    print(
        f"Total Required Investment to reach ADI goals ({total_target_adi:,.2f} {detected_currency_symbol}): {total_investment:,.2f} {detected_currency_symbol}")

    print("\nDelta = Owned - Target. Negative delta indicates missing shares needed to reach the target.")
    if holdings:
        print("(*) indicates stock already present in your portfolio.")
    print("-" * 115)


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

    # Portfolio Source selection
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--ibkr", action="store_true", help="Source: IBKR Flex Query CSV (Default).")
    source_group.add_argument(
        "--xtb", action="store_true", help="Source: XTB CSV.")
    source_group.add_argument(
        "--tradeville", action="store_true", help="Source: Tradeville CSV.")
    source_group.add_argument(
        "--auto", action="store_true", help="Automatically detect the source (Future Release).")

    args = parser.parse_args()

    # Determine the source
    source = "ibkr"
    if args.xtb:
        source = "xtb"
    elif args.tradeville:
        source = "tradeville"
    elif args.auto:
        source = "auto"

    # If no flags are provided, default to running both
    run_all = not (args.portfolio or args.wishlist)
    holdings = None

    if args.portfolio or run_all:
        try:
            portfolio = get_portfolio(source=source)
        except (NotImplementedError, ValueError) as e:
            print(f"\nError: {e}")
            return

        source_currency = SUPPORTED_SOURCES[source].get("currency", "$")

        if portfolio:
            all_stocks, total_adi_full = process_portfolio(
                portfolio, source=source, currency=source_currency)
            # Build a holdings lookup for Gap Analysis
            holdings = {s['ticker']: s['quantity'] for s in all_stocks}

            print(
                f"\nPortfolio Annual Dividend Income (ADI): {total_adi_full: >10.2f} {source_currency}")
            print("-" * 90)

            # ... rest of portfolio processing ...
            threshold = 15.0
            filtered_stocks, total_adi_filtered = filter_portfolio_by_threshold(
                all_stocks, threshold)

            print(
                f"Primary Dividend Sources (ADI >= {threshold} {source_currency}):\n")
            print(
                f"{'#': >3} | {'Stock (Yield)': <16} | {'Quantity': <10} | {'Div/Share': <17} | {f'Annual Total ({source_currency})': <15}")
            print("-" * 90)

            if not filtered_stocks:
                print("No stocks meet the specified dividend threshold.")
            else:
                for idx, stock in enumerate(filtered_stocks):
                    stock_yield_str = f"{stock['ticker']} ({stock['yield']:.2f}%)"
                    print(f"{(idx+1): >2}: | {stock_yield_str: <16} | {stock['quantity']: >10.2f} | "
                          f"{stock['annual_dividend_per_share']: >9.2f} /share | "
                          f"{stock['annual_revenue']: >12.2f}")

            print("-" * 90)
            print(
                f"Total ADI from Primary Sources: {total_adi_filtered: >41.2f} {source_currency}")
            print("-" * 90)

    if args.wishlist or run_all:
        # Pass holdings data only if gaps can be calculated
        process_wishlist(holdings=holdings)


if __name__ == "__main__":
    main()
