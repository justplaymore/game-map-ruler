"""测距会话状态机：热键即点选，纯逻辑（不依赖 Qt / win32），可单元测试。

每个功能恰好两次热键按键完成一次测距：
  - 功能1（校准）：按 + 第一次 = 开始 + A 点；第二次 = B 点 + 结算比例。
  - 功能2（测距）：按 - 第一次 = A 点；第二次 = B 点 + 结算目标距离。
两个会话互斥，同一时刻至多一个。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple

from geometry import calibrate, pixel_distance, target_distance

Point = Tuple[int, int]


class SessionKind(Enum):
    CALIBRATE = auto()  # 功能1：建立校准基准比例
    TARGET = auto()     # 功能2：测距（目标实际距离）


class State(Enum):
    IDLE = auto()
    CAL_A = auto()  # 校准：已选 A，等待 B
    TGT_A = auto()  # 测距：已选 A，等待 B


class Action(Enum):
    START_CAL_A = auto()        # 校准开始并记录 A
    SET_CAL_B_FINISH = auto()   # 校准 B 确定并结算
    START_TGT_A = auto()        # 测距开始并记录 A
    SET_TGT_B_FINISH = auto()   # 测距 B 确定并结算
    IGNORE_CROSS_KEY = auto()   # 会话中按了另一个热键
    REJECT_NO_CALIBRATION = auto()  # 未校准就测距
    CANCELED = auto()           # 取消会话


@dataclass
class Session:
    kind: SessionKind
    a: Optional[Point] = None
    b: Optional[Point] = None
    px_dist: float = 0.0
    # 校准会话：每像素米数（m/px）；测距会话：目标实际距离（米）
    actual: float = 0.0
    # 第一次按键时的客户区几何（用于结算前校验窗口是否移动/缩放）
    origin: Point = (0, 0)
    size: Point = (0, 0)

    def has_both_points(self) -> bool:
        return self.a is not None and self.b is not None


class AppState:
    def __init__(
        self,
        reference_meters: float = 300.0,
        ratio: float = 0.0,
        calibrated: bool = False,
    ):
        self.state: State = State.IDLE
        self.session: Optional[Session] = None
        self.reference_meters: float = reference_meters
        self.ratio: float = ratio
        self.calibrated: bool = calibrated

    # ---- 配置 ----
    def set_reference_meters(self, value: float) -> None:
        self.reference_meters = float(value)

    # ---- 事件 ----
    def on_calibrate_press(self, pixel: Point, origin: Point, size: Point):
        """功能1 热键按下：第一次开始+A，第二次 B+结算。"""
        if self.state == State.IDLE:
            self.session = Session(SessionKind.CALIBRATE, a=pixel, origin=origin, size=size)
            self.state = State.CAL_A
            return Action.START_CAL_A, self.session
        if self.state == State.CAL_A:
            return self._finish(pixel)
        return Action.IGNORE_CROSS_KEY, self.session

    def on_target_press(self, pixel: Point, origin: Point, size: Point):
        """功能2 热键按下：第一次开始+A，第二次 B+结算。"""
        if self.state == State.IDLE:
            if not self.calibrated:
                return Action.REJECT_NO_CALIBRATION, None
            self.session = Session(SessionKind.TARGET, a=pixel, origin=origin, size=size)
            self.state = State.TGT_A
            return Action.START_TGT_A, self.session
        if self.state == State.TGT_A:
            return self._finish(pixel)
        return Action.IGNORE_CROSS_KEY, self.session

    def cancel(self) -> Action:
        """取消当前会话（ESC / 右键 / 清除按钮）。"""
        self.session = None
        self.state = State.IDLE
        return Action.CANCELED

    # ---- 内部 ----
    def _finish(self, pixel: Point):
        """第二次按键：确定 B 并结算。像素距离为 0 时 raise ValueError。"""
        session = self.session
        assert session is not None and session.a is not None
        session.b = pixel
        session.px_dist = pixel_distance(session.a, session.b)
        if session.kind == SessionKind.CALIBRATE:
            self.ratio = calibrate(self.reference_meters, session.px_dist)
            self.calibrated = True
            session.actual = self.ratio
            self.state = State.IDLE
            return Action.SET_CAL_B_FINISH, session
        session.actual = target_distance(session.px_dist, self.ratio)
        self.state = State.IDLE
        return Action.SET_TGT_B_FINISH, session
