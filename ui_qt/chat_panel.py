# -*- coding: utf-8 -*-
"""PySide6 聊天面板：空状态 / 圆角气泡 / 思考折叠 / 输入融合容器 / 流式。"""

import html

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QTextEdit, QPushButton, QSizePolicy,
)
from PySide6.QtGui import QFont


def _esc(text: str) -> str:
    return html.escape(text).replace("\n", "<br/>")


def _md_inline(text: str) -> str:
    """极简行内 markdown → HTML（加粗/行内代码/换行）。"""
    t = _esc(text)
    import re
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r"<code style='background:#eef0f3;padding:1px 5px;border-radius:4px;'>\1</code>", t)
    return t


class ChatPanel(QWidget):
    def __init__(self, parent, on_send):
        super().__init__(parent)
        self.setObjectName("ChatArea")
        self.on_send = on_send
        self.busy = False
        self._stream_text = ""
        self._current_ai_frame = None
        self._current_ai_label = None
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("MessageScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.msg_host = QWidget()
        self.msg_lay = QVBoxLayout(self.msg_host)
        self.msg_lay.setContentsMargins(20, 16, 20, 16)
        self.msg_lay.setSpacing(10)
        self.msg_lay.addStretch(1)
        self.scroll.setWidget(self.msg_host)
        lay.addWidget(self.scroll, 1)

        self.empty = QWidget(self.scroll)
        self.empty.setAttribute(Qt.WA_TransparentForMouseEvents)
        el = QVBoxLayout(self.empty)
        el.setAlignment(Qt.AlignCenter)
        self.empty_icon = QLabel("✦")
        self.empty_icon.setAlignment(Qt.AlignCenter)
        self.empty_icon.setStyleSheet("font-size: 52px; color: #D8DBE0; font-weight: 300;")
        el.addWidget(self.empty_icon)
        self.empty_title = QLabel("开始你的学习")
        self.empty_title.setAlignment(Qt.AlignCenter)
        self.empty_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #111827; margin-top: 6px;")
        el.addWidget(self.empty_title)
        self.empty_hint = QLabel("新建课程 → 上传学习资料 → 与 AI 对话\n资料会自动整理成知识库（LLM Wiki）")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setStyleSheet("font-size: 12px; color: #9CA3AF; letter-spacing: 0.5px;")
        el.addWidget(self.empty_hint)
        self.empty.hide()

        input_area = QWidget()
        input_area.setObjectName("InputArea")
        ilay_outer = QVBoxLayout(input_area)
        ilay_outer.setContentsMargins(0, 10, 0, 14)
        inp_wrap = QWidget()
        inp_wrap.setObjectName("InputContainer")
        inp_wrap.setMaximumWidth(860)
        ilay = QHBoxLayout(inp_wrap)
        ilay.setContentsMargins(10, 4, 10, 4)
        ilay.setSpacing(8)
        self.input_box = QTextEdit()
        self.input_box.setObjectName("ChatInput")
        self.input_box.setPlaceholderText("输入问题，Enter 发送，Shift+Enter 换行")
        self.input_box.setFixedHeight(64)
        self.input_box.setAcceptRichText(False)
        ilay.addWidget(self.input_box, 1)
        self.send_btn = QPushButton("➤")
        self.send_btn.setObjectName("SendBtn")
        self.send_btn.setFixedSize(44, 44)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setToolTip("发送消息（Enter）")
        self.send_btn.clicked.connect(self._send_click)
        ilay.addWidget(self.send_btn)
        ilay_outer.addWidget(inp_wrap, 0, Qt.AlignHCenter)
        lay.addWidget(input_area)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "empty"):
            self.empty.setGeometry(self.scroll.viewport().rect())

    def _send_click(self):
        text = self.input_box.toPlainText().strip()
        if text and not self.busy:
            self.input_box.clear()
            self.on_send(text)

    def _show_empty(self):
        self.empty.show()
        self.empty.raise_()

    def _hide_empty(self):
        self.empty.hide()

    def _has_messages(self) -> bool:
        return self.msg_lay.count() > 1

    def _make_bubble(self, role: str, name: str, align_right: bool) -> tuple[QFrame, QLabel]:
        if not self._has_messages():
            self._hide_empty()
        outer = QFrame()
        ol = QVBoxLayout(outer)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.setSpacing(4)
        if not align_right:
            nm = QLabel(name)
            nm.setObjectName("BubbleName")
            ol.addWidget(nm)
        bubble = QFrame()
        bubble.setObjectName("BubbleUser" if align_right else "BubbleAI")
        bl = QVBoxLayout(bubble)
        bl.setContentsMargins(12, 8, 12, 8)
        label = QLabel()
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        label.setOpenExternalLinks(False)
        bl.addWidget(label)
        if not align_right:
            bubble.setMaximumWidth(760)
        ol.addWidget(bubble)
        if align_right:
            outer.setMaximumWidth(760)
        self.msg_lay.insertWidget(self.msg_lay.count() - 1, outer)
        self._scroll_bottom()
        return bubble, label

    def add_user(self, text: str):
        self._make_bubble("user", "你", align_right=True)[1].setText(_md_inline(text))

    def add_ai_static(self, text: str):
        self._make_bubble("ai", "DeepSeek", align_right=False)[1].setText(_md_inline(text))

    def add_ai_stream_start(self):
        self._current_ai_frame, self._current_ai_label = self._make_bubble(
            "ai", "DeepSeek", align_right=False)
        self._stream_text = ""

    def add_ai_stream_chunk(self, chunk: str):
        if self._current_ai_label is None:
            self.add_ai_stream_start()
        self._stream_text += chunk
        self._current_ai_label.setText(_md_inline(self._stream_text) + "▌")
        self._scroll_bottom()

    def add_ai_thinking(self, text: str):
        if not text:
            return
        if self._current_ai_frame is None:
            self.add_ai_stream_start()
        head = QLabel("思考过程（点击展开）")
        head.setObjectName("ThinkingHead")
        head.setCursor(Qt.PointingHandCursor)
        box = QFrame()
        box.setObjectName("BubbleAI")
        bl = QVBoxLayout(box)
        bl.setContentsMargins(10, 6, 10, 6)
        lab = QLabel(_md_inline(text[:2000]))
        lab.setWordWrap(True)
        lab.setTextFormat(Qt.RichText)
        lab.setStyleSheet("color: #9aa0a6; font-size: 12px;")
        bl.addWidget(lab)
        box.hide()
        layout = self._current_ai_frame.layout()
        layout.insertWidget(layout.count() - 1, head)
        layout.insertWidget(layout.count() - 1, box)

        def toggle(_=None):
            box.setVisible(not box.isVisible())
            head.setText("思考过程（点击收起）" if box.isVisible() else "思考过程（点击展开）")
            self._scroll_bottom()

        head.mousePressEvent = toggle

    def add_ai_done(self, text: str, usage):
        if self._current_ai_label is None:
            self.add_ai_static(text)
        else:
            self._current_ai_label.setText(_md_inline(text))
            self._current_ai_label = None
            self._current_ai_frame = None
        if usage:
            hit = usage.hit_ratio
            info = QLabel(f"缓存命中 {hit*100:.0f}% · 输入 {usage.prompt_tokens} · 输出 {usage.completion_tokens}")
            info.setObjectName("BubbleName")
            info.setStyleSheet("color: #9aa0a6; font-size: 11px;")
            self.msg_lay.insertWidget(self.msg_lay.count() - 1, info)
        self._scroll_bottom()

    def clear_all(self):
        while self.msg_lay.count() > 1:
            item = self.msg_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._current_ai_label = None
        self._current_ai_frame = None
        self._stream_text = ""
        self._show_empty()

    def set_busy(self, busy: bool):
        self.busy = busy
        self.send_btn.setEnabled(not busy)

    def _scroll_bottom(self):
        bar = self.scroll.verticalScrollBar()
        QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))
