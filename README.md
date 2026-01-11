# Stock Market Tools

This repository contains a collection of Python-based tools for stock market analysis and portfolio management.

## Repository Structure

The projects are located in the `projects/` directory:

- [Stock Picker](file:///Users/svc_sps/Documents/GitHub/stock-market/projects/stock-picker): A tool to calculate the necessary investment amount for reaching desired fractional share goals.
- [Dividends Builder](file:///Users/svc_sps/Documents/GitHub/stock-market/projects/dividends-builder): A tool to calculate annual dividend revenue based on a stock portfolio.

---

## [Dividends Builder](projects/dividends-builder)

The Dividends Builder tool helps you track and forecast your annual dividend income.

### Usage

1. **Prepare your Portfolio**: The tool parses a CSV export of your portfolio.
   - **Flexible Header Detection**: The script checks the first line for the `Symbol` field. If not found, it automatically skips the first **4 lines** (assuming they contain metadata).
   - The CSV must contain the following fields: `Symbol`, `Description`, `ISIN`, `Quantity`, `CostBasisPrice`, `FifoPnlUnrealized`.
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
   Set the `PORTFOLIO_PATH` environment variable to your CSV file's location and run the script:
   ```bash
   export PORTFOLIO_PATH="path/to/your/portfolio.csv"
   python projects/dividends-builder/main.py
   ```

### Wishlist Analysis (Target Planning)
The tool can also calculate the required investment to reach specific annual dividend goals using a `wishlist.csv` file.

1. **Create `projects/dividends-builder/wishlist.csv`**:
   - **Format**: `STOCK, TARGET_TDA`
   - **Example**:
     ```csv
     STOCK, TARGET_TDA
     AAPL, 25
     MSFT, 70
     KO, 100
     TSM, 50
     SBUX, 100
     ```

2. **View the Roadmap**:
   When you run the script, it will provide a breakdown of how many shares you need and the total capital required to reach those targets.

   **Example Output**:
   ```text
   Wishlist Analysis (Required Investment to reach Target TDA 345.00 $):
   --------------------------------------------------------------------------------------------------------------
     # | Stock (Yield)    | Target TDA | Req. Shares  | Price    | Total Cost  
   --------------------------------------------------------------------------------------------------------------
    1: | AAPL (0.40%)     |    25.00 $ |      24.0385 |  259.37 $ |    6234.87 $
    2: | MSFT (0.76%)     |    70.00 $ |      19.2308 |  479.28 $ |    9216.94 $
    3: | KO (2.89%)       |   100.00 $ |      49.0196 |   70.51 $ |    3456.37 $
    4: | TSM (1.04%)      |    50.00 $ |      14.8368 |  323.63 $ |    4801.63 $
    5: | SBUX (2.79%)     |   100.00 $ |      40.3226 |   88.88 $ |    3583.87 $
   --------------------------------------------------------------------------------------------------------------
   Total Required Investment to reach target ADA goals: 27,293.65 $
   --------------------------------------------------------------------------------------------------------------
   ```

### Features
- Fetches real-time dividend data using `yfinance`.
- Correctly handles yield percentages (e.g., 0.4 interpreted as 0.4%).
- Provides individual stock reports and a total Portfolio Annual Dividend Amount (ADA).
- **Target Planning**: Calculate required capital and shares to reach annual income goals.
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
