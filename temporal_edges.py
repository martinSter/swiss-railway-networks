#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Name: temporal_edges.py
Description: This script creates the temporal representation.
Author: Martin Sterchi
Date: 2025-07-23
"""

import pandas as pd
import numpy as np

# Function to sort entries within a group in ascending order of ABFAHRTSZEIT
def sort_data(group):
    return group.sort_values('ABFAHRTSZEIT', ascending = True)

# Function to compute (directed) edges according to spaces-of-changes principle.
def get_edges_in_groups(group):
    # Empty list for results of a group.
    results = []
    # Loop over all rows in group.
    for i in range(len(group)):
        # Nested loop over all subsequent rows.
        for j in range(i + 1, len(group)):
            # Now, append edge to results list.
            results.append((
                group.iloc[i]["STATION_NAME"], # Station of origin
                group.iloc[j]["STATION_NAME"], # Station of destination
                # Time of departure in minutes since the day began.
                (group.iloc[i]["ABFAHRTSZEIT"] - pd.to_datetime("2025-03-05 00:00:00")).total_seconds() / 60,
                # Duration in minutes.
                (group.iloc[j]['ANKUNFTSZEIT'] - group.iloc[i]['ABFAHRTSZEIT']).total_seconds() / 60
            ))
    # Return list.
    return results

# Main function to run the procedure
def main():
    
    # -----------------------------------------------------------------------
    # We first repeat part of the procedure to get the space-of-stops representation.
    
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
    
    # -----------------------------------------------------------------------
    # Here comes the part specific to the temporal representation.
    
    # Now apply that function group-wise.
    edges_series = df.groupby("FAHRT_BEZEICHNER", group_keys=False).apply(get_edges_in_groups, include_groups=False)
    
    # Flatten the result into one edgelist.
    edgelist = [x for l in edges_series.values for x in l]
    
    # Set of stations that appear in edgelist
    stations_in_edgelist = set([e for sub in edgelist for e in sub[:2]])

    # Reduces nodes dataframe to only places in edgelist
    nodes = ds[ds['STATION_NAME'].isin(stations_in_edgelist)]
    
    # Impute missing elevation for Tirano
    nodes.loc[nodes['STATION_NAME'] == "Tirano", "ELEVATION"] = 441
    
    # Export node list
    nodes.sort_values("BPUIC").to_csv("nodelist.csv", sep = ';', encoding = 'utf-8', index = False)

    # Create a node dict with BPUIC as values
    node_dict = dict(zip(nodes.STATION_NAME, nodes.BPUIC))
    
    # Transform edge dict to nested list and replace all station names with their BPUIC
    edges = [[node_dict[e[0]], node_dict[e[1]], int(e[2]), int(e[3])] for e in edgelist]

    # Create a dataframe
    edges = pd.DataFrame(edges, columns = ['BPUIC1','BPUIC2','START','DURATION'])

    # Export edge list
    edges.to_csv("edgelist_temporal.csv", sep = ';', encoding = 'utf-8', index = False)

# -------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
