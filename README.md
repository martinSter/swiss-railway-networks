# How to create the four representations of the Swiss railway network

This repository allows you to fully reproduce the four representations of the Swiss railway network.

The source data our work is based on can be found here:

* "Actual Data": https://data.opentransportdata.swiss/en/dataset/istdaten
* "Service Points (Today)": https://data.opentransportdata.swiss/en/dataset/service-points-actual-date
* "Number of Passengers Boarding and Alighting": https://data.opentransportdata.swiss/en/dataset/einundaus
* "Line (Operation Points)": https://data.sbb.ch/explore/dataset/linie-mit-betriebspunkten/information/

We have included all source datasets we used in the `raw/` subdirectory of this repository except for the "Actual Data" source dataset which is too large to be included on GitHub. But you can download this dataset from the first link above. We have used the data from March 5, 2025.

If you simply want to rerun the processing of the raw data and get the CSV files for the four representations, you can run `./make_all.sh`. This bash script will create the virtual environment and install all necessary libraries (according to `requirements.txt`). It will then activate the virtual environment and run all python scripts and create the data. Note that the bash script will also create checksums for the CSV files so you can check if your CSV files are identical to the ones we provide.

Please note that the processing of the raw data may take about 20 minutes.

The final CSV files will be written into the directory `clean/` (note that we decided to commit the latest version of the data to the repository).