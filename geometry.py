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

"""纯几何/换算函数：像素距离、校准比例、目标距离、屏幕坐标映射。

本模块不依赖 Qt / win32，可独立单元测试。
坐标约定：像素坐标以游戏窗口客户区左上角为原点；屏幕坐标为物理像素。
"""

from __future__ import annotations

from typing import Optional, Tuple

Point = Tuple[int, int]


def screen_to_pixel(cursor: Point, origin: Point, size: Point) -> Optional[Point]:
    """屏幕坐标 → 客户区像素坐标。

    cursor 为鼠标的屏幕坐标；origin 为客户区原点（屏幕坐标）；
    size 为客户区宽高。鼠标不在客户区内返回 None。
    """
    px = cursor[0] - origin[0]
    py = cursor[1] - origin[1]
    if px < 0 or py < 0 or px >= size[0] or py >= size[1]:
        return None
    return (px, py)


def pixel_distance(a: Point, b: Point) -> float:
    """两点间欧氏像素距离。"""
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def calibrate(reference_meters: float, pixel_distance_px: float) -> float:
    """校准比例：每像素对应的实际米数 = 基准实际距离 / 基准像素距离。"""
    if reference_meters <= 0:
        raise ValueError("基准实际距离必须大于 0")
    if pixel_distance_px <= 0:
        raise ValueError("基准像素距离必须大于 0（两点不能重合）")
    return reference_meters / pixel_distance_px


def target_distance(pixel_distance_px: float, ratio_m_per_px: float) -> float:
    """目标实际距离 = 目标像素距离 × 校准比例。"""
    if pixel_distance_px < 0 or ratio_m_per_px < 0:
        raise ValueError("像素距离与比例不能为负")
    return pixel_distance_px * ratio_m_per_px


def window_geometry_changed(
    old_origin: Point, old_size: Point, new_origin: Point, new_size: Point
) -> bool:
    """两次按键间窗口客户区几何（原点/尺寸）是否发生变化。"""
    return old_origin != new_origin or old_size != new_size
