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

"""热键：名称 ↔ (修饰键, 虚拟键码) 映射、注册管理、热键捕获对话框。

注意：键盘上的 "+" 即 Shift+"="，RegisterHotKey 必须带 MOD_SHIFT
才能只在按 "+" 时触发（单独按 "=" 不触发）。
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout

from winapi import MOD_SHIFT, register_hotkey, unregister_hotkey

ModifierVk = Tuple[int, int]

# 热键名称 → (修饰键, 虚拟键码)
KEY_MAP: Dict[str, ModifierVk] = {}

for _ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
    KEY_MAP[_ch] = (0, ord(_ch))
for _i in range(12):
    KEY_MAP[f"F{_i + 1}"] = (0, 0x70 + _i)
KEY_MAP["+"] = (MOD_SHIFT, 0xBB)  # Shift+= → "+"
KEY_MAP["="] = (0, 0xBB)
KEY_MAP["-"] = (0, 0xBD)

HOTKEY_NAMES_KNOWN = frozenset(KEY_MAP)


def qt_key_to_name(key) -> Optional[str]:
    """Qt 按键 → 热键名称；不支持的按键返回 None。"""
    if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
        return chr(int(key))
    if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
        return chr(int(key))
    if key == Qt.Key.Key_Plus:
        return "+"
    if key == Qt.Key.Key_Minus:
        return "-"
    if key == Qt.Key.Key_Equal:
        return "="
    if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
        return f"F{int(key) - int(Qt.Key.Key_F1) + 1}"
    return None


class HotkeyManager:
    """基于 RegisterHotKey 的全局热键注册管理（需与 Qt 窗口句柄绑定）。"""

    def __init__(self, hwnd: int):
        self.hwnd = hwnd
        self._registered: Dict[int, ModifierVk] = {}

    def register(self, hotkey_id: int, name: str) -> bool:
        """注册热键；同 id 已注册则先注销。名称不合法或注册失败返回 False。"""
        if name not in KEY_MAP:
            return False
        mods, vk = KEY_MAP[name]
        if hotkey_id in self._registered:
            unregister_hotkey(self.hwnd, hotkey_id)
            del self._registered[hotkey_id]
        if register_hotkey(self.hwnd, hotkey_id, mods, vk):
            self._registered[hotkey_id] = (mods, vk)
            return True
        return False

    def unregister_all(self) -> None:
        for hotkey_id in list(self._registered):
            unregister_hotkey(self.hwnd, hotkey_id)
        self._registered.clear()


class HotkeyCaptureDialog(QDialog):
    """捕获用户按下的新热键。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("更改热键")
        self.setModal(True)
        self.setMinimumWidth(260)
        self.selected_name: Optional[str] = None
        layout = QVBoxLayout(self)
        self._label = QLabel("请按下新快捷键…（Esc 取消）")
        self._label.setWordWrap(True)
        layout.addWidget(self._label)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        name = qt_key_to_name(event.key())
        if name is None:
            self._label.setText(
                "不支持的按键，请重试（支持 A–Z、0–9、F1–F12、+、-、=）"
            )
            return
        self.selected_name = name
        self.accept()
