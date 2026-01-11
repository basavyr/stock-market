# Research and Implementation Plan: Portfolio Dividend Revenue Analysis

## I. Project Overview
The primary objective of this project is to develop a standardized framework for the automated calculation and reporting of annual dividend revenue (ADA) for diversified equity portfolios. By integrating real-time market data with local portfolio records, the system provides accurate forecasting of passive income streams.

## II. Data Acquisition and Preprocessing Protocol
The system utilizes a hybrid data acquisition strategy, combining local CSV parsing with real-time API integration:

*   **Ingestion**: Portfolio data is sourced from standardized CSV exports, optimized for **IBKR Flex Queries**.
*   **Dynamic Header Detection**: To accommodate varying export formats, the system dynamically scans for the row containing the `Symbol` field. This allows it to bypass an arbitrary number of metadata or cash balance lines.
*   **Field Mapping**: Required attributes include `Symbol`, `Description`, `ISIN`, `Quantity`, `CostBasisPrice`, and `FifoPnlUnrealized`.
*   **Real-time Integration**: The `yfinance` library is employed to fetch live market data. To ensure a clean terminal interface, internal HTTP exception logging is suppressed for non-critical errors.
*   **Progress Tracking**: Computational progress is monitored via the `tqdm` library, providing visual feedback during high-latency data retrieval operations.

## III. Computational Methodology
The core analytical logic follows a sequential calculation model:

1.  **Individual Annualization**: For each equity holding, the annual dividend per share is derived using the product of the `currentPrice` and the `dividendYield` (corrected by a $10^{-2}$ scalar for percentage compatibility).
2.  **Asset-level Revenue**: Total annual revenue per holding is computed as `Quantity` * `Annual Dividend per Share`.
3.  **Revenue Thresholding (Filtering)**: Assets are evaluated against a predefined threshold (default: $15.0$ USD/annum). Assets failing to meet this criterion are excluded from the detailed reporting phase.
4.  **Portfolio Aggregation**: The **Annual Dividend Income (ADI)** is calculated for both the comprehensive portfolio and the filtered subset.

### 3. Wishlist Analysis (Target Planning)
A special analysis is performed on a `wishlist.csv` file to determine the investment required to reach specific dividend income goals:
- **Share Calculation**: `Required Shares = Target ADI / Annual Dividend per Share`.
- **Valuation**: `Total Cost = Required Shares * Current Market Price`.
- **Precision**: Shares are calculated up to 4 decimal places.

## IV. Presentation and Reporting Logic
The reporting module generates a hierarchical summary with distinct sections:

1.  **Portfolio Analysis (ADI)**: A comprehensive overview of current holdings.
    *   Total Portfolio Annual Dividend Income (ADI) display.
    *   **High Earner Report**: A concise table of assets meeting the threshold, combining Ticker and Yield for clarity.
2.  **Wishlist Target Planning (ADI)**: A strategic roadmap for future targets.
    *   Target ADI goal for the entire wishlist.
    *   A detailed table showing required shares and total investment (formatted with commas for thousands).
    *   Final aggregate investment requirement.

## V. Deployment and Execution Guide
Execution requires the definition of the `PORTFOLIO_PATH` environment variable. The `wishlist.csv` should be located in the same directory as the script.

1.  **Environment Configuration**:
    ```bash
    export PORTFOLIO_PATH="/path/to/portfolio.csv"
    ```
2.  **System Execution**:
    ```bash
    python projects/dividends-builder/main.py
    ```

## VI. Future Work (Optional Enhancements)
The following enhancements are identified for potential future iteration, though currently categorized as non-essential for core functionality:

- [ ] **Advanced Error Parsing**: Implementation of robust type-checking for non-numeric CSV fields.
- [ ] **Data Visualization**: Development of a Matplotlib or Seaborn-based visualization suite for income distribution analysis.
