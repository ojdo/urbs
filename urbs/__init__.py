"""urbs: A linear optimisation model for distributed energy systems

urbs minimises total cost for providing energy in form of desired commodities
(usually electricity) to satisfy a given demand in form of timeseries. The
model contains commodities (electricity, fossil fuels, renewable energy
sources, greenhouse gases), processes that convert one commodity to another
(while emitting greenhouse gases as a secondary output), transmission for
transporting commodities between sites and storage for saving/retrieving
commodities.

"""

from .excelio import read_excel
from .model import create_model
from .plot import COLORS, plot, result_figures
from .pyomoio import get_entity, get_entities, get_constants, get_timeseries
from .report import report
from .util import save, load
