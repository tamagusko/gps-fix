"""Render raw and corrected routes over the OSM graph as PNGs."""

from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox
import pandas as pd


def plot_route(
    graph: nx.MultiDiGraph,
    df: pd.DataFrame,
    title: str,
    path: Path,
    color: str,
) -> None:
    """Plot a trace over the road graph and save it as a PNG.

    Both the raw and corrected maps share the same graph, so they render at an
    identical extent and are directly comparable.

    Args:
        graph: OSM graph in WGS84 (provides the basemap and extent).
        df: Points with ``lat`` and ``lon`` columns, in route order.
        title: Figure title.
        path: Destination PNG path; parent directories are created.
        color: Matplotlib colour for the route line and markers.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = ox.plot_graph(
        graph,
        show=False,
        close=False,
        node_size=0,
        edge_color="#cccccc",
        edge_linewidth=0.8,
        bgcolor="white",
    )
    ax.plot(
        df["lon"],
        df["lat"],
        color=color,
        linewidth=1.5,
        marker="o",
        markersize=2.5,
        alpha=0.85,
    )
    ax.set_title(title, color="black")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
