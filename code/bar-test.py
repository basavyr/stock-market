#! /Users/robertpoenaru/.pyenv/shims/python

import matplotlib.pyplot as plt
import yfinance as fin
import numpy as np
import time
import datetime

# print(datetime.datetime.fromtimestamp(time.time()))


date = lambda: str(datetime.datetime.fromtimestamp(time.time()))[:16]

print(date())

# guide from https://matplotlib.org/3.1.1/gallery/lines_bars_and_markers/barchart.html#sphx-glr-gallery-lines-bars-and-markers-barchart-py


def autolabel(axes, bars):
    """Attach a text label above each bar in *rects*, displaying its height."""
    for bar in bars:
        height = bar.get_height()
        axes.annotate(f'{round(height,2)}',
                      xy=(bar.get_x() + bar.get_width() / 2, height),
                      xytext=(0, 3),  # 3 points vertical offset
                      textcoords="offset points",
                      ha='center', va='bottom')


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
        map(lambda x: x[0] * x[1], zip(stock_shares, stock_prices)))

    required_market_value = list(
        map(lambda x: x[0] * x[1], zip(required_shares, stock_prices)))

    width = 0.35
    fig, ax = plt.subplots()
    bar1 = ax.bar(x_ticks - width / 2, current_market_value,
                  width=width, label='current shares')
    bar2 = ax.bar(x_ticks + width / 2, required_market_value,
                  width=width, label='required shares')

    # plt.annotate(
    #     f'Total \n amount={round(sum(current_market_value),3)}', [1, 250])
    # plt.annotate(
    #     f'Required \n amount={round(sum(required_market_value),3)}', [1.2, 150])
    plt.text(0.25, 0.75, f'Total \n amount={round(sum(current_market_value),3)}', horizontalalignment='center',
             verticalalignment='center', transform=ax.transAxes, fontsize=8)
    plt.text(0.25, 0.65, f'Required \n amount={round(sum(required_market_value),3)}', horizontalalignment='center',
             verticalalignment='center', transform=ax.transAxes, fontsize=8)
    ax.set_title(f'Investment portfolio \n As of: {date()}')
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(stock_names)
    ax.set_ylabel('Amount $')
    max_scale_amount = max(max(current_market_value),
                           max(required_market_value))
    ax.set_ylim(0, max_scale_amount + 100)
    ax.legend(loc='best')

    autolabel(ax, bar1)
    autolabel(ax, bar2)
    # plt.xticks(x_ticks, stock_names)
    # plt.yticks([0, max(stock_shares)/2, max(stock_shares)])
    # plt.title('Current investment portfolio')
    # plt.xlabel('Company')
    # plt.ylabel('Total invested \n capital ($)')

    fig.tight_layout()
    plt.savefig('financial.png', dpi=400, bbox_inches='tight')


OPTIMAL_SHARE = 3.0
names = ['AAPL', 'MSFT', 'SBUX']
shares = [2.22, 0.69, 1.93]
required_shares = [OPTIMAL_SHARE - x for x in shares]
ShowStocks(names, shares, required_shares)
