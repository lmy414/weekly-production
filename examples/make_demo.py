# SPDX-License-Identifier: GPL-3.0-only
"""Generate redistributable fictional episode and character packs from code."""
from pathlib import Path
from functools import lru_cache
import argparse
import json
import math
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/weekly-production/scripts"))
from weekly_runtime.media import ffmpeg_path

INK = "#263c4d"
PAPER = "#f7f2df"
MINT = "#bce0d2"
CORAL = "#f89b86"
BLUE = "#789ac8"
FONT = ROOT / "skills/weekly-production/assets/ui/fonts/noto-sans-sc/NotoSansSC-variable.ttf"
HOME = "https://github.com/lmy414/weekly-production"
TITLES = ["像素城市的夜行电台", "月面邮差，今天也准时", "把雨声调成一段旋律", "给明天寄一封信", "一颗星星的下班时间"]


@lru_cache(maxsize=20)
def font(size):
    return ImageFont.truetype(str(FONT), size)


@lru_cache(maxsize=12)
def mascot(pose="default", frame=0):
    """An original geometric pixel messenger; no reference artwork is used."""
    im = Image.new("RGBA", (180, 244))
    d = ImageDraw.Draw(im)
    # Hair, headphones, jacket and boots use an intentionally limited palette.
    d.polygon([(51, 52), (63, 31), (115, 31), (133, 53), (138, 139), (119, 165), (48, 156), (42, 93)], fill=INK)
    d.polygon([(54, 54), (66, 36), (112, 36), (126, 55), (132, 143), (113, 153), (49, 148), (47, 91)], fill=BLUE)
    d.rectangle((52, 76, 127, 102), fill=INK)
    d.rectangle((57, 70, 122, 112), fill="#ffe0c4")
    d.rectangle((66, 101, 114, 126), fill="#ffe0c4")
    d.polygon([(56, 62), (72, 44), (110, 46), (123, 64), (107, 83), (98, 65), (82, 86), (74, 65), (58, 90)], fill=BLUE)
    d.rectangle((68, 86, 75, 94), fill=INK)
    if pose in {"champion", "applause", "goodbye"}:
        d.line((103, 90, 112, 90), fill=INK, width=3)
    else:
        d.rectangle((105, 86, 112, 94), fill=INK)
    d.rectangle((69, 86, 72, 88), fill=PAPER)
    d.rectangle((106, 86, 109, 88), fill=PAPER)
    d.rectangle((60, 99, 72, 103), fill=CORAL)
    d.rectangle((108, 99, 120, 103), fill=CORAL)
    d.line((85, 109, 94, 109), fill=INK, width=2)
    d.rectangle((46, 68, 53, 96), fill=INK)
    d.rectangle((128, 68, 135, 96), fill=INK)
    d.rectangle((47, 72, 51, 90), fill=CORAL)
    d.rectangle((130, 72, 134, 90), fill=CORAL)
    d.line((51, 66, 58, 40, 120, 40, 131, 65), fill=INK, width=4)
    d.rectangle((79, 123, 101, 137), fill="#ffe0c4")
    d.polygon([(63, 130), (80, 126), (91, 144), (102, 127), (119, 134), (126, 190), (54, 190)], fill=INK)
    d.polygon([(66, 133), (80, 132), (90, 149), (104, 132), (116, 137), (121, 185), (58, 185)], fill=MINT)
    d.polygon([(82, 133), (98, 133), (90, 149)], fill=PAPER)
    d.rectangle((84, 148, 97, 160), fill=CORAL)
    d.rectangle((62, 174, 119, 181), fill=PAPER)
    d.rectangle((91, 169, 114, 185), fill=INK)
    d.rectangle((94, 171, 111, 181), fill=CORAL)
    d.polygon([(59, 188), (121, 188), (131, 206), (50, 206)], fill=INK)
    d.rectangle((62, 206, 79, 228), fill="#ffe0c4")
    d.rectangle((99, 206, 116, 228), fill="#ffe0c4")
    d.rectangle((59, 224, 80, 236), fill=INK)
    d.rectangle((98, 224, 119, 236), fill=INK)
    raised = pose in {"welcome", "transition", "champion", "applause", "goodbye"}
    if raised:
        d.line((65, 137, 45, 152, 25, 123), fill=INK, width=17)
        d.line((65, 137, 45, 152, 25, 123), fill=MINT, width=11)
        d.rectangle((15, 103, 33, 125), fill=INK)
        d.rectangle((18, 104, 30, 121), fill="#ffe0c4")
        d.rectangle((19, 96, 23, 111), fill="#ffe0c4")
        d.rectangle((27, 98, 31, 111), fill="#ffe0c4")
    else:
        d.line((65, 137, 47, 167, 44, 187), fill=INK, width=17)
        d.line((65, 137, 47, 167, 44, 183), fill=MINT, width=11)
        d.rectangle((37, 181, 49, 195), fill="#ffe0c4")
    d.line((118, 140, 135, 170, 126, 184), fill=INK, width=17)
    d.line((118, 140, 135, 170, 126, 181), fill=MINT, width=11)
    d.rectangle((120, 179, 133, 192), fill="#ffe0c4")
    if pose == "champion":
        d.polygon([(66, 27), (62, 12), (77, 20), (90, 7), (103, 20), (118, 12), (113, 27)], fill="#f5cf73", outline=INK)
    return im.resize((540, 732), Image.Resampling.NEAREST)


def music(path, seconds=32, variant=0):
    rate = 48000
    t = np.arange(round(seconds * rate)) / rate
    output = np.zeros(len(t))
    notes = [72, 76, 79, 83, 81, 79, 76, 74, 72, 76, 79, 86, 84, 83, 79, 76]
    beat = .375
    for n in range(math.ceil(seconds / beat)):
        start, end = round(n * beat * rate), min(len(t), round((n + 1) * beat * rate))
        local = np.arange(end - start) / rate
        hz = 440 * 2 ** ((notes[(n + variant * 3) % len(notes)] - 69) / 12)
        env = np.minimum(1, local / .012) * np.maximum(0, 1 - local / beat) ** 1.7
        lead = np.sin(2 * np.pi * hz * local) + .22 * np.sin(4 * np.pi * hz * local)
        bass_hz = 130.8128 * 2 ** ([0, -3, -5, -7][(n // 4) % 4] / 12)
        bass = np.sin(2 * np.pi * bass_hz * local) * np.exp(-local * 5)
        output[start:end] += (.13 * lead * env + .07 * bass)
    fade = np.minimum(1, t / .1) * np.minimum(1, np.maximum(0, seconds - t) / .2)
    output *= fade
    stereo = np.column_stack((output, output * .96))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2); handle.setsampwidth(2); handle.setframerate(rate)
        handle.writeframes(np.rint(stereo * 32767).astype("<i2").tobytes())


def source_frame(index, number, seconds=12):
    time = number / 30
    palette = [("#253c50", "#a8d6d0"), ("#27334f", "#d3c8ed"), ("#224d52", "#c2dfcc"), ("#516584", "#ffe4bd"), ("#2e3450", "#f0cfa1")]
    bg, accent = palette[index]
    im = Image.new("RGB", (960, 540), bg)
    d = ImageDraw.Draw(im)
    for n in range(35):
        x, y = (n * 137 + index * 47) % 960, (n * 73 + index * 17) % 350
        size = 2 if (n + int(time * 2)) % 3 else 4
        d.rectangle((x, y, x + size, y + size), fill=accent)
    d.ellipse((650, 45, 810, 205), fill=accent)
    d.ellipse((670, 35, 820, 185), fill=bg)
    offset = int(time * 11) % 110
    for n in range(-1, 10):
        x = n * 110 - offset
        height = 50 + ((n + index * 3) * 37 % 160)
        d.rectangle((x, 430 - height, x + 87, 500), fill="#344f67")
        for wx in range(x + 13, x + 75, 23):
            for wy in range(440 - height, 450, 27):
                d.rectangle((wx, wy, wx + 9, wy + 10), fill=accent if (wx + wy) % 4 else CORAL)
    d.rectangle((0, 465, 960, 540), fill="#1b2e41")
    for x in range(0, 960, 80):
        d.rectangle((x - int(time * 35) % 80, 498, x + 42 - int(time * 35) % 80, 501), fill=accent)
    avatar = mascot("welcome" if int(time / 3) % 2 else "default").resize((270, 366), Image.Resampling.NEAREST)
    im.paste(avatar, (90 + int(7 * math.sin(time * 3)), 145 + int(4 * math.sin(time * 4))), avatar)
    d = ImageDraw.Draw(im)
    d.rectangle((33, 28, 273, 64), fill=accent)
    d.text((46, 31), "FICTIONAL / DEMO 0" + str(index + 1), font=font(20), fill=bg)
    d.text((390, 225), ["夜行电台", "月面来信", "雨声采样", "明日邮局", "星星下班了"][index], font=font(55), fill=PAPER)
    lines = ["晚安，城市。", "把问候寄到月亮。", "听，雨落下的节拍。", "给明天留一点期待。", "今天的光，也送到了。"]
    d.text((395, 312), lines[index], font=font(25), fill=accent)
    d.rectangle((393, 365, 862, 369), fill="#55748b")
    d.rectangle((393, 365, 393 + int(469 * time / seconds), 369), fill=CORAL)
    d.text((395, 391), "程序生成画面与声音 · 无真实作品数据", font=font(17), fill=accent)
    return im


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")


def generate(directory):
    directory = directory.expanduser().resolve()
    if directory.exists():
        raise FileExistsError("请选择尚不存在的示例目录：" + str(directory))
    episode, character = directory / "episode", directory / "character"
    videos, images, audio = episode / "videos", character / "images", episode / "audio"
    for path in (videos, images, audio): path.mkdir(parents=True)
    roles = {"default": "default", "welcome": "welcome", "transition": "transition", "champion": "champion", "applause": "applause", "goodbye": "goodbye"}
    for role in roles:
        mascot(role).save(images / (role + ".png"))
    write_json(character / "character.json", {"schema": "weekly-production/character-v1", "id": "pixel-messenger", "name": "像素信使（合成示例）", "images": {k: "images/" + v + ".png" for k, v in roles.items()}})
    music(audio / "pixel-post.wav")
    works = []
    for index, title in enumerate(TITLES):
        soundtrack = audio / f"work-{index + 1}.wav"
        music(soundtrack, 12, index + 1)
        path = videos / f"demo-{index + 1}.mp4"
        command = [ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-nostdin", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "960x540", "-r", "30", "-i", "pipe:0", "-i", str(soundtrack), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-ar", "48000", "-t", "12", "-movflags", "+faststart", str(path)]
        with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL) as process:
            for number in range(360): process.stdin.write(source_frame(index, number).tobytes())
            process.stdin.close()
            if process.wait(): raise RuntimeError("示例视频编码失败")
        works.append({"bvid": "BV" + str(index + 1) * 10, "title": title, "short_title": title, "author": "合成示例工作室", "source_url": HOME + "/tree/main/examples", "published_at": f"2026-10-{index + 2:02d}T12:00:00+08:00", "observed_at": "2026-10-25T00:00:00+08:00", "part_count": 1, "metrics": {"view": 30000 + index * 17000, "reply": 60 + index * 30, "danmaku": 100 + index * 40, "favorite": 500 + index * 180, "coin": 300 + index * 100, "like": 1000 + index * 500, "share": 100 + index * 40}, "video": "videos/" + path.name, "clip": {"start": 0, "end": 12, "summary": "完整播放程序生成的 12 秒短片。"}})
        print(json.dumps({"generated": path.name}, ensure_ascii=False), file=sys.stderr, flush=True)
    write_json(episode / "episode.json", {"schema": "weekly-production/episode-v1", "id": "demo-001", "title": "像素信使 · 虚构节目演示", "period": {"begin": "2026-09-27T00:00:00+08:00", "end": "2026-10-25T00:00:00+08:00", "timezone": "Asia/Shanghai"}, "metric_basis": "cumulative", "works": works, "copy": {"opening_kicker": "像素信使 · 合成示例", "opening_subtitle": "5 部虚构短片，一起开播", "opening_tagline": "把素材放进来，让周刊动起来。", "opening_note": "演示画面、音源与数据均由程序生成", "statistics_text": "换上你的作品、文案与配乐，制作下一期周刊。", "outro_text": "这一期，准时送达。", "end_text": "下期见。"}, "music": {"file": "audio/pixel-post.wav", "title": "Pixel Post", "artist": "Weekly Production 合成示例", "source_url": HOME + "/blob/main/examples/make_demo.py"}, "branding": {"producer": "Weekly Production", "website_name": "项目主页", "website_url": HOME, "update_schedule": "每周六晚 22:00 更新（北京时间）"}})
    (directory / "README.txt").write_text("这是 Weekly Production 的合成示例。作品、BV 标识、作者、统计数据、角色、画面和音乐均为虚构，由 examples/make_demo.py 生成。示例 BV 标识不指向真实投稿。仅用于演示和测试。示例内容按 GPL-3.0-only 分发，字体保留其原许可。\n", "utf-8")
    return {"episode": str(episode / "episode.json"), "character": str(character / "character.json")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("demo"))
    print(json.dumps(generate(parser.parse_args().directory), ensure_ascii=False))
