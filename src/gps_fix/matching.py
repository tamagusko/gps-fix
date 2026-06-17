"""Map-match GPS points by projecting them onto the nearest road edge."""

from dataclasses import dataclass

import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
from pyproj import Transformer
from shapely.geometry import LineString, Point

TOLERANCE_M = 1.0  # a point counts as "fixed" if it moves more than this


@dataclass(frozen=True)
class MatchResult:
    """Outcome of map-matching a trace.

    Attributes:
        df: Corrected points (input schema with ``lat``/``lon`` snapped).
        moved_m: Per-point displacement from raw to snapped, in metres.
        fixed_count: Number of points moved beyond the tolerance.
        tolerance_m: Displacement threshold used to flag a point as fixed.
    """

    df: pd.DataFrame
    moved_m: np.ndarray
    fixed_count: int
    tolerance_m: float


def _edge_geometry(graph: nx.MultiDiGraph, u: int, v: int, k: int) -> LineString:
    """Return the geometry of edge ``(u, v, k)`` in the graph's CRS."""
    data = graph.edges[u, v, k]
    if "geometry" in data:
        return data["geometry"]
    return LineString(
        [
            (graph.nodes[u]["x"], graph.nodes[u]["y"]),
            (graph.nodes[v]["x"], graph.nodes[v]["y"]),
        ]
    )


def match_trace(
    graph: nx.MultiDiGraph, df: pd.DataFrame, tolerance_m: float = TOLERANCE_M
) -> MatchResult:
    """Snap each GPS point onto the closest road edge.

    The graph is projected to a metric CRS, each point is projected onto the
    geometry of its nearest edge, and the snapped position is converted back to
    WGS84. This keeps drifted points on real streets rather than the noisy raw
    location, while preserving the trace's order and one output row per input.

    Args:
        graph: Routable OSM graph in WGS84.
        df: GPS points with ``lat`` and ``lon`` columns.
        tolerance_m: Minimum displacement (metres) to flag a point as fixed.

    Returns:
        A :class:`MatchResult` with the corrected trace and statistics.
    """
    proj = ox.project_graph(graph)
    crs = proj.graph["crs"]
    to_metric = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    to_wgs84 = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)

    xs, ys = to_metric.transform(df["lon"].to_numpy(), df["lat"].to_numpy())
    edges = ox.distance.nearest_edges(proj, xs, ys)

    snapped_x = np.empty(len(df))
    snapped_y = np.empty(len(df))
    for i, (x, y, edge) in enumerate(zip(xs, ys, edges)):
        geom = _edge_geometry(proj, *edge)
        point = geom.interpolate(geom.project(Point(x, y)))
        snapped_x[i] = point.x
        snapped_y[i] = point.y

    lon, lat = to_wgs84.transform(snapped_x, snapped_y)
    moved_m = np.hypot(snapped_x - xs, snapped_y - ys)

    fixed = df.copy()
    fixed["lat"] = lat
    fixed["lon"] = lon
    return MatchResult(
        df=fixed,
        moved_m=moved_m,
        fixed_count=int((moved_m > tolerance_m).sum()),
        tolerance_m=tolerance_m,
    )
