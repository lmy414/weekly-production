# SPDX-License-Identifier: GPL-3.0-only
"""Static pages built from a deliberately small public content model."""
from pathlib import Path, PurePosixPath
from html import escape
import json
import re
import shutil

from weekly_runtime.common import SKILL, digest, file_hash, atomic_json, InputError
from .settings import address
from .views import layout, issue_body, archive, rules

ISSUE_FIELDS = {"id", "number", "title", "label", "date", "published_at", "updated_at", "metric_basis",
                "basis_label", "period_label", "period_begin", "period_end", "deck", "intro", "authors",
                "cover", "host", "share", "works", "observed_label"}
WORK_FIELDS = {"bvid", "rank", "score", "title", "short_title", "author", "source_url", "published_date",
               "observed_at", "part_count", "metrics", "category", "summary", "cover", "share", "timestamp"}
METRICS = {"view", "reply", "danmaku", "favorite", "coin", "like", "share"}


def asset_refs(issue):
    refs = [issue[k] for k in ("cover", "host", "share")]
    refs += [w[k] for w in issue["works"] for k in ("cover", "share")]
    for ref in refs:
        path = PurePosixPath(ref)
        if (not ref.startswith("/assets/issues/" + issue["id"] + "/") or "\\" in ref
                or ".." in path.parts or len(path.parts) != 5 or path.suffix not in (".png", ".jpg", ".webp")):
            raise InputError("web.assets", "无效的公开图片路径")
    return refs


def assert_issue(issue):
    if set(issue) != ISSUE_FIELDS or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", issue["id"]):
        raise InputError("web.issue", "无效期号或包含内部字段")
    works = issue["works"]
    if not works or [w["rank"] for w in works] != list(range(1, len(works) + 1)):
        raise InputError("web.works", "名次须连续")
    if len({w["bvid"] for w in works}) != len(works):
        raise InputError("web.works", "BV 号重复")
    for w in works:
        if set(w) != WORK_FIELDS or not re.fullmatch(r"BV[A-Za-z0-9]{10}", w["bvid"]):
            raise InputError("web.work", "作品包含内部字段或无效 BV 号")
        address(w["source_url"], "web.source_url")
        if w["category"] not in ("剧情", "音乐", "整活", "动画", "其他") or not w["summary"]:
            raise InputError("web.summary", "需要公开介绍与作品类型")
        if set(w["metrics"]) != METRICS:
            raise InputError("web.metrics", "缺少公开指标")
        values = [w["score"], *w["metrics"].values()]
        if any(type(v) is not int or v < 0 for v in values) or type(w["part_count"]) is not int or w["part_count"] < 1:
            raise InputError("web.metrics", "指标和得分须为非负整数，分 P 数须为正整数")
    asset_refs(issue)


def verify(output):
    output = Path(output).resolve()
    missing = []
    for page in output.rglob("*.html"):
        text = page.read_text("utf-8")
        for ref in re.findall(r'(?:href|src)="([^"#]+)', text):
            if not ref.startswith("/") or ref.startswith("//"):
                continue
            target = output / ref.split("?")[0].split("#")[0].lstrip("/")
            if target.is_dir():
                target /= "index.html"
            if not target.is_file():
                missing.append(ref)
        if any(marker in text for marker in ("episode.lock.json", "human_approved", "source_duration", "SESSDATA", "api_key", "C:\\Users\\", "E:\\")):
            raise InputError("web.privacy", "页面含内部字段或本机路径")
    if missing:
        raise InputError("web.assets", "缺少静态资源：" + ", ".join(sorted(set(missing))))
    return {"html_pages": len(list(output.rglob("*.html"))), "missing_assets": 0}


def build_pages(output, issues, rule, settings, media):
    output = Path(output)
    issues = sorted(issues, key=lambda i: (i["published_at"], i["id"]), reverse=True)
    allowed = {}
    for issue in issues:
        assert_issue(issue)
        for ref in asset_refs(issue):
            source = Path(media) / ref.removeprefix("/assets/issues/")
            if not source.is_file() or source.is_symlink():
                raise InputError("web.assets", "缺少公开图片")
            target = output / ref.lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            allowed[ref] = file_hash(source)
    assets = output / "assets"
    for name in ("site.css", "app.js", "favicon.svg"):
        shutil.copy2(SKILL / "assets/web" / name, assets / name)
    fonts = assets / "fonts"
    fonts.mkdir()
    for name in ("fusion-pixel-12px.woff2", "OFL.txt"):
        shutil.copy2(SKILL / "assets/ui/fonts" / name, fonts / ("pixel.woff2" if name.endswith("woff2") else name))
    shutil.copytree(SKILL / "assets/ui/fonts/LICENSES", fonts / "LICENSES")
    shutil.copy2(output / issues[0]["cover"].lstrip("/"), assets / "site-og.jpg")
    revision = digest({"issues": issues, "images": allowed, "settings": settings.public(),
                       "code": {p.relative_to(SKILL).as_posix(): file_hash(p) for folder in (SKILL / "scripts/weekly_web", SKILL / "assets/web")
                                for p in sorted(folder.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}})[:14]
    def page(title, body, **kwargs):
        return layout(title, body, revision=revision, site=settings, **kwargs)
    pages = {"/": page(issues[0]["title"], issue_body(issues[0], settings), image=issues[0]["cover"]),
             "/issues/": page("往期档案", archive(issues), path="/issues/", active="archive"),
             "/rules/": page("收录与计分规则", rules(rule), path="/rules/", active="rules")}
    for issue in issues:
        url = "/issues/" + issue["id"] + "/"
        pages[url] = page(issue["title"], issue_body(issue, settings), path=url, image=issue["cover"], description=issue["deck"])
    for url, html in pages.items():
        target = output / url.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, "utf-8")
    (output / "404.html").write_text(page("页面没有找到", '<section class="page-heading"><h1>这一页还没开播。</h1><p><a href="/">回到本期周刊</a></p></section>'), "utf-8")
    robots = "User-agent: *\nAllow: /\n"
    if settings.site_url:
        robots += "Sitemap: " + settings.site_url + "/sitemap.xml\n"
        xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        xml += "".join("<url><loc>" + escape(settings.site_url + url) + "</loc></url>" for url in pages) + "</urlset>"
        (output / "sitemap.xml").write_text(xml, "utf-8")
    (output / "robots.txt").write_text(robots, "utf-8")
    # This is a whitelist of display content for future archive updates, never raw episode inputs.
    atomic_json(output / "export-manifest.json", {"schema": "weekly-production/web-v1", "issues": issues})
    report = {"schema": "weekly-production/web-build-v1", "revision": revision, "issues": [i["id"] for i in issues],
              "works": sum(len(i["works"]) for i in issues), "pages": len(pages), "qr_enabled": settings.qr_enabled}
    atomic_json(output / "build-info.json", report)
    return {**report, **verify(output)}
