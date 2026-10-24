# SPDX-License-Identifier: GPL-3.0-only
"""Convenience entry point for the bundled production CLI."""
from pathlib import Path
import runpy
import sys
scripts = Path(__file__).resolve().parent / "skills/weekly-production/scripts"
sys.path.insert(0, str(scripts))
if __name__ == "__main__":
    runpy.run_path(str(scripts / "weekly.py"), run_name="__main__")
