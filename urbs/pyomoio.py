import pandas as pd
import pyomo.core as pyomo


def get_entity(instance, name):
    """ Retrieve values (or duals) for an entity in a model instance.

    Args:
        instance: a Pyomo ConcreteModel instance
        name: name of a Set, Param, Var, Constraint or Objective

    Returns:
        a Pandas Series with domain as index and values (or 1's, for sets) of
        entity name. For constraints, it retrieves the dual values
    """

    # retrieve entity, its type and its onset names
    entity = instance.__getattribute__(name)
    labels = _get_onset_names(entity)

    # extract values
    if isinstance(entity, pyomo.Set):
        # Pyomo sets don't have values, only elements
        results = pd.DataFrame([(v, 1) for v in entity.value])

        # for unconstrained sets, the column label is identical to their index
        # hence, make index equal to entity name and append underscore to name
        # (=the later column title) to preserve identical index names for both
        # unconstrained supersets
        if not labels:
            labels = [name]
            name = name+'_'

    elif isinstance(entity, pyomo.Param):
        if entity.dim() > 1:
            results = pd.DataFrame([v[0]+(v[1],) for v in entity.iteritems()])
        else:
            results = pd.DataFrame(entity.iteritems())

    elif isinstance(entity, pyomo.Constraint):
        if entity.dim() > 1:
            results = pd.DataFrame(
                [v[0] + (instance.dual[v[1]],) for v in entity.iteritems()])
        elif entity.dim() == 1:
            results = pd.DataFrame(
                [(v[0], instance.dual[v[1]]) for v in entity.iteritems()])
        else:
            results = pd.DataFrame(
                [(v[0], instance.dual[v[1]]) for v in entity.iteritems()])
            labels = ['None']

    else:
        # create DataFrame
        if entity.dim() > 1:
            # concatenate index tuples with value if entity has
            # multidimensional indices v[0]
            results = pd.DataFrame(
                [v[0]+(v[1].value,) for v in entity.iteritems()])
        elif entity.dim() == 1:
            # otherwise, create tuple from scalar index v[0]
            results = pd.DataFrame(
                [(v[0], v[1].value) for v in entity.iteritems()])
        else:
            # assert(entity.dim() == 0)
            results = pd.DataFrame(
                [(v[0], v[1].value) for v in entity.iteritems()])
            labels = ['None']

    # check for duplicate onset names and append one to several "_" to make
    # them unique, e.g. ['sit', 'sit', 'com'] becomes ['sit', 'sit_', 'com']
    for k, label in enumerate(labels):
        if label in labels[:k]:
            labels[k] = labels[k] + "_"

    if not results.empty:
        # name columns according to labels + entity name
        results.columns = labels + [name]
        results.set_index(labels, inplace=True)

        # convert to Series
        results = results[name]
    else:
        # return empty Series
        results = pd.Series(name=name)
    return results


def get_entities(instance, names):
    """ Return one DataFrame with entities in columns and a common index.

    Works only on entities that share a common domain (set or set_tuple), which
    is used as index of the returned DataFrame.

    Args:
        instance: a Pyomo ConcreteModel instance
        names: list of entity names (as returned by list_entities)

    Returns:
        a Pandas DataFrame with entities as columns and domains as index
    """

    df = pd.DataFrame()
    for name in names:
        other = get_entity(instance, name)

        if df.empty:
            df = other.to_frame()
        else:
            index_names_before = df.index.names

            df = df.join(other, how='outer')

            if index_names_before != df.index.names:
                df.index.names = index_names_before

    return df


def list_entities(instance, entity_type):
    """ Return list of sets, params, variables, constraints or objectives

    Args:
        instance: a Pyomo ConcreteModel object
        entity_type: "set", "par", "var", "con" or "obj"

    Returns:
        DataFrame of entities

    Example:
        >>> data = read_excel('mimo-example.xlsx')
        >>> model = create_model(data, range(1,25))
        >>> list_entities(model, 'obj')  #doctest: +NORMALIZE_WHITESPACE
                                         Description Domain
        Name
        obj   minimize(cost = sum of all cost types)     []

    """

    # helper function to discern entities by type
    def filter_by_type(entity, entity_type):
        if entity_type == 'set':
            return isinstance(entity, pyomo.Set) and not entity.virtual
        elif entity_type == 'par':
            return isinstance(entity, pyomo.Param)
        elif entity_type == 'var':
            return isinstance(entity, pyomo.Var)
        elif entity_type == 'con':
            return isinstance(entity, pyomo.Constraint)
        elif entity_type == 'obj':
            return isinstance(entity, pyomo.Objective)
        else:
            raise ValueError("Unknown entity_type '{}'".format(entity_type))

    # create entity iterator, using a python 2 and 3 compatible idiom:
    # http://python3porting.com/differences.html#index-6
    try:
        iter_entities = instance.__dict__.iteritems()  # Python 2 compat
    except AttributeError:
        iter_entities = instance.__dict__.items()  # Python way

    # now iterate over all entties and keep only those whose type matches
    entities = sorted(
        (name, entity.doc, _get_onset_names(entity))
        for (name, entity) in iter_entities
        if filter_by_type(entity, entity_type))

    # if something was found, wrap tuples in DataFrame, otherwise return empty
    if entities:
        entities = pd.DataFrame(entities,
                                columns=['Name', 'Description', 'Domain'])
        entities.set_index('Name', inplace=True)
    else:
        entities = pd.DataFrame()
    return entities


def _get_onset_names(entity):
    """ Return a list of domain set names for a given model entity

    Args:
        entity: a member entity (i.e. a Set, Param, Var, Objective, Constraint)
                of a Pyomo ConcreteModel object

    Returns:
        list of domain set names for that entity

    Example:
        >>> data = read_excel('mimo-example.xlsx')
        >>> model = create_model(data, range(1,25))
        >>> _get_onset_names(model.e_co_stock)
        ['t', 'sit', 'com', 'com_type']
    """
    # get column titles for entities from domain set names
    labels = []

    if isinstance(entity, pyomo.Set):
        if entity.dimen > 1:
            # N-dimensional set tuples, possibly with nested set tuples within
            if entity.domain:
                # retreive list of domain sets, which itself could be nested
                domains = entity.domain.set_tuple
            else:
                try:
                    # if no domain attribute exists, some
                    domains = entity.set_tuple
                except AttributeError:
                    # if that fails, too, a constructed (union, difference,
                    # intersection, ...) set exists. In that case, the
                    # attribute _setA holds the domain for the base set
                    domains = entity._setA.domain.set_tuple

            for domain_set in domains:
                labels.extend(_get_onset_names(domain_set))

        elif entity.dimen == 1:
            if entity.domain:
                # 1D subset; add domain name
                labels.append(entity.domain.name)
            else:
                # unrestricted set; add entity name
                labels.append(entity.name)
        else:
            # no domain, so no labels needed
            pass

    elif isinstance(entity, (pyomo.Param, pyomo.Var, pyomo.Constraint,
                    pyomo.Objective)):
        if entity.dim() > 0 and entity._index:
            labels = _get_onset_names(entity._index)
        else:
            # zero dimensions, so no onset labels
            pass

    else:
        raise ValueError("Unknown entity type!")

    return labels


def get_constants(instance):
    """Return summary DataFrames for important variables

    Usage:
        costs, cpro, ctra, csto = get_constants(instance)

    Args:
        instance: a urbs model instance

    Returns:
        (costs, cpro, ctra, csto) tuple

    Example:
        >>> import pyomo.environ
        >>> from pyomo.opt.base import SolverFactory
        >>> data = read_excel('mimo-example.xlsx')
        >>> prob = create_model(data, range(1,25))
        >>> optim = SolverFactory('glpk')
        >>> result = optim.solve(prob)
        >>> cap_pro = get_constants(prob)[1]['Total']
        >>> cap_pro.xs('Wind park', level='Process').apply(int)
        Site
        Mid      13000
        North    23258
        South        0
        Name: Total, dtype: int64
    """
    costs = get_entity(instance, 'costs')
    cpro = get_entities(instance, ['cap_pro', 'cap_pro_new'])
    ctra = get_entities(instance, ['cap_tra', 'cap_tra_new'])
    csto = get_entities(instance, ['cap_sto_c', 'cap_sto_c_new',
                                   'cap_sto_p', 'cap_sto_p_new'])

    # better labels and index names and return sorted
    if not cpro.empty:
        cpro.index.names = ['Site', 'Process']
        cpro.columns = ['Total', 'New']
        cpro.sortlevel(inplace=True)
    if not ctra.empty:
        ctra.index.names = ['Site In', 'Site Out', 'Transmission', 'Commodity']
        ctra.columns = ['Total', 'New']
        ctra.sortlevel(inplace=True)
    if not csto.empty:
        csto.columns = ['C Total', 'C New', 'P Total', 'P New']
        csto.sortlevel(inplace=True)

    return costs, cpro, ctra, csto


def get_timeseries(instance, com, sit, timesteps=None):
    """Return DataFrames of all timeseries referring to given commodity

    Usage:
        create, consume, store, imp, exp, der = get_timeseries(instance, co,
                                                          sit, timesteps)

    Args:
        instance: a urbs model instance
        com: a commodity
        sit: a site
        timesteps: optional list of timesteps, defaults: all modelled timesteps

    Returns:
        a tuple of (created, consumed, storage, imported, exported,
        dsm) with DataFrames timeseries. These are:

        - created: timeseries of commodity creation, including stock source
        - consumed: timeseries of commodity consumption, including demand
        - storage: timeseries of commodity storage (level, stored, retrieved)
        - imported: timeseries of commodity import (by site)
        - exported: timeseries of commodity export (by site)
        - dsm: timeseries of demand-side management (original, shifted, delta)
    """
    if timesteps is None:
        timesteps = sorted(get_entity(instance, 'tm').index)

    # wrap common function arguments for shorter function calls
    args = (instance, com, sit, timesteps)

    # call individual timeseries getter functions
    created, consumed = get_process_timeseries(*args)
    stored = get_storage_timeseries(*args)
    imported, exported = get_transmission_timeseries(*args)
    dsm = get_dsm_timeseries(*args)
    
    # cross-cutting concern: show shifted demand in process balance as consumed
    consumed = consumed.join(dsm.pop('Shifted').rename('Demand'))
    
    return created, consumed, stored, imported, exported, dsm


def get_process_timeseries(instance, com, sit, timesteps):
    # STOCK
    eco = get_entity(instance, 'e_co_stock').unstack()['Stock']
    eco = eco.xs(sit, level='sit').unstack().fillna(0)
    try:
        stock = eco.loc[timesteps][com]
    except KeyError:
        stock = pd.Series(0, index=timesteps)
    stock.name = 'Stock'
    
    # PROCESS
    # select all entries of created and consumed desired commodity com and site
    # sit. Keep only entries with non-zero values and unstack process column.
    # Finally, slice to the desired timesteps.
    epro = get_entities(instance, ['e_pro_in', 'e_pro_out'])
    try:
        epro = epro.xs(sit, level='sit').xs(com, level='com')
        try:
            created = epro[epro['e_pro_out'] > 0]['e_pro_out'].unstack(level='pro')
            created = created.loc[timesteps].fillna(0)
        except KeyError:
            created = pd.DataFrame(index=timesteps)

        try:
            consumed = epro[epro['e_pro_in'] > 0]['e_pro_in'].unstack(level='pro')
            consumed = consumed.loc[timesteps].fillna(0)
        except KeyError:
            consumed = pd.DataFrame(index=timesteps)
    except KeyError:
        created = pd.DataFrame(index=timesteps)
        consumed = pd.DataFrame(index=timesteps)

    # show stock as created
    created = created.join(stock)

    return created, consumed


def get_storage_timeseries(instance, com, sit, timesteps):
    esto = get_entities(instance, ['e_sto_con', 'e_sto_in', 'e_sto_out'])
    
    try:
        esto = esto.groupby(level=['t', 'sit', 'com']).sum()
        esto = esto.xs(sit, level='sit')
        stored = esto.xs(com, level='com')
        stored = stored.loc[timesteps]
        stored.columns = ['Level', 'Stored', 'Retrieved']
    except (KeyError, ValueError):
        stored = pd.DataFrame(0, index=timesteps,
                              columns=['Level', 'Stored', 'Retrieved'])

    return stored
    

def get_transmission_timeseries(instance, com, sit, timesteps):
    etra = get_entities(instance, ['e_tra_in', 'e_tra_out'])
    
    try:
        etra.index.names = ['tm', 'sitin', 'sitout', 'tra', 'com']
        etra = etra.groupby(level=['tm', 'sitin', 'sitout', 'com']).sum()
        etra = etra.xs(com, level='com')

        imported = (etra.xs(sit, level='sitout')['e_tra_out']
                        .unstack()
                        .fillna(0))
        exported = (etra.xs(sit, level='sitin')['e_tra_in']
                        .unstack()
                        .fillna(0))

    except (ValueError, KeyError):
        imported = pd.DataFrame(index=timesteps)
        exported = pd.DataFrame(index=timesteps)
    
    return imported, exported


def get_dsm_timeseries(instance, com, sit, timesteps):
    # DEMAND
    # default to zeros if commodity has no demand, get timeseries
    try:
        demand = instance.demand.loc[timesteps][sit, com]
    except KeyError:
        demand = pd.Series(0, index=timesteps)
    demand.name = 'Demand'

    # DEMAND SIDE MANAGEMENT (load shifting)
    dsmup = get_entity(instance, 'dsm_up')
    dsmdo = get_entity(instance, 'dsm_down')

    if dsmup.empty:
        # if no DSM happened, the demand is not modified (demanddelta == 0)
        demanddelta = pd.Series(0, index=timesteps)

    else:
        # DSM happened (dsmup implies that dsmdo must be non-zero, too)
        # so the demand will be modified by the difference of DSM up and
        # DSM down uses
        # for sit in m.dsm_site_tuples:
        try:
            dsmup = dsmup.xs(sit, level='sit')
            dsmup = dsmup.xs(com, level='com')

            dsmdo = dsmdo.xs(sit, level='sit')
            dsmdo = dsmdo.xs(com, level='com')
            #  series by summing the first time step set
            dsmdo = dsmdo.unstack().sum(axis=0)
            dsmdo.index.names = ['t']

            # derive secondary timeseries
            demanddelta = dsmup - dsmdo
        except KeyError:
            demanddelta = pd.Series(0, index=timesteps)

    shifted = demand + demanddelta

    # give sensible names to the derived timeseries
    demanddelta.name = 'Delta'
    shifted.name = 'Shifted'

    dsm = pd.concat([shifted, 
                     demand.rename('Unshifted'), 
                     demanddelta], axis=1)

    return dsm

