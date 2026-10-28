#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Name: temporal_edges.py
Description: This script creates the temporal representation.
Author: Martin Sterchi
Date: 2026-10-28
"""

import pandas as pd
import numpy as np
from preprocessing import load_data, make_nodelist

# Main function to run the procedure
def main():
    
    # Load the train stops and the stations
    df, ds = load_data()

    # -----------------------------------------------------------------------
    # Here comes the part specific to the temporal representation.

    # Position of each stop within its trip (keeps the row order of the raw data).
    df['POS'] = df.groupby('FAHRT_BEZEICHNER').cumcount()
    stops = df[['FAHRT_BEZEICHNER', 'POS', 'STATION_NAME', 'ABFAHRTSZEIT', 'ANKUNFTSZEIT']]

    # All pairs (i, j) of stops with i before j within the same trip.
    pairs = stops.merge(stops, on = 'FAHRT_BEZEICHNER', suffixes = ('_1', '_2'))
    pairs = pairs[pairs['POS_1'] < pairs['POS_2']]
    # Same order as a nested loop over the trips (sorted).
    pairs = pairs.sort_values(['FAHRT_BEZEICHNER', 'POS_1', 'POS_2'])

    # Time of departure in minutes since the day began.
    pairs['START'] = (pairs['ABFAHRTSZEIT_1'] - pd.to_datetime("2025-03-05 00:00:00")).dt.total_seconds() / 60
    # Duration in minutes.
    pairs['DURATION'] = (pairs['ANKUNFTSZEIT_2'] - pairs['ABFAHRTSZEIT_1']).dt.total_seconds() / 60

    # Create and export the node list for the stations that appear in edgelist
    nodes = make_nodelist(ds, set(pairs['STATION_NAME_1']) | set(pairs['STATION_NAME_2']))

    # Create a node dict with BPUIC as values
    node_dict = dict(zip(nodes.STATION_NAME, nodes.BPUIC))
    
    # Replace all station names with their BPUIC
    edges = pd.DataFrame({'BPUIC1': pairs['STATION_NAME_1'].map(node_dict),
                          'BPUIC2': pairs['STATION_NAME_2'].map(node_dict),
                          'START': pairs['START'].astype(int),
                          'DURATION': pairs['DURATION'].astype(int)})

    # Report the size of the network
    print(f"Temporal: {len(nodes)} nodes ({len(set(edges['BPUIC1']) | set(edges['BPUIC2']))} with at least one edge), {len(edges)} edges")

    # Export edge list
    edges.to_csv("clean/edgelist_temporal.csv", sep = ';', encoding = 'utf-8', index = False)

# -------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
