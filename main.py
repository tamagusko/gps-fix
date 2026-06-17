"""Run the GPS map-matching pipeline and open the result maps.

Usage from the project root:

    python main.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from gps_fix import main as run_pipeline  # noqa: E402  (after sys.path setup)

MAPS = ("raw_route.png", "fixed_route.png")


def open_file(path: Path) -> None:
    """Open a file with the operating system's default application."""
    if not path.exists():
        return
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    elif sys.platform.startswith("win"):
        subprocess.run(["cmd", "/c", "start", "", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def main() -> int:
    """Run the pipeline, then open the raw and corrected maps."""
    code = run_pipeline()
    if code == 0:
        for name in MAPS:
            open_file(ROOT / "outputs" / name)
    return code


if __name__ == "__main__":
    sys.exit(main())
