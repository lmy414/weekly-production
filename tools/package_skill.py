# SPDX-License-Identifier: GPL-3.0-only
"""Package or install only the production Skill's explicitly allowed public files."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/weekly-production"


def public_files():
    required = {"SKILL.md", "LICENSE", "agents/openai.yaml", "references/input.md", "references/cli.md",
                "scripts/weekly.py", "scripts/capture.mjs", "scripts/requirements.txt", "scripts/requirements-analysis.txt",
                "scripts/package.json", "scripts/package-lock.json"}
    allowed = set(required)
    allowed.update(str(p.relative_to(SKILL)).replace("\\", "/") for p in (SKILL / "scripts/weekly_runtime").glob("*.py"))
    ui_names = {"index.html", "studio.js", "studio.css", "program.js", "program.css", "editorial.js", "editorial.css", "motion.js", "motion.css"}
    allowed.update("assets/ui/" + name for name in ui_names)
    for path in (SKILL / "assets/ui/fonts").rglob("*"):
        if path.is_file():
            if path.suffix.lower() not in {".woff2", ".ttf", ".otf", ".txt", ".json", ".md"}:
                raise ValueError("Unexpected font asset: " + str(path))
            allowed.add(str(path.relative_to(SKILL)).replace("\\", "/"))
    for name in allowed:
        path = SKILL / name
        if not path.is_file() or path.is_symlink():
            raise ValueError("Missing or linked package file: " + name)
        if any(part in {".private", "episodes", "media", "state", "node_modules", "__pycache__"} for part in Path(name).parts):
            raise ValueError("Private directory cannot be packaged")
    return sorted(allowed)


def package(destination):
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = public_files()
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(SKILL / name, "weekly-production/" + name)
    with zipfile.ZipFile(destination) as archive:
        if set(archive.namelist()) != {"weekly-production/" + name for name in files} or archive.testzip():
            raise ValueError("Package manifest or CRC check failed")
    return {"path": str(destination), "files": len(files), "bytes": destination.stat().st_size,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}


def install(destination):
    destination = Path(destination).expanduser().resolve()
    if destination.exists():
        raise FileExistsError("Use a fresh destination; existing skills are never overwritten: " + str(destination))
    for name in public_files():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SKILL / name, target)
    return {"installed": str(destination), "files": len(public_files())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path)
    parser.add_argument("--install", type=Path)
    args = parser.parse_args()
    result = {}
    if args.zip:
        result["package"] = package(args.zip)
    if args.install:
        result["install"] = install(args.install)
    if not result:
        result["files"] = public_files()
    print(json.dumps(result, ensure_ascii=False))
