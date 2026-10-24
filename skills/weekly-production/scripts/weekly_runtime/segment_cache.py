# SPDX-License-Identifier: GPL-3.0-only
"""Reuse work segments only when their source, broadcast plate and output match."""
import hashlib
import json

from pathlib import Path
from .program import EXPORT_PROFILE

WORK_RECIPE = "work-window-and-continuous-podium-pcm-v1"


def file_hash(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def work_fingerprint(scene, media, output):
    entry = media[scene["row"]["bvid"]]
    value = {"recipe": WORK_RECIPE, "profile": EXPORT_PROFILE,
             "template": scene["template"], "frames": scene["frames"],
             "clip_start": scene["clip_start"], "selection": scene["selection_method"],
             "data_seconds": scene.get("data_seconds"),
             "source": file_hash(Path(entry["path"])),
             "plate": file_hash(output / "plates" / (scene["id"] + ".png"))}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def matches(entry, fingerprint, target):
    return bool(entry and target.is_file() and entry.get("fingerprint") == fingerprint
                and entry.get("output_sha256") == file_hash(target))


def record(fingerprint, target):
    return {"fingerprint": fingerprint, "output_sha256": file_hash(target)}
