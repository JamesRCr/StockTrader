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
import pandas
import matplotlib.pyplot as plt
from yahoofinancials import YahooFinancials
from datetime import datetime
plt.style.use("ggplot")


def retrieve_stock_data(ticker, start, end):
    """
    Retrieves daily stock open, close, and adjusted close data.
    """
    json = YahooFinancials(ticker).get_historical_price_data(start, end, "daily")
    print(f"Got {ticker} information")
    df = pandas.DataFrame(columns=["open", "close", "adjclose"])
    for row in json[ticker]["prices"]:
        date = datetime.fromisoformat(row["formatted_date"])
        df.loc[date] = [row["open"], row["close"], row["adjclose"]]
    df.index.name = "date"
    return df


def bootstrap_risk_assessment(stock_data, confidence, info, plot=False):
    returns = stock_data["adjclose"].pct_change().dropna()
    if plot:
        returns.hist(bins=40, density=True, histtype="stepfilled", alpha=0.5)
        plt.title(f"Daily returns on {info[0]}, {info[1][:4]}-{info[2][:4]}", weight="bold")
        plt.show()
    return returns.quantile(1-confidence)


def get_stock_list():
    with open("nasdaqlisted.txt", "r") as nasdaq:
        nasdaq.readline()
        tickers = [line.split("|")[0] for line in nasdaq]
    return tickers[:-1]


def main(start, end, confidence, threshold):
    green_light = []
    for ticker in get_stock_list()[:1000]:
        try:
            print(f"Assessing: {ticker}")
            stock = retrieve_stock_data(ticker, start, end)
            assessment = bootstrap_risk_assessment(stock, confidence, [ticker, start, end])
            if assessment >= threshold:
                print(f"{ticker}: {assessment}")
                bootstrap_risk_assessment(stock, confidence, [ticker, start, end], plot=True)
                green_light.append((f"{ticker}", assessment))
        except AttributeError:
            continue
        except KeyError:
            continue
    green_light.sort(key=lambda x: x[1])
    return green_light


if __name__ == '__main__':
    start_date, end_date = "2010-01-01", "2014-01-01"
    con, thresh = 0.95, -0.03
    print(main(start_date, end_date, con, thresh))


