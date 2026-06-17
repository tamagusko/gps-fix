"""Build a routable OSM road graph covering the GPS trace."""

import networkx as nx
import osmnx as ox
import pandas as pd

BUFFER_DEG = 0.002  # ~200 m padding around the trace bounding box


def build_graph(df: pd.DataFrame, network_type: str = "all") -> nx.MultiDiGraph:
    """Download a road graph spanning the trace bounding box plus a buffer.

    Args:
        df: GPS points with ``lat`` and ``lon`` columns.
        network_type: OSMnx network filter (e.g. ``"drive"``, ``"walk"``).

    Returns:
        An OSM graph in WGS84, large enough to contain every point.

    Raises:
        ValueError: If no road network is found for the area.
    """
    left = df["lon"].min() - BUFFER_DEG
    right = df["lon"].max() + BUFFER_DEG
    bottom = df["lat"].min() - BUFFER_DEG
    top = df["lat"].max() + BUFFER_DEG

    try:
        graph = ox.graph_from_bbox(
            bbox=(left, bottom, right, top), network_type=network_type
        )
    except Exception as exc:  # network/empty-result errors from OSMnx
        raise ValueError(f"Could not build road graph for the trace: {exc}") from exc

    if graph.number_of_edges() == 0:
        raise ValueError("Road graph has no edges for the trace area.")
    return graph
