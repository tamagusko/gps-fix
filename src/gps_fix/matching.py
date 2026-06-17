"""Map-match a GPS trace with an HMM, keeping the route continuous.

Each point keeps several candidate edges. A Viterbi pass picks the edge
sequence that balances closeness to the raw point (emission) against agreement
between consecutive-point spacing and on-graph travel distance (transition).
Because 1 Hz points are metres apart, this keeps a point on the through-road at
an intersection instead of letting it jump onto the crossing road.
"""

from dataclasses import dataclass

import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
from pyproj import Transformer
from shapely.geometry import Point

SIGMA_M = 8.0  # GPS noise scale for the emission term
MAX_CAND_M = 40.0  # candidate edge search radius
N_CAND = 6  # candidate edges kept per point
BETA_M = 10.0  # transition tolerance between GPS gap and graph distance
SPIKE_M = 6.0  # smooth an isolated point this far off its neighbours' line
DESPIKE_PASSES = 4  # repeat smoothing so multi-point spikes collapse
STATIONARY_M = 3.0  # cluster points within this radius as one stop (no motion)
NO_PATH_PENALTY = -1e3  # log-score when no on-graph route connects candidates
TOLERANCE_M = 1.0  # a point counts as "fixed" if it moves more than this


@dataclass(frozen=True)
class MatchResult:
    """Outcome of map-matching a trace.

    Attributes:
        df: Corrected points (input schema with ``lat``/``lon`` snapped).
        moved_m: Per-point displacement from raw to snapped, in metres.
        fixed_count: Number of points moved beyond the tolerance.
        tolerance_m: Displacement threshold used to flag a point as fixed.
        route_lon: Longitudes of the continuous on-graph route.
        route_lat: Latitudes of the continuous on-graph route.
    """

    df: pd.DataFrame
    moved_m: np.ndarray
    fixed_count: int
    tolerance_m: float
    route_lon: np.ndarray
    route_lat: np.ndarray


def match_trace(
    graph: nx.MultiDiGraph, df: pd.DataFrame, tolerance_m: float = TOLERANCE_M
) -> MatchResult:
    """Map-match the trace and build a continuous corrected route.

    Args:
        graph: Routable OSM graph in WGS84.
        df: GPS points with ``lat`` and ``lon`` columns, in time order.
        tolerance_m: Minimum displacement (metres) to flag a point as fixed.

    Returns:
        A :class:`MatchResult` with the corrected per-point trace, the
        continuous route geometry, and statistics.
    """
    proj = ox.project_graph(graph)
    crs = proj.graph["crs"]
    to_metric = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    to_wgs84 = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)

    xs, ys = to_metric.transform(df["lon"].to_numpy(), df["lat"].to_numpy())
    node_x = nx.get_node_attributes(proj, "x")
    node_y = nx.get_node_attributes(proj, "y")
    edge_geoms = ox.graph_to_gdfs(proj, nodes=False)["geometry"]

    # Collapse stationary clusters (stops/jitter) to one representative point so
    # they match once instead of scattering across nearby edges.
    groups = _stationary_groups(xs, ys)
    gx = np.array([xs[groups == g].mean() for g in range(groups.max() + 1)])
    gy = np.array([ys[groups == g].mean() for g in range(groups.max() + 1)])

    candidates = _candidates(edge_geoms, gx, gy, node_x, node_y)
    chosen = _viterbi(proj, candidates, gx, gy)

    rep_x = np.array([candidates[g][c].point.x for g, c in enumerate(chosen)])
    rep_y = np.array([candidates[g][c].point.y for g, c in enumerate(chosen)])
    _despike(rep_x, rep_y)

    snapped_x = rep_x[groups]  # expand representatives back to every point
    snapped_y = rep_y[groups]
    lon, lat = to_wgs84.transform(snapped_x, snapped_y)
    moved_m = np.hypot(snapped_x - xs, snapped_y - ys)

    fixed = df.copy()
    fixed["lat"] = lat
    fixed["lon"] = lon
    # The representatives are continuity-consistent and densely sampled (1 Hz),
    # so connecting them in order is one continuous trip path.
    route_lon, route_lat = to_wgs84.transform(rep_x, rep_y)
    return MatchResult(
        df=fixed,
        moved_m=moved_m,
        fixed_count=int((moved_m > tolerance_m).sum()),
        tolerance_m=tolerance_m,
        route_lon=np.asarray(route_lon),
        route_lat=np.asarray(route_lat),
    )


def _stationary_groups(xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Group consecutive points that stay within ``STATIONARY_M`` of an anchor.

    Returns an array of group ids (one per point). A new group starts whenever
    a point moves beyond the threshold from the current group's anchor, so
    stops and GPS jitter collapse into a single representative.
    """
    groups = np.zeros(len(xs), dtype=int)
    anchor_x, anchor_y, gid = xs[0], ys[0], 0
    for i in range(1, len(xs)):
        if np.hypot(xs[i] - anchor_x, ys[i] - anchor_y) > STATIONARY_M:
            gid += 1
            anchor_x, anchor_y = xs[i], ys[i]
        groups[i] = gid
    return groups


@dataclass(frozen=True)
class _Candidate:
    """A candidate edge match for one GPS point (projected CRS)."""

    point: Point  # raw point projected onto the edge
    dist: float  # distance from raw point to the edge, metres
    node: int  # edge endpoint used for on-graph routing


def _candidates(edge_geoms, xs, ys, node_x, node_y) -> list[list[_Candidate]]:
    """Find up to ``N_CAND`` nearby edges for each point, nearest first."""
    geoms = edge_geoms.to_numpy()
    index = edge_geoms.index.to_list()
    out: list[list[_Candidate]] = []
    for x, y in zip(xs, ys):
        raw = Point(x, y)
        dists = np.array([g.distance(raw) for g in geoms])
        cands: list[_Candidate] = []
        for idx in np.argsort(dists)[:N_CAND]:
            dist = float(dists[idx])
            if dist > MAX_CAND_M and cands:
                break  # always keep at least the nearest edge
            geom = geoms[idx]
            point = geom.interpolate(geom.project(raw))
            u, v = index[idx][0], index[idx][1]
            du = (node_x[u] - point.x) ** 2 + (node_y[u] - point.y) ** 2
            dv = (node_x[v] - point.x) ** 2 + (node_y[v] - point.y) ** 2
            cands.append(_Candidate(point=point, dist=dist, node=u if du <= dv else v))
        out.append(cands)
    return out


def _viterbi(proj, candidates, xs, ys) -> list[int]:
    """Pick the most likely candidate per point via the Viterbi algorithm."""
    cache: dict[tuple[int, int], float] = {}

    def route_len(a: int, b: int) -> float | None:
        if a == b:
            return 0.0
        if (a, b) not in cache:
            try:
                cache[a, b] = nx.shortest_path_length(proj, a, b, weight="length")
            except nx.NetworkXNoPath:
                cache[a, b] = None
        return cache[a, b]

    n = len(candidates)
    scores = [[-0.5 * (c.dist / SIGMA_M) ** 2 for c in candidates[0]]]
    back: list[list[int]] = [[-1] * len(candidates[0])]
    for i in range(1, n):
        gap = float(np.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1]))
        prev = scores[i - 1]
        row, row_back = [], []
        for cand in candidates[i]:
            emission = -0.5 * (cand.dist / SIGMA_M) ** 2
            best, best_k = float("-inf"), 0
            for k, pcand in enumerate(candidates[i - 1]):
                rl = route_len(pcand.node, cand.node)
                trans = NO_PATH_PENALTY if rl is None else -abs(gap - rl) / BETA_M
                total = prev[k] + trans
                if total > best:
                    best, best_k = total, k
            row.append(best + emission)
            row_back.append(best_k)
        scores.append(row)
        back.append(row_back)

    chosen = [int(np.argmax(scores[-1]))]
    for i in range(n - 1, 0, -1):
        chosen.append(back[i][chosen[-1]])
    chosen.reverse()
    return chosen


def _despike(sx: np.ndarray, sy: np.ndarray) -> None:
    """Pull out-and-back excursions back onto the local trajectory.

    An excursion is a short run of points that leaves the path and returns to
    it: the anchors on either side sit close together while the route through
    the run is much longer. Each interior point is projected onto the chord
    between its anchors. The check runs at several half-widths so excursions
    spanning more than one point collapse, while genuine road curves -- whose
    route length barely exceeds the chord -- are left untouched. Modifies
    ``sx``/``sy`` in place.
    """
    for half_width in (1, 2):
        for _ in range(DESPIKE_PASSES):
            changed = False
            for i in range(half_width, len(sx) - half_width):
                ax, ay = sx[i - half_width], sy[i - half_width]
                bx, by = sx[i + half_width], sy[i + half_width]
                span = np.hypot(bx - ax, by - ay)
                if span < 1e-6:
                    continue
                legs = np.hypot(sx[i] - ax, sy[i] - ay) + np.hypot(bx - sx[i], by - sy[i])
                deviation = abs(
                    (sx[i] - ax) * (by - ay) - (sy[i] - ay) * (bx - ax)
                ) / span
                if deviation > SPIKE_M and legs / span > 1.6:
                    t = ((sx[i] - ax) * (bx - ax) + (sy[i] - ay) * (by - ay)) / span**2
                    t = min(1.0, max(0.0, t))
                    sx[i] = ax + t * (bx - ax)
                    sy[i] = ay + t * (by - ay)
                    changed = True
            if not changed:
                break
