# gps-fix

Map-match noisy GPS coordinates to the OpenStreetMap road and path network.

A Hidden Markov Model (Viterbi) matches the trace to OSM edges (roads,
cycleways, and footways), balancing each point's distance to an edge against
the agreement between consecutive-point spacing and on-graph travel distance.
Because the points are sampled at 1 Hz (metres apart), this keeps a point on
the through-road at an intersection instead of letting it jump onto a crossing
road. The matched edges are stitched into one continuous on-graph route. The
trace order and one-row-per-point mapping are preserved.

## What it does

Given `data/gps.csv` (raw GPS points), it produces in `outputs/`:

- `raw_route.png` — the raw GPS route over the OSM network.
- `fixed_route.png` — the corrected route, same map extent.
- `gps_fixed.csv` — the input schema with corrected `lat`/`lon`.
- `report.md` — how many coordinates were corrected.

## Install

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

Runs the whole pipeline on `data/gps.csv`, writes `outputs/`, and opens the
raw and corrected maps. To run without opening the maps:

```bash
PYTHONPATH=src python -m gps_fix
```

## Input

CSV with at least `lat` and `lon` columns (WGS84). Extra columns (e.g.
timestamps) are preserved in the output.

## How it works

1. Load and validate the CSV (`io_csv.py`).
2. Build a routable OSM graph for the trace bounding box plus a buffer and
   prune dead-end stubs that would otherwise capture points near junctions
   (`graph.py`, `network_type="all"`).
3. Collapse stationary clusters (stops/jitter) to one representative, project
   the graph to a metric CRS, score candidate edges per point, and run a
   Viterbi HMM to choose a continuous edge sequence; snap each point to its
   chosen edge and smooth any residual out-and-back spikes (`matching.py`).
4. Save the corrected CSV, two comparable PNGs, and the report
   (`plotting.py`, `report.py`).

The HMM follows the Newson & Krumm (2009) formulation, with preprocessing
ideas (stationary-point removal) inspired by NREL's
[mappymatch](https://github.com/NREL/mappymatch) and
[leuvenmapmatching](https://github.com/wannesm/LeuvenMapMatching).

## License

MIT — see [LICENSE](LICENSE).
