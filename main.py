"""入口：QApplication → MainWindow（置顶 HUD 面板）。

注意：Qt 6 在 Windows 上默认启用 Per-Monitor V2 DPI 感知，
不要再手动调用 SetProcessDpiAwareness（重复设置会冲突导致崩溃），
GetCursorPos / ClientToScreen 与 mss 坐标因此保持一致。
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("游戏像素测距")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
