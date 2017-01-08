import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from .pyomoio import get_constants, get_timeseries


COLORS = {
    'Biomass plant': (0, 122, 55),
    'Coal plant': (100, 100, 100),
    'Gas plant': (237, 227, 0),
    'Gud plant': (153, 153, 0),
    'Hydro plant': (198, 188, 240),
    'Lignite plant': (116, 66, 65),
    'Photovoltaics': (243, 174, 0),
    'Slack powerplant': (163, 74, 130),
    'Wind park': (122, 179, 225),
    'Decoration': (128, 128, 128),  # plot labels
    'Original Demand': (130, 130, 130),  # thick demand line
    'Demand': (25, 25, 25),  # thick shifted demand line
    'Demand delta': (130, 130, 130),  # dashed demand delta
    'Grid': (128, 128, 128),  # background grid
    'Overproduction': (190, 0, 99),  # excess power
    'Storage': (60, 36, 154),  # storage area
    'Stock': (222, 222, 222),  # stock commodity power
    'Purchase': (0, 153, 153),
    'Feed-in': (255, 204, 153)}


def sort_plot_elements(elements):
    """Sort timeseries for plotting

    Sorts the timeseries (created, consumed) ascending with variance.
    It places base load at the bottom and peak load at the top.
    This enhances clearity and readability of the plots.

    Args:
        elements: timeseries of created or consumed

    Returns:
        elements_sorted: sorted timeseries of created or consumed
    """
    # no need of sorting the columns if there's only one
    if len(elements.columns) < 2:
        return elements

    # calculate standard deviation
    std = pd.DataFrame(np.zeros_like(elements.tail(1)),
                       index=elements.index[-1:]+1,
                       columns=elements.columns)
    # calculate mean
    mean = pd.DataFrame(np.zeros_like(elements.tail(1)),
                        index=elements.index[-1:]+1,
                        columns=elements.columns)
    # calculate quotient
    quotient = pd.DataFrame(
        np.zeros_like(elements.tail(1)),
        index=elements.index[-1:]+1,
        columns=elements.columns)

    for col in std.columns:
        std[col] = np.std(elements[col])
        mean[col] = np.mean(elements[col])
        quotient[col] = std[col] / mean[col]
    # fill nan values (due to division by 0)
    quotient = quotient.fillna(0)
    # sort created/consumed ascencing with quotient i.e. base load first
    elements = elements.append(quotient)
    new_columns = elements.columns[elements.ix[elements.last_valid_index()]
                                           .argsort()]
    elements_sorted = elements[new_columns][:-1]

    return elements_sorted


def plot(prob, com, sit, timesteps=None, power_unit='MW', energy_unit='MWh',
         figure_size=(16, 12)):
    """Plot a stacked timeseries of commodity balance and storage.

    Creates a stackplot of the energy balance of a given commodity, together
    with stored energy in a second subplot.

    Args:
        prob: urbs model instance
        com: commodity name to plot
        sit: site name to plot
        timesteps: optional list of  timesteps to plot; default: prob.tm
        power_unit: optional string for unit; default: 'MW'
        energy_unit: optional string for storage plot; default: 'MWh'
        figure_size: optional (width, height) tuple in inch; default: (16, 12)

    Returns:
        fig: figure handle
    """
    import matplotlib.pyplot as plt
    import matplotlib as mpl

    if timesteps is None:
        # default to all simulated timesteps
        timesteps = sorted(get_entity(prob, 'tm').index)

    (created, consumed, stored, imported, exported,
     dsm) = get_timeseries(prob, com, sit, timesteps)

    costs, cpro, ctra, csto = get_constants(prob)

    # move retrieved/stored storage timeseries to created/consumed and
    # rename storage columns back to 'storage' for color mapping
    created = created.join(stored['Retrieved'])
    consumed = consumed.join(stored['Stored'])
    created.rename(columns={'Retrieved': 'Storage'}, inplace=True)
    consumed.rename(columns={'Stored': 'Storage'}, inplace=True)

    # only keep storage content in storage timeseries
    stored = stored['Level']

    # add imported/exported timeseries
    created = created.join(imported)
    consumed = consumed.join(exported)

    # move demand to its own plot
    demand = consumed.pop('Demand')
    original = dsm.pop('Unshifted')
    deltademand = dsm.pop('Delta')
    try:
        # detect whether DSM could be used in this plot
        # if so, show DSM subplot (even if deltademand == 0 for the whole time)
        plot_dsm = prob.dsm.loc[(sit, com),
                                ['cap-max-do', 'cap-max-up']].sum() > 0
    except KeyError:
        plot_dsm = False

    # remove all columns from created which are all-zeros in both created and
    # consumed (except the last one, to prevent a completely empty frame)
    for col in created.columns:
        if not created[col].any() and len(created.columns) > 1:
            if col not in consumed.columns or not consumed[col].any():
                created.pop(col)

    # sorting plot elements
    created = sort_plot_elements(created)
    consumed = sort_plot_elements(consumed)

    # FIGURE
    fig = plt.figure(figsize=figure_size)
    all_axes = []
    if plot_dsm:
        gs = mpl.gridspec.GridSpec(3, 1, height_ratios=[3, 1, 1], hspace=0.05)
    else:
        gs = mpl.gridspec.GridSpec(2, 1, height_ratios=[2, 1], hspace=0.05)

    # STACKPLOT
    ax0 = plt.subplot(gs[0])
    all_axes.append(ax0)

    # PLOT CONSUMED
    sp00 = ax0.stackplot(consumed.index,
                         -consumed.as_matrix().T,
                         labels=tuple(consumed.columns),
                         linewidth=0.15)

    # color
    for k, commodity in enumerate(consumed.columns):
        commodity_color = to_color(commodity)

        sp00[k].set_facecolor(commodity_color)
        sp00[k].set_edgecolor((.5, .5, .5))

    # PLOT CREATED
    sp0 = ax0.stackplot(created.index,
                        created.as_matrix().T,
                        labels=tuple(created.columns),
                        linewidth=0.15)

    for k, commodity in enumerate(created.columns):
        commodity_color = to_color(commodity)

        sp0[k].set_facecolor(commodity_color)
        sp0[k].set_edgecolor(to_color('Decoration'))

    # label
    ax0.set_title('Energy balance of {} in {}'.format(com, sit))
    ax0.set_ylabel('Power ({})'.format(power_unit))

    # legend
    handles, labels = ax0.get_legend_handles_labels()

    # add "only" consumed commodities to the legend
    for item in consumed.columns[::-1]:
        # if item not in created add to legend, except items
        # from consumed which are all-zeros
        if item in created.columns or consumed[item].any():
            pass
        else:
            # remove item/commodity is not consumed
            item_index = labels.index(item)
            handles.pop(item_index)
            labels.pop(item_index)

    for item in labels:
        if labels.count(item) > 1:
            item_index = labels.index(item)
            handles.pop(item_index)
            labels.pop(item_index)

    lg = ax0.legend(handles=handles[::-1],
                    labels=labels[::-1],
                    frameon=False,
                    loc='upper left',
                    bbox_to_anchor=(1, 1))
    plt.setp(lg.get_patches(), edgecolor=to_color('Decoration'),
             linewidth=0.15)
    plt.setp(ax0.get_xticklabels(), visible=False)

    # PLOT DEMAND
    ax0.plot(original.index, original.values, linewidth=0.8,
             color=to_color('Original Demand'))

    ax0.plot(demand.index, demand.values, linewidth=1.0,
             color=to_color('Demand'))

    # PLOT STORAGE
    ax1 = plt.subplot(gs[1], sharex=ax0)
    all_axes.append(ax1)
    sp1 = ax1.stackplot(stored.index, stored.values, linewidth=0.15)
    if plot_dsm:
        # hide xtick labels only if DSM plot follows
        plt.setp(ax1.get_xticklabels(), visible=False)

    # color & labels
    sp1[0].set_facecolor(to_color('Storage'))
    sp1[0].set_edgecolor(to_color('Decoration'))
    ax1.set_ylabel('Energy ({})'.format(energy_unit))

    try:
        ax1.set_ylim((0, 0.5 + csto.loc[sit, :, com]['C Total'].sum()))
    except KeyError:
        pass

    if plot_dsm:
        # PLOT DEMAND SIDE MANAGEMENT
        ax2 = plt.subplot(gs[2], sharex=ax0)
        all_axes.append(ax2)
        ax2.bar(deltademand.index,
                deltademand.values,
                color=to_color('Demand delta'),
                edgecolor='none')

        # labels & y-limits
        ax2.set_xlabel('Time in year (h)')
        ax2.set_ylabel('Energy ({})'.format(energy_unit))

    # make xtick distance duration-dependent
    if len(timesteps) > 26*168:
        steps_between_ticks = 168*4
    elif len(timesteps) > 3*168:
        steps_between_ticks = 168
    elif len(timesteps) > 2 * 24:
        steps_between_ticks = 24
    elif len(timesteps) > 24:
        steps_between_ticks = 6
    else:
        steps_between_ticks = 3
    xticks = timesteps[::steps_between_ticks]

    # set limits and ticks for all axes
    for ax in all_axes:
        ax.set_frame_on(False)
        ax.set_xlim((timesteps[0], timesteps[-1]))
        ax.set_xticks(xticks)
        ax.xaxis.grid(True, 'major', color=to_color('Grid'),
                      linestyle='-')
        ax.yaxis.grid(True, 'major', color=to_color('Grid'),
                      linestyle='-')
        ax.xaxis.set_ticks_position('none')
        ax.yaxis.set_ticks_position('none')

        # group 1,000,000 with commas, but only if maximum or minimum are
        # sufficiently large. Otherwise, keep default tick labels
        ymin, ymax = ax.get_ylim()
        if ymin < -90 or ymax > 90:
            group_thousands = mpl.ticker.FuncFormatter(
                lambda x, pos: '{:0,d}'.format(int(x)))
            ax.yaxis.set_major_formatter(group_thousands)
        else:
            skip_lowest = mpl.ticker.FuncFormatter(
                lambda y, pos: '' if pos == 0 else y)
            ax.yaxis.set_major_formatter(skip_lowest)

    return fig


def result_figures(prob, figure_basename, plot_title_prefix=None, periods={},
                   **kwds):
    """Create plot for each site and demand commodity and save to files.

    Args:
        prob: urbs model instance
        figure_basename: relative filename prefix that is shared
        plot_title_prefix: (optional) plot title identifier
        periods: (optional) dict of 'period name': timesteps_list items
                 if omitted, one period 'all' with all timesteps is assumed
        **kwds: (optional) keyword arguments are forwarded to urbs.plot()
    """
    # default to all timesteps if no
    if not periods:
        periods = {'all': sorted(get_entity(prob, 'tm').index)}

    # create timeseries plot for each demand (site, commodity) timeseries
    for sit, com in prob.demand.columns:
        for period, timesteps in periods.items():
            # do the plotting
            fig = plot(prob, com, sit, timesteps=timesteps, **kwds)

            # change the figure title
            ax0 = fig.get_axes()[0]
            # if no custom title prefix is specified, use the figure
            if not plot_title_prefix:
                plot_title_prefix = os.path.basename(figure_basename)
            new_figure_title = ax0.get_title().replace(
                'Energy balance of ', '{}: '.format(plot_title_prefix))
            ax0.set_title(new_figure_title)

            # save plot to files
            for ext in ['png', 'pdf']:
                fig_filename = '{}-{}-{}-{}.{}'.format(
                                    figure_basename, com, sit, period, ext)
                fig.savefig(fig_filename, bbox_inches='tight')
            plt.close(fig)


def to_color(obj=None):
    """Assign a deterministic pseudo-random color to argument.

    If COLORS[obj] is set, return that. Otherwise, create a random color from
    the hash(obj) representation string. For strings, this value depends only
    on the string content, so that same strings always yield the same color.

    Args:
        obj: any hashable object

    Returns:
        a (r, g, b) color tuple if COLORS[obj] is set, otherwise a hexstring
    """
    if obj is None:
        obj = random()
    try:
        color = tuple(rgb/255.0 for rgb in COLORS[obj])
    except KeyError:
        # random deterministic color
        import hashlib
        color = '#' + hashlib.sha1(obj.encode()).hexdigest()[-6:]
    return color

