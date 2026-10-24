# SPDX-License-Identifier: GPL-3.0-only
"""The existing broadcast renderer, now driven only by explicit local files."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json
import math
import time
from PIL import Image, ImageDraw
from .common import atomic_json, progress
from .program import EXPORT_PROFILE, schedule
from .media import run_ffmpeg
from .audio import prepare_audio
from .segment_cache import work_fingerprint, matches, record


def render_input(program):
    """Approval is administrative and must never change a rendered picture or sound."""
    value = json.loads(json.dumps(program))
    value.pop("publication", None)
    return value

def validate_export(program, media, capture):
    if program.get("export_profile") != EXPORT_PROFILE:
        raise ValueError("审片与发布必须使用同一套正式导出规格")
    if program["context"].get("audio", {}).get("narration") is not False:
        raise ValueError("节目使用文字说明，不启用播报语音")
    if program["context"].get("clip_selection_policy") != "complete-segment-v1":
        raise ValueError("完整段落选段尚未应用，不能用开头片段替代")
    if any(scene["template"] in ("news", "news_chapter") for scene in program["scenes"]):
        raise ValueError("新闻栏目已停用，请重新生成本期编排")
    if capture.get("render_input") != render_input(program):
        raise ValueError("节目内容已改变，先重新捕获同一套正式画面")
    if capture.get("errors") or any(s.get("overflow") for s in capture.get("scenes", [])):
        raise ValueError("画面捕获或文字排版检查未通过")
    if any(s.get("characterDialogue") for s in capture.get("scenes", [])):
        raise ValueError("节目角色仅作插画展示，请移除角色对白与主持身份文案")
    if {s["id"] for s in capture.get("scenes", [])} != {s["id"] for s in program["scenes"]}:
        raise ValueError("节目画面不完整")
    for scene in program["scenes"]:
        if scene["template"] not in ("ranking", "podium"):
            continue
        entry = media.get(scene["row"]["bvid"], {})
        if "path" not in entry or abs(entry.get("start", -1) - scene.get("clip_start", -999)) > .001 or abs(entry.get("seconds", 0) - scene["duration"]) > .05 or entry.get("selection_method") != "complete-segment-v1":
            raise ValueError("原片缺失或与完整选段不一致：" + scene["row"]["bvid"])
        path = Path(entry["path"]).resolve()
        if not path.is_file():
            raise ValueError("无效视频素材路径")

def concatenate_program(out, program):
    """Master directly from PCM scene audio; keep encoded pictures untouched."""
    concat=out/"concat.txt"
    concat.write_text("\n".join(f"file 'segments/{scene['id']}.mov'" for scene in program["scenes"]),encoding="utf-8")
    temporary=out/"program.partial.mp4"
    gain=-.75
    for attempt in range(2):
        run_ffmpeg(["-f","concat","-safe",1,"-i",concat,"-c:v","copy","-af",f"volume={gain:.3f}dB",
                    "-c:a","aac","-b:a",EXPORT_PROFILE["audio_bitrate"],"-movflags","+faststart",temporary],out/"concat.log",timeout=600)
        run_ffmpeg(["-i",temporary,"-vn","-af","loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json","-f","null","-"],out/"master-loudness.log",timeout=300)
        log=(out/"master-loudness.log").read_text("utf-8")
        measured=json.loads(log[log.rfind('{'):log.rfind('}')+1])
        peak=float(measured["input_tp"])
        if not math.isfinite(peak) or not math.isfinite(float(measured["input_i"])):
            raise ValueError("节目声音测量无有效结果")
        if peak<=-1:
            break
        gain+=-1.25-peak
    else:
        raise ValueError("AAC 编码后的音频峰值未达到余量要求")
    run_ffmpeg(["-v","error","-xerror","-i",temporary,"-f","null","-"],out/"full-decode.log",timeout=600)
    target=out/"program.mp4";temporary.replace(target)
    mastering={"version":"pcm-master-v1","gain_db":round(gain,3),"integrated_lufs":float(measured["input_i"]),
               "true_peak_dbtp":peak,"loudness_range_lu":float(measured["input_lra"]),"peak_check_passed":True}
    atomic_json(out/"audio/mastering.json",mastering)
    return target, mastering

def render_program(out, program, media, capture, workers=2):
    out = Path(out)
    schedule(program)
    validate_export(program, media, capture)
    segments = out/"segments"; segments.mkdir(exist_ok=True)
    audio_report = prepare_audio(program, out/"audio")
    cache_file = segments/"work-cache.json"
    cache = json.loads(cache_file.read_text("utf-8")) if cache_file.is_file() else {}
    reused = []
    started = time.monotonic()


    def encode(scene):
        sid=scene["id"];seconds=scene["duration"]
        plate=out/"plates"/(sid+".png"); target=segments/(sid+".mov")
        if not plate.is_file(): raise FileNotFoundError(plate)
        row=scene.get("row")
        fingerprint = work_fingerprint(scene, media, out) if scene["template"] in ("ranking", "podium") else None
        if fingerprint and matches(cache.get(sid), fingerprint, target):
            reused.append(sid)
            progress("reuse", scene=sid, template=scene["template"])
            return target
        common=["-r",30,"-fps_mode","cfr","-c:v","libx264","-preset",EXPORT_PROFILE["preset"],"-crf",EXPORT_PROFILE["crf"],"-pix_fmt","yuv420p","-threads",4,"-c:a","pcm_s16le","-ar",48000,"-ac",2,"-t",seconds,"-video_track_timescale",90000,target]
        if scene["template"] in ("ranking","podium"):
            entry=media.get(row["bvid"],{})
            if "path" not in entry: raise ValueError("原片缺失："+row["bvid"])
            if abs(entry.get("start",-1)-scene["clip_start"])>.001 or abs(entry.get("seconds",0)-seconds)>.05 or entry.get("selection_method")!=scene["selection_method"]:
                raise ValueError("视频素材与本期选段不一致，请重新准备："+row["bvid"])
            clip=Path(entry["path"])
            transparent=out/"plates"/(sid+"-overlay.png")
            with Image.open(plate).convert("RGBA") as image:
                ImageDraw.Draw(image).rectangle((44,184,1443,971),fill=(0,0,0,0))
                image.save(transparent)
            image_filter="scale=1400:788:force_original_aspect_ratio=decrease,pad=1400:788:(ow-iw)/2:(oh-ih)/2:color=0x1b2935,setsar=1"
            if scene["template"]=="podium":
                vf=f"[0:v]fps=30,split=2[small][large];[small]{image_filter}[win];color=c=0xf6f1e2:s=1920x1080:r=30:d={seconds}[bg];[bg][win]overlay=44:184[base];[base][1:v]overlay=0:0[framed];[large]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[full];[full][framed]overlay=0:0:enable='lt(t,7)':shortest=1,format=yuv420p[v]"
            else:
                vf=f"[0:v]fps=30,{image_filter}[win];color=c=0xf6f1e2:s=1920x1080:r=30:d={seconds}[bg];[bg][win]overlay=44:184[base];[base][1:v]overlay=0:0:shortest=1,format=yuv420p[v]"
            af=f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,apad,atrim=duration={seconds},afade=t=in:d=0.08,afade=t=out:st={max(0,seconds-.12)}:d=0.12[a]"
            inputs=["-i",clip,"-loop",1,"-framerate",30,"-i",transparent]
            run_ffmpeg([*inputs,"-filter_complex",vf+";"+af,"-map","[v]","-map","[a]",*common],segments/(sid+".log"),timeout=600)
        else:
            if scene.get("animation"):
                motion=out/"motion"/sid
                fps=scene["animation"]["fps"]
                count=math.ceil(seconds*fps)
                if not all((motion/f"frame-{n:04d}.png").is_file() for n in range(1,count+1)):
                    raise FileNotFoundError("转场动画未完整捕获："+sid)
                inputs=["-framerate",fps,"-i",motion/"frame-%04d.png"]
            else:
                inputs=["-loop",1,"-framerate",30,"-i",plate]
            inputs += ["-i",out/"audio"/(sid+".wav")]
            af=f"[1:a]atrim=duration={seconds},asetpts=PTS-STARTPTS[a]"
            run_ffmpeg([*inputs,"-filter_complex",f"[0:v]format=yuv420p[v];{af}","-map","[v]","-map","[a]",*common],segments/(sid+".log"),timeout=600)
        if fingerprint:
            cache[sid] = record(fingerprint, target)
        progress("encode", scene=sid, template=scene["template"], seconds=seconds)
        return target

    with ThreadPoolExecutor(max_workers=max(1,min(workers,3))) as executor:
        futures=[executor.submit(encode,scene) for scene in program["scenes"]]
        for future in as_completed(futures): future.result()
    atomic_json(cache_file, cache)
    target, mastering=concatenate_program(out, program)
    report = {"profile": EXPORT_PROFILE, "template_version": program["template_version"],
              "duration": program["duration"], "frames": program["total_frames"],
              "scenes": len(program["scenes"]), "works": len(program["context"]["selected"]),
              "full_decode_passed": True, "mastering": mastering,
              "reused_work_segments": len(reused), "encode_wall_seconds": round(time.monotonic()-started, 2)}
    atomic_json(out / "production.json", report)
    return report
