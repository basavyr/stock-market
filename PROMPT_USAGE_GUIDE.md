# Financial Portfolio Optimization Prompt - Usage Guide

## Overview

The `prompt.md` file is a universal, reusable template for analyzing investment portfolios and recommending allocation strategies. It can be used with any financial AI assistant (Claude, ChatGPT, or specialized finance tools) to deliver customized portfolio optimization recommendations.

## What You Need to Provide

### 1. Current Portfolio CSV File
**File name:** `Report-With-Cash.csv` (or similar)

**Required structure:**
```csv
NetCashBalanceSLB,NetCashBalanceSLBSecurities,NetCashBalanceSLBCommodities
[cash_amount],[cash_amount],[cash_amount]
[optional_rows]

Symbol,Description,ISIN,Quantity,CostBasisPrice,FifoPnlUnrealized
TICKER1,Company Name,ISIN_CODE,shares,cost_basis,unrealized_pnl
TICKER2,Company Name,ISIN_CODE,shares,cost_basis,unrealized_pnl
[... more holdings ...]
```

**Example:**
```csv
NetCashBalanceSLB,NetCashBalanceSLBSecurities,NetCashBalanceSLBCommodities
5629.90,5629.90,0

Symbol,Description,ISIN,Quantity,CostBasisPrice,FifoPnlUnrealized
AAPL,APPLE INC,US0378331005,35.5375,171.478745494,3631.974081
MSFT,MICROSOFT CORP,US5949181045,16.6096,305.085620906,1796.899871
```

### 2. Investment Wishlist CSV File
**File name:** `wishlist.csv` (or similar)

**Required structure:**
```csv
ticker,company_name
TSLA,Tesla Inc
GOOGL,Alphabet Inc
META,Meta Platforms Inc
[... more companies ...]
```

**Note:** Tickers can be uppercase or lowercase. Company names are optional but helpful.

### 3. Investment Profile (Optional but Recommended)
Provide the following information in your message to the analyst:

- **Time Horizon:** How long do you plan to hold these investments? (3-7 years, 10+ years, etc.)
- **Risk Tolerance:** Conservative, Moderate, or Aggressive
- **Diversification Goals:** Any specific sectors to emphasize or avoid?
- **Special Constraints:** Tax considerations, ESG screening, minimum position sizes, etc.
- **Investment Goals:** Growth, Income, Diversification, etc.

## How to Get Your Analysis

### Step 1: Prepare Your Files
1. Export your portfolio as CSV from your brokerage
2. Ensure it has the structure shown above
3. Create a wishlist CSV with the companies you want to analyze

### Step 2: Choose Your AI Assistant
- **Claude** (recommended for deep analysis)
- **ChatGPT** (good general purpose)
- **Specialized Finance Tools** (Bloomberg Terminal, FactSet, etc.)

### Step 3: Prepare the Prompt
1. Copy the entire contents of `prompt.md`
2. Prepare a message that includes:
   - The prompt from `prompt.md`
   - Your portfolio CSV data
   - Your wishlist CSV data
   - Your investment profile (optional)

### Step 4: Submit for Analysis
Paste your message into the AI with instructions like:

```
Here is a financial portfolio optimization prompt and my personal investment data.

PROMPT:
[paste entire prompt.md contents]

MY PORTFOLIO DATA (Report-With-Cash.csv):
[paste your portfolio CSV]

MY WISHLIST (wishlist.csv):
[paste your wishlist CSV]

MY INVESTMENT PROFILE:
- Time Horizon: 3-7 years
- Risk Tolerance: Moderate-to-High
- Goal: Reduce tech concentration, add income-generating assets
- Special Considerations: [any special requirements]

Please conduct a comprehensive analysis and provide:
1. Assessment of my current portfolio
2. Analysis of each company in my wishlist
3. Specific allocation recommendations (dollar amounts and shares)
4. Risk assessment for each recommended position
5. Overall portfolio strategy and implementation plan
```

### Step 5: Review the Results

The analyst will provide:

1. **Executive Summary** - Overview of recommendations and rebalancing rationale
2. **Current Portfolio Analysis** - Assessment of your holdings and diversification
3. **Macro & Sector Context** - Industry tailwinds, headwinds, and current valuations
4. **Individual Company Analyses** - Deep dive on each wishlist company including:
   - Financial metrics and valuation
   - Business fundamentals
   - Growth drivers and catalysts
   - Risk assessment
   - Conviction level and monitoring metrics
5. **Allocation Recommendations** - Specific dollar amounts and share quantities for each company
6. **Portfolio Strategy** - How the allocation improves your portfolio post-investment
7. **Implementation Roadmap** - Step-by-step execution plan

### Step 6: Implement and Monitor

1. Execute purchases according to the recommended allocation
2. Monitor the key metrics identified for each position
3. Set calendar reminders for upcoming catalysts
4. Revisit the allocation at recommended checkpoints (3-year, 5-year, 7-year)
5. Rebalance if fundamentals change or allocations drift significantly

## What You'll Get Back

### For Each Recommended Stock:

**RECOMMENDATION:**
- Cash to deploy (exact dollar amount)
- Shares to purchase (including fractional shares)
- New portfolio weight (%)
- Conviction level (HIGH/MEDIUM/LOW)

**WHY INVEST:**
- Valuation & upside potential
- Business quality & competitive strength
- Near-term catalysts (1-2 years)
- Long-term growth drivers (3-7 years)
- Portfolio fit & diversification benefits

**RISKS:**
- 3-5 specific material risks
- Probability and impact assessment
- How to monitor each risk
- Mitigation strategies
- Timeline for clarity

**CONFIDENCE LEVEL:**
- Rationale for conviction level
- Key monitoring metrics
- Red flags that would reduce conviction
- Green flags that would increase conviction

### Overall Portfolio Recommendations:

**ALLOCATION TABLE:**
- All recommended positions with cash amounts and share quantities
- Action type (New vs. Increase)
- Portfolio weight (%)

**POST-ALLOCATION ANALYSIS:**
- Sector breakdown (before vs. after)
- Concentration metrics
- Expected portfolio characteristics
- Diversification improvements

**IMPLEMENTATION ROADMAP:**
- Step-by-step execution plan
- Suggested order of purchases
- Tax considerations
- Monitoring plan and rebalancing triggers

## Key Features of the Analysis

✅ **Data-Driven:** All recommendations backed by current financial data
✅ **Specific:** Exact dollar amounts and share quantities provided
✅ **Forward-Looking:** Focus on future growth and catalysts
✅ **Transparent:** Clear assumptions, confidence levels, and sources
✅ **Comprehensive:** Both opportunity and risk analysis with equal rigor
✅ **Actionable:** Specific implementation steps and monitoring metrics
✅ **Balanced:** 3-7 year perspective, not short-term trading focus

## CSV File Examples

### Portfolio CSV Example:
```
NetCashBalanceSLB,NetCashBalanceSLBSecurities,NetCashBalanceSLBCommodities
5629.90,5629.90,0

Symbol,Description,ISIN,Quantity,CostBasisPrice,FifoPnlUnrealized
AAPL,APPLE INC,US0378331005,35.5375,171.4787,3631.97
NVDA,NVIDIA CORP,US67066G1040,142.186,36.7604,21580.94
MSFT,MICROSOFT CORP,US5949181045,16.6096,305.0856,1796.90
```

### Wishlist CSV Example:
```
ticker,company_name
tsla,Tesla Inc
googl,Alphabet Inc
meta,Meta Platforms Inc
nvda,Nvidia Corp
avgo,Broadcom Inc
xom,Exxon Mobil Corp
duk,Duke Energy Corp
```

## Common Questions

**Q: How long does the analysis take?**
A: Depends on your AI assistant. Typically 10-30 minutes for comprehensive analysis of 10-20 companies.

**Q: Can I ask follow-up questions?**
A: Yes! Ask the analyst to:
- Explain specific positions in more detail
- Compare two companies
- Stress-test assumptions
- Adjust allocations based on new preferences

**Q: How often should I revisit this analysis?**
A: The prompt recommends:
- **Quarterly:** Monitor key metrics and news
- **At 3 years:** Reassess thesis for each position
- **At 5 years:** Consider taking profits on winners
- **At 7 years:** Execute your stated plan to shift to bonds/funds

**Q: What if my portfolio changes before I implement?**
A: You can:
1. Run the analysis again with updated CSV files
2. Ask the analyst to adjust recommendations for specific changes
3. Focus on the highest-conviction positions if you have limited capital

**Q: Can I use this for different time horizons?**
A: Yes! The prompt is flexible:
- 1-3 years: Focus on near-term catalysts
- 3-7 years: Balanced view of near and long-term
- 10+ years: Emphasize long-term secular trends

**Q: What if I disagree with a recommendation?**
A: Discuss with the analyst:
- Ask for alternative scenarios
- Provide your own assumptions
- Request analysis of different allocation approaches
- Ask about specific risk scenarios

## Tips for Best Results

1. **Use Current Data:** Make sure your portfolio CSV has current prices/holdings
2. **Be Specific:** In your investment profile, be clear about constraints
3. **Ask Questions:** Don't accept recommendations you don't understand
4. **Verify Data:** Double-check stock prices and financial data are recent
5. **Consider Tax Impact:** Mention any cost-basis considerations
6. **Document Decisions:** Keep notes on why you accept/reject recommendations
7. **Monitor Regularly:** Set calendar reminders for key dates

## Support & Feedback

If you have questions about:
- **The prompt:** Review the "How to Use" section in prompt.md
- **CSV format:** Check the example structures above
- **Your analysis:** Ask your AI assistant follow-up questions
- **General strategy:** Consult with a financial advisor

---

**Prompt Version:** 2.0 (Universal Template)
**Last Updated:** February 15, 2026
**Status:** Production Ready
