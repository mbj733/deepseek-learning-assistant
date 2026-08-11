#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DeepSeek 学习助手 v5 — PySide6 现代 UI。

启动入口：python app.py
"""

import os
import sys

# 支持从任意位置运行（含 PyInstaller 打包）
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from core.config import Config
from ui_qt.main_window import MainWindow
from PySide6.QtWidgets import QApplication


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DeepSeek 学习助手")
    config = Config()
    win = MainWindow(config)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
