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

"""置顶 HUD 主窗口：数值显示、状态机驱动、全局热键处理。

无边框半透明置顶面板，显示四项数值（基准像素距离、基准实际距离、
目标像素距离、目标实际距离）与校准比例；热键（+ / -）在游戏窗口
聚焦时全局生效，按下瞬间取鼠标位置为像素点。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Optional

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app_state import Action, AppState, Session, SessionKind
from config import Config
from geometry import screen_to_pixel, window_geometry_changed
from hotkey import HOTKEY_NAMES_KNOWN, HotkeyCaptureDialog, HotkeyManager
from winapi import (
    WM_HOTKEY,
    get_cursor_pos,
    get_foreground_window,
    get_window_client_origin_size,
)

HOTKEY_ID_CALIBRATE = 1
HOTKEY_ID_TARGET = 2

# 面板配色
COLOR_IDLE = "#9aa0a6"
COLOR_ACTIVE = "#f59f00"
COLOR_DONE = "#2f9e44"

STYLE_PANEL = """
QFrame#panel {
    background-color: rgba(22, 24, 32, 218);
    border: 1px solid rgba(255, 255, 255, 46);
    border-radius: 10px;
}
QLabel { color: #e8eaf0; background: transparent; }
QLabel#value { color: #cfe3ff; font-weight: bold; }
QLabel#status { font-weight: bold; }
QLabel#hint { color: #b0b6c0; font-size: 9pt; }
QDoubleSpinBox {
    background: rgba(255,255,255,26); color: #e8eaf0;
    border: 1px solid rgba(255,255,255,60); border-radius: 4px; padding: 1px 4px;
}
QPushButton, QToolButton {
    background: rgba(255,255,255,26); color: #e8eaf0;
    border: 1px solid rgba(255,255,255,60); border-radius: 4px; padding: 2px 8px;
}
QPushButton:hover, QToolButton:hover { background: rgba(255,255,255,52); }
QCheckBox { color: #e8eaf0; background: transparent; }
"""


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.state = AppState(
            reference_meters=self.config.reference_meters,
            ratio=self.config.ratio_m_per_px,
            calibrated=self.config.calibrated,
        )
        self._last_target_hwnd: Optional[int] = None
        self._drag_offset: Optional[QPoint] = None

        self.setWindowTitle("游戏地图测距工具")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 启动/显示时不激活窗口，避免抢走游戏的键盘焦点
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet(STYLE_PANEL)
        # 面板需要键盘焦点才能接收 Esc 取消
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._build_ui()
        self._apply_config_to_ui()

        self.hotkeys = HotkeyManager(int(self.winId()))
        self._register_hotkeys()
        self._set_status("空闲", COLOR_IDLE)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        panel = QFrame()
        panel.setObjectName("panel")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.addWidget(panel)

        lay = QVBoxLayout(panel)
        lay.setSpacing(4)
        lay.setContentsMargins(12, 10, 12, 10)

        # 标题行
        head = QHBoxLayout()
        title = QLabel("游戏地图测距工具")
        title.setStyleSheet("font-weight: bold; font-size: 11pt;")
        self.btn_close = QToolButton()
        self.btn_close.setText("✕")
        self.btn_close.setFixedSize(20, 20)
        self.btn_close.clicked.connect(QApplication.instance().quit)
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(self.btn_close)
        lay.addLayout(head)

        # 状态行
        self.lbl_status = QLabel()
        self.lbl_status.setObjectName("status")
        lay.addWidget(self.lbl_status)

        # 数值区
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)

        self.lbl_ref_spin = QDoubleSpinBox()
        self.lbl_ref_spin.setRange(0.1, 9_999_999.0)
        self.lbl_ref_spin.setDecimals(2)
        self.lbl_ref_spin.setSuffix(" 米")
        self.lbl_ref_spin.valueChanged.connect(self._on_ref_changed)

        self.lbl_cal_px = self._make_value_label()
        self.lbl_cal_ratio = self._make_value_label()
        self.lbl_tgt_px = self._make_value_label()
        self.lbl_tgt_dist = self._make_value_label()

        grid.addWidget(QLabel("基准实际距离"), 0, 0)
        grid.addWidget(self.lbl_ref_spin, 0, 1)
        grid.addWidget(QLabel("基准像素距离"), 1, 0)
        grid.addWidget(self.lbl_cal_px, 1, 1)
        grid.addWidget(QLabel("校准比例"), 2, 0)
        grid.addWidget(self.lbl_cal_ratio, 2, 1)
        grid.addWidget(QLabel("目标像素距离"), 3, 0)
        grid.addWidget(self.lbl_tgt_px, 3, 1)
        grid.addWidget(QLabel("目标实际距离"), 4, 0)
        grid.addWidget(self.lbl_tgt_dist, 4, 1)
        lay.addLayout(grid)

        # 热键行
        hot_row = QHBoxLayout()
        self.btn_cal_hotkey = QPushButton()
        self.btn_cal_hotkey.clicked.connect(
            lambda: self._change_hotkey(HOTKEY_ID_CALIBRATE)
        )
        self.btn_tgt_hotkey = QPushButton()
        self.btn_tgt_hotkey.clicked.connect(
            lambda: self._change_hotkey(HOTKEY_ID_TARGET)
        )
        hot_row.addWidget(self.btn_cal_hotkey)
        hot_row.addWidget(self.btn_tgt_hotkey)
        lay.addLayout(hot_row)

        # 操作行
        op_row = QHBoxLayout()
        self.btn_clear = QPushButton("清除")
        self.btn_clear.clicked.connect(self._on_clear)
        self.chk_topmost = QCheckBox("置顶")
        self.chk_topmost.setChecked(True)
        self.chk_topmost.toggled.connect(self._on_topmost_toggled)
        op_row.addWidget(self.btn_clear)
        op_row.addWidget(self.chk_topmost)
        op_row.addStretch(1)
        lay.addLayout(op_row)

        # 提示行
        self.lbl_hint = QLabel()
        self.lbl_hint.setObjectName("hint")
        self.lbl_hint.setWordWrap(True)
        lay.addWidget(self.lbl_hint)

    def _make_value_label(self) -> QLabel:
        label = QLabel("--")
        label.setObjectName("value")
        label.setAlignment(Qt.AlignmentFlag.AlignRight)
        return label

    def _apply_config_to_ui(self) -> None:
        self.lbl_ref_spin.setValue(self.config.reference_meters)
        if self.config.calibrated and self.config.ratio_m_per_px > 0:
            self.lbl_cal_ratio.setText(f"{self.config.ratio_m_per_px:.4f} m/px")
            self._hint(f"已载入校准比例：{self.config.ratio_m_per_px:.4f} m/px")

    def _register_hotkeys(self) -> None:
        ok_cal = self._try_register(HOTKEY_ID_CALIBRATE, self.config.hotkey_calibrate)
        ok_tgt = self._try_register(HOTKEY_ID_TARGET, self.config.hotkey_target)
        if not (ok_cal and ok_tgt):
            self._hint("热键注册失败（可能被占用），已降级为面板内快捷键")

    def _try_register(self, hotkey_id: int, name: str) -> bool:
        if name not in HOTKEY_NAMES_KNOWN:
            name = "+" if hotkey_id == HOTKEY_ID_CALIBRATE else "-"
            if hotkey_id == HOTKEY_ID_CALIBRATE:
                self.config.hotkey_calibrate = name
            else:
                self.config.hotkey_target = name
            self.config.save()
        ok = self.hotkeys.register(hotkey_id, name)
        self._update_hotkey_buttons()
        return ok

    def _update_hotkey_buttons(self) -> None:
        self.btn_cal_hotkey.setText(f"校准热键 {self.config.hotkey_calibrate}")
        self.btn_tgt_hotkey.setText(f"测距热键 {self.config.hotkey_target}")

    # ------------------------------------------------------------- 事件
    def nativeEvent(self, eventType, message):
        """处理全局热键 WM_HOTKEY。

        注意：不要调用 super().nativeEvent() —— Qt 6.11 在本机环境下
        窗口创建期间调用默认实现会导致原生崩溃（访问冲突）；直接返回
        (False, 0) 语义等价于未处理。
        """
        if eventType in ("windows_generic_MSG", b"windows_generic_MSG"):
            try:
                msg = wintypes.MSG.from_address(int(message))
            except (TypeError, ValueError):
                return False, 0
            if msg.message == WM_HOTKEY:
                if msg.wParam == HOTKEY_ID_CALIBRATE:
                    self._on_hotkey(SessionKind.CALIBRATE)
                    return True, 0
                if msg.wParam == HOTKEY_ID_TARGET:
                    self._on_hotkey(SessionKind.TARGET)
                    return True, 0
        return False, 0

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._cancel_session()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._cancel_session()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None

    def closeEvent(self, event):
        self.hotkeys.unregister_all()
        self.config.save()
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        # 不主动 setFocus：避免启动时抢走游戏窗口的键盘焦点
        # （点击面板控件时自然获得焦点，Esc/右键取消照常可用）

    # ------------------------------------------------------------- 热键处理
    def _on_hotkey(self, kind: SessionKind) -> None:
        hwnd = get_foreground_window()
        own = int(self.winId())
        if hwnd == own:
            # 前台是本工具：沿用上次目标窗口（鼠标在面板上，映射会拒绝）
            if self._last_target_hwnd is None:
                self._hint("未捕获到游戏窗口：请先切换到游戏再按键")
                return
            hwnd = self._last_target_hwnd
        else:
            self._last_target_hwnd = hwnd

        geo = get_window_client_origin_size(hwnd)
        if geo is None:
            self._hint("目标窗口不可见（已最小化或客户区无效）")
            return
        origin, size = geo

        pixel = screen_to_pixel(get_cursor_pos(), origin, size)
        if pixel is None:
            self._hint("鼠标不在目标窗口内，本次按键已忽略")
            return

        try:
            if kind == SessionKind.CALIBRATE:
                action, session = self.state.on_calibrate_press(pixel, origin, size)
            else:
                action, session = self.state.on_target_press(pixel, origin, size)
        except ValueError as exc:
            self.state.cancel()
            self._set_status("空闲", COLOR_IDLE)
            self._hint(str(exc))
            return

        self._dispatch(action, session, origin, size)

    def _dispatch(self, action, session, cur_origin, cur_size) -> None:
        if action == Action.START_CAL_A:
            self._set_status("校准：已选 A，移到第二点后按 +", COLOR_ACTIVE)
            self._hint("A 点已记录；移动鼠标到第二个已知点，再按校准热键结束")
        elif action == Action.START_TGT_A:
            self._set_status("测距：已选 A，移到目标另一端后按 -", COLOR_ACTIVE)
            self._hint("A 点已记录；移动鼠标到目标另一端，再按测距热键结束")
        elif action == Action.SET_CAL_B_FINISH:
            self._settle_calibrate(session, cur_origin, cur_size)
        elif action == Action.SET_TGT_B_FINISH:
            self._settle_target(session, cur_origin, cur_size)
        elif action == Action.REJECT_NO_CALIBRATION:
            self._hint("尚未校准：请先按校准热键（+）完成基准校准")
        elif action == Action.IGNORE_CROSS_KEY:
            self._hint("当前会话由另一个热键推进，本次按键已忽略")

    def _settle_calibrate(self, session: Session, cur_origin, cur_size) -> None:
        self._set_value(self.lbl_cal_px, session.px_dist, "px")
        self._set_value(self.lbl_cal_ratio, session.actual, "m/px", decimals=4)
        self.config.ratio_m_per_px = session.actual
        self.config.calibrated = True
        self.config.save()
        self._set_status("校准完成", COLOR_DONE)
        self._hint(f"比例已保存：{session.actual:.4f} m/px")
        self._warn_geometry(session, cur_origin, cur_size)

    def _settle_target(self, session: Session, cur_origin, cur_size) -> None:
        self._set_value(self.lbl_tgt_px, session.px_dist, "px")
        self._set_value(self.lbl_tgt_dist, session.actual, "米", decimals=2)
        self._set_status("测距完成", COLOR_DONE)
        self._hint(f"目标实际距离：{session.actual:.2f} 米（{session.px_dist:.1f} px）")
        self._warn_geometry(session, cur_origin, cur_size)

    def _warn_geometry(self, session: Session, cur_origin, cur_size) -> None:
        if window_geometry_changed(session.origin, session.size, cur_origin, cur_size):
            self._hint("注意：两次按键间窗口位置/大小发生变化，结果可能不准")

    # ------------------------------------------------------------- 工具方法
    def _set_value(self, label: QLabel, value: float, unit: str, decimals: int = 1) -> None:
        label.setText(f"{value:.{decimals}f} {unit}")

    def _set_status(self, text: str, color: str) -> None:
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(f"color: {color}; font-weight: bold;")

    def _hint(self, text: str) -> None:
        self.lbl_hint.setText(text)

    def _cancel_session(self) -> None:
        self.state.cancel()
        self._set_status("空闲", COLOR_IDLE)
        self._hint("已取消本次测距")

    def _on_clear(self) -> None:
        self.state.cancel()
        self.lbl_cal_px.setText("--")
        self.lbl_cal_ratio.setText("--")
        self.lbl_tgt_px.setText("--")
        self.lbl_tgt_dist.setText("--")
        self._set_status("空闲", COLOR_IDLE)
        self._hint("已清除测量结果")

    def _on_ref_changed(self, value: float) -> None:
        self.state.set_reference_meters(value)
        self.config.reference_meters = value
        self.config.save()

    def _on_topmost_toggled(self, checked: bool) -> None:
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked)
        self.show()

    def _change_hotkey(self, hotkey_id: int) -> None:
        dialog = HotkeyCaptureDialog(self)
        if dialog.exec() != HotkeyCaptureDialog.DialogCode.Accepted:
            return
        name = dialog.selected_name
        if name is None:
            return
        if not self.hotkeys.register(hotkey_id, name):
            self._hint(f"热键 {name} 注册失败（可能被占用），已保留原热键")
            return
        if hotkey_id == HOTKEY_ID_CALIBRATE:
            self.config.hotkey_calibrate = name
        else:
            self.config.hotkey_target = name
        self.config.save()
        self._update_hotkey_buttons()
        self._hint(f"热键已更改为 {name}")
