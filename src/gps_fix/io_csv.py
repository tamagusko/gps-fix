"""Read raw GPS points and write the corrected trace."""

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ("lat", "lon")


def load_gps(path: Path) -> pd.DataFrame:
    """Load a GPS CSV and validate its coordinate columns.

    Args:
        path: Path to the raw GPS CSV. Must contain ``lat`` and ``lon``
            columns of finite WGS84 degrees; extra columns are preserved.

    Returns:
        The points as a DataFrame, in file order.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: If the file is empty or lacks required columns.
    """
    if not path.exists():
        raise FileNotFoundError(f"GPS file not found: {path}")

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"GPS file is empty: {path}")

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"GPS file missing columns {missing}: {path}")

    df = df.dropna(subset=list(REQUIRED_COLUMNS)).reset_index(drop=True)
    if df.empty:
        raise ValueError(f"No valid lat/lon rows in: {path}")
    return df


def save_gps(df: pd.DataFrame, path: Path) -> None:
    """Write the corrected trace, preserving the input schema and order.

    Args:
        df: Corrected points (same columns as the input).
        path: Destination CSV path; parent directories are created.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
