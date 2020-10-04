import quandl
from datetime import date
from fuzzywuzzy import fuzz
import csv


def stock_search(name: str) -> list:
    """Searches the HKEX_metadata.csv file for the data.
    - It uses fuzzy ratio to evaluate how similar the listing is to the input string
    - If the ratio is higher than the current one, it deletes all potential matches
    in favour of this new one
    - If the ratio is the same, it adds it to the list
    - Schema: [[Ratio, row], [Ratio, row2], ...]
    - row Schema: [code, name (code), description, refreshed_at, from_date, to_date]
    """
    match = [[0, []]]
    csv_file = csv.reader(open('HKEX_metadata.csv', "r"), delimiter=",")
    next(csv_file)
    for row in csv_file:
        listing = row[1]
        Ratio = fuzz.ratio(listing.lower(), name.lower())
        if Ratio > match[0][0]:
            del match[1:]
            match[0][0] = Ratio
            match[0][1] = row
        elif Ratio == match[0][0]:
            match.append([])
            match[-1].append(Ratio)
            match[-1].append(row)
    return match


def stock_data(code: list, start_date: str, end_date: str):
    """ Retrieves stock data from a list of codes from stock_search """
    quandl.read_key()
    data = []
    for stock in code:
        data.append((stock[1][1], quandl.get(f'HKEX/{stock[1][0]}', start_date=start_date, end_date=end_date)))
    return data


if __name__ == '__main__':
    stock_code = stock_search('05806')
    stock_data = stock_data(stock_code, '2010/01/01', str(date.today()))
    for i in stock_data:
        print(i)
