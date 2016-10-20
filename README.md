# urbs - 1node example

*For installation instructions, please refer to the master branch in the main model repository [**tum-ens/urbs**](https://github.com/tum-ens/urbs).*

This branch contains a small example study with one site, custom run and comparison script and even dares to slightly modify the `urbs.plot` function to automatically skip the empty plots for demand side management (DSM). It also demonstrates how to write a custom scenario generator function, a feat that is enabled by Python's capability to hand functions around just like ordinary objects.

## Plots

### Comparison

<a href="img/comparison.png"><img src="img/comparison.png" alt="Bar chart of total system cost, electricity generation shares and storage use for all ten scenarios s01 to s10." style="width:400px"></a>

### Scenario s01

<a href="img/plot-s01.png"><img src="img/plot-s01.png" alt="Timeseries plot of month June for electricity generation in scenario s01: diesel generator covers main load, only slightly supported by photovoltaics during the day." style="width:400px"></a>

### Scenario s05

<a href="img/plot-s05.png"><img src="img/plot-s05.png" alt="Timeseries plot of month June for electricity generation in scenario s05: photovoltaics covers over half the load, using battery as support during morning/evening hours. Diesel as night backup." style="width:400px"></a>

