# SPDX-License-Identifier: GPL-3.0-only
"""Build a weekly MP4; optionally export its static pages and share images."""
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
    for name in ("validate", "plan", "analyze", "build", "export"):
        sub = commands.add_parser(name)
        sub.add_argument("--episode", required=True, type=Path)
        sub.add_argument("--character", required=True, type=Path)
        sub.add_argument("--output", type=Path, required=name in ("build", "plan", "export"))
        sub.add_argument("--json", action="store_true")
        if name == "build":
            sub.add_argument("--workers", type=int, choices=(1, 2, 3), default=2)
            sub.add_argument("--web-output", type=Path, help="成片通过检查后，同时生成文字网页与 PNG 分享图")
        if name == "export":
            sub.add_argument("--directory", required=True, type=Path, help="静态网页与分享图目录")
        if name in ("build", "export"):
            sub.add_argument("--web-config", type=Path, help="可复用的网站与二维码设置")
            sub.add_argument("--editorial", type=Path, help="独立的公开介绍，不修改已锁定成片输入")
            sub.add_argument("--site-url", help="自己的网站根地址，不会自动启用二维码")
            qr = sub.add_mutually_exclusive_group()
            qr.add_argument("--qr", dest="qr_enabled", action="store_true", default=None, help="启用二维码，须自行配置链接源")
            qr.add_argument("--no-qr", dest="qr_enabled", action="store_false", help="关闭二维码，覆盖配置文件")
            sub.add_argument("--qr-source", choices=("website", "original", "custom"), help="默认 website，跳转本期网站")
            sub.add_argument("--qr-url", help="custom 模式的链接模板，支持 {issue_id} 与 {bvid}")
        if name == "analyze":
            sub.add_argument("--asr", action="store_true", help="使用已缓存的本地 Whisper small 模型")
    args = parser.parse_args(argv)
    try:
        web_settings = None
        if args.command in ("build", "export"):
            from weekly_web.settings import load_settings
            web_options = (args.web_config, args.editorial, args.site_url, args.qr_enabled, args.qr_source, args.qr_url)
            if args.command == "build" and not args.web_output and any(v is not None for v in web_options):
                raise InputError("web-output", "使用网页或二维码设置时，请同时指定 --web-output")
            web_settings = load_settings(args.web_config, site_url=args.site_url, qr_enabled=args.qr_enabled,
                                         qr_source=args.qr_source, qr_url=args.qr_url)
        if args.command == "doctor":
            from weekly_runtime.media import runtime
            result = {"ok": True, "version": VERSION, "runtime": runtime()}
        elif args.command == "build":
            from weekly_runtime.pipeline import build
            result = build(args.episode, args.character, args.output, args.workers)
            if args.web_output:
                from weekly_web.exporter import export_site
                try:
                    result["web"] = export_site(args.episode, args.character, args.output, args.web_output, web_settings, args.editorial)
                except Exception as exc:
                    result["web"] = {"ok": False, "error": str(exc)}
                    result["ok"] = False
                    print(json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)
                    return 2 if isinstance(exc, InputError) else 1
        elif args.command == "export":
            from weekly_web.exporter import export_site
            result = export_site(args.episode, args.character, args.output, args.directory, web_settings, args.editorial)
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
