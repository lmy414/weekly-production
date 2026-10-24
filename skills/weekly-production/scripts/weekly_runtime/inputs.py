# SPDX-License-Identifier: GPL-3.0-only
"""Validate the two private input packs without database or network access."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit
import math
import re

from PIL import Image

from .common import InputError, file_hash, read_json, timestamp
from .scoring import calculate, sort_key

ROLES = ("welcome", "watching", "transition", "scope", "score", "thinking", "applause", "surprise", "top3", "top2", "champion", "goodbye", "cover")
METRICS = ("view", "reply", "danmaku", "favorite", "coin", "like", "share")
COPY_FIELDS = {"opening_kicker", "opening_subtitle", "opening_tagline", "opening_note", "statistics_text", "outro_text", "end_text"}


def text(value, field, maximum=500):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise InputError(field, f"需要非空文本，最长 {maximum} 字")
    return value.strip()


def number(value, field, minimum=0, maximum=math.inf):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise InputError(field, f"需要 {minimum} 至 {maximum} 之间的有限数值")
    return value


def integer(value, field, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise InputError(field, f"需要大于等于 {minimum} 的整数")
    return value


def local_file(value, base, field):
    raw = text(value, field, 4096)
    if raw.startswith(("http://", "https://", "file://", "ftp://")):
        raise InputError(field, "只接收本地文件，不下载远程素材")
    path = Path(raw).expanduser()
    path = (path if path.is_absolute() else base / path).resolve()
    if not path.is_file():
        raise InputError(field, f"本地文件不存在：{path}")
    return path


def url(value, field):
    raw = text(value, field, 4096)
    parts = urlsplit(raw)
    if parts.scheme not in ("https", "http") or not parts.hostname or parts.username or parts.password:
        raise InputError(field, "需要无账号凭据的 HTTP(S) 来源链接")
    return raw


def probe(path):
    import av
    try:
        with av.open(str(path)) as media:
            video = next(iter(media.streams.video), None)
            audio = next(iter(media.streams.audio), None)
            if video is not None and video.duration is not None:
                duration = float(video.duration * video.time_base)
            elif audio is not None and audio.duration is not None:
                duration = float(audio.duration * audio.time_base)
            else:
                duration = float(media.duration / av.time_base) if media.duration is not None else 0
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError("无法确定有效时长")
            return {"duration": duration, "video": video is not None, "audio": audio is not None,
                    "width": video.width if video else None, "height": video.height if video else None,
                    "fps": str(video.average_rate) if video else None}
    except Exception as exc:
        raise InputError(str(path), "无法读取有效媒体：" + str(exc)[:180]) from exc


def load_inputs(episode_file, character_file, require_clips=True):
    ep_path, char_path = Path(episode_file).expanduser().resolve(), Path(character_file).expanduser().resolve()
    ep, character = read_json(ep_path), read_json(char_path)
    if set(ep) - {"schema", "id", "title", "period", "metric_basis", "works", "copy", "music", "branding"}:
        raise InputError("episode", "包含未知字段")
    if set(character) - {"schema", "id", "name", "images"}:
        raise InputError("character", "包含未知字段")
    if ep.get("schema") != "weekly-production/episode-v1":
        raise InputError("episode.schema", "需要 weekly-production/episode-v1")
    if character.get("schema") != "weekly-production/character-v1":
        raise InputError("character.schema", "需要 weekly-production/character-v1")
    issue = text(ep.get("id"), "episode.id", 80)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", issue):
        raise InputError("episode.id", "只允许小写字母、数字与连接号")
    title = text(ep.get("title"), "episode.title", 160)
    period = ep.get("period")
    if not isinstance(period, dict) or period.get("timezone", "Asia/Shanghai") != "Asia/Shanghai":
        raise InputError("episode.period", "需要 begin、end，timezone 为 Asia/Shanghai")
    begin, end = (timestamp(period.get(k), "episode.period." + k) for k in ("begin", "end"))
    if end <= begin:
        raise InputError("episode.period", "结束时间必须晚于开始时间")
    basis = ep.get("metric_basis")
    if basis not in ("cumulative", "weekly_delta"):
        raise InputError("episode.metric_basis", "需要 cumulative 或 weekly_delta")
    for key in ("id", "name"):
        text(character.get(key), "character." + key, 100)
    images = character.get("images")
    if not isinstance(images, dict) or "default" not in images or set(images) - set(ROLES) - {"default"}:
        raise InputError("character.images", "需要 default 和已定义的用途映射")
    assets, hashes, checked_images = {}, {}, {}
    for role in ("default", *ROLES):
        path = local_file(images.get(role, images["default"]), char_path.parent, "character.images." + role)
        if path not in checked_images:
            try:
                with Image.open(path) as image:
                    image.load()
                    if image.format != "PNG" or image.convert("RGBA").getchannel("A").getextrema()[0] != 0:
                        raise ValueError("需要包含透明像素的 PNG")
                    if max(image.size) > 12000:
                        raise ValueError("角色图片尺寸超过限制")
            except Exception as exc:
                raise InputError("character.images." + role, str(exc)) from exc
            checked_images[path] = file_hash(path)
        assets[role] = str(path)
        hashes[str(path)] = checked_images[path]
    works = ep.get("works")
    if not isinstance(works, list) or not 1 <= len(works) <= 15:
        raise InputError("episode.works", "当前版式需要 1 至 15 条作品")
    rows, sources, missing, seen = [], {}, [], set()
    for index, work in enumerate(works):
        field = f"episode.works[{index}]"
        if not isinstance(work, dict):
            raise InputError(field, "作品必须是对象")
        if set(work) - {"bvid", "title", "author", "source_url", "published_at", "observed_at", "part_count", "metrics", "video", "clip", "short_title", "rank", "score", "provenance"}:
            raise InputError(field, "包含未知字段")
        bv = text(work.get("bvid"), field + ".bvid", 12)
        if not re.fullmatch(r"BV[1-9A-HJ-NP-Za-km-z]{10}", bv) or bv in seen:
            raise InputError(field + ".bvid", "需要不重复的有效 BV 号")
        seen.add(bv)
        metrics = work.get("metrics")
        if not isinstance(metrics, dict):
            raise InputError(field + ".metrics", "缺少指标对象")
        metrics = {key: integer(metrics.get(key), field + ".metrics." + key) for key in METRICS}
        parts = integer(work.get("part_count"), field + ".part_count", 1)
        breakdown = calculate(metrics, parts)
        if "score" in work and integer(work["score"], field + ".score") != breakdown["score"]:
            raise InputError(field + ".score", "与公开综合公式的计算结果不一致")
        published = timestamp(work.get("published_at"), field + ".published_at")
        captured = timestamp(work.get("observed_at"), field + ".observed_at")
        if published >= end or (basis == "cumulative" and published < begin):
            raise InputError(field + ".published_at", "作品不在本期允许的投稿范围")
        path = local_file(work.get("video"), ep_path.parent, field + ".video")
        info = probe(path)
        if not info["video"]:
            raise InputError(field + ".video", "文件没有视频画面")
        clip = work.get("clip")
        if clip is None and info["duration"] <= 60:
            clip = {"start": 0, "end": math.floor(info["duration"] * 30 + 1e-6) / 30}
        if clip is None:
            missing.append({"bvid": bv, "field": field + ".clip", "reason": "长作品需先确定完整连续段落"})
        elif not isinstance(clip, dict):
            raise InputError(field + ".clip", "需要 start、end")
        else:
            start = number(clip.get("start"), field + ".clip.start")
            finish = number(clip.get("end"), field + ".clip.end")
            if start >= finish or finish > info["duration"] + 1 / 30:
                raise InputError(field + ".clip", "范围为空或超出实际视频时长")
            if abs(start * 30 - round(start * 30)) > .001 or abs(finish * 30 - round(finish * 30)) > .001:
                raise InputError(field + ".clip", "起止时间需对齐 30 fps 帧边界")
            clip = {**deepcopy(clip), "start": start, "end": finish}
        row = {"bvid": bv, "title": text(work.get("title"), field + ".title"),
               "author": text(work.get("author"), field + ".author", 100), "url": url(work.get("source_url"), field + ".source_url"),
               "published_at": published, "captured_at": captured, "part_count": parts,
               "duration": info["duration"], "metrics": metrics, "score": breakdown["score"], "score_breakdown": breakdown}
        if "short_title" in work:
            row["short_title"] = text(work["short_title"], field + ".short_title", 100)
        if "rank" in work:
            row["expected_rank"] = integer(work["rank"], field + ".rank", 1)
        sources[bv] = {"path": str(path), "info": info, "clip": clip}
        hashes[str(path)] = file_hash(path)
        rows.append(row)
    rows.sort(key=sort_key)
    for rank, row in enumerate(rows, 1):
        if row.get("expected_rank", rank) != rank:
            raise InputError(row["bvid"] + ".rank", "与本期作品集合的综合计分顺序不一致")
        row.pop("expected_rank", None)
        row["rank"] = rank
    if missing and require_clips:
        raise InputError("episode.works.clip", "; ".join(x["bvid"] + "：" + x["reason"] for x in missing))
    music = ep.get("music")
    if not isinstance(music, dict):
        raise InputError("episode.music", "缺少本期 BGM 配置")
    if set(music) - {"file", "title", "artist", "source_url", "sha256", "gain_db", "start_seconds"}:
        raise InputError("episode.music", "包含未知字段")
    music_file = local_file(music.get("file"), ep_path.parent, "episode.music.file")
    music_info = probe(music_file)
    if not music_info["audio"]:
        raise InputError("episode.music.file", "音源没有有效音轨")
    music_hash = file_hash(music_file)
    if "sha256" in music and music["sha256"] != music_hash:
        raise InputError("episode.music.sha256", "音源与已确认版本不一致")
    bgm = {"schema": "ai-girl-weekly/bgm-v1", "path": str(music_file), "sha256": music_hash,
           "title": text(music.get("title"), "episode.music.title", 200), "artist": text(music.get("artist"), "episode.music.artist", 200),
           "source_url": url(music.get("source_url"), "episode.music.source_url"),
           "gain_db": number(music.get("gain_db", -1.5), "episode.music.gain_db", -30, 0),
           "start_seconds": number(music.get("start_seconds", 0), "episode.music.start_seconds", 0, music_info["duration"] - .001)}
    if not bgm["source_url"].startswith("https://"):
        raise InputError("episode.music.source_url", "原曲来源需要 HTTPS 链接")
    hashes[str(music_file)] = music_hash
    copy = ep.get("copy", {})
    if not isinstance(copy, dict) or set(copy) - COPY_FIELDS:
        raise InputError("episode.copy", "包含不支持的文案字段，见 references/input.md")
    copy = {key: text(value, "episode.copy." + key, 500) for key, value in copy.items()}
    branding = ep.get("branding", {})
    if not isinstance(branding, dict) or set(branding) - {"producer", "website_name", "website_url", "update_schedule"}:
        raise InputError("episode.branding", "不支持的署名字段")
    branding = {key: (url(value, "episode.branding." + key) if key == "website_url" else text(value, "episode.branding." + key, 200)) for key, value in branding.items()}
    hashes[str(ep_path)] = file_hash(ep_path)
    hashes[str(char_path)] = file_hash(char_path)
    return {"episode_file": str(ep_path), "character_file": str(char_path), "id": issue, "title": title,
            "begin": begin, "end": end, "kind": "cumulative" if basis == "cumulative" else "weekly",
            "rows": rows, "sources": sources, "bgm": bgm, "assets": assets,
            "character": {"id": character["id"], "name": character["name"]},
            "copy": copy, "branding": branding, "hashes": hashes, "missing": missing}
