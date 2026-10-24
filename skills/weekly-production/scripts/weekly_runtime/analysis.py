# SPDX-License-Identifier: GPL-3.0-only
"""Local timestamped contact sheets and optional cached-model ASR; never downloads."""
from pathlib import Path
import json
import math
import subprocess

import av
from PIL import Image, ImageDraw, ImageFont

from .common import UI, atomic_json, progress
from .media import ffmpeg_path
from .verify import frame_at


def analyze(bundle, asr=False):
    out = Path(bundle["episode_file"]).parent / ".weekly-analysis"
    results = []
    model = None
    if asr:
        from faster_whisper import WhisperModel
        model = WhisperModel("small", device="cpu", compute_type="int8", local_files_only=True, cpu_threads=4)
    font = ImageFont.truetype(str(UI / "fonts/noto-sans-sc/NotoSansSC-variable.ttf"), 20)
    for row in bundle["rows"]:
        source = bundle["sources"][row["bvid"]]
        directory = out / row["bvid"] / bundle["hashes"][source["path"]][:16]
        directory.mkdir(parents=True, exist_ok=True)
        evidence_file = directory / "evidence.json"
        if evidence_file.exists():
            cached = json.loads(evidence_file.read_text("utf-8"))
            if not asr or cached.get("asr_model") == "small":
                results.append({"bvid": row["bvid"], "evidence": str(evidence_file), "panels": cached["panels"]})
                continue
        frames = []
        duration = source["info"]["duration"]
        count = min(60, max(1, math.ceil(duration)))
        with av.open(source["path"]) as media:
            for n in range(count):
                seconds = min(duration - .05, n * duration / count)
                frame = frame_at(media, max(0, seconds))
                frame.thumbnail((320, 180))
                frames.append((seconds, frame))
        panels = []
        for page in range(math.ceil(len(frames) / 24)):
            cells = frames[page * 24:(page + 1) * 24]
            image = Image.new("RGB", (1280, math.ceil(len(cells) / 4) * 210), "#172033")
            draw = ImageDraw.Draw(image)
            for n, (seconds, frame) in enumerate(cells):
                x, y = n % 4 * 320, n // 4 * 210
                image.paste(frame, (x + (320 - frame.width) // 2, y))
                draw.text((x + 8, y + 182), f"{seconds:07.2f}s", font=font, fill="white")
            target = directory / f"timeline-{page + 1:02d}.jpg"
            image.save(target, quality=90)
            panels.append(str(target))
        transcript = []
        if model and source["info"]["audio"]:
            import numpy as np
            decoded = subprocess.run([ffmpeg_path(), "-v", "error", "-nostdin", "-i", source["path"], "-vn", "-ar", "16000", "-ac", "1", "-f", "f32le", "-"], capture_output=True, check=True)
            segments, _ = model.transcribe(np.frombuffer(decoded.stdout, dtype=np.float32), language="zh", word_timestamps=True, vad_filter=False)
            transcript = [{"start": s.start, "end": s.end, "text": s.text,
                           "words": [{"start": w.start, "end": w.end, "word": w.word} for w in s.words or []]} for s in segments]
        evidence = {"bvid": row["bvid"], "source": source["path"], "source_sha256": bundle["hashes"][source["path"]],
                    "duration": duration, "panels": panels, "transcript": transcript,
                    "asr_model": "small" if model else None, "asr_is_evidence_not_verified_subtitles": True}
        atomic_json(evidence_file, evidence)
        results.append({"bvid": row["bvid"], "evidence": str(evidence_file), "panels": panels})
        progress("analyze", bvid=row["bvid"], frames=len(frames))
    return {"ok": True, "analysis": results, "missing": bundle["missing"]}
