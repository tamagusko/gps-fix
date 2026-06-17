# gps-fix

Map-match noisy GPS coordinates to the OpenStreetMap road and path network.

Each GPS point is projected onto the nearest OSM edge (roads, cycleways, and
footways), so drifted points are pulled back onto real streets instead of the
noisy raw location. The trace order and one-row-per-point mapping are preserved.

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
PYTHONPATH=src python -m gps_fix
```

Runs end to end with no arguments, reading `data/gps.csv` and writing `outputs/`.

## Input

CSV with at least `lat` and `lon` columns (WGS84). Extra columns (e.g.
timestamps) are preserved in the output.

## How it works

1. Load and validate the CSV (`io_csv.py`).
2. Build a routable OSM graph for the trace bounding box plus a buffer
   (`graph.py`, `network_type="all"`).
3. Project the graph to a metric CRS and snap each point onto its nearest edge
   (`matching.py`).
4. Save the corrected CSV, two comparable PNGs, and the report
   (`plotting.py`, `report.py`).
