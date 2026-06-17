"""Render raw and corrected routes over the OSM graph as PNGs."""

from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox


def plot_route(
    graph: nx.MultiDiGraph,
    lon: Sequence[float],
    lat: Sequence[float],
    title: str,
    path: Path,
    color: str,
    markers: tuple[Sequence[float], Sequence[float]] | None = None,
) -> None:
    """Plot a route over the road graph and save it as a PNG.

    All maps share the same graph, so they render at an identical extent and
    are directly comparable.

    Args:
        graph: OSM graph in WGS84 (provides the basemap and extent).
        lon: Route longitudes, in order.
        lat: Route latitudes, in order.
        title: Figure title.
        path: Destination PNG path; parent directories are created.
        color: Matplotlib colour for the route line.
        markers: Optional ``(lon, lat)`` of corrected points to overlay.
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
    ax.plot(lon, lat, color=color, linewidth=1.6, alpha=0.9, zorder=3)
    if markers is not None:
        ax.scatter(
            markers[0], markers[1], s=5, color=color, alpha=0.6, zorder=4
        )
    ax.set_title(title, color="black")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
