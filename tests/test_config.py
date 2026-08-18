# Copyright (C) 2026 justplaymore
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""config 读写单元测试。"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, DEFAULTS  # noqa: E402


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "config.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_defaults_when_missing(self):
        cfg = Config(self.path)
        self.assertEqual(cfg.hotkey_calibrate, "+")
        self.assertEqual(cfg.hotkey_target, "-")
        self.assertEqual(cfg.reference_meters, 300.0)
        self.assertEqual(cfg.ratio_m_per_px, 0.0)
        self.assertFalse(cfg.calibrated)

    def test_round_trip(self):
        cfg = Config(self.path)
        cfg.hotkey_calibrate = "F8"
        cfg.hotkey_target = "="
        cfg.reference_meters = 500.0
        cfg.ratio_m_per_px = 0.1234
        cfg.calibrated = True
        cfg.save()

        cfg2 = Config(self.path)
        self.assertEqual(cfg2.hotkey_calibrate, "F8")
        self.assertEqual(cfg2.hotkey_target, "=")
        self.assertEqual(cfg2.reference_meters, 500.0)
        self.assertEqual(cfg2.ratio_m_per_px, 0.1234)
        self.assertTrue(cfg2.calibrated)

    def test_corrupt_file_falls_back_to_defaults(self):
        self.path.write_text("{ not valid json !!", encoding="utf-8")
        cfg = Config(self.path)
        self.assertEqual(cfg.hotkey_calibrate, DEFAULTS["hotkey_calibrate"])
        self.assertEqual(cfg.reference_meters, DEFAULTS["reference_meters"])

    def test_partial_file_keeps_known_keys(self):
        self.path.write_text(json.dumps({"hotkey_target": "F5"}), encoding="utf-8")
        cfg = Config(self.path)
        self.assertEqual(cfg.hotkey_target, "F5")
        self.assertEqual(cfg.hotkey_calibrate, "+")  # 缺失键回退默认


if __name__ == "__main__":
    unittest.main()
