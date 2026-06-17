"""Write a short Markdown report summarising the correction."""

from pathlib import Path

from gps_fix.matching import MatchResult


def write_report(result: MatchResult, path: Path) -> str:
    """Write a Markdown summary of how many points were corrected.

    Args:
        result: The map-matching outcome.
        path: Destination Markdown path; parent directories are created.

    Returns:
        The headline sentence (also the first line of the file).
    """
    total = len(result.df)
    fixed = result.fixed_count
    pct = 100.0 * fixed / total if total else 0.0
    max_shift = float(result.moved_m.max()) if total else 0.0
    mean_shift = float(result.moved_m.mean()) if total else 0.0

    headline = f"Corrected {fixed} of {total} coordinates ({pct:.1f}%)."
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# GPS Map-Matching Report\n\n"
        f"{headline}\n\n"
        f"- Total points: {total}\n"
        f"- Corrected points: {fixed}\n"
        f"- Unchanged points: {total - fixed}\n"
        f"- Fix tolerance: {result.tolerance_m:.1f} m\n"
        f"- Mean displacement: {mean_shift:.2f} m\n"
        f"- Max displacement: {max_shift:.2f} m\n\n"
        f"A coordinate counts as corrected when it moved more than the fix "
        f"tolerance after being snapped to the nearest OSM road edge.\n"
    )
    return headline
