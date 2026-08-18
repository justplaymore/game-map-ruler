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

"""Windows API 封装（ctypes，仅依赖系统 user32/shcore，无需 pywin32）。

所有坐标均为物理像素（进程已声明 Per-Monitor DPI Aware）。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Optional, Tuple

user32 = ctypes.windll.user32

# RegisterHotKey 修饰键
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

WM_HOTKEY = 0x0312


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


# ---- 热键 ----
def register_hotkey(hwnd: int, hotkey_id: int, modifiers: int, vk: int) -> bool:
    return bool(user32.RegisterHotKey(wintypes.HWND(hwnd), hotkey_id, modifiers, vk))


def unregister_hotkey(hwnd: int, hotkey_id: int) -> bool:
    return bool(user32.UnregisterHotKey(wintypes.HWND(hwnd), hotkey_id))


# ---- 窗口信息 ----
def get_foreground_window() -> int:
    return int(user32.GetForegroundWindow())


def get_client_rect(hwnd: int) -> Tuple[int, int]:
    """客户区宽高；失败或无有效区域返回 (0, 0)。"""
    rect = RECT()
    if not user32.GetClientRect(wintypes.HWND(hwnd), ctypes.byref(rect)):
        return (0, 0)
    return (rect.right - rect.left, rect.bottom - rect.top)


def client_to_screen(hwnd: int, x: int, y: int) -> Tuple[int, int]:
    point = POINT(x, y)
    user32.ClientToScreen(wintypes.HWND(hwnd), ctypes.byref(point))
    return (point.x, point.y)


def get_window_client_origin_size(hwnd: int) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """返回 (客户区原点屏幕坐标, 客户区宽高)；窗口不可见/无效时返回 None。"""
    size = get_client_rect(hwnd)
    if size[0] <= 0 or size[1] <= 0:
        return None
    origin = client_to_screen(hwnd, 0, 0)
    return origin, size


# ---- 鼠标 ----
def get_cursor_pos() -> Tuple[int, int]:
    point = POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return (point.x, point.y)
