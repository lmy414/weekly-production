# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from production_fixtures import packs
from weekly_runtime.pipeline import build


class DeliveryTests(unittest.TestCase):
    def test_failed_quality_check_preserves_existing_final_file(self):
        with tempfile.TemporaryDirectory() as folder:
            episode, character = packs(folder, count=1)
            target = Path(folder) / "final.mp4"
            target.write_bytes(b"previous verified final")
            def encoded(out, *args):
                (out / "program.mp4").write_bytes(b"bad new encoding")
                return {"reused_work_segments": 0}
            with patch("weekly_runtime.pipeline.runtime", return_value={}), patch("weekly_runtime.pipeline.capture", return_value={}), patch("weekly_runtime.pipeline.render_program", side_effect=encoded), patch("weekly_runtime.pipeline.verify", side_effect=ValueError("quality check failed")):
                with self.assertRaisesRegex(ValueError, "quality check failed"):
                    build(episode, character, target)
            self.assertEqual(target.read_bytes(), b"previous verified final")


if __name__ == "__main__":
    unittest.main()
