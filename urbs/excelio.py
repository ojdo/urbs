import pandas as pd
from xlrd import XLRDError


def read_excel(filename):
    """Read Excel input file and prepare URBS input dict.

    Reads an Excel spreadsheet that adheres to the structure shown in
    mimo-example.xlsx. Two preprocessing steps happen here:
    1. Column titles in 'Demand' and 'SupIm' are split, so that
    'Site.Commodity' becomes the MultiIndex column ('Site', 'Commodity').
    2. The attribute 'annuity-factor' is derived here from the columns 'wacc'
    and 'depreciation' for 'Process', 'Transmission' and 'Storage'.

    Args:
        filename: filename to an Excel spreadsheet with the required sheets
            'Commodity', 'Process', 'Transmission', 'Storage', 'Demand' and
            'SupIm'.

    Returns:
        a dict of 6 DataFrames

    Example:
        >>> data = read_excel('mimo-example.xlsx')
        >>> data['hacks'].loc['Global CO2 limit', 'Value']
        150000000
    """
    with pd.ExcelFile(filename) as xls:
        site = xls.parse('Site').set_index(['Name'])
        commodity = (
            xls.parse('Commodity').set_index(['Site', 'Commodity', 'Type']))
        process = xls.parse('Process').set_index(['Site', 'Process'])
        process_commodity = (
            xls.parse('Process-Commodity')
               .set_index(['Process', 'Commodity', 'Direction']))
        transmission = (
            xls.parse('Transmission')
               .set_index(['Site In', 'Site Out',
                           'Transmission', 'Commodity']))
        storage = (
            xls.parse('Storage').set_index(['Site', 'Storage', 'Commodity']))
        demand = xls.parse('Demand').set_index(['t'])
        supim = xls.parse('SupIm').set_index(['t'])
        buy_sell_price = xls.parse('Buy-Sell-Price').set_index(['t'])
        dsm = xls.parse('DSM').set_index(['Site', 'Commodity'])
        try:
            hacks = xls.parse('Hacks').set_index(['Name'])
        except XLRDError:
            hacks = None

    # prepare input data
    # split columns by dots '.', so that 'DE.Elec' becomes the two-level
    # column index ('DE', 'Elec')
    demand.columns = split_columns(demand.columns, '.')
    supim.columns = split_columns(supim.columns, '.')
    buy_sell_price.columns = split_columns(buy_sell_price.columns, '.')

    data = {
        'site': site,
        'commodity': commodity,
        'process': process,
        'process_commodity': process_commodity,
        'transmission': transmission,
        'storage': storage,
        'demand': demand,
        'supim': supim,
        'buy_sell_price': buy_sell_price,
        'dsm': dsm}
    if hacks is not None:
        data['hacks'] = hacks

    # sort nested indexes to make direct assignments work
    for key in data:
        if isinstance(data[key].index, pd.core.index.MultiIndex):
            data[key].sortlevel(inplace=True)
    return data


def split_columns(columns, sep='.'):
    """Split columns by separator into MultiIndex.

    Given a list of column labels containing a separator string (default: '.'),
    derive a MulitIndex that is split at the separator string.

    Args:
        columns: list of column labels, containing the separator string
        sep: the separator string (default: '.')

    Returns:
        a MultiIndex corresponding to input, with levels split at separator

    Example:
        >>> split_columns(['DE.Elec', 'MA.Elec', 'NO.Wind'])
        MultiIndex(levels=[['DE', 'MA', 'NO'], ['Elec', 'Wind']],
                   labels=[[0, 1, 2], [0, 0, 1]])

    """
    if len(columns) == 0:
        return columns
    column_tuples = [tuple(col.split('.')) for col in columns]
    return pd.MultiIndex.from_tuples(column_tuples)
