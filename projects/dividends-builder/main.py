import yfinance as yf


def main():
    ticker = yf.Ticker("BTU")

    info = ticker.info
    dividends = ticker.dividends

    # print(info)
    print("TTM Dividend Yield:", info.get("dividendYield"), " %")
    print("Forward Dividend Rate:", info.get("dividendRate"))
    print("Dividend History:")
    print(dividends.tail())


if __name__ == "__main__":
    main()
