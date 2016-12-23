import os
import pyomo.environ
import shutil
import urbs
from datetime import datetime
from pyomo.opt.base import SolverFactory

# SCENARIOS

def sce_gen(scenario_name, pv_cost, st_cost, bat_cost, tank_cost, gas_price,
            co2_limit):
    def scenario(data):
        # short-hands for individual DataFrames
        com = data['commodity']
        pro = data['process']
        sto = data['storage']

        # row indices for entries
        pv_plant = ('House', 'Photovoltaics')
        st_plant = ('House', 'Solarthermal')
        battery = ('House', 'Battery', 'Electricity')
        tank = ('House', 'Tank', 'Heat')
        gas = ('House', 'Gas', 'Stock')
        co2 = ('House', 'CO2', 'Env')

        # change investment/fuel cost values according to arguments
        pro.loc[pv_plant, 'inv-cost'] = pv_cost  # EUR/kW
        pro.loc[st_plant, 'inv-cost'] = st_cost  # EUR/kW
        sto.loc[battery, 'inv-cost-c'] = bat_cost  # EUR/kWh
        sto.loc[tank, 'inv-cost-c'] = tank_cost  # EUR/kWh
        com.loc[gas, 'price'] = gas_price  # EUR/kWh
        com.loc[co2, 'max'] = co2_limit  # kg/a

        return data
    scenario.__name__ = scenario_name
    return scenario


def elp_gen(scenario_name, elec_price):
    def scenario(data):
        com = data['commodity']
        elec_buy = ('House', 'Elec-buy', 'Buy')
        com.loc[elec_buy, 'price'] = elec_price  # EUR/kWh
        return data
    scenario.__name__ = scenario_name
    return scenario

# HELPER FUNCTIONS

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
    data = urbs.read_excel(input_file)
    data = scenario(data)

    # create model
    prob = urbs.create_model(data, timesteps)

    # refresh time stamp string and create filename for logfile
    now = prob.created
    log_filename = os.path.join(result_dir, '{}.log').format(sce)

    # solve model and read results
    optim = SolverFactory('gurobi')  # cplex, glpk, gurobi, ...
    optim = setup_solver(optim, logfile=log_filename)
    result = optim.solve(prob, tee=True)

    # copy input file to result directory
    shutil.copyfile(input_file, os.path.join(result_dir, input_file))

	# write report to spreadsheet
    urbs.report(
        prob,
        os.path.join(result_dir, '{}.xlsx').format(sce),
        ['Electricity', 'Heat', 'CO2'], prob.sit)

    urbs.result_figures(
        prob,
        os.path.join(result_dir, '{}'.format(sce)),
        plot_title_prefix=sce.replace('_', ' '),
        periods=plot_periods, power_unit='kW', energy_unit='kWh',
        figure_size=(24,4))
    return prob

if __name__ == '__main__':
    input_file = '1house.xlsx'
    result_name = os.path.splitext(input_file)[0]  # cut away file extension
    result_dir = prepare_result_directory(result_name)  # name + time stamp

    # optimisation timesteps (up to a full year; select less for debugging)
    (offset, length) = (0, 8760)  # time step selection
    timesteps = range(offset, offset+length+1)

    # plotting timesteps: individual months
    plot_periods = {
        '01-jan': range(   1,  745),
        '02-feb': range( 745, 1417),
        '03-mar': range(1417, 2161),
        '04-apr': range(2161, 2881),
        '05-may': range(2881, 3625),
        '06-jun': range(3625, 4345),
        '07-jul': range(4345, 5089),
        '08-aug': range(5089, 5833),
        '09-sep': range(5833, 6553),
        '10-oct': range(6553, 7297),
        '11-nov': range(7297, 8017),
        '12-dec': range(8017, 8761),
    }

    # add or change plot colors
    my_colors = {
        'Battery': (100, 160, 200),
        'Demand': (0, 0, 0),
        'Gas boiler': (218, 215, 203),
        'Feed-in': (62, 173, 0),
        'Heating rod': (180, 50, 15),
        'Heatpump': (227, 114, 34),
        'Photovoltaics': (0, 101, 189),
        'Purchase': (0, 51, 89),
        'Solarthermal': (255, 220, 0),
        'Storage': (100, 160, 200)}
    for name, color in my_colors.items():
        urbs.COLORS[name] = color

    # select scenarios to be run
    scenarios = [
        #        name                 pv    st   bat  tank    gas   co2
        #                            inv   inv   inv   inv  price limit
        sce_gen('s01-base',         2000,  950, 1200,  100, 0.070, 3700),
        sce_gen('s02-cheap-pv',     1000,  950, 1200,  100, 0.070, 3700),
        sce_gen('s03-cheap-st-50',  2000,  425, 1200,  100, 0.070, 3700),
        sce_gen('s04-cheap-st-25',  2000,  213, 1200,  100, 0.070, 3700),
        sce_gen('s05-cheap-bat',    2000,  950,  600,  100, 0.070, 3700),
        sce_gen('s06-cheap-tnk',    2000,  950, 1200,   50, 0.070, 3700),
        sce_gen('s07-cheap-gas',    2000,  950, 1200,  100, 0.035, 3700),
        sce_gen('s08-expen-gas',    2000,  950, 1200,  100, 0.140, 3700),
        sce_gen('s09-limit-co2-25', 2000,  950, 1200,  100, 0.070, 2775),
        sce_gen('s10-limit-co2-50', 2000,  950, 1200,  100, 0.070, 1850),

        #       name              elec
        #                        price
        elp_gen('s11-ep20',      0.20),  # numeric: constant
        elp_gen('s12-ep25',      0.25),
        elp_gen('s13-ep30',      0.30),
        elp_gen('s14-ep35',      0.35),
        elp_gen('s15-buy1', '1,0xBuy'),  # string: timeseries
        elp_gen('s16-buy3', '3,0xBuy'),  # '2,0xBuy' is equal to s01-ref
        elp_gen('s17-buy5', '5,0xBuy'),
    ]

    for scenario in scenarios:
        prob = run_scenario(input_file, timesteps, scenario,
                            result_dir, plot_periods=plot_periods)
