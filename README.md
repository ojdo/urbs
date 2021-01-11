> 2021-01-11: I archive this personal fork, as this model is being maintained in the upstream repo [tum-ens/urbs](https://github.com/tum-ens/urbs). I only don't delete it for its (technically outdated, but illustrative) examples [1house](https://github.com/ojdo/urbs/tree/1house) and [1node](https://github.com/ojdo/urbs/tree/1node) that demonstrate intermediate to advanced use of urbs for performing small-scale case studies.

# urbs

urbs is a [linear programming](https://en.wikipedia.org/wiki/Linear_programming) optimisation model for capacity expansion planning and unit commitment for distributed energy systems. Its name, latin for city, stems from its origin as a model for optimisation for urban energy systems. Since then, it has been adapted to multiple scales from neighbourhoods to continents.

[![Documentation Status](https://readthedocs.org/projects/urbs/badge/?version=latest)](http://urbs.readthedocs.io/en/latest/?badge=latest)
[![DOI](https://zenodo.org/badge/doi/10.5281/zenodo.60484.svg)](http://dx.doi.org/10.5281/zenodo.60484)
[![Gitter](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/tum-ens/urbs?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)

## Features

  * urbs is a linear programming model for multi-commodity energy systems with a focus on optimal storage sizing and use.
  * It finds the minimum cost energy system to satisfy given demand timeseries for possibly multiple commodities (e.g. electricity).
  * By default, operates on hourly-spaced timesteps (configurable).
  * Thanks to [Pandas](https://pandas.pydata.org), complex data analysis is easy.
  * The model itself is quite small thanks to relying on the [Pyomo](http://www.pyomo.org/)
  * The small codebase includes reporting and plotting functionality.

## Screenshots

<a href="doc/img/plot.png"><img src="doc/img/plot.png" alt="Timeseries plot of 8 days of electricity generation in vertex 'North' in scenario_all_together in hourly resolution: Hydro and biomass provide flat base load of about 50% to cover the daily fluctuating load, while large share of wind and small part photovoltaic generation cover the rest, supported by a day-night storage." style="width:400px"></a>

<a href="doc/img/comparison.png"><img src="doc/img/comparison.png" alt="Bar chart of cumulated annual electricity generation costs for all 5 scenarios defined in runme.py." style="width:400px"></a>

*Continue in [tum-ens/urbs](https://github.com/tum-ens/urbs) for the full and up-to-date README.md.*
