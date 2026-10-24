# SPDX-License-Identifier: GPL-3.0-only
"""Programme recordings, fallback instrumental score and transition sounds."""
from pathlib import Path
from copy import deepcopy
import hashlib
import math
import re
import wave
from urllib.parse import urlsplit

import numpy as np

from .common import atomic_json

VERSION = "whale-studio-score-v1"
RATE = 48000
BEAT = .5
LOOP_SECONDS = 16


def note(midi, seconds, voice="bell"):
    t = np.arange(round(seconds * RATE), dtype=np.float64) / RATE
    frequency = 440 * 2 ** ((midi - 69) / 12)
    phase = 2 * np.pi * frequency * t
    if voice == "bass":
        sound = np.sin(phase) + .18 * np.sin(3 * phase) / 3
        envelope = np.minimum(t / .008, 1) * np.exp(-t * 3.8)
    elif voice == "pad":
        sound = np.sin(phase) + .12 * np.sin(2 * phase)
        envelope = np.minimum(t / .12, 1) * np.minimum((seconds - t) / .28, 1) * .7
    else:
        sound = np.sin(phase) + .24 * np.sin(2 * phase) + .10 * np.sin(3 * phase)
        envelope = np.minimum(t / .004, 1) * np.exp(-t * (5 if voice == "pluck" else 3.5))
    envelope *= np.clip((seconds - t) / .025, 0, 1)
    return (sound * envelope).astype(np.float32)


def add(track, mono, start, gain, pan=0):
    offset = round(start * RATE)
    size = min(len(mono), len(track) - offset)
    if size <= 0:
        return
    angle = (pan + 1) * np.pi / 4
    track[offset:offset + size, 0] += mono[:size] * (gain * math.cos(angle))
    track[offset:offset + size, 1] += mono[:size] * (gain * math.sin(angle))


def score_layers():
    backing = np.zeros((RATE * LOOP_SECONDS, 2), dtype=np.float32)
    melody = np.zeros_like(backing)
    chords = [(48, 52, 55, 59), (45, 48, 52, 55), (41, 45, 48, 52), (43, 47, 50, 55)]
    tune = [(72, .75), (76, .25), (79, .5), (76, .5),
            (74, .5), (76, .5), (79, .5), (83, .5),
            (81, .75), (79, .25), (76, .5), (72, .5),
            (71, .5), (74, .5), (76, .5), (79, .5),
            (77, .75), (81, .25), (79, .5), (76, .5),
            (74, .5), (72, .5), (69, 1),
            (71, .5), (74, .5), (79, .5), (77, .5),
            (76, .5), (74, .5), (72, 1)]
    at = 0
    for pitch, length in tune:
        add(melody, note(pitch, length + .18), at, .20, -.12)
        add(melody, note(pitch, length + .16), at + .125, .035, .55)
        at += length
    rng = np.random.default_rng(21024)
    for bar in range(8):
        base = bar * 2
        chord = chords[(bar // 2) % 4]
        for index, pitch in enumerate(chord):
            add(backing, note(pitch + 12, 2, "pad"), base, .055, (index - 1.5) / 3)
        for eighth in range(8):
            add(backing, note(chord[eighth % 4] + 24, .22, "pluck"), base + eighth * .25,
                .065, -.45 if eighth % 2 else .45)
            noise = rng.normal(0, 1, round(RATE * .05)).astype(np.float32)
            noise = np.concatenate(([0], np.diff(noise))) * np.exp(-np.arange(len(noise)) / (RATE * .009))
            add(backing, noise, base + eighth * .25, .012, .3)
        for beat in range(4):
            add(backing, note(chord[0] if beat % 2 == 0 else chord[2] - 12, .32, "bass"),
                base + beat * BEAT, .22, 0)
            t = np.arange(round(RATE * .19)) / RATE
            kick = np.sin(2 * np.pi * (48 * t + 36 * .035 * (1 - np.exp(-t / .035)))) * np.exp(-t * 28)
            if beat % 2 == 0:
                add(backing, kick.astype(np.float32), base + beat * BEAT, .14)
            else:
                noise = rng.normal(0, 1, len(t))
                snare = (.45 * noise + .55 * np.sin(2 * np.pi * 185 * t)) * np.exp(-t * 42)
                add(backing, snare.astype(np.float32), base + beat * BEAT, .065, -.15)
    return backing, melody


def stinger(track, scene):
    kind = scene["template"]
    duration = len(track) / RATE
    if kind == "next":
        sequence = [(79, .08), (84, .18), (88, .29)]
    elif kind == "podium_reveal":
        rank = scene.get("row", {}).get("rank", 3)
        root = {1: 72, 2: 69, 3: 67}[rank]
        sequence = [(root, .12), (root + 4, .37), (root + 7, .62), (root + 12, .92)]
        for pitch in (root - 12, root, root + 4, root + 7):
            add(track, note(pitch, min(2.2, duration - 1.05), "pad"), 1.05, .15, -.2)
    else:
        sequence = [(72, .10), (76, .32), (79, .54), (84, .88)]
    for pitch, start in sequence:
        add(track, note(pitch, min(.7, duration - start)), start, .25, -.18 if pitch % 2 else .18)
    transition_sweep(track, scene)


def transition_sweep(track, scene, gain=.16):
    duration = len(track) / RATE
    seconds = min(.48, duration / 2)
    t = np.arange(round(RATE * seconds)) / RATE
    rng = np.random.default_rng(621)
    noise = rng.normal(0, 1, len(t))
    filtered = np.convolve(noise, np.ones(13) / 13, mode="same")
    sweep = (.55 * filtered + .12 * np.sin(2 * np.pi * (410 * t + 800 * t * t)))
    sweep *= np.sin(np.pi * t / seconds) ** 2
    add(track, sweep.astype(np.float32), max(0, duration - seconds - .04), gain, .12)


def scene_audio(scene, offset, layers):
    length = round(scene["duration"] * RATE)
    indices = (np.arange(length) + round(offset * RATE)) % len(layers[0])
    kind = scene["template"]
    theme = kind in ("opening", "outro", "credits", "end")
    track = layers[0][indices].copy() + layers[1][indices] * (1 if theme else .18)
    if kind in ("next", "chapter", "podium_reveal", "news_chapter"):
        track *= .65
        stinger(track, scene)
        target_rms = .10
    else:
        target_rms = .085 if theme else .047
    rms = float(np.sqrt(np.mean(track.astype(np.float64) ** 2)))
    track *= min(target_rms / max(rms, 1e-9), 3)
    peak = float(np.max(np.abs(track)))
    if peak > .60:
        track *= .60 / peak
    fade_in = min(round((.12 if kind == "opening" else .012) * RATE), length // 2)
    fade_out = min(round((1.2 if kind == "end" else .06) * RATE), length // 2)
    track[:fade_in] *= np.linspace(0, 1, fade_in, dtype=np.float32)[:, None]
    track[-fade_out:] *= np.linspace(1, 0, fade_out, dtype=np.float32)[:, None]
    return track


def prepare_audio(program, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if program.get("context", {}).get("audio", {}).get("bgm"):
        return prepare_recorded_audio(program, directory)
    layers = score_layers()
    offset = 0
    report = {"version": VERSION, "sample_rate": RATE, "channels": 2,
              "narration": False, "composition": "original procedural instrumental; no samples or vocals", "scenes": {}}
    for scene in program["scenes"]:
        if scene["template"] in ("ranking", "podium"):
            continue
        if scene["template"] in ("opening", "news_chapter", "outro"):
            offset = 0
        track = scene_audio(scene, offset, layers)
        target = directory / (scene["id"] + ".wav")
        pcm = np.rint(np.clip(track, -1, 1) * 32767).astype("<i2").tobytes()
        with wave.open(str(target), "wb") as output:
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(RATE)
            output.writeframes(pcm)
        report["scenes"][scene["id"]] = {"file": target.name, "samples": len(track),
            "seconds": len(track) / RATE, "peak_dbfs": round(20 * math.log10(max(float(np.max(np.abs(track))), 1e-9)), 2),
            "rms_dbfs": round(20 * math.log10(max(float(np.sqrt(np.mean(track ** 2))), 1e-9)), 2),
            "sha256": hashlib.sha256(pcm).hexdigest()}
        offset += scene["duration"]
    atomic_json(directory / "audio-manifest.json", report)
    return report


def configure_bgm(program, document):
    if document.get("schema") != "ai-girl-weekly/bgm-v1":
        raise ValueError("未知配乐配置格式")
    for key in ("title", "artist", "source_url", "path", "sha256"):
        if not isinstance(document.get(key), str) or not document[key].strip():
            raise ValueError("配乐缺少本地音源、署名、来源或哈希")
    source = Path(document["path"]).resolve()
    if not source.is_file():
        raise ValueError("配乐本地文件不存在")
    url = urlsplit(document["source_url"])
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise ValueError("配乐须保留有效的原曲 HTTPS 来源")
    if not re.fullmatch(r"[a-f0-9]{64}", document["sha256"]):
        raise ValueError("配乐哈希格式无效")
    with source.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != document["sha256"]:
            raise ValueError("配乐音源与已确认版本不一致")
    gain = document.get("gain_db", -1.5)
    start = document.get("start_seconds", 0)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (gain, start)) or not -30 <= gain <= 0 or start < 0:
        raise ValueError("配乐起点或音量设置无效")
    spec = {key: deepcopy(document[key]) for key in ("title", "artist", "source_url", "path", "sha256")}
    spec.update(gain_db=gain, start_seconds=start)
    program["context"]["audio"].update(cards="recorded-bgm-v1", bgm=spec)
    return program


def prepare_recorded_audio(program, directory):
    from .media import run_ffmpeg
    spec = program["context"]["audio"]["bgm"]
    configure_bgm(program, {"schema": "ai-girl-weekly/bgm-v1", **spec})
    decoded = directory / "bgm-normalized.wav"
    run_ffmpeg(["-i", Path(spec["path"]), "-vn", "-af", "loudnorm=I=-18.5:TP=-4:LRA=11",
                "-ar", RATE, "-ac", 2, "-c:a", "pcm_s16le", decoded], directory/"bgm-decode.log", timeout=180)
    with wave.open(str(decoded), "rb") as source:
        if (source.getframerate(), source.getnchannels(), source.getsampwidth()) != (RATE, 2, 2):
            raise ValueError("配乐解码规格不一致")
        recording = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2").reshape(-1, 2).astype(np.float32)/32768
    if not len(recording) or not np.any(recording):
        raise ValueError("配乐没有有效声音")
    cursor = round(spec["start_seconds"] * RATE)
    if cursor >= len(recording):
        raise ValueError("配乐起点超过音源长度")
    gain = 10 ** (spec["gain_db"] / 20)
    work = {"ranking", "podium"}
    scenes = program["scenes"]
    report = {"version": "recorded-bgm-v1", "sample_rate": RATE, "channels": 2, "narration": False,
              "composition": "external recording; source vocals and pitch preserved", "bgm": deepcopy(spec),
              "decoded_samples": len(recording), "timeline": "continuous across non-work scenes", "scenes": {}}
    for index, scene in enumerate(scenes):
        if scene["template"] in work:
            continue
        length = round(scene["duration"] * RATE)
        begin = cursor
        indices = (np.arange(length) + cursor) % len(recording)
        track = recording[indices].copy() * gain
        if scene["template"] in ("next", "chapter", "podium_reveal"):
            transition_sweep(track, scene, gain=.06)
        previous_music = index > 0 and scenes[index - 1]["template"] not in work
        following_music = index + 1 < len(scenes) and scenes[index + 1]["template"] not in work
        if not previous_music:
            fade = min(round(.12 * RATE), length // 2)
            track[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)[:, None]
        if not following_music:
            fade = min(round((1.2 if scene["template"] == "end" else .12) * RATE), length // 2)
            track[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)[:, None]
        peak = float(np.max(np.abs(track)))
        if peak > .65:
            track *= .65 / peak
        target = directory / (scene["id"] + ".wav")
        pcm = np.rint(np.clip(track, -1, 1) * 32767).astype("<i2").tobytes()
        with wave.open(str(target), "wb") as output:
            output.setnchannels(2); output.setsampwidth(2); output.setframerate(RATE); output.writeframes(pcm)
        report["scenes"][scene["id"]] = {"file": target.name, "samples": length, "seconds": length/RATE,
            "source_start_sample": begin % len(recording), "peak_dbfs": round(20*math.log10(max(float(np.max(np.abs(track))), 1e-9)), 2),
            "sha256": hashlib.sha256(pcm).hexdigest()}
        cursor += length
    atomic_json(directory / "audio-manifest.json", report)
    return report
