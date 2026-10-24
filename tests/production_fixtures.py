# SPDX-License-Identifier: GPL-3.0-only
"""Wholly synthetic private packs; no production data or artwork."""
from pathlib import Path
import json
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/weekly-production/scripts"))
from weekly_runtime.media import run_ffmpeg


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), "utf-8")


def packs(root, count=3):
    root = Path(root)
    ep, char = root / "episode data", root / "character art"
    ep.mkdir(parents=True); char.mkdir(parents=True)
    image = Image.new("RGBA", (320, 480))
    draw = ImageDraw.Draw(image)
    draw.ellipse((60, 30, 260, 230), fill="#bce7db", outline="#273549", width=6)
    draw.rectangle((90, 220, 230, 440), fill="#f79885")
    image.save(char / "default.png")
    art = {"schema": "weekly-production/character-v1", "id": "synthetic-host", "name": "虚构测试角色", "images": {"default": "default.png"}}
    write_json(char / "character.json", art)
    run_ffmpeg(["-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:duration=2", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=2", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ac", 2, "-shortest", ep / "source.mp4"], ep / "source.log")
    rate = 48000
    t = np.arange(rate * 4) / rate
    samples = np.column_stack((.18 * np.sin(2 * np.pi * (220 * t + 11 * t * t)), .15 * np.sin(2 * np.pi * 330 * t)))
    with wave.open(str(ep / "bgm.wav"), "wb") as audio:
        audio.setnchannels(2); audio.setsampwidth(2); audio.setframerate(rate)
        audio.writeframes(np.rint(samples * 32767).astype("<i2").tobytes())
    works = [{"bvid": "BV" + str(n) * 10, "title": f"虚构作品 {n}", "short_title": f"测试片段 {n}", "author": "合成测试作者",
              "source_url": "https://example.org/synthetic/" + str(n), "published_at": "2024-01-02T12:00:00+08:00",
              "observed_at": "2024-01-29T00:00:00+08:00", "part_count": 1, "video": "source.mp4",
              "metrics": {"view": 1000 * (count + 1 - n), "reply": 10, "danmaku": 5, "favorite": 20, "coin": 30, "like": 50, "share": 2}}
             for n in range(1, count + 1)]
    data = {"schema": "weekly-production/episode-v1", "id": "synthetic-001", "title": "合成材料完整制作测试",
            "period": {"begin": "2024-01-01T00:00:00+08:00", "end": "2024-01-29T00:00:00+08:00", "timezone": "Asia/Shanghai"},
            "metric_basis": "cumulative", "works": works,
            "music": {"file": "bgm.wav", "title": "合成正弦配乐", "artist": "测试程序", "source_url": "https://example.org/synthetic/music"}}
    write_json(ep / "episode.json", data)
    return ep / "episode.json", char / "character.json"
