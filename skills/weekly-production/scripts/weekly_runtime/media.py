# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import os
import shutil
import subprocess

from .common import InputError, SKILL, UI, atomic_json, digest, file_hash, progress, read_json


def ffmpeg_path():
    configured = os.environ.get("WEEKLY_FFMPEG") or shutil.which("ffmpeg")
    if configured:
        return configured
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ffmpeg(arguments, log, timeout=600):
    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as handle:
        result = subprocess.run([ffmpeg_path(), "-hide_banner", "-nostdin", "-y", *map(str, arguments)],
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=handle, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"FFmpeg 失败，详见 {log}")


def runtime():
    import importlib.metadata
    import platform
    libraries = {}
    for distribution, module in (("Pillow", "PIL.Image"), ("numpy", "numpy"), ("av", "av"), ("imageio-ffmpeg", "imageio_ffmpeg")):
        try:
            __import__(module)
            libraries[distribution] = importlib.metadata.version(distribution)
        except ImportError as exc:
            raise InputError("runtime." + distribution, "请安装 scripts/requirements.txt 中的 Python 依赖") from exc
    node = os.environ.get("WEEKLY_NODE") or shutil.which("node")
    chrome = os.environ.get("WEEKLY_CHROME")
    if not chrome:
        chrome = next((shutil.which(name) for name in ("chromium", "chromium-browser", "google-chrome", "chrome") if shutil.which(name)), None)
    if not chrome:
        cache = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".cache")) / "ms-playwright"
        choices = sorted([*cache.glob("chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"),
                          *cache.glob("chromium_headless_shell-*/chrome-linux/headless_shell"),
                          *cache.glob("chromium-*/chrome-win/chrome.exe")])
        chrome = str(choices[-1]) if choices else None
    if not node:
        raise InputError("runtime.node", "未找到 Node.js，可设置 WEEKLY_NODE")
    if not chrome or not Path(chrome).is_file():
        raise InputError("runtime.chrome", "未找到 Chromium，可设置 WEEKLY_CHROME")
    ffmpeg = ffmpeg_path()
    if not Path(ffmpeg).is_file() and not shutil.which(ffmpeg):
        raise InputError("runtime.ffmpeg", "未找到 FFmpeg，可设置 WEEKLY_FFMPEG")
    module = os.environ.get("WEEKLY_PUPPETEER", "puppeteer-core")
    check = subprocess.run([node, "-e", "process.stdout.write(require.resolve(process.argv[1]))", module],
                           cwd=SKILL / "scripts", capture_output=True, text=True, timeout=20)
    if check.returncode:
        raise InputError("runtime.puppeteer", "运行 npm install --prefix <Skill>/scripts，或设置 WEEKLY_PUPPETEER")
    fonts = [UI / "fonts/fusion-pixel-12px.woff2", UI / "fonts/noto-sans-sc/NotoSansSC-variable.ttf"]
    if not all(p.is_file() for p in fonts):
        raise InputError("runtime.fonts", "Skill 内置字体不完整")
    return {"node": node, "chrome": chrome, "ffmpeg": ffmpeg, "puppeteer": check.stdout.strip(),
            "python_version": platform.python_version(), "python_libraries": libraries,
            "node_version": subprocess.check_output([node, "--version"], text=True).strip(),
            "chrome_version": subprocess.check_output([chrome, "--version"], text=True, timeout=20).strip(),
            "ffmpeg_version": subprocess.check_output([ffmpeg, "-version"], text=True, timeout=20).splitlines()[0]}


def prepare_media(bundle, program, out):
    directory = out / "media"
    directory.mkdir(parents=True, exist_ok=True)
    results = {}
    for scene in program["scenes"]:
        if scene["template"] not in ("ranking", "podium"):
            continue
        bvid = scene["row"]["bvid"]
        source = bundle["sources"][bvid]
        path = Path(source["path"])
        start, seconds = scene["clip_start"], scene["duration"]
        key = digest({"source": bundle["hashes"][str(path)], "start": start, "seconds": seconds, "recipe": "local-excerpt-v1"})[:20]
        if start == 0 and source["info"]["audio"] and abs(seconds - source["info"]["duration"]) <= 1 / 30:
            target = path
        else:
            target = directory / f"{bvid}-{key}.mp4"
            receipt = target.with_suffix(".json")
            valid = False
            if target.is_file() and receipt.is_file():
                try:
                    saved = read_json(receipt)
                    valid = saved.get("key") == key and saved.get("sha256") == file_hash(target)
                except (ValueError, OSError):
                    pass
            if not valid:
                temporary = target.with_suffix(".partial.mp4")
                inputs = ["-ss", start, "-i", path]
                if not source["info"]["audio"]:
                    inputs += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
                run_ffmpeg([*inputs, "-t", seconds, "-map", "0:v:0", "-map", "0:a:0" if source["info"]["audio"] else "1:a:0",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", 18, "-pix_fmt", "yuv420p", "-c:a", "aac",
                            "-b:a", "256k", "-ar", 48000, "-ac", 2, "-movflags", "+faststart", temporary], directory / f"{bvid}.log")
                temporary.replace(target)
                atomic_json(receipt, {"key": key, "sha256": file_hash(target)})
        results[bvid] = {"path": str(target), "seconds": seconds, "start": start, "has_audio": source["info"]["audio"] or target != path,
                         "selection_method": "complete-segment-v1", "source": source["info"]}
        progress("media", bvid=bvid, seconds=seconds)
    atomic_json(out / "media.json", results)
    return results
