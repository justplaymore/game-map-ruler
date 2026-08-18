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

"""geometry 纯函数单元测试（python -m unittest / pytest 均可运行）。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geometry import (  # noqa: E402
    calibrate,
    pixel_distance,
    screen_to_pixel,
    target_distance,
    window_geometry_changed,
)


class TestScreenToPixel(unittest.TestCase):
    def test_basic(self):
        # 客户区原点 (100, 200)，光标 (150, 260) → 像素 (50, 60)
        self.assertEqual(screen_to_pixel((150, 260), (100, 200), (800, 600)), (50, 60))

    def test_origin_equals_cursor(self):
        self.assertEqual(screen_to_pixel((100, 200), (100, 200), (800, 600)), (0, 0))

    def test_outside_left(self):
        self.assertIsNone(screen_to_pixel((99, 200), (100, 200), (800, 600)))

    def test_outside_top(self):
        self.assertIsNone(screen_to_pixel((100, 199), (100, 200), (800, 600)))

    def test_outside_right_boundary(self):
        # x == origin+width 视为越界（半开区间）
        self.assertIsNone(screen_to_pixel((900, 200), (100, 200), (800, 600)))

    def test_outside_bottom_boundary(self):
        self.assertIsNone(screen_to_pixel((100, 800), (100, 200), (800, 600)))

    def test_negative_monitor_coords(self):
        # 副显示器在左侧：原点为负坐标也能正确映射
        self.assertEqual(screen_to_pixel((-400, 300), (-500, 200), (800, 600)), (100, 100))


class TestPixelDistance(unittest.TestCase):
    def test_pythagorean(self):
        self.assertAlmostEqual(pixel_distance((0, 0), (3, 4)), 5.0)

    def test_reversed(self):
        self.assertAlmostEqual(pixel_distance((3, 4), (0, 0)), 5.0)

    def test_same_point(self):
        self.assertEqual(pixel_distance((10, 20), (10, 20)), 0.0)

    def test_horizontal(self):
        self.assertEqual(pixel_distance((10, 5), (110, 5)), 100.0)


class TestCalibrate(unittest.TestCase):
    def test_ratio(self):
        self.assertAlmostEqual(calibrate(300.0, 150.0), 2.0)
        self.assertAlmostEqual(calibrate(100.0, 400.0), 0.25)

    def test_zero_pixel_distance_raises(self):
        with self.assertRaises(ValueError):
            calibrate(300.0, 0.0)

    def test_negative_pixel_distance_raises(self):
        with self.assertRaises(ValueError):
            calibrate(300.0, -1.0)

    def test_invalid_reference_raises(self):
        with self.assertRaises(ValueError):
            calibrate(0.0, 100.0)
        with self.assertRaises(ValueError):
            calibrate(-5.0, 100.0)


class TestTargetDistance(unittest.TestCase):
    def test_basic(self):
        self.assertAlmostEqual(target_distance(200.0, 2.0), 400.0)

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            target_distance(-1.0, 2.0)
        with self.assertRaises(ValueError):
            target_distance(1.0, -2.0)


class TestWindowGeometryChanged(unittest.TestCase):
    def test_unchanged(self):
        self.assertFalse(window_geometry_changed((0, 0), (800, 600), (0, 0), (800, 600)))

    def test_moved(self):
        self.assertTrue(window_geometry_changed((0, 0), (800, 600), (10, 0), (800, 600)))

    def test_resized(self):
        self.assertTrue(window_geometry_changed((0, 0), (800, 600), (0, 0), (1024, 768)))


if __name__ == "__main__":
    unittest.main()
