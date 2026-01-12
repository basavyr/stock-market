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

1. **Prepare your Portfolio**: Place your CSV reports in a dedicated directory. The tool searches for specific, strict filenames within this directory:
   - **IBKR**: `ibkr.csv`
   - **XTB**: `xtb.csv`
   - **Tradeville**: `tradeville.csv`

   - **Dynamic Header Detection (IBKR)**: For IBKR, the script automatically scans the `ibkr.csv` file to find the row containing the `Symbol` header, bypassing metadata lines.
   - **Required Fields**: For a successful parse, the CSV must include at least these columns: `Symbol`, `Description`, `ISIN`, `Quantity`, `CostBasisPrice`, `FifoPnlUnrealized`.
   - **Example format (`ibkr.csv`):**
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
   Specify the **directory path** containing your portfolio files using the `PORTFOLIO_PATH` environment variable:
   ```bash
   export PORTFOLIO_PATH="path/to/your/data_directory/"
   
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
   - **Format**: `STOCK, TARGET_ADI, CURRENCY`
   - **Note**: The reporting currency is defined in the 3rd column of the **header line** only (e.g., `USD` or `RON`).
   - **Example**:
     ```csv
     STOCK, TARGET_ADI, USD
     AAPL, 30
     MSFT, 30
     KO, 50
     TSM, 30
     SBUX, 50
     MRK, 30
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

## Useful Resources

- [A Relaxed Optimization Approach for Cardinality-Constrained Portfolio Optimization](https://arxiv.org/pdf/1810.10563) - Jize Zhang, Tim Leung, Aleksandr Aravkin (2018).
