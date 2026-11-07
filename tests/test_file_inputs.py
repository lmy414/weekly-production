# SPDX-License-Identifier: GPL-3.0-only
from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from production_fixtures import packs, write_json
from weekly_runtime.assembly import assemble
from weekly_runtime.common import InputError, read_json
from weekly_runtime.inputs import load_inputs
from weekly_runtime.encoder import render_input
from weekly_runtime.pipeline import build_lock, ensure_unchanged, work_directory


class FileInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.episode, cls.character = packs(cls.temporary.name)
        cls.base = read_json(cls.episode)
        cls.base_art = read_json(cls.character)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        write_json(self.episode, deepcopy(self.base))
        write_json(self.character, deepcopy(self.base_art))

    def load(self):
        return load_inputs(self.episode, self.character)

    def test_external_paths_defaults_and_exact_short_source(self):
        bundle = self.load()
        self.assertEqual(len(set(bundle["assets"].values())), 1)
        self.assertEqual(len(bundle["rows"]), 3)
        program = assemble(bundle)
        self.assertEqual(next(s["start"] for s in program["scenes"] if s["template"] == "podium"), 40)
        first_work = next(i for i, s in enumerate(program["scenes"]) if s["template"] == "podium")
        self.assertTrue(all(s["template"] in ("opening", "rundown", "scope", "scoring", "scoring_details", "podium_reveal") for s in program["scenes"][:first_work]))
        self.assertTrue(all(s["duration"] == 2 for s in program["scenes"] if s["template"] == "podium"))
        self.assertFalse(program["context"]["audio"]["narration"])
        self.assertNotIn("news", [s["template"] for s in program["scenes"]])

    def test_top_25_has_two_readable_rundown_pages(self):
        data = deepcopy(self.base)
        data["works"] = []
        for n in range(1, 26):
            row = deepcopy(self.base["works"][0])
            row.update(bvid="BV111111111" + "123456789ABCDEFGHJKLMNPQR"[n - 1], title=f"虚构测试作品 {n}",
                       source_url=f"https://example.org/synthetic/{n}")
            row["metrics"]["view"] = 1000 + n
            data["works"].append(row)
        write_json(self.episode, data)
        program = assemble(self.load())
        pages = [s for s in program["scenes"] if s["template"] == "rundown"]
        self.assertEqual([(s["lineup_start"], s["lineup_end"]) for s in pages], [(0, 15), (15, 25)])
        self.assertEqual(len([s for s in program["scenes"] if s["template"] in ("ranking", "podium")]), 25)
        self.assertLess(max(s["end"] for s in program["scenes"] if s["template"] in ("scoring", "scoring_details")),
                        min(s["start"] for s in program["scenes"] if s["template"] in ("ranking", "podium")))

    def test_relevance_flags_and_private_database_are_not_required(self):
        with patch("socket.socket.connect", side_effect=AssertionError("network forbidden")):
            self.assertEqual(self.load()["id"], "synthetic-001")

    def test_missing_metric_is_never_filled_with_zero(self):
        for field in ("view", "coin", "like", "share"):
            data = deepcopy(self.base)
            del data["works"][0]["metrics"][field]
            write_json(self.episode, data)
            with self.subTest(field=field), self.assertRaises(InputError):
                self.load()

    def test_invalid_and_duplicate_data_fail_before_render(self):
        for transform in (
            lambda x: x["works"][0]["metrics"].update(view=-1),
            lambda x: x["works"][0]["metrics"].update(view=True),
            lambda x: x["works"][0].update(score=1),
            lambda x: x["works"][0].update(rank=3),
            lambda x: x["works"][0].update(video="https://example.org/source.mp4"),
            lambda x: x["works"][0].update(published_at="2024-01-02T12:00:00"),
            lambda x: x["works"][0].update(clip={"start": 0, "end": 30}),
            lambda x: x["works"].append(deepcopy(x["works"][0])),
        ):
            data = deepcopy(self.base); transform(data); write_json(self.episode, data)
            with self.subTest(data=data["works"][0]), self.assertRaises(InputError):
                self.load()

    def test_configured_missing_role_is_an_error_not_default_fallback(self):
        art = deepcopy(self.base_art); art["images"]["welcome"] = "missing.png"
        write_json(self.character, art)
        with self.assertRaisesRegex(InputError, "welcome"):
            self.load()

    def test_song_hash_cannot_silently_change(self):
        data = deepcopy(self.base); data["music"]["sha256"] = "0" * 64
        write_json(self.episode, data)
        with self.assertRaisesRegex(InputError, "sha256"):
            self.load()

    def test_human_status_does_not_change_rendered_content(self):
        program = assemble(self.load()); before = render_input(program)
        program["publication"] = {"approved": True, "reviewer": "synthetic"}
        self.assertEqual(render_input(program), before)

    def test_change_detection_and_exclusive_output(self):
        bundle = self.load()
        data = deepcopy(self.base); data["title"] = "修改文案"
        write_json(self.episode, data)
        with self.assertRaises(InputError):
            ensure_unchanged(bundle["hashes"])
        _, folder = work_directory(Path(self.temporary.name) / "output.mp4")
        with build_lock(folder):
            with self.assertRaises(InputError):
                with build_lock(folder):
                    pass
        with build_lock(folder):
            pass


if __name__ == "__main__":
    unittest.main()
