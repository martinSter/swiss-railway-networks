#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Name: space_of_stops.py
Description: This script creates the space-of-stops network representation.
Author: Martin Sterchi
Date: 2025-07-23
"""

import pandas as pd
import numpy as np
from collections import Counter

# Function to sort entries within a group in ascending order of ABFAHRTSZEIT
def sort_data(group):
    return group.sort_values('ABFAHRTSZEIT', ascending = True)

# Main function to run the procedure
def main():
    
    # Load the data ("Actual Data")
    df = pd.read_csv('raw/2025-03-05_istdaten.csv', sep=";", low_memory=False)
    
    # Impute 'Zug'
    df.loc[df["PRODUKT_ID"].isna(), "PRODUKT_ID"] = 'Zug'
    
    # Convert BETRIEBSTAG to date format
    df['BETRIEBSTAG'] = pd.to_datetime(df['BETRIEBSTAG'], format = "%d.%m.%Y")
    
    # Convert ANKUNFTSZEIT, AN_PROGNOSE, ABFAHRTSZEIT, AB_PROGNOSE to datetime format
    df['ANKUNFTSZEIT'] = pd.to_datetime(df['ANKUNFTSZEIT'], format = "%d.%m.%Y %H:%M")
    df['AN_PROGNOSE'] = pd.to_datetime(df['AN_PROGNOSE'], format = "%d.%m.%Y %H:%M:%S")
    df['ABFAHRTSZEIT'] = pd.to_datetime(df['ABFAHRTSZEIT'], format = "%d.%m.%Y %H:%M")
    df['AB_PROGNOSE'] = pd.to_datetime(df['AB_PROGNOSE'], format = "%d.%m.%Y %H:%M:%S")
    
    # First we reduce to only trains
    df = df[df['PRODUKT_ID'] == "Zug"]
    # Filter out all entries with FAELLT_AUS_TF == True
    df = df[df['FAELLT_AUS_TF'] == False]
    # Filter out all entries with LINIEN_TEXT == "ATZ" (car trains)
    df = df[df['LINIEN_TEXT'] != "ATZ"]
    
    # Merge stations in Brig, Lugano, Locarno
    df.loc[df['HALTESTELLEN_NAME'] == "Brig Bahnhofplatz", "BPUIC"] = 8501609
    df.loc[df['HALTESTELLEN_NAME'] == "Lugano FLP", "BPUIC"] = 8505300
    df.loc[df['HALTESTELLEN_NAME'] == "Locarno FART", "BPUIC"] = 8505400
    df.loc[df['HALTESTELLEN_NAME'] == "Brig Bahnhofplatz", "HALTESTELLEN_NAME"] = "Brig"
    df.loc[df['HALTESTELLEN_NAME'] == "Lugano FLP", "HALTESTELLEN_NAME"] = "Lugano"
    df.loc[df['HALTESTELLEN_NAME'] == "Locarno FART", "HALTESTELLEN_NAME"] = "Locarno"
    
    # Load the data ("Service Points (Today)")
    ds = pd.read_csv('raw/actual_date-swiss-only-service_point-2025-03-06.csv', sep = ";", low_memory = False)
    
    # Keep only the relevant columns
    ds = ds[["number","designationOfficial","cantonName","municipalityName","businessOrganisationDescriptionEn","wgs84East","wgs84North","height"]]
    
    # Load the data ("Number of Passengers Boarding and Alighting")
    ds_freq = pd.read_csv('raw/t01x-sbb-cff-ffs-frequentia-2023.csv', sep = ";", low_memory = False)
    
    # For every station, we only keep the most recent measurements.
    ds_freq = ds_freq.loc[ds_freq.groupby('UIC')['Jahr_Annee_Anno'].idxmax()]
    
    # Remove thousand separator and make integers out of it.
    ds_freq['DTV_TJM_TGM'] = ds_freq['DTV_TJM_TGM'].str.replace('’', '').astype(int)
    ds_freq['DWV_TMJO_TFM'] = ds_freq['DWV_TMJO_TFM'].str.replace('’', '').astype(int)
    ds_freq['DNWV_TMJNO_TMGNL'] = ds_freq['DNWV_TMJNO_TMGNL'].str.replace('’', '').astype(int)
    
    # Keep only the relevant columns
    ds_freq = ds_freq[["UIC","DTV_TJM_TGM","DWV_TMJO_TFM","DNWV_TMJNO_TMGNL"]]

    # Join to 'ds'
    ds = pd.merge(ds, ds_freq, left_on = 'number', right_on = 'UIC', how = 'left')

    # Drop 'UIC'
    ds = ds.drop('UIC', axis=1)

    # Better column names
    ds.columns = ['BPUIC','STATION_NAME','CANTON','MUNICIPALITY','COMPANY',
                  'LONGITUDE','LATITUDE','ELEVATION','AVG_DAILY_TRAFFIC',
                  'AVG_DAILY_TRAFFIC_WEEKDAYS','AVG_DAILY_TRAFFIC_WEEKENDS']

    # Left-join with station names and coordinates
    df = pd.merge(df, ds, on = 'BPUIC', how = 'left')

    # There are 18 missing values for 'HALTESTELLEN_NAME' which we impute from 'STATION_NAME'.
    df.loc[df['HALTESTELLEN_NAME'].isna(), "HALTESTELLEN_NAME"] = df.loc[df['HALTESTELLEN_NAME'].isna(), "STATION_NAME"]

    # First group by FAHRT_BEZEICHNER and then filter out all groups with only one entry
    # It's mostly trains that stop at a place at the border (I think)
    df_filtered = df.groupby('FAHRT_BEZEICHNER').filter(lambda g: len(g) > 1)
    
    # Sort for each group
    df_sorted = df_filtered.groupby('FAHRT_BEZEICHNER', group_keys=True).apply(sort_data, include_groups=False)
    
    # Empty list
    edgelist = []
    
    # Variables to store previous row and its index
    prev_row = None
    prev_idx = None

    # Loop over rows of dataframe
    for i, row in df_sorted.iterrows():
        # Only start with second row
        # Only if the two rows belong to the same Fahrt
        if prev_idx is not None and prev_idx == i[0]:
            # Add edge to edgelist assuming it's a directed edge
            edgelist.append((prev_row['STATION_NAME'], 
                             row['STATION_NAME'], 
                            (row['ANKUNFTSZEIT'] - prev_row['ABFAHRTSZEIT']).total_seconds() / 60))
        # Set current row and row index to previous ones
        prev_idx = i[0]
        prev_row = row
    
    # Empty dict
    edges = {}

    # Loop over elements in edgelist
    for i in edgelist:
        # Create key
        key = (i[0], i[1])
        # Get previous entries in dict (if there are any)
        prev = edges.get(key, (0, 0))
        # Update values in dict
        edges[key] = (prev[0] + 1, prev[1] + i[2])

    # Divide summed up travel times by number of trips
    edges = {k: (v[0], round(v[1]/v[0], 2)) for k, v in edges.items()}

    # Remove the two edges between Basel Bad Bf and Schaffhausen (there are German stations in-between)
    del edges[('Basel Bad Bf', 'Schaffhausen')]
    del edges[('Schaffhausen', 'Basel Bad Bf')]

    # Set of stations that appear in edgelist
    stations_in_edgelist = set(sum(list(edges.keys()), ()))

    # Reduces nodes dataframe to only places in edgelist
    nodes = ds[ds['STATION_NAME'].isin(stations_in_edgelist)]
    
    # Impute missing elevation for Tirano
    nodes.loc[nodes['STATION_NAME'] == "Tirano", "ELEVATION"] = 441
    
    # Export node list
    nodes.sort_values("BPUIC").to_csv("nodelist.csv", sep = ';', encoding = 'utf-8', index = False)

    # Create a node dict with BPUIC as values
    node_dict = dict(zip(nodes.STATION_NAME, nodes.BPUIC))

    # Transform edge dict to nested list and replace all station names with their BPUIC
    edges = [[node_dict[k[0]], node_dict[k[1]], v[0], v[1]] for k,v in edges.items()]

    # Create a dataframe
    edges = pd.DataFrame(edges, columns = ['BPUIC1','BPUIC2','NUM_CONNECTIONS','AVG_DURATION'])

    # Export edge list
    edges.to_csv("edgelist_SoSto.csv", sep = ';', encoding = 'utf-8', index = False)

# -------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
