#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script Name: space_of_stations.py
Description: This script creates the space-of-stations network representation.
Author: Martin Sterchi
Date: 2026-10-28
"""

import pandas as pd
import numpy as np
import geopy.distance
from collections import Counter, defaultdict
from preprocessing import load_data, make_nodelist

# Function to check whether elements a and b are NOT adjacent in lst.
def is_shortcut(lst, a, b):
    return not any((x, y) == (a, b) or (x, y) == (b, a) for x, y in zip(lst, lst[1:]))

# Main function to run the procedure
def main():

    # -----------------------------------------------------------------------
    # We first repeat the procedure to get the space-of-stops representation.

    # Load the train stops and the stations
    df, ds = load_data()

    # Group the stops by trip. Within a trip, the raw data is already in order of ABFAHRTSZEIT,
    # so a stable sort by FAHRT_BEZEICHNER keeps the stops in the right sequence.
    df = df.sort_values('FAHRT_BEZEICHNER', kind = 'stable')

    # Next stop within the same trip (the last stop of a trip has none)
    df['NEXT_STATION'] = df.groupby('FAHRT_BEZEICHNER')['STATION_NAME'].shift(-1)
    stops = df.dropna(subset = ['NEXT_STATION'])

    # Unique (directed) edges in order of first appearance
    edges = stops[['STATION_NAME', 'NEXT_STATION']].drop_duplicates()

    # Remove the two edges between Basel Bad Bf and Schaffhausen (there are German stations in-between)
    basel_schaffhausen = {('Basel Bad Bf', 'Schaffhausen'), ('Schaffhausen', 'Basel Bad Bf')}
    edges = edges[[e not in basel_schaffhausen for e in zip(edges['STATION_NAME'], edges['NEXT_STATION'])]]

    # Create and export the node list for the stations that appear in edgelist
    # (including Domodossola, which is connected manually below).
    nodes = make_nodelist(ds, set(edges['STATION_NAME']) | set(edges['NEXT_STATION']))

    # -----------------------------------------------------------------------
    # Here comes the part specific to the space-of-stations representation.

    # Get a sorted list of unique undirected edges (sorted so that the output is reproducible).
    unique_undirected_edges = sorted(set((min(e1, e2), max(e1, e2)) for e1, e2 in zip(edges["STATION_NAME"], edges["NEXT_STATION"])))

    # In order to make the procedure further below more efficient, we extract here all unique trips ("Fahrten").
    # If the same key (sequence of stops) reappears, the value will be overwritten.
    # But that behavior is desired: we only want to keep one FAHRT_BEZEICHNER per key.
    fahrten = {}
    for fahrt, seq in df.groupby('FAHRT_BEZEICHNER')['STATION_NAME'].agg(tuple).items():
        fahrten[seq] = fahrt

    # Sequence of stations for each of these 'Fahrten'.
    sequences = {fahrt: list(seq) for seq, fahrt in fahrten.items()}

    # Dict with stations as keys and the set of 'Fahrten' in which they appear as values.
    result_dict = defaultdict(set)
    for fahrt, seq in sequences.items():
        for station in seq:
            result_dict[station].add(fahrt)

    # An edge is a shortcut if, in any 'Fahrt' in which both of its stations appear, they are not adjacent.
    shortcut_edges = {edge for edge in unique_undirected_edges
                      if any(is_shortcut(sequences[fahrt], edge[0], edge[1])
                             for fahrt in result_dict[edge[0]] & result_dict[edge[1]])}

    # Report the shortcut edges
    print(f"{len(shortcut_edges)} of {len(unique_undirected_edges)} undirected edges are shortcuts:")
    for edge in sorted(shortcut_edges):
        print(f"  {edge[0]} - {edge[1]}")

    # Get the final list of non-shortcut edges.
    final_edges = [e for e in unique_undirected_edges if e not in shortcut_edges]

    # Load the data ("Line (Operation Points)")
    linien = pd.read_csv('raw/linie-mit-betriebspunkten.csv', sep = ";")

    # Reduce to relevant columns
    linien = linien[["Name Haltestelle","Linie","KM","Linien Text","BPUIC"]]

    # Join the rows of nodelist based on BPUIC.
    linien = pd.merge(linien, nodes[["BPUIC","STATION_NAME"]], on = 'BPUIC', how = 'left')

    # Drop all rows that are not stations.
    linien = linien.dropna(subset = ["STATION_NAME"])

    # Sort by KM within each line
    linien_sorted = linien.sort_values(['Linie', 'KM'], kind = 'stable')

    # Create a new column that for each row contains the next stop within the group.
    linien_sorted["NEXT_STATION"] = linien_sorted.groupby("Linie")["STATION_NAME"].shift(-1)

    # Do the same for KM.
    linien_sorted["NEXT_STATION_KM"] = linien_sorted.groupby("Linie")["KM"].shift(-1)

    # Compute distance.
    linien_sorted["DISTANCE"] = linien_sorted["NEXT_STATION_KM"] - linien_sorted["KM"]

    # Drop all rows where 'NEXT_STATION' is missing
    linien_sorted = linien_sorted.dropna(subset = ["NEXT_STATION"])

    # Manually remove edges.
    final_edges.remove(('Bern', 'Zofingen'))
    final_edges.remove(('Bern Wankdorf', 'Zürich HB'))
    final_edges.remove(('Morges', 'Yverdon-les-Bains'))
    final_edges.remove(('Aarau', 'Sissach'))
    final_edges.remove(('Bergün/Bravuogn', 'Pontresina'))
    #final_edges.remove(('Interlaken West', 'Spiez')) # 27.10.2026: All stations between Spiez and Interlaken West have been shutdown. Thus, this edge should exist.
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
    final_edges.append(('Grenchen Nord', 'Lengnau BE')) # 27.10.2026: Clearly adjacent, but no train from Grenchen Nord stops in Lengnau which is why the edge is not detected.
    final_edges.append(('Domodossola', 'Masera')) # 28.10.2026: Domodossola is added manually (not in the "Actual Data"), Masera and Preglia are linked through it.
    final_edges.append(('Domodossola', 'Preglia'))

    # Coordinates of each station.
    coords = dict(zip(nodes.STATION_NAME, zip(nodes.LATITUDE, nodes.LONGITUDE)))

    # Compute direct distances between node pairs.
    final_edges = [(e[0], e[1], geopy.distance.geodesic(coords[e[0]], coords[e[1]]).km) for e in final_edges]

    # Dict with exact distances, keys arranged in the same way as above.
    # Some station pairs appear on several lines with slightly different distances: we keep the smallest one.
    linien_edges_dict = {}
    for n1, n2, dist in zip(linien_sorted['STATION_NAME'], linien_sorted['NEXT_STATION'], linien_sorted['DISTANCE']):
        key = (min(n1, n2), max(n1, n2))
        linien_edges_dict[key] = min(dist, linien_edges_dict.get(key, dist))

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

    # Report the size of the network
    print(f"Space-of-stations: {len(nodes)} nodes ({len(set(edges['BPUIC1']) | set(edges['BPUIC2']))} with at least one edge), {len(edges)} edges")

    # Export edge list
    edges.to_csv("clean/edgelist_SoSta.csv", sep = ';', encoding = 'utf-8', index = False)

# -------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
