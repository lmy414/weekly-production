# SPDX-License-Identifier: GPL-3.0-only
from .audio import configure_bgm
from .program import make_program, schedule
from .scoring import rule_info


def assemble(bundle):
    manifest = {"episode_id": bundle["id"], "title": bundle["title"], "kind": bundle["kind"],
                "begin_ts": bundle["begin"], "end_ts": bundle["end"], "rule": rule_info(),
                "coverage": {"videos": len(bundle["rows"]), "source": "provided-input"}}
    program = make_program(manifest, bundle["rows"])
    context = program["context"]
    context.update(host=bundle["character"]["name"], host_asset_pack=bundle["character"]["id"],
                   copy=bundle["copy"], branding=bundle["branding"], clip_selection_policy="complete-segment-v1")
    context["work_copy"] = {row["bvid"]: {"short_title": row["short_title"]} for row in bundle["rows"] if "short_title" in row}
    context["update_schedule"] = bundle["branding"].get("update_schedule", context["update_schedule"])
    configure_bgm(program, bundle["bgm"])
    for scene in program["scenes"]:
        if scene["template"] not in ("ranking", "podium"):
            continue
        source = bundle["sources"][scene["row"]["bvid"]]
        clip = source["clip"]
        scene.update(clip_start=clip["start"], duration=clip["end"] - clip["start"],
                     selection_method="complete-segment-v1",
                     clip_selection={"start": clip["start"], "end": clip["end"], "source_duration": source["info"]["duration"],
                                     "summary": clip.get("summary", "由输入指定的连续段落"), "human_approved": False})
    return schedule(program)
