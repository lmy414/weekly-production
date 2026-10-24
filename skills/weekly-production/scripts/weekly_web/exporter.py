# SPDX-License-Identifier: GPL-3.0-only
"""Turn a verified movie's exact lineup and timing into pages and images."""
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil

from PIL import Image, ImageOps
import av

from weekly_runtime.common import SKILL, TZ, InputError, read_json, file_hash, digest, timestamp
from weekly_runtime.inputs import load_inputs
from weekly_runtime.pipeline import work_directory, ensure_unchanged, build_lock
from weekly_runtime.encoder import render_input
from weekly_runtime.scoring import rule_info
from .settings import Settings
from .cards import Cards
from .builder import assert_issue, asset_refs, build_pages


def verified_inputs(episode, character, video):
    bundle = load_inputs(episode, character)
    target, work = work_directory(video)
    result = read_json(work / "last-build.json")
    lock = read_json(work / "episode.lock.json")
    program = read_json(work / "program.json")
    if result.get("verified") is not True or not target.is_file() or file_hash(target) != result.get("sha256"):
        raise InputError("output", "成品未通过验证，或 MP4 与构建记录不一致")
    if Path(lock["episode"]).resolve() != Path(episode).resolve() or Path(lock["character"]).resolve() != Path(character).resolve():
        raise InputError("episode", "入口与成片绑定记录不一致")
    ensure_unchanged(lock["inputs"])
    if lock.get("program_sha256") != digest(render_input(program)):
        raise InputError("program", "成片时间轴与锁定记录不一致")
    selected = program["context"]["selected"]
    if [(w["bvid"], w["rank"], w["score"], w["metrics"]) for w in bundle["rows"]] != [(w["bvid"], w["rank"], w["score"], w["metrics"]) for w in selected]:
        raise InputError("program", "本期片单与已验证成片不一致")
    return bundle, program, work, {**result, "output": str(target)}


def frame_at(path, seconds):
    with av.open(str(path)) as media:
        stream = media.streams.video[0]
        media.seek(int(seconds / float(stream.time_base)), stream=stream, backward=True)
        for frame in media.decode(stream):
            if frame.pts is not None and float(frame.pts * stream.time_base) + 1e-6 >= seconds:
                return frame.to_image().convert("RGB")
    raise InputError("video", "无法读取已确认选段的图片")


def make_issue(bundle, program, work, result, settings, media, editorial=None):
    ep = read_json(bundle["episode_file"])
    copy = read_json(editorial) if editorial else {}
    allowed = {"label", "published_at", "deck", "intro", "works"}
    if set(copy) - allowed:
        raise InputError("editorial", "只支持 label、published_at、deck、intro 与 works")
    annotations = copy.get("works", {})
    if not isinstance(annotations, dict) or set(annotations) - {w["bvid"] for w in bundle["rows"]}:
        raise InputError("editorial.works", "只能为入选作品补充介绍")
    issue_id = bundle["id"]
    destination = Path(media) / issue_id
    destination.mkdir(parents=True, exist_ok=True)
    prefix = "/assets/issues/" + issue_id + "/"
    begin, end = (datetime.fromtimestamp(bundle[k], TZ) for k in ("begin", "end"))
    published = copy.get("published_at", end.replace(hour=22, minute=0, second=0, microsecond=0).isoformat())
    published = datetime.fromtimestamp(timestamp(published, "editorial.published_at"), TZ)
    host = Image.open(bundle["assets"]["welcome"]).convert("RGBA")
    host.thumbnail((850, 1000), Image.Resampling.LANCZOS)
    host.save(destination / "host.webp", quality=92, method=6)
    opening = next(s for s in program["scenes"] if s["template"] == "opening")
    cover = frame_at(result["output"], opening["start"] + min(2, opening["duration"] / 2))
    ImageOps.fit(cover, (1200, 675), method=Image.Resampling.LANCZOS).save(destination / "cover.jpg", quality=91)
    issue = {"id": issue_id, "number": program["context"]["issue_number"].zfill(3), "title": bundle["title"],
             "label": copy.get("label", "创刊特辑" if bundle["kind"] == "cumulative" else "本周主榜"),
             "date": published.strftime("%Y.%m.%d"), "published_at": published.isoformat(), "updated_at": published.isoformat(),
             "metric_basis": ep["metric_basis"], "basis_label": "累计数据榜" if bundle["kind"] == "cumulative" else "周期增量榜",
             "period_label": begin.strftime("%Y.%m.%d") + " — " + end.strftime("%m.%d"), "period_begin": begin.isoformat(), "period_end": end.isoformat(),
             "deck": copy.get("deck", f"{len(bundle['rows'])} 部 AI 娘新作，一起看完这一期。"),
             "intro": copy.get("intro", "从这一份片单出发，遇见喜欢的角色与创作者。"),
             "authors": len({w["author"] for w in bundle["rows"]}), "cover": prefix + "cover.jpg", "host": prefix + "host.webp",
             "share": prefix + "issue-share.png", "works": []}
    sources = {w["bvid"]: w for w in ep["works"]}
    scenes = {s["row"]["bvid"]: s for s in program["scenes"] if s["template"] in ("ranking", "podium")}
    for row in bundle["rows"]:
        original = sources[row["bvid"]]
        note = annotations.get(row["bvid"], original.get("provenance", {}).get("website", {}))
        if not isinstance(note, dict) or set(note) - {"summary", "category"}:
            raise InputError("editorial.works." + row["bvid"], "只支持公开 summary 与 category")
        info = bundle["sources"][row["bvid"]]
        seconds = info["clip"]["start"] + min(3, (info["clip"]["end"] - info["clip"]["start"]) / 4)
        image = ImageOps.fit(frame_at(info["path"], seconds), (960, 540), method=Image.Resampling.LANCZOS)
        image.save(destination / (row["bvid"] + ".webp"), quality=86, method=6)
        start = int(scenes[row["bvid"]]["start"])
        # Missing editorial text stays factual; internal clip summaries are never republished.
        issue["works"].append({"bvid": row["bvid"], "rank": row["rank"], "score": row["score"], "title": row["title"],
                               "short_title": row.get("short_title", row["title"]), "author": row["author"], "source_url": row["url"],
                               "published_date": datetime.fromtimestamp(row["published_at"], TZ).strftime("%Y.%m.%d"),
                               "observed_at": datetime.fromtimestamp(row["captured_at"], TZ).strftime("%Y-%m-%d %H:%M:%S"),
                               "part_count": row["part_count"], "metrics": row["metrics"], "category": note.get("category", "其他"),
                               "summary": note.get("summary", "本期第 " + str(row["rank"]) + " 名，点击标题查看原作。"),
                               "cover": prefix + row["bvid"] + ".webp", "share": prefix + row["bvid"] + "-share.png",
                               "timestamp": f"{start // 60:02d}:{start % 60:02d}"})
    observed = [r["captured_at"] for r in bundle["rows"]]
    issue["observed_label"] = datetime.fromtimestamp(min(observed), TZ).strftime("%m.%d %H:%M") + " — " + datetime.fromtimestamp(max(observed), TZ).strftime("%m.%d %H:%M")
    assert_issue(issue)
    cards = Cards(SKILL / "assets/ui/fonts/noto-sans-sc/NotoSansSC-variable.ttf", settings)
    issue["wechat_covers"] = {name: prefix + path.name for name, path in cards.wechat_covers(issue, destination).items()}
    cards.entire(issue, destination, destination / "issue-share.png")
    for row in issue["works"]:
        cards.work(issue, row, destination, destination / (row["bvid"] + "-share.png"))
    return issue


def export_site(episode, character, video, directory, settings=None, editorial=None):
    settings = settings or Settings()
    target = Path(directory).expanduser().resolve()
    if target == SKILL or target.is_relative_to(SKILL) or SKILL.is_relative_to(target):
        raise InputError("directory", "网页输出不能覆盖 Skill 源码")
    bundle, program, work, result = verified_inputs(episode, character, video)
    protected = [Path(p) for p in bundle["hashes"]] + [Path(video).resolve(), work]
    if any(p == target or p.is_relative_to(target) or target.is_relative_to(work) for p in protected):
        raise InputError("directory", "网页输出不能覆盖输入、视频或制作记录")
    target.parent.mkdir(parents=True, exist_ok=True)
    with build_lock(target.parent / ".weekly-web" / target.name):
        issues = []
        if target.exists():
            if not target.is_dir():
                raise InputError("directory", "需要目录")
            if any(target.iterdir()):
                manifest = read_json(target / "export-manifest.json")
                if manifest.get("schema") != "weekly-production/web-v1" or set(manifest) != {"schema", "issues"}:
                    raise InputError("directory", "只能更新此工具生成的网页目录")
                issues = manifest["issues"]
                for issue in issues:
                    assert_issue(issue)
        with TemporaryDirectory(prefix="weekly-export-", dir=target.parent) as temporary:
            scratch = Path(temporary).resolve()
            media, stage = scratch / "media", scratch / "site"
            stage.mkdir()
            for issue in issues:
                if issue["id"] == bundle["id"]:
                    continue
                for ref in asset_refs(issue):
                    source = target / ref.lstrip("/")
                    if not source.is_file() or source.is_symlink():
                        raise InputError("web.archive", "往期图片缺失或使用了链接")
                    dest = media / ref.removeprefix("/assets/issues/")
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
            issue = make_issue(bundle, program, work, result, settings, media, editorial)
            issues = [i for i in issues if i["id"] != issue["id"]] + [issue]
            report = build_pages(stage, issues, rule_info(), settings, media)
            ensure_unchanged(bundle["hashes"])
            if file_hash(video) != result["sha256"]:
                raise InputError("output", "导出期间成品发生变化")
            backup = scratch / "previous"
            if target.exists():
                target.rename(backup)
            try:
                stage.rename(target)
            except BaseException:
                if backup.exists():
                    backup.rename(target)
                raise
            # TemporaryDirectory removes only our absolute sibling workspace and the tool-owned old export.
            assert scratch.parent == target.parent and scratch.name.startswith("weekly-export-")
    return {"ok": True, "directory": str(target), "index": str(target / "index.html"), "issue": issue["id"],
            "share_image": str(target / issue["share"].lstrip("/")),
            "wechat_covers": {name: str(target / ref.lstrip("/")) for name, ref in issue["wechat_covers"].items()},
            "work_cards": [str(target / w["share"].lstrip("/")) for w in issue["works"]],
            "qr": {"enabled": settings.qr_enabled, "source": settings.qr_source,
                   "issue_url": settings.qr_target(issue), "work_urls": {w["bvid"]: settings.qr_target(issue, w) for w in issue["works"]}},
            "build": report, "publication": None}
