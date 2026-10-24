# SPDX-License-Identifier: GPL-3.0-only
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import wave

import numpy as np
from production_fixtures import packs, write_json
from weekly_runtime.audio import RATE, configure_bgm, prepare_audio
from weekly_runtime.assembly import assemble
from weekly_runtime.common import InputError, file_hash, read_json
from weekly_runtime.inputs import load_inputs
from weekly_runtime.media import prepare_media
from weekly_runtime.segment_cache import work_fingerprint, record, matches


class MediaAudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.episode, cls.character = packs(cls.temporary.name, count=1)
        cls.base = read_json(cls.episode)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        write_json(self.episode, deepcopy(self.base))

    def bundle(self):
        return load_inputs(self.episode, self.character)

    def test_recorded_music_is_continuous_and_does_not_overlay_work(self):
        bundle = self.bundle()
        program = {"context": {"audio": {"narration": False}}, "scenes": [
            {"id": "a", "template": "opening", "duration": 1},
            {"id": "b", "template": "scope", "duration": 1},
            {"id": "work", "template": "ranking", "duration": 30},
            {"id": "c", "template": "end", "duration": 1}]}
        configure_bgm(program, bundle["bgm"])
        with tempfile.TemporaryDirectory() as folder:
            report = prepare_audio(program, folder)
            self.assertNotIn("work", report["scenes"])
            self.assertEqual([report["scenes"][key]["source_start_sample"] for key in ("a", "b", "c")], [0, RATE, 2 * RATE])
            self.assertFalse(report["narration"])
            def pcm(path):
                with wave.open(str(path), "rb") as sound:
                    self.assertEqual((sound.getframerate(), sound.getnchannels()), (RATE, 2))
                    return np.frombuffer(sound.readframes(sound.getnframes()), dtype="<i2").reshape(-1, 2).astype(float)
            source = pcm(Path(folder) / "bgm-normalized.wav")
            actual = pcm(Path(folder) / "b.wav")
            expected = source[RATE:2 * RATE] * 10 ** (-1.5 / 20)
            self.assertLess(float(np.max(np.abs(actual[9600:-9600] - expected[9600:-9600]))), 3)

    def test_local_range_is_cropped_and_corrupted_cache_rebuilt(self):
        data = deepcopy(self.base)
        data["works"][0]["clip"] = {"start": 1, "end": 2}
        write_json(self.episode, data)
        bundle = self.bundle(); program = assemble(bundle)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            first = prepare_media(bundle, program, out)
            entry = next(iter(first.values())); path = Path(entry["path"])
            original_hash = file_hash(path)
            self.assertNotEqual(path, Path(bundle["sources"]["BV1111111111"]["path"]))
            path.write_bytes(b"corrupted-cache")
            second = prepare_media(bundle, program, out)
            self.assertEqual(file_hash(Path(next(iter(second.values()))["path"])), original_hash)

    def test_work_cache_reuses_timeline_move_but_rejects_changed_source_and_output(self):
        bundle = self.bundle(); program = assemble(bundle)
        scene = next(s for s in program["scenes"] if s["template"] == "podium")
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder); (out / "plates").mkdir()
            plate = out / "plates" / (scene["id"] + ".png"); plate.write_bytes(b"synthetic plate")
            source = out / "source.mp4"; source.write_bytes(b"synthetic source")
            media = {scene["row"]["bvid"]: {"path": str(source)}}
            target = out / "work.mov"; target.write_bytes(b"synthetic encoding")
            fingerprint = work_fingerprint(scene, media, out)
            entry = record(fingerprint, target)
            self.assertTrue(matches(entry, fingerprint, target))
            self.assertEqual(fingerprint, work_fingerprint({**scene, "start": 100}, media, out))
            source.write_bytes(b"changed source")
            self.assertNotEqual(fingerprint, work_fingerprint(scene, media, out))
            target.write_bytes(b"broken encoding")
            self.assertFalse(matches(entry, fingerprint, target))


if __name__ == "__main__":
    unittest.main()
