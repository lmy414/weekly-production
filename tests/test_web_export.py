# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import shutil
import sys
import unittest

from PIL import Image
from production_fixtures import packs, write_json, ROOT
from weekly_runtime.assembly import assemble
from weekly_runtime.inputs import load_inputs
from weekly_runtime.common import InputError, atomic_json, digest, file_hash
from weekly_runtime.encoder import render_input
from weekly_runtime.pipeline import work_directory
from weekly_web.settings import load_settings
from weekly_web.exporter import export_site, verified_inputs
from weekly_web.cards import Cards
from weekly_web.builder import assert_issue


def recorded_movie(root, issue_id="synthetic-001"):
    """Minimal metadata fixtures for exporter guards; not a video quality test."""
    episode, character = packs(root, count=1)
    data = json.loads(episode.read_text("utf-8"))
    data["id"] = issue_id
    data["branding"] = {"website_url": "https://unused-signature.example"}
    data["works"][0]["provenance"] = {"private_notes": "PRIVATE-EDITORIAL-MARKER"}
    write_json(episode, data)
    bundle = load_inputs(episode, character)
    program = assemble(bundle)
    target, work = work_directory(Path(root) / "movie.mp4")
    shutil.copy2(episode.parent / "source.mp4", target)
    atomic_json(work / "program.json", program)
    atomic_json(work / "episode.lock.json", {"episode": str(episode.resolve()), "character": str(character.resolve()),
                                              "inputs": bundle["hashes"], "program_sha256": digest(render_input(program))})
    atomic_json(work / "last-build.json", {"output": str(target), "verified": True, "sha256": file_hash(target)})
    return episode, character, target, work


class QRSettingsTests(unittest.TestCase):
    def test_no_operator_domain_or_automatic_qr(self):
        self.assertFalse(load_settings().qr_enabled)
        config = load_settings(site_url="https://weekly.example.com/")
        self.assertFalse(config.qr_enabled)
        self.assertIsNone(config.qr_target({"id": "issue-001"}))
        with self.assertRaisesRegex(InputError, "自己的网站地址"):
            load_settings(qr_enabled=True)

    def test_website_default_and_explicit_source_overrides(self):
        issue, work = {"id": "issue-002"}, {"bvid": "BV1111111111", "source_url": "https://example.org/original"}
        website = load_settings(site_url="https://weekly.example.com", qr_enabled=True)
        self.assertEqual(website.qr_target(issue), "https://weekly.example.com/issues/issue-002/")
        self.assertEqual(website.qr_target(issue, work), "https://weekly.example.com/issues/issue-002/#work-BV1111111111")
        original = load_settings(site_url=website.site_url, qr_enabled=True, qr_source="original")
        self.assertEqual(original.qr_target(issue, work), work["source_url"])
        self.assertEqual(original.qr_target(issue), website.qr_target(issue))
        custom = load_settings(qr_enabled=True, qr_source="custom", qr_url="https://example.org/{issue_id}/?work={bvid}")
        self.assertEqual(custom.qr_target(issue, work), "https://example.org/issue-002/?work=BV1111111111")

    def test_config_does_not_accept_unsafe_or_implicit_addresses(self):
        for url in ("javascript:alert(1)", "https://user:password@example.com", "https://example.com/?tracking=1", "https://example.com/path/", "https://example.com/\n"):
            with self.subTest(url=url), self.assertRaises(InputError):
                load_settings(site_url=url)
        with self.assertRaises(InputError):
            load_settings(qr_enabled=True, qr_source="custom", qr_url="https://example.com/{bvid.__class__}")
        self.assertEqual(load_settings(site_url="https://例子.com").site_url, "https://xn--fsqu00a.com")

    def test_cli_override_can_disable_a_configured_qr(self):
        with TemporaryDirectory() as folder:
            config = Path(folder) / "web.json"
            write_json(config, {"site_url": "https://weekly.example.com", "qr": {"enabled": True}})
            self.assertTrue(load_settings(config).qr_enabled)
            self.assertFalse(load_settings(config, qr_enabled=False).qr_enabled)

    def test_disabled_card_has_no_qr_pixels(self):
        font = ROOT / "skills/weekly-production/assets/ui/fonts/noto-sans-sc/NotoSansSC-variable.ttf"
        plain = Cards(font, load_settings())
        enabled = Cards(font, load_settings(site_url="https://weekly.example.com", qr_enabled=True))
        a, ad = plain.background(500)
        b, bd = enabled.background(500)
        plain.bottom(a, ad, {"id": "issue-001"}, 270)
        enabled.bottom(b, bd, {"id": "issue-001"}, 270)
        # A real QR is drawn only in the enabled image's footer box.
        self.assertNotEqual(a.crop((996, 275, 1160, 439)).tobytes(), b.crop((996, 275, 1160, 439)).tobytes())


class WebExportTests(unittest.TestCase):
    def test_public_output_and_repeated_export_preserve_archive(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            first = root / "first"
            first.mkdir()
            episode, character, video, _ = recorded_movie(first)
            out = root / "website"
            with patch("weekly_web.exporter.frame_at", return_value=Image.new("RGB", (640, 360), "teal")):
                result = export_site(episode, character, video, out)
                again = export_site(episode, character, video, out)
                self.assertEqual(result["build"]["revision"], again["build"]["revision"])
                self.assertFalse(result["qr"]["enabled"])
                for name, size in {"landscape": (1410, 600), "square": (1080, 1080)}.items():
                    with Image.open(result["wechat_covers"][name]) as cover:
                        self.assertEqual(cover.size, size)
                        self.assertEqual(cover.format, "JPEG")
                        self.assertEqual(cover.mode, "RGB")
                second = root / "second"
                second.mkdir()
                ep2, ch2, vid2, _ = recorded_movie(second, "synthetic-002")
                updated = export_site(ep2, ch2, vid2, out)
            self.assertEqual(set(updated["build"]["issues"]), {"synthetic-001", "synthetic-002"})
            self.assertEqual(updated["build"]["html_pages"], 6)
            self.assertTrue((out / "issues/synthetic-001/index.html").is_file())
            for name in ("cover-wechat-2.35x1.jpg", "cover-wechat-1x1.jpg"):
                self.assertTrue((out / "assets/issues/synthetic-001" / name).is_file())
            text = "".join(p.read_text("utf-8") for p in out.rglob("*") if p.suffix in (".html", ".json"))
            for value in ("PRIVATE-EDITORIAL-MARKER", "unused-signature.example", "episode.lock", "private_notes", str(episode)):
                self.assertNotIn(value, text)
            self.assertFalse(any(p.suffix in (".mp4", ".wav") for p in out.rglob("*")))
            self.assertNotIn("style=", (out / "index.html").read_text("utf-8"))

    def test_legacy_archive_and_cover_path_validation(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            episode, character, video, _ = recorded_movie(root)
            out = root / "website"
            with patch("weekly_web.exporter.frame_at", return_value=Image.new("RGB", (640, 360), "teal")):
                export_site(episode, character, video, out)
                manifest = json.loads((out / "export-manifest.json").read_text("utf-8"))
                issue = manifest["issues"][0]
                covers = issue.pop("wechat_covers")
                assert_issue(issue)
                atomic_json(out / "export-manifest.json", manifest)
                result = export_site(episode, character, video, out)
                self.assertEqual(set(result["wechat_covers"]), {"landscape", "square"})
                issue["wechat_covers"] = {**covers, "private": "C:/private.png"}
                with self.assertRaisesRegex(InputError, "公众号封面"):
                    assert_issue(issue)
                issue["wechat_covers"] = {**covers, "square": "/assets/issues/synthetic-001/../private.jpg"}
                with self.assertRaisesRegex(InputError, "图片路径"):
                    assert_issue(issue)

    def test_unverified_changed_video_inputs_and_program_are_rejected(self):
        with TemporaryDirectory() as folder:
            episode, character, video, work = recorded_movie(folder)
            verified_inputs(episode, character, video)
            original_video = video.read_bytes()
            video.write_bytes(b"changed")
            with self.assertRaisesRegex(InputError, "MP4"):
                verified_inputs(episode, character, video)
            video.write_bytes(original_video)
            program = json.loads((work / "program.json").read_text("utf-8"))
            program["duration"] += 1
            atomic_json(work / "program.json", program)
            with self.assertRaisesRegex(InputError, "时间轴"):
                verified_inputs(episode, character, video)
            episode.write_text(episode.read_text("utf-8") + "\n", "utf-8")
            with self.assertRaisesRegex(InputError, "发生变化"):
                verified_inputs(episode, character, video)

    def test_bad_editorial_keeps_previous_output_and_unknown_folder_is_safe(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            episode, character, video, _ = recorded_movie(root)
            out = root / "website"
            with patch("weekly_web.exporter.frame_at", return_value=Image.new("RGB", (640, 360), "teal")):
                export_site(episode, character, video, out)
                previous = (out / "index.html").read_bytes()
                editorial = root / "editorial.json"
                write_json(editorial, {"works": {"BV1111111111": {"summary": "说明", "category": "bad"}}})
                with self.assertRaises(InputError):
                    export_site(episode, character, video, out, editorial=editorial)
                self.assertEqual(previous, (out / "index.html").read_bytes())
                unknown = root / "other"
                unknown.mkdir()
                (unknown / "keep.txt").write_text("keep", "utf-8")
                with self.assertRaises(InputError):
                    export_site(episode, character, video, unknown)
                self.assertEqual((unknown / "keep.txt").read_text("utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
