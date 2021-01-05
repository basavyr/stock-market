import matplotlib.pyplot as plt
import yfinance as fin
import numpy as np

def ShowStocks(stock_names, stock_shares, required_shares):

    x_ticks = np.arange(len(stock_names))

    stock_prices = []

    for stock in stock_names:
        stock_value = fin.Ticker(stock)
        max_day_price = float(stock_value.info['regularMarketDayHigh'])
        stock_prices.append(max_day_price)

    # print(stock_prices)
    # print(stock_shares)

    current_market_value = list(
        map(lambda x: x[0]*x[1], zip(stock_shares, stock_prices)))

    required_market_value = list(
        map(lambda x: x[0]*x[1], zip(required_shares, stock_prices)))

    width = 0.35
    fig, ax = plt.subplots()
    ax.bar(x_ticks-width/2, current_market_value,
           width=width, label='current shares')
    ax.bar(x_ticks+width/2, required_market_value,
           width=width, label='required shares')

    fig.tight_layout()
    # print(sum(required_market_value))

    # plt.annotate(
    #     f'Total \n amount={round(sum(current_market_value),3)}', [1, 250])
    # plt.annotate(
    #     f'Required \n amount={round(sum(required_market_value),3)}', [1.2, 150])
    # plt.xticks(x_ticks, stock_names)
    # plt.yticks([0, max(stock_shares)/2, max(stock_shares)])
    # plt.title('Current investment portfolio')
    # plt.xlabel('Company')
    # plt.ylabel('Total invested \n capital ($)')
    plt.savefig('financial.png', dpi=400, bbox_inches='tight')


OPTIMAL_SHARE = 3.0
names = ['AAPL', 'MSFT', 'SBUX']
shares = [2.22, 0.69, 1.93]
required_shares = [OPTIMAL_SHARE-x for x in shares]
ShowStocks(names, shares, required_shares)
