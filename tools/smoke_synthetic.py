# SPDX-License-Identifier: GPL-3.0-only
"""Create fictional packs outside the repository and exercise the actual installed CLI."""
from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from production_fixtures import packs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", required=True, type=Path)
    parser.add_argument("--directory", required=True, type=Path)
    args = parser.parse_args()
    if args.directory.exists():
        raise FileExistsError("Use a fresh synthetic test directory")
    episode, character = packs(args.directory, count=1)
    result = subprocess.run([sys.executable, str(args.cli.resolve()), "build", "--episode", str(episode), "--character", str(character), "--output", str(args.directory / "synthetic.mp4"), "--json"], capture_output=True, text=True, encoding="utf-8")
    (args.directory / "build-stdout.json").write_text(result.stdout, "utf-8")
    (args.directory / "build-stderr.log").write_text(result.stderr, "utf-8")
    if result.returncode:
        print(result.stdout)
        print(result.stderr[-2000:], file=sys.stderr)
        raise SystemExit(result.returncode)
    print(result.stdout)
