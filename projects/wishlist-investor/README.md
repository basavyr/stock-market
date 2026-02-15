# Investment Opportunities

Introductory notations:
- Throughout the project, the meaning of "investor profile" or "client" or "user" will mean the person for which this project is attributed to. For example, if I would like to use the "Investment Opportunities", then I am a client/user and I can consider myself an investor profile. We can use these terms inter-changeably.
- A portfolio in which the client has holdings will be referred to as Current Portfolio/Portfolio or a simple notation P (if needed)
- The total capital in cash (cash into client's brokerage account) is referred to as "Total Cash" or CASH
- Wishlist: a list of companies for which the client would like to invest CASH, in order to extend the underlying portfolio P. (Wishlist might or might not contain companies which are already in P)

## Goal

This project aims at building the following functionality:

An investment plan based on three factors, which are specific to the current investor profile:
1. A "wishlist": a list of companies in which the client might want to invest.
2. Total capital that is "ready to be invested" (i.e., cash on the brokerage account). This is a fixed amount in USD (CASH).
3. Current holdings. The stocks already owned by the profile might help on new financial decisions; avoiding over-investing in a company, or avoiding scenarios in which over-allocation in the same sector, etc. The wishlist does not guarantee that it only has stocks that are not present in the current portfolio P.

This needs to be implemented in such a way that responses are based on the actual financial characteristics of the companies from the wishlist. It should be based on the evolution of its earnings (quarter-to-quarter, YoY, etc), revenues, profit, profit margins, earnings per share, dividend yield (current and forward), price to earnings, and so on. Moreover, I would like to be able to understand if the company is planning to invest/extend its core business, or if it wants to add new business models. Also important would be to know when to see potential risks with the company (e.g., closure of departments, internal stock sellout, regulatory changes from new Government bills and so on).

## Structured Plan to Execute

The way that this should work is very straightforward, and it will be detailed below.

0. We should always assume an investment scenario in which the client is just accumulating capital, trying to invest by prudent and responsible purchases of shares over the long term. The client is not interested in speculative behavior; no day-trading and no selling of shares after a a short period of time.
1. First, a pure analysis of the amount of cash that is available needs to be put into perspective with the current portfolio. This will help to understand how big is the actual investment plan relative to the current holdings.
2. Wishlist breakdown per individual company, take each company, check if it is present or not in the portfolio. The company, if present, then we should check its current profit (e.g., if the client has this company as a great resource regarding unrealized profit, then maybe we should consider as a preferred stock; however, if the stock has way too much percentage of the total portfolio valuation, then we should proceed with caution, as over-investing in a single company might be detrimental in the long term).
3. Once a clear context of each wishlist stock is determined, then allocation of a potential investment ca ne done. Report should be clearly structured, following each company, the recommended amount to invest, and then the fundamental reasons for it. Moreover, for each company this can be condensed into a "Why" and then also a section called "Keep in Mind", where after this potential positive analysis is argumented, a few potential real risks must also be mentioned.

## Final results

All this data can be compiled into a proper format, such that it can then be displayed on a simple static web application created with Hugo. The design principles can be inspired from Interactive Brokers, such that it will fit a nice and fluent but professional look with style to fit an investment capability.

There should be a concise list with all the companies from the wishlist, the recommended amount, and then the reasoning "Why" and "Keep in Mind" sections. These must be nicely structured as a tabular view, but the "Keep in Mind" section can be collapsed first, and then user decides to how it per each company.

## Data Structure

A) The current portfolio details are available as .csv in "./Report-With-Cash.csv". This (as you will see in the requirements section) must be abstracted from codebase and user. The file is useful because it contains information regarding available CASH but also the actual holdings.

B) Regarding the wishlist: we do not have as of right now a concise local file .csv or .json where we hold this information. I am thinking that this can be done in a few possible ways:
- construct wishlist right from the browser web app itself; after we create the list, we have a "generate investment report" button that will start the actual execution with the scenario described above. Everything should be persistent to the local browser cookies or whatever is necessary.
- the final results can be nicely structured as json.

!!! These are just sketch ideas and intuitions, not strict requirements. We need to established via a careful optimal plan to determine the best way to handle the wishlist database and data flow.

## Requirements

- Build using Python (current pytorch environment already set here).
- Static website built using Hugo.
- Avoid any hardcoded variable, paths, values. There can be ".env" here where we store what we need.
- Streamlined operations of the entire workflow (minimal as possible)
- Rely on as much as local (javascript static browser) processing where needed, such that it can be shipped as a standalone static website compatible for any needs.
- The design principles can be inspired from Interactive Brokers, such that it will fit a nice and fluent but professional look with style to fit an investment capability

## Prototype Workflow (No API Keys)

This prototype is split into two parts:

1) A Hugo UI (runs in the browser) used to:
   - upload the portfolio CSV (stored locally in `localStorage`)
   - build a wishlist via ticker search (stored locally in `localStorage`)
   - generate and render the investment plan

2) A local Python backend (runs on your machine) used to fetch real market prices at report-build time using `yfinance` (free) and to write/return the unified `report.json`.

### 1) Run the static website

From `projects/wishlist-investor`:

```bash
hugo server --source hugo
```

Open the shown local URL and follow the wizard.

### 2) Run the local Python backend

From `projects/wishlist-investor`:

```bash
pip install yfinance
python3 backend.py
```

Keep it running while you use the website. The UI will call it at `http://127.0.0.1:8750`.

### 3) Generate the report

In the wizard, after you upload `Report-With-Cash.csv` and add wishlist tickers, click `Generate Report`.

### Notes

- `report.json` is the unified JSON containing current holdings + wishlist + real quotes + recommendations.
- Local caches are stored under `.cache/` (gitignored).
