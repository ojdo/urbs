import coopr.environ
import os
import urbs
from coopr.opt.base import SolverFactory
from datetime import datetime


# SCENARIOS
def scenario_base(data):
    # do nothing
    return data


def scenario_no_supim(data):
    # don't allow supply intermittent processes
    pro = data['process']
    supim_processes = (pro.index.get_level_values('Process').isin([
                  'Photovoltaics', 'Wind park']))
    pro.loc[supim_processes, 'cap-up'] = 0
    pro.loc[supim_processes, 'cap-lo'] = 0
    pro.loc[supim_processes, 'inst-cap'] = 0
    return data


def scenario_supim_expensive(data):
    # make supply intermittent processes expensive
    pro = data['process']
    supim_processes = (pro.index.get_level_values('Process').isin([
                  'Photovoltaics', 'Wind park']))
    pro.loc[supim_processes, 'inv-cost'] *= 3
    pro.loc[supim_processes, 'fix-cost'] *= 3
    return data


def scenario_heat_pump_expensive(data):
    """ heat pump variable costs increased 50-fold to force other """
    pro = data['process']
    heat_pumps = (pro.index.get_level_values('Process').isin([
                  'Heat pump domestic', 'Heat pump plant']))
    pro.loc[heat_pumps, 'var-cost'] *= 50.0
    return data


def scenario_cheap_battery(data):
    """ make storage cheap by reducing inv-cost by 95%, 
    fix and var-cost by 90% for batteries """
    sto = data['storage']
    battery = (sto.index.get_level_values('Storage') == 'Battery')
    sto.loc[battery, 'inv-cost-c'] *= 0.05
    sto.loc[battery, 'inv-cost-p'] *= 0.05
    sto.loc[battery, 'fix-cost-c'] *= 0.10
    sto.loc[battery, 'fix-cost-p'] *= 0.10
    sto.loc[battery, 'var-cost-c'] *= 0.10
    sto.loc[battery, 'var-cost-p'] *= 0.10
    pro = data['process']
    pro['inst-cap'] = 0
    pro['cap-lo'] = 0
    return data


def prepare_result_directory(result_name):
    """ create a time stamped directory within the result folder """
    # timestamp for result directory
    now = datetime.now().strftime('%Y%m%dT%H%M')

    # create result directory if not existent
    result_dir = os.path.join('result', '{}-{}'.format(result_name, now))
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    return result_dir


def setup_solver(optim, logfile='solver.log'):
    """ """
    if optim.name == 'gurobi':
        # reference with list of option names
        # http://www.gurobi.com/documentation/5.6/reference-manual/parameters
        optim.set_options("logfile={}".format(logfile)) 
        # optim.set_options("timelimit=7200")  # seconds
        # optim.set_options("mipgap=5e-4")  # default = 1e-4
        optim.set_options("threads=48")
    elif optim.name == 'glpk':
        # reference with list of options
        # execute 'glpsol --help'
        optim.set_options("log={}".format(logfile))
        # optim.set_options("tmlim=7200")  # seconds
        # optim.set_options("mipgap=.0005")
    else:
        print("Warning from setup_solver: no options set for solver "
              "'{}'!".format(optim.name))
    return optim

def run_scenario(input_file, timesteps, scenario, result_dir, plot_periods={}):
    """ run an urbs model for given input, time steps and scenario

    Args:
        input_file: filename to an Excel spreadsheet for urbs.read_excel
        timesteps: a list of timesteps, e.g. range(0,8761)
        scenario: a scenario function that modifies the input data dict
        result_dir: directory name for result spreadsheet and plots

    Returns:
        the urbs model instance
    """

    # scenario name, read and modify data for scenario
    sce = scenario.__name__
    data = urbs.load(input_file)
    data = scenario(data)

    # create model
    model = urbs.create_model(data, timesteps)
    prob = model.create()

    # refresh time stamp string and create filename for logfile
    now = prob.created
    log_filename = os.path.join(result_dir, '{}-{}.log').format(sce, now)

    # solve model and read results
    optim = SolverFactory('gurobi')  # cplex, glpk, gurobi, ...
    optim = setup_solver(optim, logfile=log_filename)
    result = optim.solve(prob, tee=True)
    prob.load(result)

    # write report to spreadsheet
    #urbs.report(
    #    prob,
    #    os.path.join(result_dir, '{}-{}.xlsx').format(sce, now),
    #    prob.com_demand, prob.sit)

    # store optimisation problem for later re-analysis
    urbs.save(
        prob,
        os.path.join(result_dir, '{}-{}.pgz').format(sce, now))

    urbs.result_figures(
        prob, 
        os.path.join(result_dir, sce),
        plot_title_prefix=sce.replace('_', ' ').title(),
        periods=plot_periods,
        power_unit='kW', energy_unit='kWh')
    return prob

if __name__ == '__main__':
    input_file = 'rivhg15.pgz'
    result_name = os.path.splitext(input_file)[0]  # cut away file extension
    result_dir = prepare_result_directory(result_name)  # name + time stamp

    # simulation timesteps
    timesteps = range(0,8761)
    
    # plotting timesteps
    plot_length = 24*7  
    periods = {
        'spr': range(1000, 1000 + plot_length + 1),
        'sum': range(3000, 3000 + plot_length + 1),
        'aut': range(5000, 5000 + plot_length + 1),
        'win': range(7000, 7000 + plot_length + 1),
    }
    
    # add or change plot colors as (r, g, b) tuples (range 0-255 each)
    my_colors = {
        'Alpenstrasse': (215,25,28),
        'Diezmanning': (227,74,51),
        'Einzelhandel': (240,124,74),
        'Moosham': (253,174,97),
        'Nord': (253,201,128),
        'Pipeline': (254,228,159),
        'Rainbachstrasse': (255,255,191),
        'Reiterstrasse': (227,243,182),
        'Schletter': (199,232,173),
        'Suedwesten': (171,221,164),
        'Umspannwerk': (128,191,171),
        'Zentrum': (85,161,178),
        'District heating plant': (184, 81, 88),
        'Elec heating domestic': (233, 157, 126),
        'Gas power plant': (166, 116, 115),
        'Gas heating plant': (120, 81, 80),
        'Gas heating domestic': (116, 66, 65),
        'Heat pump domestic': (252, 226, 148),
        'Heat pump plant': (252, 217, 116),
        'Photovoltaics': (226, 126, 85),
        'Slack heating plant': (196, 42, 163),
        'Slack power plant': (196, 42, 163),
        'Transformer': (235, 154, 96),
        'Wind park': (0, 82, 147),
    }
    for country, color in my_colors.iteritems():
        urbs.COLORS[country] = color

    # select scenarios to be run
    scenarios = [
        scenario_base,
        scenario_no_supim,
        scenario_supim_expensive,
        scenario_cheap_battery,
        scenario_heat_pump_expensive]

    for scenario in scenarios:
        prob = run_scenario(input_file, timesteps, scenario, 
                            result_dir, plot_periods=periods)
