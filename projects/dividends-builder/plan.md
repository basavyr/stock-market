# Research and Implementation Plan: Portfolio Dividend Revenue Analysis

## I. Project Overview
The primary objective of this project is to develop a standardized framework for the automated calculation and reporting of annual dividend income (ADI) for diversified equity portfolios. By integrating real-time market data with local portfolio records, the system provides accurate forecasting of passive income streams.

## II. Data Acquisition and Preprocessing Protocol
The system utilizes a hybrid data acquisition strategy, combining local CSV parsing with real-time API integration:

*   **Ingestion**: Portfolio data is sourced from a centralized directory (defined by `PORTFOLIO_PATH`). The system explicitly searches for strict filenames based on the selected broker: `ibkr.csv`, `xtb.csv`, or `tradeville.csv`.
*   **Dynamic Header Detection (IBKR & Tradeville)**: The system supports both IBKR Flex Queries and Tradeville CSV exports. The Tradeville parser specifically handles "SEP=" delimiter specifications and automatically suffixes BVB symbols with ".RO" for yfinance compatibility.
*   **Field Mapping**: Required attributes include `Symbol`, `Description`, `ISIN`, `Quantity`, `CostBasisPrice`, and `FifoPnlUnrealized`. (Note: Field names may vary by broker source).
*   **Real-time Integration**: The `yfinance` library is employed to fetch live market data. To ensure a clean terminal interface, internal HTTP exception logging is suppressed for non-critical errors.
*   **Currency Conversion Engine**: The system implements an automated exchange rate engine. If the stock's listing currency (e.g., USD for AAPL) differs from the wishlist's target currency (detected from the CSV header), the script automatically fetches live exchange rates (e.g., `USDRON=X`) and normalizes all dividends and prices for consistent analysis.
*   **Progress Tracking**: Computational progress is monitored via the `tqdm` library, providing visual feedback during high-latency data retrieval operations.

## III. Computational Methodology
The core analytical logic follows a sequential calculation model:

1.  **Individual Annualization**: For each equity holding, the annual dividend per share is derived using the product of the `currentPrice` and the `dividendYield` (corrected by a $10^{-2}$ scalar for percentage compatibility).
2.  **Asset-level Revenue**: Total annual revenue per holding is computed as `Quantity` * `Annual Dividend per Share`.
3.  **Revenue Thresholding (Filtering)**: Assets are evaluated against a predefined threshold (default: $15.0$ USD/annum). Assets failing to meet this criterion are excluded from the detailed reporting phase.
4.  **Portfolio Aggregation**: The **Annual Dividend Income (ADI)** is calculated for both the comprehensive portfolio and the filtered subset.

### 3. Wishlist Gap Analysis (Target Planning)
When both portfolio and wishlist workflows are active, the system performs a **Gap Analysis**:
- **Cross-Referencing**: Each wishlist stock is checked against current portfolio holdings.
- **Differential Calculation**: The system identifies the "dividend income gap" between the current ADI of owned shares and the target ADI goal.
- **Adjusted Targets**: `Required Shares = (Target ADI - Current ADI) / Annual Dividend per Share`.
- **Valuation**: `Total Cost = Adjusted Required Shares * Current Market Price`.
- **Visual Feedback**: Wishlist stocks already present in the portfolio are marked with an asterisk (`*`) and their current share count is displayed.

## IV. Presentation and Reporting Logic
The reporting module generates a hierarchical summary with distinct sections:

1.  **Portfolio Analysis (ADI)**: A comprehensive overview of current holdings.
    *   Total Portfolio Annual Dividend Income (ADI) display.
    *   **Primary Dividend Sources**: A concise table of assets meeting the threshold, combining Ticker and Yield for clarity.
2.  **Wishlist Target Planning (ADI)**: A strategic roadmap for future targets.
    *   **Dynamic Currency Detection**: The reporting currency is extracted directly from the `wishlist.csv` header (3rd field), allowing targets to be set in either USD or RON independently of the portfolio source.
    *   Target ADI goal for the entire wishlist.
    *   A detailed table showing the target gap (Delta) and total investment (formatted with commas for thousands).
    *   Final aggregate investment requirement.

## V. Deployment and Execution Guide
Execution requires the definition of the `PORTFOLIO_PATH` environment variable. The `wishlist.csv` should be located in the same directory as the script.

1.  **Environment Configuration**:
    ```bash
    # Point to the directory containing your portfolio files
    export PORTFOLIO_PATH="/path/to/portfolio_directory/"
    ```
2.  **System Execution**:
    ```bash
    python projects/dividends-builder/main.py
    ```

## VI. Future Work (Optional Enhancements)
The following enhancements are identified for potential future iteration, though currently categorized as non-essential for core functionality:

- [ ] **Advanced Error Parsing**: Implementation of robust type-checking for non-numeric CSV fields.
- [ ] **Data Visualization**: Development of a Matplotlib or Seaborn-based visualization suite for income distribution analysis.
