"""Run the GPS map-matching pipeline end to end with no arguments."""

import sys
from pathlib import Path

from gps_fix.graph import build_graph
from gps_fix.io_csv import load_gps, save_gps
from gps_fix.matching import match_trace
from gps_fix.plotting import plot_route
from gps_fix.report import write_report

ROOT = Path(__file__).resolve().parents[2]
INPUT_CSV = ROOT / "data" / "gps.csv"
OUTPUT_DIR = ROOT / "outputs"


def main() -> int:
    """Load, map-match, and export the corrected trace, maps, and report.

    Returns:
        Process exit code: ``0`` on success, ``1`` on a handled failure.
    """
    try:
        df_raw = load_gps(INPUT_CSV)
        print(f"Loaded {len(df_raw)} GPS points from {INPUT_CSV}")

        graph = build_graph(df_raw)
        print(f"Built road graph: {graph.number_of_edges()} edges")

        result = match_trace(graph, df_raw)
        save_gps(result.df, OUTPUT_DIR / "gps_fixed.csv")
        plot_route(
            graph,
            df_raw["lon"],
            df_raw["lat"],
            "Raw GPS route",
            OUTPUT_DIR / "raw_route.png",
            "red",
        )
        plot_route(
            graph,
            result.route_lon,
            result.route_lat,
            "Corrected route",
            OUTPUT_DIR / "fixed_route.png",
            "green",
            markers=(result.df["lon"], result.df["lat"]),
        )
        headline = write_report(result, OUTPUT_DIR / "report.md")
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(headline)
    print(f"Outputs written to {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
