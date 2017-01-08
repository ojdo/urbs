import pandas as pd
from .pyomoio import get_constants, get_timeseries

def report(instance, filename, commodities=None, sites=None):
    """Write result summary to a spreadsheet file

    Args:
        instance: a urbs model instance
        filename: Excel spreadsheet filename, will be overwritten if exists
        commodities: optional list of commodities for which to write timeseries
        sites: optional list of sites for which to write timeseries

    Returns:
        Nothing
    """
    # get the data
    costs, cpro, ctra, csto = get_constants(instance)

    # create spreadsheet writer object
    with pd.ExcelWriter(filename) as writer:

        # write constants to spreadsheet
        costs.to_frame().to_excel(writer, 'Costs')
        cpro.to_excel(writer, 'Process caps')
        ctra.to_excel(writer, 'Transmission caps')
        csto.to_excel(writer, 'Storage caps')

        # initialize timeseries tableaus
        energies = []
        timeseries = {}

        # collect timeseries data
        for co in commodities:
            for sit in sites:
                (created, consumed, stored, imported, exported,
                 dsm) = get_timeseries(instance, co, sit)

                overprod = pd.DataFrame(
                    columns=['Overproduction'],
                    data=created.sum(axis=1)
                         - consumed.sum(axis=1) 
                         + imported.sum(axis=1)
                         - exported.sum(axis=1) 
                         + stored['Retrieved']
                         - stored['Stored'])

                tableau = pd.concat([created, consumed, stored, imported, 
                                     exported, overprod, dsm],
                                    axis=1,
                                    keys=['Created', 'Consumed', 'Storage', 
                                          'Import from', 'Export to', 
                                          'Balance', 'DSM'])
                timeseries[(co, sit)] = tableau.copy()

                # timeseries sums
                sums = pd.concat([created.sum(),
                                  consumed.sum(),
                                  stored.sum().drop('Level'),
                                  imported.sum(),
                                  exported.sum(),
                                  overprod.sum(),
                                  dsm.sum()], axis=0,
                                 keys=['Created', 'Consumed', 'Storage',
                                       'Import', 'Export', 'Balance', 'DSM'])
                energies.append(sums.to_frame("{}.{}".format(co, sit)))

        # write timeseries data (if any)
        if timeseries:
            # concatenate Commodity sums
            energy = pd.concat(energies, axis=1).fillna(0)
            energy.to_excel(writer, 'Commodity sums')

            # write timeseries to individual sheets
            for co in commodities:
                for sit in sites:
                    # sheet names cannot be longer than 31 characters...
                    sheet_name = "{}.{} timeseries".format(co, sit)[:31]
                    timeseries[(co, sit)].to_excel(writer, sheet_name)
