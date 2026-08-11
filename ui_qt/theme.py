# -*- coding: utf-8 -*-
"""PySide6 主题 — 高级感：深色主按钮 / 灰阶体系 / 圆形发送 / 深浅两套。

配色体系：主背景 #FAFAFA · 面板 #FFFFFF · 侧栏 #F3F4F6 · 边框 #E8EAED
文字 #111827/#374151/#6B7280 三层级 · 强调橙 #E2563A（点缀）
"""

ACCENT = "#E2563A"
ACCENT_HOVER = "#C2410C"
ACCENT_SOFT = "#FDF0ED"
DARK_BTN = "#1A1A1A"
DARK_BTN_HOVER = "#333333"

FONT_FAMILY = '"Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif'


def build_qss(dark: bool) -> str:
    if dark:
        bg = "#161719"; panel = "#1E2022"; panel2 = "#26282B"
        sidebar = "#1A1B1D"; border = "#2E3033"
        text = "#E8EAED"; body = "#C9CDD3"; muted = "#8A9099"
        accent = "#E27052"; accent_hover = "#EE8A6E"; accent_soft = "#382620"
        btn = "#F0F1F2"; btn_hover = "#FFFFFF"
        input_bg = "#232527"; input_border = "#3A3D41"
        send_bg = "#F0F1F2"; send_fg = "#161719"
        bubble_ai = "#1E2022"
    else:
        bg = "#FAFAFA"; panel = "#FFFFFF"; panel2 = "#F3F4F6"
        sidebar = "#F3F4F6"; border = "#E8EAED"
        text = "#111827"; body = "#374151"; muted = "#6B7280"
        accent = ACCENT; accent_hover = ACCENT_HOVER; accent_soft = ACCENT_SOFT
        btn = DARK_BTN; btn_hover = DARK_BTN_HOVER
        input_bg = "#FFFFFF"; input_border = "#D8DBE0"
        send_bg = DARK_BTN; send_fg = "#FFFFFF"
        bubble_ai = "#FFFFFF"

    return f"""
* {{
    font-family: {FONT_FAMILY};
    font-size: 13px;
    color: {body};
}}
QMainWindow, QDialog {{
    background: {bg};
}}
QScrollArea {{ background: {bg}; }}
QScrollArea > QWidget > QWidget {{ background: {bg}; }}
QListWidget, QTreeWidget, QTextBrowser, QTabWidget {{ background: transparent; }}

#TopBar {{
    background: {bg};
}}
#AppTitle {{
    font-size: 15px;
    font-weight: 700;
    color: {text};
}}
#AppSub {{
    font-size: 11px;
    color: {muted};
}}
QToolButton#TopIcon {{
    background: transparent;
    border: none;
    border-radius: 7px;
    padding: 5px;
    font-size: 15px;
    color: {muted};
}}
QToolButton#TopIcon:hover {{
    background: {panel2};
    color: {text};
}}

#Sidebar {{
    background: {sidebar};
}}
#SidebarTitle {{
    font-size: 11px;
    font-weight: 600;
    color: {muted};
    padding: 2px 4px;
}}
QListWidget#ProjectList, QTreeWidget#WikiTree, QListWidget#FileList {{
    background: transparent;
    border: none;
    outline: none;
    padding: 4px;
}}
QListWidget#ProjectList::item, QTreeWidget#WikiTree::item, QListWidget#FileList::item {{
    border-radius: 6px;
    padding: 7px 10px;
    margin: 2px 4px;
    color: {body};
}}
QListWidget#ProjectList::item:hover, QTreeWidget#WikiTree::item:hover, QListWidget#FileList::item:hover {{
    background: {panel};
}}
QListWidget#ProjectList::item:selected, QTreeWidget#WikiTree::item:selected, QListWidget#FileList::item:selected {{
    background: {accent_soft};
    color: {text};
    font-weight: 600;
}}
QTabWidget#SideTabs::pane {{
    border: none;
    background: transparent;
}}
QTabBar#SideTabs::tab {{
    background: transparent;
    color: {muted};
    padding: 5px 16px;
    border-radius: 6px;
    margin: 1px 3px;
    font-size: 12px;
}}
QTabBar#SideTabs::tab:selected {{
    background: {panel};
    color: {text};
    font-weight: 600;
}}
QTabBar#SideTabs::tab:hover {{ color: {text}; }}
QComboBox {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 7px;
    padding: 6px 10px;
    color: {body};
}}
QComboBox:hover {{ border-color: {muted}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}

#ChatArea {{
    background: {bg};
}}
#MessageScroll {{
    background: {bg};
    border: none;
}}
#BubbleUser {{
    background: {accent_soft};
    border-radius: 12px;
    border: none;
}}
#BubbleAI {{
    background: {bubble_ai};
    border-radius: 14px;
    border: 1px solid {border};
}}
#BubbleName {{
    font-size: 11px;
    font-weight: 600;
    color: {muted};
}}
#ThinkingHead {{
    background: transparent;
    border: none;
    color: {muted};
    font-size: 11px;
}}
#ThinkingHead:hover {{ color: {accent}; }}

#InputArea {{
    background: {bg};
}}
#InputContainer {{
    background: {panel};
    border: 1px solid {border};
    border-bottom: 2px solid {border};
    border-radius: 12px;
}}
#InputContainer:focus-within {{
    border: 1px solid {muted};
    border-bottom: 2px solid {muted};
}}
#ChatInput {{
    background: transparent;
    border: none;
    padding: 8px 8px;
    font-size: 14px;
    color: {body};
}}
#SendBtn {{
    background: {send_bg};
    color: {send_fg};
    border: none;
    border-radius: 22px;
    font-size: 15px;
}}
#SendBtn:hover {{ background: {btn_hover}; }}
#SendBtn:pressed {{ background: {send_bg}; }}
#SendBtn:disabled {{
    background: {panel2};
    color: {muted};
}}
#GhostBtn {{
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    color: {muted};
}}
#GhostBtn:hover {{ background: {panel}; color: {text}; }}
#StatusBar {{
    background: {panel2};
    border-top: 1px solid {border};
    color: {muted};
    font-size: 11px;
}}

#PreviewPanel {{
    background: {panel};
    border-left: 1px solid {border};
}}
#PreviewTitle {{
    font-size: 11px;
    font-weight: 600;
    color: {muted};
}}
#PreviewText {{
    background: transparent;
    border: none;
    color: {body};
    font-size: 13px;
}}

QPushButton {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 7px;
    padding: 6px 14px;
    color: {body};
}}
QPushButton:hover {{ border-color: {muted}; color: {text}; }}
QPushButton#Primary {{
    background: {btn};
    color: {send_fg};
    border: none;
    font-weight: 500;
}}
QPushButton#Primary:hover {{ background: {btn_hover}; }}
QPushButton#Danger {{ color: #DC2626; }}
QPushButton#Danger:hover {{ border-color: #DC2626; color: #DC2626; }}

QScrollBar:vertical {{
    background: transparent; width: 8px; margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {border}; border-radius: 4px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {muted}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {border}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; }}

QDialog QLabel {{ color: {body}; }}
QLineEdit, QPlainTextEdit, QTextEdit {{
    background: {input_bg};
    border: 1px solid {input_border};
    border-radius: 7px;
    padding: 6px 10px;
    color: {body};
    selection-background-color: {accent};
    selection-color: #FFFFFF;
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{ border-color: {accent}; }}
QDialog QPushButton {{
    min-width: 80px;
}}
"""


def build_dark_qss() -> str:
    return build_qss(True)


def build_light_qss() -> str:
    return build_qss(False)
