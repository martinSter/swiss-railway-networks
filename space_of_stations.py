#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Name: space_of_stations.py
Description: This script creates the space-of-stations network representation.
Author: Martin Sterchi
Date: 2025-07-23
"""

import pandas as pd
import numpy as np
import geopy.distance
from collections import Counter, defaultdict

# Function to sort entries within a group in ascending order of ABFAHRTSZEIT
def sort_data(group):
    return group.sort_values('ABFAHRTSZEIT', ascending = True)

# Function to sort entries within a group in ascending order of KM
def sort_data2(group):
    return group.sort_values('KM', ascending = True)

# Function to check whether elements a and b are NOT adjacent in lst.
def is_shortcut(lst, a, b):
    return not any((x, y) == (a, b) or (x, y) == (b, a) for x, y in zip(lst, lst[1:]))

# Define a function to compute direct distance.
def compute_distance(station1, station2):
    return geopy.distance.geodesic(
        nodes.loc[nodes['STATION_NAME'] == station1, "coord"].item(), 
        nodes.loc[nodes['STATION_NAME'] == station2, "coord"].item()).km
            
# Main function to run the procedure
def main():
    
    # -----------------------------------------------------------------------
    # We first repeat the procedure to get the space-of-stops representation.
    
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

    # Transform edge dict to nested list and replace all station names with their BPUIC
    edges = [[k[0], k[1], v[0], v[1]] for k,v in edges.items()]

    # Create a dataframe
    edges = pd.DataFrame(edges, columns = ['STATION1','STATION2','NUM_CONNECTIONS','AVG_DURATION'])
    
    # -----------------------------------------------------------------------
    # Here comes the part specific to the space-of-stations representation.
    
    # Get a list of unique undirected edges.
    unique_undirected_edges = list(set((min(e1, e2), max(e1, e2)) for e1, e2 in zip(edges["STATION1"], edges["STATION2"])))
    
    # In order to make the procedure further below more efficient, we extract here all unique trips ("Fahrten").
    # Empty dict
    fahrten = {}

    # Loop over grouped df.
    # If the same key (sequence of stops) reappears, the value will be overwritten.
    # But that behavior is desired: we only want to keep one FAHRT_BEZEICHNER per key.
    for fahrt, group in df.groupby('FAHRT_BEZEICHNER'):
        fahrten[tuple(group['STATION_NAME'])] = fahrt
        
    # Reduce the dataframe to the 'Fahrten' in list of values of dict.
    df = df[df['FAHRT_BEZEICHNER'].isin(list(fahrten.values()))]

    # defaultdict with lists
    result_dict = defaultdict(list)

    # Iterate over rows
    for _, row in df.iterrows():
        # Create a dict with stations as keys and FAHRT_BEZEICHNER as values.
        result_dict[row['STATION_NAME']].append(row['FAHRT_BEZEICHNER'])

    # Convert back to normal dict.
    result_dict = dict(result_dict)

    # Empty list for shortcuts.
    shortcut_edges = []

    # Loop over list of undirected edges.
    for idx, edge in enumerate(unique_undirected_edges):
        # Find all 'Fahrten' in which both stations of the edge appear.
        intersection = list(set(result_dict[edge[0]]) & set(result_dict[edge[1]]))
        # Initialize shortcut to False
        shortcut = False
        # Loop over 'Fahrten' in which both stations of the edge appear.
        for fahrt in intersection:
            # Get the sequence of stations in current 'Fahrt'.
            seq_of_stations = df.loc[df['FAHRT_BEZEICHNER'] == fahrt, 'STATION_NAME'].tolist()
            # Check whether the edge represents a shortcut in that sequence.
            shortcut = is_shortcut(seq_of_stations, edge[0], edge[1])
            # If it is a shortcut, we add it to the list and break the inner loop.
            if shortcut:
                # Add to list and break the loop.
                shortcut_edges.append((fahrt, edge))
                break

    # Extract only edges
    shortcut_edges_clean = [i[1] for i in shortcut_edges]

    # Get the final list of non-shortcut edges.
    final_edges = [e for e in unique_undirected_edges if e not in shortcut_edges_clean]

    # Load the data ("Line (Operation Points)")
    linien = pd.read_csv('raw/linie-mit-betriebspunkten.csv', sep = ";")

    # Reduce to relevant columns
    linien = linien[["Name Haltestelle","Linie","KM","Linien Text","BPUIC"]]

    # Join the rows of nodelist based on BPUIC.
    linien = pd.merge(linien, nodes[["BPUIC","STATION_NAME"]], on = 'BPUIC', how = 'left')

    # Drop all rows that are not stations.
    linien = linien.dropna(subset = ["STATION_NAME"])

    # Sort for each group
    linien_sorted = linien.groupby('Linie', group_keys=False).apply(sort_data2, include_groups=True)

    # Create a new column that for each row contains the next stop within the group.
    linien_sorted["NEXT_STATION"] = linien_sorted.groupby("Linie")["STATION_NAME"].shift(-1)

    # Do the same for KM.
    linien_sorted["NEXT_STATION_KM"] = linien_sorted.groupby("Linie")["KM"].shift(-1)

    # Compute distance.
    linien_sorted["DISTANCE"] = linien_sorted["NEXT_STATION_KM"] - linien_sorted["KM"]

    # Drop all rows where 'NEXT_STATION' is missing
    linien_sorted = linien_sorted.dropna(subset = ["NEXT_STATION"])

    # Now let's extract the edges
    linien_edges = list(zip(linien_sorted['STATION_NAME'], linien_sorted['NEXT_STATION']))

    # Make sure the tuples are arranged in the same way as above (and unique).
    linien_edges = list(set((min(e[0], e[1]), max(e[0], e[1])) for e in linien_edges))

    # Manually remove edges.
    final_edges.remove(('Bern', 'Zofingen'))
    final_edges.remove(('Bern Wankdorf', 'Zürich HB'))
    final_edges.remove(('Morges', 'Yverdon-les-Bains'))
    final_edges.remove(('Aarau', 'Sissach'))
    final_edges.remove(('Bergün/Bravuogn', 'Pontresina'))
    final_edges.remove(('Interlaken West', 'Spiez'))
    final_edges.remove(('Biel/Bienne', 'Grenchen Nord'))
    final_edges.remove(('Chambrelien', 'Neuchâtel'))
    final_edges.remove(('Concise', 'Yverdon-les-Bains'))
    final_edges.remove(('Etoy', 'Rolle'))
    final_edges.remove(('Klosters Platz', 'Susch')) # Avoid several edges representing the Vereina tunnel

    # Manually add edges.
    final_edges.append(('Biasca', 'Erstfeld')) # New Gotthard tunnel
    final_edges.append(('Bern Wankdorf', 'Rothrist')) # Bahn-2000
    final_edges.append(('Chambrelien', 'Corcelles-Peseux')) # Connector that was missing
    final_edges.append(('Concise', 'Grandson')) # Connector that was missing
    final_edges.append(('Immensee', 'Rotkreuz')) # Connector that was missing
    final_edges.append(('Olten', 'Rothrist')) # Connector not going through Aarburg-Oftringen
    final_edges.append(('Rothrist', 'Solothurn')) # Bahn-2000
    final_edges.append(('Aarau', 'Däniken SO')) # Eppenberg tunnel
    final_edges.append(('Liestal', 'Muttenz')) # Adler tunnel
    final_edges.append(('Thalwil', 'Zürich HB')) # Zimmerberg tunnel
    final_edges.append(('Zürich Altstetten', 'Zürich HB')) # Separate infrastructure connecting the two stations

    # New column with coordinates in the same column.
    nodes['coord'] = list(zip(nodes.LATITUDE, nodes.LONGITUDE))

    # Compute direct distances between node pairs.
    final_edges = [(e[0], e[1], compute_distance(e[0], e[1])) for e in final_edges]

    # List of edges including distances.
    linien_edges = list(zip(linien_sorted['STATION_NAME'], linien_sorted['NEXT_STATION'], linien_sorted['DISTANCE']))

    # Make sure the tuples are arranged in the same way as above (and unique).
    linien_edges = list(set((min(e[0], e[1]), max(e[0], e[1]), e[2]) for e in linien_edges))

    # Convert to a dict.
    linien_edges_dict = {(e[0], e[1]): e[2] for e in linien_edges}

    # Add exact distance for edges that exist in dict with exact distance.
    final_edges = [(n1, n2, dist, linien_edges_dict.get((n1, n2), np.nan)) for n1, n2, dist in final_edges]
    
    # Create a node dict with BPUIC as values
    node_dict = dict(zip(nodes.STATION_NAME, nodes.BPUIC))

    # Transform edge dict to nested list and replace all station names with their BPUIC.
    # Also, round the distances to 4 decimal points.
    edges = [[node_dict[e[0]], node_dict[e[1]], round(e[2], 4), round(e[3], 4)] for e in final_edges]

    # Create a dataframe
    edges = pd.DataFrame(edges, columns = ['BPUIC1','BPUIC2','DISTANCE_GEODESIC','DISTANCE_EXACT'])

    # Correct mistake in edge between Baar Lindenpark and Zug.
    edges.loc[(edges['BPUIC1'] == 8515993) & (edges['BPUIC2'] == 8502204), 'DISTANCE_EXACT'] = 1.0593

    # Export edge list
    edges.to_csv("edgelist_SoSta.csv", sep = ';', encoding = 'utf-8', index = False)

# -------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
