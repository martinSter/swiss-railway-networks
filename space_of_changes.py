#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Name: space_of_changes.py
Description: This script creates the space-of-changes network representation.
Author: Martin Sterchi
Date: 2026-10-28
"""

import pandas as pd
from preprocessing import load_data, make_nodelist

# Main function to run the procedure
def main():

    # Load the train stops and the stations
    df, ds = load_data()

    # -----------------------------------------------------------------------
    # Here comes the part specific to the space-of-changes representation.

    # Position of each stop within its trip (keeps the row order of the raw data).
    # We assume that rows are ordered in the raw data. Please check this if you 
    # adapt this code to data from other day.
    df['POS'] = df.groupby('FAHRT_BEZEICHNER').cumcount()
    stops = df[['FAHRT_BEZEICHNER', 'POS', 'STATION_NAME', 'ABFAHRTSZEIT', 'ANKUNFTSZEIT']]

    # All pairs (i, j) of stops with i before j within the same trip.
    # This is much faster than the loop I had previously.
    pairs = stops.merge(stops, on = 'FAHRT_BEZEICHNER', suffixes = ('_1', '_2'))
    pairs = pairs[pairs['POS_1'] < pairs['POS_2']]
    # Same order as a nested loop over the trips (sorted), so edges appear in a stable order.
    # This is mostly for reproducibility (so that checksums come back the same).
    pairs = pairs.sort_values(['FAHRT_BEZEICHNER', 'POS_1', 'POS_2'])

    # Travel time (minutes)
    pairs['DURATION'] = (pairs['ANKUNFTSZEIT_2'] - pairs['ABFAHRTSZEIT_1']).dt.total_seconds() / 60

    # Number of connections and average travel time per (origin, destination).
    # sort=False keeps the edges in order of first appearance.
    edges = (pairs.groupby(['STATION_NAME_1', 'STATION_NAME_2'], sort = False)['DURATION']
                  .agg(NUM_CONNECTIONS = 'size', AVG_DURATION = 'mean')
                  .reset_index())
    edges['AVG_DURATION'] = edges['AVG_DURATION'].map(lambda x: round(x, 2))

    # Remove the two self-loops ("Les Planches (Aigle)" and "Monthey-En Place")
    edges = edges[edges['STATION_NAME_1'] != edges['STATION_NAME_2']]

    # Create and export the node list for the stations that appear in edgelist
    nodes = make_nodelist(ds, set(edges['STATION_NAME_1']) | set(edges['STATION_NAME_2']))

    # Create a node dict with BPUIC as values
    node_dict = dict(zip(nodes.STATION_NAME, nodes.BPUIC))

    # Replace all station names with their BPUIC
    edges['BPUIC1'] = edges['STATION_NAME_1'].map(node_dict)
    edges['BPUIC2'] = edges['STATION_NAME_2'].map(node_dict)
    edges = edges[['BPUIC1','BPUIC2','NUM_CONNECTIONS','AVG_DURATION']]

    # Report the size of the network
    print(f"Space-of-changes: {len(nodes)} nodes ({len(set(edges['BPUIC1']) | set(edges['BPUIC2']))} with at least one edge), {len(edges)} edges")

    # Export edge list
    edges.to_csv("clean/edgelist_SoCha.csv", sep = ';', encoding = 'utf-8', index = False)

# -------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
