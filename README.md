# Stock Market Tools

This repository contains a collection of Python-based tools for stock market analysis and portfolio management.

## Repository Structure

The projects are located in the `projects/` directory:

- [Stock Picker](projects/stock-picker): A tool to calculate the necessary investment amount for reaching desired fractional share goals.
- [Dividends Builder](projects/dividends-builder): A privacy-safe dividend planning dashboard that loads your portfolio from a local-only `export.json`.

---

## [Dividends Builder](projects/dividends-builder)

The Dividends Builder tool helps you track and forecast your annual dividend income (ADI).

### Privacy model

This project is designed so that **no personal portfolio data is committed** or shipped on GitHub Pages.

- You generate `projects/dividends-builder/export.json` locally (gitignored).
- You upload `export.json` in the browser; it renders client-side and is stored in `localStorage`.

### Usage

1. **Generate `export.json` locally** (recommended workflow)

   Install the generator dependency:

   ```bash
   pip install yfinance
   ```

   Put your broker CSV report(s) in `~/Downloads` (defaults):

   - **IBKR**: `Report-With-Cash*.csv`
   - **Tradeville**: `portof*.csv`

   Or set explicit paths / globs via `.env`:

   ```bash
   cp projects/dividends-builder/.env.example projects/dividends-builder/.env
   ```

   Run the generator:

   ```bash
   python3 projects/dividends-builder/generate.py
   ```

   This writes/updates `projects/dividends-builder/export.json`.

   Notes:
   - Updates are *smart*: if only one CSV is found, only that source is updated and the other is preserved.
   - `export.json` intentionally contains no absolute paths.

2. **Load the dashboard (GitHub Pages or local) and upload `export.json`**

   In the dashboard UI:
   - Click `[UPLOAD_EXPORT]` and select your `export.json`.
   - Targets you type are stored locally; use `[RESET_TARGETS]` to clear targets or `[CLEAR_DATA]` to remove the uploaded export from `localStorage`.

### Features
- Fetches dividend + price data using `yfinance` to estimate per-holding ADI.
- Multi-source support (currently IBKR + Tradeville).
- Privacy-first: portfolio is generated locally and loaded via upload; nothing is shipped with the site.
- Dashboard supports per-row target ADI planning, projected totals, sorting, and light/dark theme.
- Robust error handling for missing symbols or `yfinance` connectivity issues.

---

## [Stock Picker](projects/stock-picker)

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
