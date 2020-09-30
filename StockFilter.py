"""
StockFilter
1. Determine a time frame T to analyze, and a shorter time frame S as a sieve.
2. Over T, compute the average % return over every S period. This is the min return.
3. Over T, calculate the B volatility.
4. If min return and B are acceptable, the stock is considered.

StockTrader
1. Has a list of current holdings, and calls StockFilter to add new stocks.
2. Decides to buy/sell based on some factors.

StockStrategist
1. Set portfolio %'s for different holdings (ETFs, stocks,...).
2. Logs every change in capital.
3. Will buy in the holdings that are under the target %.
4. Will allocate cash depending on the volatility of the day.
"""
import concurrent.futures
import math
import requests
import time
from datetime import datetime, timedelta
import lxml
import lxml.html
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt


class PriceHistory:
    def __init__(self, symbol, start, end):
        """
        :param symbol: example "AAPL, or TRI.TO"
        :param start: Start date as datetime object
        :param end: End date as datetime object
        """
        self.symbol = symbol.upper()
        self.start = start
        self.end = end
        self.hdrs = {"authority": "finance.yahoo.com",
                     "method": "GET",
                     "scheme": "https",
                     "accept": "text/html,application/xhtml+xml",
                     "accept-encoding": "gzip, deflate, br",
                     "accept-language": "en-US,en;q=0.9",
                     "cache-control": "no-cache",
                     "dnt": "1",
                     "pragma": "no-cache",
                     "sec-fetch-mode": "navigate",
                     "sec-fetch-site": "same-origin",
                     "sec-fetch-user": "?1",
                     "upgrade-insecure-requests": "1",
                     "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64)"}
        self.urls = self.__urls__()

    @staticmethod
    def __table__(url, hdrs):
        page = requests.get(url, headers=hdrs)
        tree = lxml.html.fromstring(page.content)
        table = tree.xpath('//table')
        string = lxml.etree.tostring(table[0], method='xml')
        data = pd.read_html(string)[0]
        return data

    @staticmethod
    def __clean_history__(price_history):
        history = price_history.drop(len(price_history) - 1)
        history = history.set_index('Date')
        return history

    def scrape_history(self, url):
        """
        :param url: URL location of stock price history
        :return: price history
        """
        hdrs = self.hdrs
        price_history = self.__table__(url, hdrs)
        price_history = self.__clean_history__(price_history)
        return price_history

    @staticmethod
    def __check__(s, e):
        start = np.datetime64(s, "D")
        end = np.datetime64(e, "D")
        if np.busday_count(start, end) > 100:
            response = True
        else:
            response = False
        return response

    def __calc_pages__(self, response):
        s, e = [self.start, self.end]
        if response:
            pages = math.ceil(np.busday_count(np.datetime64(s, "D"), np.datetime64(e, "D")) / 100)
        else:
            pages = 1
        return pages

    @staticmethod
    def __calc_start__(pages, s, e):
        calendar_days = (e - s) / pages
        while pages > 0:
            s = s + calendar_days
            yield s
            pages -= 1

    def __starts__(self, pages, s, e):
        starts = []
        for s in self.__calc_start__(pages, s, e):
            if pages == 0:
                break
            starts.append(s)
        starts.append(e)
        return starts

    def __getStarts__(self):
        response = self.__check__(self.start, self.end)
        pages = self.__calc_pages__(response)
        starts = self.__starts__(pages, self.start, self.end)
        return starts

    @staticmethod
    def __format_date__(date_datetime):
        date_timetuple = date_datetime.timetuple()
        date_mktime = time.mktime(date_timetuple)
        date_int = int(date_mktime)
        date_str = str(date_int)
        return date_str

    def __urls__(self):
        """
        Returns
        -------
        urls : a list of urls complete with start and end dates for each 100 trading day block
        """
        starts = self.__getStarts__()
        symbol = self.symbol
        urls = []
        for d in range(len(starts) - 1):
            start = str(self.__format_date__(starts[d]))
            end = str(self.__format_date__(starts[d + 1]))
            url = "HTTP://finance.yahoo.com/quote/{0}/history?period1={1}&period2={" \
                  "2}&interval=1d&filter=history&frequency=1d "
            url = url.format(symbol, start, end)
            urls.append(url)
        return urls


def bootstrap_risk_assessment(stock_data, confidence, info, plot=False):
    stock_data = pd.to_numeric(stock_data['Adj Close**'], errors='coerce').dropna()
    returns = stock_data.pct_change()
    if plot:
        returns.hist(bins=40, density=True, histtype="stepfilled", alpha=0.5)
        plt.title(f"Daily returns on {info[0]}, {info[1].date()}-{info[2].date()}", weight="bold")
        plt.show()
    return returns.quantile(1 - confidence)


def get_stock_list():
    with open("nasdaqlisted.txt", "r") as nasdaq:
        nasdaq.readline()
        tickers = [line.split("|")[0] for line in nasdaq]
    return tickers[:-1]


def main(start, end, confidence, threshold):
    green_light = []
    for ticker in get_stock_list()[:100]:
        try:
            print(f"Assessing: {ticker}")
            t0 = time.time()
            stock = PriceHistory(ticker, start_date, end_date)
            urls = stock.urls
            threads = min(30, len(urls))
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
                history = list(executor.map(stock.scrape_history, urls))
            t1 = time.time()
            print(f"{t1 - t0} seconds to download {len(urls)} urls for {ticker}.")
            history_concat = pd.concat(history)
            history_concat = history_concat[~history_concat.Open.str.contains("Dividend")]
            assessment = bootstrap_risk_assessment(history_concat, confidence, [ticker, start_date, end_date])
            if assessment >= threshold:
                print(f"{ticker}: {assessment}")
                green_light.append((f"{ticker}", assessment))
        except KeyError:
            print('Fatal Error: Site Down')
            continue
        except TypeError:
            continue
        except IndexError:
            continue
    green_light.sort(key=lambda x: x[1])
    return green_light


if __name__ == '__main__':
    start_date, end_date = datetime.today() - timedelta(days=365*10), datetime.today()
    con, thresh = 0.95, -0.03
    start_time = time.time()
    green_stocks = main(start_date, end_date, con, thresh)
    end_time = time.time()
    print(f"Gathered {len(green_stocks)} good stocks in {end_time-start_time}s")
    for i in green_stocks:
        print(i)
