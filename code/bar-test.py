import matplotlib.pyplot as plt
import yfinance as fin


def ShowStocks(stock_names, stock_shares):
    x_ticks = [x for x in range(len(stock_names))]
    stock_prices = []
    for stock in stock_names:
        stock_value = fin.Ticker(stock)
        max_day_price = float(stock_value.info['regularMarketDayHigh'])
        stock_prices.append(max_day_price)
    print(stock_prices)
    print(stock_shares)
    Y = list(map(lambda x: x[0]*x[1], zip(stock_shares, stock_prices)))
    plt.bar(x_ticks, Y, width=0.3, align='center')
    plt.annotate(f'Total \n amount={sum(Y)}', [1, 250])
    plt.xticks(x_ticks, stock_names)
    # plt.yticks([0, max(stock_shares)/2, max(stock_shares)])
    plt.title('Current investment portfolio')
    # plt.xlabel('Company')
    plt.ylabel('Total invested \n capital ($)')
    plt.savefig('financial.png', dpi=400, bbox_inches='tight')


names = ['AAPL', 'MSFT', 'SBUX']
shares = [2.22, 0.69, 1.93]

ShowStocks(names, shares)
