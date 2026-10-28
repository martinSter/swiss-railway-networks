#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Name: space_of_stops.py
Description: This script creates the space-of-stops network representation.
Author: Martin Sterchi
Date: 2026-10-28
"""

import pandas as pd
from preprocessing import load_data, make_nodelist

# Main function to run the procedure
def main():

    # Load the train stops and the stations
    df, ds = load_data()

    # Group the stops by trip. Within a trip, the raw data is already in order of ABFAHRTSZEIT,
    # so a stable sort by FAHRT_BEZEICHNER keeps the stops in the right sequence.
    df = df.sort_values('FAHRT_BEZEICHNER', kind = 'stable')

    # Next stop within the same trip and the travel time to it (minutes)
    grouped = df.groupby('FAHRT_BEZEICHNER')
    df['NEXT_STATION'] = grouped['STATION_NAME'].shift(-1)
    df['DURATION'] = (grouped['ANKUNFTSZEIT'].shift(-1) - df['ABFAHRTSZEIT']).dt.total_seconds() / 60

    # The last stop of a trip has no next stop
    df = df.dropna(subset = ['NEXT_STATION'])

    # Number of connections and average travel time per (directed) edge.
    # sort=False keeps the edges in order of first appearance.
    edges = (df.groupby(['STATION_NAME', 'NEXT_STATION'], sort = False)['DURATION']
               .agg(NUM_CONNECTIONS = 'size', AVG_DURATION = 'mean')
               .reset_index())
    edges['AVG_DURATION'] = edges['AVG_DURATION'].map(lambda x: round(x, 2))

    # Remove the two edges between Basel Bad Bf and Schaffhausen (there are German stations in-between)
    basel_schaffhausen = {('Basel Bad Bf', 'Schaffhausen'), ('Schaffhausen', 'Basel Bad Bf')}
    edges = edges[[e not in basel_schaffhausen for e in zip(edges['STATION_NAME'], edges['NEXT_STATION'])]]

    # Create and export the node list for the stations that appear in edgelist
    nodes = make_nodelist(ds, set(edges['STATION_NAME']) | set(edges['NEXT_STATION']))

    # Create a node dict with BPUIC as values
    node_dict = dict(zip(nodes.STATION_NAME, nodes.BPUIC))

    # Replace all station names with their BPUIC
    edges['BPUIC1'] = edges['STATION_NAME'].map(node_dict)
    edges['BPUIC2'] = edges['NEXT_STATION'].map(node_dict)
    edges = edges[['BPUIC1','BPUIC2','NUM_CONNECTIONS','AVG_DURATION']]

    # Report the size of the network
    print(f"Space-of-stops: {len(nodes)} nodes ({len(set(edges['BPUIC1']) | set(edges['BPUIC2']))} with at least one edge), {len(edges)} edges")

    # Export edge list
    edges.to_csv("clean/edgelist_SoSto.csv", sep = ';', encoding = 'utf-8', index = False)

# -------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
