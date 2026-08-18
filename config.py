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

"""config.json 读写：热键、基准实际距离、校准比例。

配置保存在本文件同级目录的 config.json，损坏或缺失时回退默认值。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

DEFAULTS: Dict[str, Any] = {
    "hotkey_calibrate": "+",      # 功能1：建立校准基准比例
    "hotkey_target": "-",         # 功能2：测距（目标实际距离）
    "reference_meters": 300.0,    # 基准实际距离（米）
    "ratio_m_per_px": 0.0,        # 校准比例（米/像素）
    "calibrated": False,          # 是否已完成校准
}


class Config:
    def __init__(self, path: str | Path = DEFAULT_CONFIG_PATH):
        self.path = Path(path)
        self.data: Dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return  # 损坏配置：保留默认值
        if isinstance(loaded, dict):
            for key in DEFAULTS:
                if key in loaded:
                    self.data[key] = loaded[key]

    def save(self) -> None:
        try:
            self.path.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass  # 目录只读等场景：静默失败，不影响运行

    # ---- 便捷属性 ----
    @property
    def hotkey_calibrate(self) -> str:
        return self.data["hotkey_calibrate"]

    @hotkey_calibrate.setter
    def hotkey_calibrate(self, value: str) -> None:
        self.data["hotkey_calibrate"] = value

    @property
    def hotkey_target(self) -> str:
        return self.data["hotkey_target"]

    @hotkey_target.setter
    def hotkey_target(self, value: str) -> None:
        self.data["hotkey_target"] = value

    @property
    def reference_meters(self) -> float:
        return float(self.data["reference_meters"])

    @reference_meters.setter
    def reference_meters(self, value: float) -> None:
        self.data["reference_meters"] = float(value)

    @property
    def ratio_m_per_px(self) -> float:
        return float(self.data["ratio_m_per_px"])

    @ratio_m_per_px.setter
    def ratio_m_per_px(self, value: float) -> None:
        self.data["ratio_m_per_px"] = float(value)

    @property
    def calibrated(self) -> bool:
        return bool(self.data["calibrated"])

    @calibrated.setter
    def calibrated(self, value: bool) -> None:
        self.data["calibrated"] = bool(value)
