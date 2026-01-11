# Stock Market Tools

This repository contains a collection of Python-based tools for stock market analysis and portfolio management.

## Repository Structure

The projects are located in the `projects/` directory:

- [Stock Picker](file:///Users/svc_sps/Documents/GitHub/stock-market/projects/stock-picker): A tool to calculate the necessary investment amount for reaching desired fractional share goals.
- [Dividends Builder](file:///Users/svc_sps/Documents/GitHub/stock-market/projects/dividends-builder): A tool to calculate annual dividend revenue based on a stock portfolio.

---

## [Dividends Builder](projects/dividends-builder)

The Dividends Builder tool helps you track and forecast your annual dividend income (ADI).

### Usage

1. **Prepare your Portfolio**: The tool is optimized for **Interactive Brokers (IBKR) Flex Query** reports in CSV format.
   - **Dynamic Header Detection**: The script automatically scans your CSV file to find the row containing the `Symbol` header. This allows it to handle reports with a variable number of metadata lines (e.g., cash balance or account info rows).
   - **Required Fields**: For a successful parse, the CSV must include at least these columns: `Symbol`, `Description`, `ISIN`, `Quantity`, `CostBasisPrice`, `FifoPnlUnrealized`.
   - **Example format (`portfolio.csv`):**
     ```csv
     [Metadata line 1]
     [Metadata line 2]
     [Metadata line 3]
     [Metadata line 4]
     Symbol,Description,ISIN,Quantity,CostBasisPrice,FifoPnlUnrealized
     AAPL,Apple Inc,US0378331005,15.5,170.25,500.00
     MSFT,Microsoft Corp,US5949181045,5.0,380.00,200.00
     ```

2. **Configure and Run**:
   You can specify your portfolio data source using flags (defaulting to IBKR):
   ```bash
   export PORTFOLIO_PATH="path/to/your/portfolio.csv"
   
   # Run with IBKR data (Standard)
   python projects/dividends-builder/main.py --ibkr
   
   # Future sources (currently raise NotImplementedError)
   python projects/dividends-builder/main.py --xtb
   python projects/dividends-builder/main.py --tradeville
   ```

   You can also target specific workflows:
   ```bash
   # Run only portfolio analysis
   python projects/dividends-builder/main.py --portfolio
   
   # Run only wishlist target planning
   python projects/dividends-builder/main.py --wishlist
   ```

### Wishlist Analysis (Target Planning)
The tool can also calculate the required investment to reach specific annual dividend goals using a `wishlist.csv` file.

1. **Create `projects/dividends-builder/wishlist.csv`**:
   - **Format**: `STOCK, TARGET_ADI`
   - **Example**:
     ```csv
     STOCK, TARGET_ADI
     AAPL, 25
     MSFT, 70
     KO, 100
     TSM, 50
     SBUX, 100
     ```

2. **View the Roadmap**:
   The script provides a strategic roadmap with required shares and total capital needed.

   **Example Output**:
   ```text
   ========================================
       WISHLIST GAP ANALYSIS (ADI)
   ========================================
   Goal: Reach a Total Annual Dividend Income (ADI) of 345.00 $
   -------------------------------------------------------------------------------------------------------------------
     # | Stock (Yield)    | Target ADI   | Owned      | Delta      | Total Cost                         
   -------------------------------------------------------------------------------------------------------------------
    1: | AAPL (0.40%)     |      25.00 $ |      10.00 |     -14.04 |    3,641.15 $ (@259.37/share)
    2: | MSFT (0.76%)     |      70.00 $ |       5.00 |     -14.23 |    6,819.50 $ (@479.28/share)
    3: | KO (2.89%)       |     100.00 $ |      20.00 |     -29.02 |    2,046.20 $ (@70.51/share)
    4: | TSM (1.04%)      |      50.00 $ |       0.00 |     -14.84 |    4,801.63 $ (@323.63/share)
    5: | SBUX (2.79%)     |     100.00 $ |      15.00 |     -25.32 |    2,250.77 $ (@88.88/share)
   -------------------------------------------------------------------------------------------------------------------
   Total Required Investment to reach ADI goals (345.00 $): 19,559.25 $
   Delta = Owned - Target. Negative delta indicates missing shares needed to reach the target.
   -------------------------------------------------------------------------------------------------------------------
   ```

### Features
- Fetches real-time dividend data using `yfinance`.
- Correctly handles yield percentages (e.g., 0.4 interpreted as 0.4%).
- Provides individual stock reports and a total portfolio **Annual Dividend Income (ADI)**.
- **Target Planning**: Calculate required capital and shares to reach ADI goals using a "blueprint" approach.
- **Flexible Execution**: Use CLI flags to run specific parts of the analysis independently.
- Robust error handling for missing symbols or `yfinance` connectivity issues.

---

## [Stock Picker](file:///Users/svc_sps/Documents/GitHub/stock-market/projects/stock-picker)

The Stock Picker tool computes the investment needed to achieve specific fractional share targets.

### Features
- Uses `yfinance` to get current market prices (specifically `regularMarketDayHigh`).
- Calculates the gap between current holdings and an `OPTIMAL_SHARE` target.
- Generates visual reports using `matplotlib`.

## Setup and Issues

### LZMA/XZ Dependency
If you encounter issues with `yfinance` or `lzma` imports, you may need to install the `xz` package. On macOS, this can be done via Homebrew:

```bash
brew install xz
```
For more details, see [this StackOverflow discussion](https://stackoverflow.com/questions/57743230/userwarning-could-not-import-the-lzma-module-your-installed-python-is-incomple).
