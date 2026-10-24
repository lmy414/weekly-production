# SPDX-License-Identifier: GPL-3.0-only
from copy import deepcopy
import re
from .common import local_time
from .inputs import ROLES
from .scoring import ALGORITHM
HOST_ASSETS = {role: None for role in ROLES}


MOTION_TEMPLATES = {"chapter", "next", "podium_reveal"}

TEMPLATE_VERSION = "pixel-studio-v9"

UPDATE_SCHEDULE = "每周六晚 22:00 更新（北京时间）"

EXPORT_PROFILE = {"id": "broadcast-1080p-v1", "width": 1920, "height": 1080,
                  "fps": 30, "crf": 18, "preset": "veryfast", "audio_rate": 48000,
                  "audio_channels": 2, "audio_bitrate": "256k"}

TEMPLATES = [
    ("cover", "本期封面", "封面图，不计入视频时间"),
    ("opening", "片头开场", "固定"),
    ("rundown", "开场榜单", "固定"),
    ("scope", "收录范围与统计区间", "固定"),
    ("scoring", "综合计分公式", "固定"),
    ("scoring_details", "得分与同分排序", "固定"),
    ("chapter", "主榜栏目卡", "需要栏目引导时启用"),
    ("ranking", "普通榜单作品窗", "固定"),
    ("next", "下一名短转场", "固定"),
    ("pickup", "PICK UP 推荐", "可选，创刊期关闭"),
    ("podium_reveal", "前三名揭晓", "固定"),
    ("podium", "前三名数据与连续全屏", "固定"),
    ("summary", "本期主榜回看", "固定"),
    ("statistics", "下期作品征集", "固定"),
    ("subrank", "副榜列表", "可选，创刊期关闭"),
    ("history", "历史回顾", "可选，创刊期关闭"),
    ("correction", "勘误与规则变更", "发生变更时启用"),
    ("outro", "片尾", "固定"),
    ("credits", "作者出处与制作署名", "固定"),
    ("end", "结束卡", "固定"),
]

def make_program(manifest, selected):
    if manifest["rule"]["id"] != ALGORITHM:
        raise ValueError("新节目模板必须使用公开的综合计分规则")
    if not selected:
        raise ValueError("没有可用于节目的作品")
    selected = deepcopy(selected)
    selected.sort(key=lambda row: (-row["score"], row["bvid"]))
    for rank, row in enumerate(selected, 1):
        row["rank"] = rank
    captures = [row["captured_at"] for row in selected if row.get("captured_at")]
    context = {
        "episode_id": manifest["episode_id"], "title": manifest["title"],
        "kind": manifest["kind"], "host": "",
        "begin": local_time(manifest["begin_ts"]), "end": local_time(manifest["end_ts"]),
        "capture_begin": local_time(min(captures)), "capture_end": local_time(max(captures)),
        "rule": manifest["rule"], "coverage": manifest["coverage"],
        "selected": selected, "rank_count": len(selected),
        "window_days": (manifest["end_ts"]-manifest["begin_ts"])/86400,
        "issue_number": (re.search(r"(\d+)$",manifest["episode_id"]) or ["","001"])[1],
        "audio": {"narration": False, "works": "original", "cards": "whale-studio-score-v1"},
        "host_asset_pack": "",
        "copy_version": "broadcast-copy-v5", "work_copy": {}, "news_copy": {},
        "update_schedule": UPDATE_SCHEDULE,
        "inclusion_rule": "AI模型与助手的拟人角色二创；剧情、动画、漫画、翻唱、整活均可，制作方式不限。",
    }
    scenes = []

    def add(template, seconds, title, host_art="transition", **payload):
        if host_art not in HOST_ASSETS:
            raise ValueError("未知主持素材：" + host_art)
        scene = {"id": f"s{len(scenes)+1:03d}", "template": template, "duration": seconds,
                 "title": title, "host_art": host_art, **payload}
        if template in MOTION_TEMPLATES:
            scene["animation"] = {"version": "pixel-stinger-v1", "fps": 15}
        scenes.append(scene)

    add("opening", 4, "创刊特辑开场" if manifest["kind"]=="cumulative" else "本周节目开场", host_art="welcome")
    add("rundown", 7, "本期榜单", host_art="welcome")
    for row in reversed([row for row in selected if row["rank"] > 3]):
        add("ranking", min(20, row["duration"]), f"第 {row['rank']} 名", row=row,
            host_art=("watching", "applause", "surprise", "thinking")[row["rank"] % 4],
            selection_method="unselected")
        next_rank = row["rank"] - 1
        if next_rank > 3:
            add("next", 1.2, f"下一位：第 {next_rank} 名", next_rank=next_rank,
                host_art=("transition", "scope", "surprise", "applause")[next_rank % 4])
    for row in reversed(selected[:3]):
        podium_art={3:"top3", 2:"top2", 1:"champion"}[row["rank"]]
        add("podium_reveal", 5, f"揭晓第 {row['rank']} 名", row=row, host_art=podium_art)
        add("podium", min(25, row["duration"]), f"前三名作品：第 {row['rank']} 名", row=row,
            host_art=podium_art,
            data_seconds=7, selection_method="unselected")
    add("summary", 12, "本期主榜回看")
    add("scope", 6, "收录规则", host_art="scope", page="inclusion")
    add("scope", 3, "本期统计区间", host_art="scope", page="period")
    add("scoring", 5, "综合计分公式", host_art="score", page="formula")
    add("scoring", 7, "五项修正系数", host_art="score", page="coefficients")
    add("scoring_details", 3, "得分与同分排序", host_art="thinking")
    add("statistics", 10, "下期想看谁？", host_art="scope")
    add("outro", 10, "片尾", host_art="applause")
    add("credits", 10, "出处与署名")
    add("end", 6, "下期再见", host_art="goodbye")
    program = {"schema": "ai-girl-weekly/program-v1", "template_version": TEMPLATE_VERSION,
               "export_profile": deepcopy(EXPORT_PROFILE),
               "canvas": {"width": 1920, "height": 1080, "fps": 30}, "context": context,
               "catalogue": [{"id": k, "title": title, "usage": usage} for k, title, usage in TEMPLATES],
               "disabled_in_inaugural": ["pickup", "subrank", "history", "correction"],
               "scenes": scenes,
               "publication": {"approved": bool(manifest.get("approved")),
                               "manifest_revision": manifest.get("revision"),
                               "state": "frozen" if manifest.get("approved") else "awaiting_human_review"}}
    schedule(program)
    return program

def schedule(program):
    cursor = 0
    fps = program["canvas"]["fps"]
    for scene in program["scenes"]:
        scene["frames"] = round(scene["duration"] * fps)
        scene["duration"] = scene["frames"] / fps
        scene["start"] = cursor / fps
        cursor += scene["frames"]
        scene["end"] = cursor / fps
    program["total_frames"] = cursor
    program["duration"] = cursor / fps
    return program
