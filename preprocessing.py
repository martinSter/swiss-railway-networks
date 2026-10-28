#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Name: preprocessing.py
Description: Data loading and node list creation shared by all network representations.
Author: Martin Sterchi
Date: 2026-10-28
"""

import pandas as pd

# Function to load the train stops from a file of the "Actual Data".
def read_trains(path):
    # Load the data ("Actual Data"), only the columns needed here
    df = pd.read_csv(path, sep=";", low_memory=False,
                     usecols=['FAHRT_BEZEICHNER','PRODUKT_ID','LINIEN_TEXT','FAELLT_AUS_TF',
                              'BPUIC','HALTESTELLEN_NAME','ANKUNFTSZEIT','ABFAHRTSZEIT'])

    # Impute 'Zug'
    df.loc[df["PRODUKT_ID"].isna(), "PRODUKT_ID"] = 'Zug'

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

    # Convert ANKUNFTSZEIT and ABFAHRTSZEIT to datetime format (only train rows are left at this point)
    df['ANKUNFTSZEIT'] = pd.to_datetime(df['ANKUNFTSZEIT'], format = "%d.%m.%Y %H:%M")
    df['ABFAHRTSZEIT'] = pd.to_datetime(df['ABFAHRTSZEIT'], format = "%d.%m.%Y %H:%M")

    return df

# Function to load the stations with their attributes.
def read_stations():
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

    return ds

# Function to load all data. Returns the train stops ('df') and the stations ('ds').
# Within a trip ('FAHRT_BEZEICHNER'), the stops in 'df' are in order of ABFAHRTSZEIT.
def load_data():
    # Train stops of March 5, 2025
    df = read_trains('raw/2025-03-05_istdaten.csv')

    # On March 5, 2025, the line Travers - Buttes was served by buses only. We therefore replace all trips
    # that stop on this line (on either day) by the same trips of May 7, 2025 (also a Wednesday),
    # shifted to March 5, 2025.
    df2 = read_trains('raw/2025-05-07_istdaten.csv')
    # Travers, La Presta Mines d'asphalte, Couvet, Môtiers NE, Fleurier, Buttes
    corridor = [8504215, 8504284, 8504285, 8504286, 8504287, 8504288]
    trips = (set(df.loc[df['BPUIC'].isin(corridor), 'FAHRT_BEZEICHNER']) |
             set(df2.loc[df2['BPUIC'].isin(corridor), 'FAHRT_BEZEICHNER']))
    df2 = df2[df2['FAHRT_BEZEICHNER'].isin(trips)].copy()
    shift = pd.Timestamp('2025-03-05') - pd.Timestamp('2025-05-07')
    df2['ANKUNFTSZEIT'] = df2['ANKUNFTSZEIT'] + shift
    df2['ABFAHRTSZEIT'] = df2['ABFAHRTSZEIT'] + shift
    df = pd.concat([df[~df['FAHRT_BEZEICHNER'].isin(trips)], df2], ignore_index = True)

    # Stations
    ds = read_stations()

    # Left-join with station names and coordinates
    df = pd.merge(df, ds, on = 'BPUIC', how = 'left')

    # There are 18 missing values for 'HALTESTELLEN_NAME' which we impute from 'STATION_NAME'.
    df.loc[df['HALTESTELLEN_NAME'].isna(), "HALTESTELLEN_NAME"] = df.loc[df['HALTESTELLEN_NAME'].isna(), "STATION_NAME"]

    return df, ds

# Function to create the node list for a set of station names and export it.
# All representations share the same node list.
def make_nodelist(ds, stations):
    # Domodossola does not appear in the "Actual Data" and is only connected in the space-of-stations
    # representation, but all representations share the same nodelist.
    stations = set(stations) | {'Domodossola'}

    # Reduces nodes dataframe to only places in edgelist
    nodes = ds[ds['STATION_NAME'].isin(stations)].copy()

    # Impute missing elevation for Tirano
    nodes.loc[nodes['STATION_NAME'] == "Tirano", "ELEVATION"] = 441

    # Columns to be checked for new column 'TRAFFIC_VALID'.
    cols = ['AVG_DAILY_TRAFFIC', 'AVG_DAILY_TRAFFIC_WEEKDAYS', 'AVG_DAILY_TRAFFIC_WEEKENDS']

    # Create a column that indicates whether the average traffic information is valid or not.
    nodes.loc[:, 'TRAFFIC_VALID'] = ~(nodes[cols].isna().all(axis=1) | (nodes[cols] == 49).any(axis=1))

    # Export node list
    nodes.sort_values("BPUIC").to_csv("clean/nodelist.csv", sep = ';', encoding = 'utf-8', index = False)

    return nodes
