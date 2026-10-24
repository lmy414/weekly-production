# SPDX-License-Identifier: GPL-3.0-only
from contextlib import contextmanager
from pathlib import Path
import json
import os
import shutil
import subprocess
import time

from . import VERSION
from .assembly import assemble
from .common import InputError, SKILL, atomic_json, digest, file_hash, progress, read_json
from .encoder import render_program, render_input
from .inputs import load_inputs
from .media import prepare_media, runtime
from .server import render_server
from .verify import verify


def work_directory(output):
    path = Path(output).expanduser().resolve()
    if path.suffix.lower() != ".mp4":
        raise InputError("output", "成品路径必须以 .mp4 结尾")
    return path, path.parent / ".weekly-production" / path.stem


@contextmanager
def build_lock(out):
    out.mkdir(parents=True, exist_ok=True)
    with (out / "build.lock").open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise InputError("output", "已有构建正在使用同一工作目录") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def template_hash():
    folders = [SKILL / "scripts/weekly_runtime", SKILL / "assets/ui"]
    files = {}
    for folder in folders:
        for path in folder.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                files[str(path.relative_to(SKILL))] = file_hash(path)
    files["scripts/capture.mjs"] = file_hash(SKILL / "scripts/capture.mjs")
    return digest(files)


def ensure_unchanged(hashes):
    for filename, expected in hashes.items():
        path = Path(filename)
        if not path.is_file() or file_hash(path) != expected:
            raise InputError(filename, "输入或素材在制作期间发生变化，请重新构建")


def plan(bundle, out):
    program = assemble(bundle)
    atomic_json(out / "program.json", program)
    atomic_json(out / "ranking-policy.json", program["context"]["rule"])
    atomic_json(out / "计分明细.json", [{k: row[k] for k in ("bvid", "rank", "score", "metrics", "score_breakdown", "captured_at")} for row in program["context"]["selected"]])
    return program


def capture(bundle, program, out, tools):
    report = out / "capture-report.json"
    marker = out / "capture-key.json"
    key = digest({"program": render_input(program), "character": {role: bundle["hashes"][path] for role, path in bundle["assets"].items()},
                  "template": template_hash(), "chrome": tools["chrome_version"]})
    # Capture freshness includes actual image hashes, so an interrupted/deleted frame cache cannot pass.
    if report.is_file() and marker.is_file():
        saved = read_json(marker)
        if saved.get("key") == key:
            files = saved.get("files", {})
            if files and all((out / name).is_file() and file_hash(out / name) == value for name, value in files.items()):
                progress("capture-cache", scenes=len(program["scenes"]))
                return read_json(report)
    env = dict(os.environ, WEEKLY_CHROME=tools["chrome"], WEEKLY_PUPPETEER=tools["puppeteer"])
    with render_server(bundle) as address:
        with (out / "capture.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen([tools["node"], str(SKILL / "scripts/capture.mjs"), str(out), address],
                                       cwd=SKILL / "scripts", env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                process.wait(timeout=1200)
            except BaseException:
                process.terminate()
                process.wait(timeout=20)
                raise
        if process.returncode:
            raise RuntimeError(f"无头画面捕获失败，详见 {out / 'capture.log'}")
    result = read_json(report)
    files = {str(p.relative_to(out)): file_hash(p) for folder in ("plates", "motion", "catalogue") for p in (out / folder).rglob("*.png")}
    files["capture-report.json"] = file_hash(report)
    atomic_json(marker, {"key": key, "files": files})
    return result


def build(episode, character, output, workers=2):
    started = time.monotonic()
    bundle = load_inputs(episode, character)
    target, out = work_directory(output)
    if str(target) in bundle["hashes"]:
        raise InputError("output", "成品路径不能覆盖输入或素材文件")
    tools = runtime()
    with build_lock(out):
        progress("validated", works=len(bundle["rows"]), network="local-files-and-loopback-only")
        program = plan(bundle, out)
        lock = {"schema": "weekly-production/lock-v1", "version": VERSION, "episode": bundle["episode_file"],
                "character": bundle["character_file"], "inputs": bundle["hashes"], "template_sha256": template_hash(),
                "program_sha256": digest(render_input(program)), "runtime": tools}
        atomic_json(out / "episode.lock.json", lock)
        media = prepare_media(bundle, program, out)
        progress("capture", scenes=len(program["scenes"]))
        captured = capture(bundle, program, out, tools)
        ensure_unchanged(bundle["hashes"])
        report = render_program(out, program, media, captured, workers)
        progress("verify", frames=program["total_frames"])
        qa = verify(out)
        ensure_unchanged(bundle["hashes"])
        if lock["template_sha256"] != template_hash():
            raise InputError("template", "制作代码或模板在构建期间改变，请重新构建")
        source = out / "program.mp4"
        temporary = target.with_name(target.stem + ".partial.mp4")
        try:
            shutil.copy2(source, temporary)
            if file_hash(temporary) != file_hash(source):
                raise RuntimeError("成品复制校验失败")
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        result = {"ok": True, "output": str(target), "sha256": file_hash(target), "bytes": target.stat().st_size,
                  "duration": program["duration"], "frames": program["total_frames"], "scenes": len(program["scenes"]),
                  "works": len(bundle["rows"]), "verified": qa["passed"], "wall_seconds": round(time.monotonic() - started, 2),
                  "work_dir": str(out), "reused_work_segments": report["reused_work_segments"]}
        atomic_json(out / "last-build.json", result)
        return result


def verify_output(output):
    target, out = work_directory(output)
    result = read_json(out / "last-build.json")
    if not target.is_file() or file_hash(target) != result.get("sha256"):
        raise InputError("output", "成品缺失或与构建记录不一致")
    lock = read_json(out / "episode.lock.json")
    ensure_unchanged(lock["inputs"])
    if lock["template_sha256"] != template_hash():
        raise InputError("template", "工具版本与该成片的构建版本不同，请使用原版本验证")
    qa = verify(out, target_override=target)
    return {"ok": True, "output": str(target), "verified": qa["passed"], "sha256": result["sha256"],
            "frames": qa["streams"]["frames"], "duration": qa["streams"]["video_seconds"]}
