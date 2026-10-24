# SPDX-License-Identifier: GPL-3.0-only
"""Two private input packs in, one broadcast MP4 out."""
from pathlib import Path
import argparse
import json
import sys

from weekly_runtime import VERSION
from weekly_runtime.common import InputError, atomic_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="检查本机制作运行环境")
    doctor.add_argument("--json", action="store_true")
    verify = commands.add_parser("verify", help="核对已有成品及绑定输入")
    verify.add_argument("--output", required=True, type=Path)
    verify.add_argument("--json", action="store_true")
    for name in ("validate", "plan", "analyze", "build"):
        sub = commands.add_parser(name)
        sub.add_argument("--episode", required=True, type=Path)
        sub.add_argument("--character", required=True, type=Path)
        sub.add_argument("--output", type=Path, required=name in ("build", "plan"))
        sub.add_argument("--json", action="store_true")
        if name == "build":
            sub.add_argument("--workers", type=int, choices=(1, 2, 3), default=2)
        if name == "analyze":
            sub.add_argument("--asr", action="store_true", help="使用已缓存的本地 Whisper small 模型")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            from weekly_runtime.media import runtime
            result = {"ok": True, "version": VERSION, "runtime": runtime()}
        elif args.command == "build":
            from weekly_runtime.pipeline import build
            result = build(args.episode, args.character, args.output, args.workers)
        elif args.command == "verify":
            from weekly_runtime.pipeline import verify_output
            result = verify_output(args.output)
        else:
            from weekly_runtime.inputs import load_inputs
            bundle = load_inputs(args.episode, args.character, require_clips=args.command == "plan")
            if args.command == "validate":
                result = {"ok": True, "ready": not bundle["missing"], "works": len(bundle["rows"]), "missing": bundle["missing"]}
            elif args.command == "analyze":
                from weekly_runtime.analysis import analyze
                result = analyze(bundle, args.asr)
            else:
                from weekly_runtime.pipeline import build_lock, plan, work_directory
                _, out = work_directory(args.output)
                with build_lock(out):
                    program = plan(bundle, out)
                result = {"ok": True, "program": str(out / "program.json"), "duration": program["duration"],
                          "frames": program["total_frames"], "scenes": len(program["scenes"])}
        print(json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)
        return 0
    except KeyboardInterrupt:
        print(json.dumps({"ok": False, "error": "interrupted"}), file=sys.stderr)
        return 130
    except Exception as exc:
        result = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
        if isinstance(exc, InputError):
            result["field"] = exc.field
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 2 if isinstance(exc, InputError) else 1


if __name__ == "__main__":
    raise SystemExit(main())
