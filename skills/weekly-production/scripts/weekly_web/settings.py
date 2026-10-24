# SPDX-License-Identifier: GPL-3.0-only
"""Explicit publishing addresses; no account or operator defaults."""
from dataclasses import dataclass, asdict
from urllib.parse import urlsplit, urlunsplit
from string import Formatter

from weekly_runtime.common import InputError, read_json


def address(value, field, *, origin=False):
    if not isinstance(value, str) or not value.strip():
        raise InputError(field, "需要自己配置 HTTP(S) 链接")
    if any(c.isspace() or ord(c) < 32 for c in value):
        raise InputError(field, "链接不能包含空白或控制字符")
    try:
        parts = urlsplit(value)
        port = parts.port
        if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
            raise ValueError()
        host = parts.hostname.encode("idna").decode("ascii")
        if ":" in host:
            host = "[" + host + "]"
        if port:
            host += ":" + str(port)
        if origin and (parts.path not in ("", "/") or parts.query or parts.fragment):
            raise ValueError()
    except (ValueError, UnicodeError) as exc:
        raise InputError(field, "需要无账号凭据的 HTTP(S) 地址；网站地址须为独立域名根路径") from exc
    return urlunsplit((parts.scheme, host, "" if origin else parts.path, parts.query, parts.fragment))


def template(value, field):
    if not isinstance(value, str):
        raise InputError(field, "需要链接模板字符串")
    try:
        for _, name, spec, conversion in Formatter().parse(value):
            if name is not None and (name not in ("issue_id", "bvid") or spec or conversion):
                raise ValueError()
        rendered = value.format(issue_id="synthetic-001", bvid="BV1111111111")
    except (ValueError, KeyError, AttributeError, IndexError) as exc:
        raise InputError(field, "链接模板只支持 {issue_id} 与 {bvid}") from exc
    address(rendered, field)
    return value


@dataclass(frozen=True)
class Settings:
    site_url: str = ""
    site_name: str = "AI 娘周刊"
    main_url: str = ""
    main_name: str = "主站"
    schedule: str = "每周六 22:00 · 北京时间"
    qr_enabled: bool = False
    qr_source: str = "website"
    qr_url: str = ""

    def public(self):
        return asdict(self)

    def issue_url(self, issue_id):
        if not self.site_url:
            return ""
        return self.site_url + "/issues/" + issue_id + "/"

    def qr_target(self, issue, work=None):
        if not self.qr_enabled:
            return None
        if self.qr_source == "original" and work:
            return address(work["source_url"], "source_url")
        if self.qr_source == "custom":
            return address(self.qr_url.format(issue_id=issue["id"], bvid=work["bvid"] if work else ""), "qr.url")
        url = self.issue_url(issue["id"])
        return url + ("#work-" + work["bvid"] if work else "")


def load_settings(path=None, *, site_url=None, qr_enabled=None, qr_source=None, qr_url=None):
    raw = read_json(path) if path else {}
    if set(raw) - {"site_url", "site_name", "main_url", "main_name", "schedule", "qr"}:
        raise InputError("web-config", "包含未知配置项")
    qr = raw.pop("qr", {})
    if not isinstance(qr, dict) or set(qr) - {"enabled", "source", "url"}:
        raise InputError("qr", "只支持 enabled、source 和 url")
    values = {**raw, "qr_enabled": qr.get("enabled", False), "qr_source": qr.get("source", "website"), "qr_url": qr.get("url", "")}
    for key, value in {"site_url": site_url, "qr_enabled": qr_enabled, "qr_source": qr_source, "qr_url": qr_url}.items():
        if value is not None:
            values[key] = value
    config = Settings(**values)
    if type(config.qr_enabled) is not bool:
        raise InputError("qr.enabled", "需要 true 或 false")
    if config.qr_source not in ("website", "original", "custom"):
        raise InputError("qr.source", "需要 website、original 或 custom")
    for key in ("site_name", "main_name", "schedule"):
        value = getattr(config, key)
        if not isinstance(value, str) or not value.strip() or len(value) > 200:
            raise InputError(key, "需要不超过 200 字的文字")
    normalized = config.public()
    for key in ("site_url", "main_url"):
        if normalized[key]:
            normalized[key] = address(normalized[key], key, origin=True)
        elif not isinstance(normalized[key], str):
            raise InputError(key, "需要字符串")
    if config.qr_url:
        template(config.qr_url, "qr.url")
    elif not isinstance(config.qr_url, str):
        raise InputError("qr.url", "需要字符串")
    config = Settings(**normalized)
    if config.qr_enabled:
        if config.qr_source == "custom" and not config.qr_url:
            raise InputError("qr.url", "开启自定义二维码前，请自己配置链接模板")
        if config.qr_source != "custom" and not config.site_url:
            raise InputError("site_url", "开启二维码前，请配置自己的网站地址；整期长图使用该地址")
    return config
