# SPDX-License-Identifier: GPL-3.0-only
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import json
import os
import sys

SKILL = Path(__file__).resolve().parents[2]
UI = SKILL / "assets/ui"
TZ = timezone(timedelta(hours=8), "Asia/Shanghai")


class InputError(ValueError):
    def __init__(self, field, message):
        self.field = field
        super().__init__(f"{field}: {message}")


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise InputError(str(path), "文件不存在")
    if path.stat().st_size > 16 * 1024 * 1024:
        raise InputError(str(path), "JSON 超过 16 MiB")
    try:
        value = json.loads(path.read_text("utf-8-sig"), parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
    except (ValueError, UnicodeError) as exc:
        raise InputError(str(path), "无效 JSON") from exc
    if not isinstance(value, dict):
        raise InputError(str(path), "JSON 顶层必须是对象")
    return value


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), "utf-8")
    os.replace(temporary, path)


def timestamp(value, field):
    try:
        if isinstance(value, bool):
            raise ValueError()
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, TZ).timestamp()
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            raise ValueError()
        return dt.timestamp()
    except (ValueError, TypeError, OverflowError, OSError) as exc:
        raise InputError(field, "需要带时区的 ISO 时间或有效 Unix 秒数") from exc


def local_time(value):
    return datetime.fromtimestamp(value, TZ).strftime("%Y-%m-%d %H:%M:%S")


def progress(step, **details):
    print(json.dumps({"step": step, **details}, ensure_ascii=False), file=sys.stderr, flush=True)
