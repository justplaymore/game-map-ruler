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

"""app_state 状态机单元测试。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_state import Action, AppState, SessionKind, State  # noqa: E402

ORIGIN = (100, 100)
SIZE = (800, 600)


class TestCalibrateFlow(unittest.TestCase):
    def test_full_flow(self):
        st = AppState(reference_meters=300.0)
        self.assertEqual(st.state, State.IDLE)

        action, session = st.on_calibrate_press((50, 50), ORIGIN, SIZE)
        self.assertEqual(action, Action.START_CAL_A)
        self.assertEqual(st.state, State.CAL_A)
        self.assertEqual(session.a, (50, 50))
        self.assertEqual(session.origin, ORIGIN)
        self.assertEqual(session.size, SIZE)

        action, session = st.on_calibrate_press((350, 450), ORIGIN, SIZE)
        self.assertEqual(action, Action.SET_CAL_B_FINISH)
        self.assertEqual(st.state, State.IDLE)
        self.assertEqual(session.b, (350, 450))
        # 像素距离 = sqrt(300² + 400²) = 500，比例 = 300/500 = 0.6
        self.assertAlmostEqual(session.px_dist, 500.0)
        self.assertAlmostEqual(session.actual, 0.6)
        self.assertTrue(st.calibrated)
        self.assertAlmostEqual(st.ratio, 0.6)

    def test_calibrate_press_after_calibrated_resets(self):
        st = AppState(reference_meters=100.0, calibrated=True, ratio=1.0)
        action, _ = st.on_calibrate_press((0, 0), ORIGIN, SIZE)
        self.assertEqual(action, Action.START_CAL_A)

    def test_zero_distance_raises(self):
        st = AppState(reference_meters=300.0)
        st.on_calibrate_press((10, 10), ORIGIN, SIZE)
        with self.assertRaises(ValueError):
            st.on_calibrate_press((10, 10), ORIGIN, SIZE)

    def test_cancel_during_calibration(self):
        st = AppState(reference_meters=300.0)
        st.on_calibrate_press((0, 0), ORIGIN, SIZE)
        self.assertEqual(st.state, State.CAL_A)
        action = st.cancel()
        self.assertEqual(action, Action.CANCELED)
        self.assertEqual(st.state, State.IDLE)
        self.assertIsNone(st.session)


class TestTargetFlow(unittest.TestCase):
    def test_reject_without_calibration(self):
        st = AppState(reference_meters=300.0)
        action, session = st.on_target_press((0, 0), ORIGIN, SIZE)
        self.assertEqual(action, Action.REJECT_NO_CALIBRATION)
        self.assertIsNone(session)
        self.assertEqual(st.state, State.IDLE)

    def test_full_flow(self):
        st = AppState(reference_meters=300.0, ratio=2.0, calibrated=True)
        action, session = st.on_target_press((100, 100), ORIGIN, SIZE)
        self.assertEqual(action, Action.START_TGT_A)
        self.assertEqual(st.state, State.TGT_A)

        action, session = st.on_target_press((400, 500), ORIGIN, SIZE)
        self.assertEqual(action, Action.SET_TGT_B_FINISH)
        self.assertEqual(st.state, State.IDLE)
        # 像素距离 = sqrt(300² + 400²) = 500；实际 = 500 × 2 = 1000
        self.assertAlmostEqual(session.px_dist, 500.0)
        self.assertAlmostEqual(session.actual, 1000.0)


class TestCrossKeyIgnore(unittest.TestCase):
    def test_target_press_during_cal_a(self):
        st = AppState(reference_meters=300.0)
        st.on_calibrate_press((0, 0), ORIGIN, SIZE)
        action, _ = st.on_target_press((1, 1), ORIGIN, SIZE)
        self.assertEqual(action, Action.IGNORE_CROSS_KEY)
        self.assertEqual(st.state, State.CAL_A)

    def test_calibrate_press_during_tgt_a(self):
        st = AppState(reference_meters=300.0, ratio=2.0, calibrated=True)
        st.on_target_press((0, 0), ORIGIN, SIZE)
        action, _ = st.on_calibrate_press((1, 1), ORIGIN, SIZE)
        self.assertEqual(action, Action.IGNORE_CROSS_KEY)
        self.assertEqual(st.state, State.TGT_A)


class TestReferenceMeters(unittest.TestCase):
    def test_updated_reference_affects_ratio(self):
        st = AppState(reference_meters=300.0)
        st.set_reference_meters(600.0)
        st.on_calibrate_press((0, 0), ORIGIN, SIZE)
        _, session = st.on_calibrate_press((400, 0), ORIGIN, SIZE)
        # 像素距离 400 → 比例 = 600/400 = 1.5
        self.assertAlmostEqual(session.actual, 1.5)


if __name__ == "__main__":
    unittest.main()
