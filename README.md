# How to create the four represenations of the Swiss railway network

This repository allows you to fully reproduce the four representations of the Swiss railway network.

The source data our work is based on can be found here:

* "Actual Data": https://data.opentransportdata.swiss/en/dataset/istdaten
* "Service Points (Today)": https://data.opentransportdata.swiss/en/dataset/service-points-actual-date
* "Number of Passengers Boarding and Alighting": https://data.opentransportdata.swiss/en/dataset/einundaus
* "Line (Operation Points)": https://data.sbb.ch/explore/dataset/linie-mit-betriebspunkten/information/

We have included all but one source datasets we used in the `raw/` subdirectory of this repository. Please note, however, that the "Actual Data" is too large to be included on GitHub. But you can download them for yourself from the first link above. We have used the data from March 5, 2025.

For easy reproducibility you can simply create a virtual environment as follows:

1. `pip install virtualenv` to install the `virtualenv` library.
2. `virtualenv -p python3 pubtransport` to create the virtual environment.
3. `source pubtransport/bin/activate` to activate the virtual environment.
4. `pip install -r requirements.txt` to recreate the virual environment according to the specifications in the requirements file.

To run the code, simply add e.g. `python3 space_of_changes.py` to some terminal and press enter.

Some of the representations, especially the space-of-changes one, may run for a while (about 10 minutes).

Each of the four Python files will create one of the representations and will create two CSV files, one for the nodes and one for the edges.

When you are done, you can deactivate the virtual environment with `deactivate`.