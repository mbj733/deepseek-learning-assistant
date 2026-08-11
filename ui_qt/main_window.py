# -*- coding: utf-8 -*-
"""PySide6 主窗口：顶栏 + 三栏（侧栏 / 聊天 / 预览）+ 底部状态。

引擎层（core/wiki/features）完全复用；本层只负责 UI 与线程桥接。
"""

import os
import threading

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter,
    QToolButton, QStatusBar, QMessageBox, QInputDialog,
)

from core.config import Config
from core.conversation import ConversationBuilder
from core.deepseek_client import DeepSeekClient
from features.cards import CardSystem
from features.sessions import ChatStore, SessionManager
from wiki.ingest import IngestEngine
from wiki.project import Project
from wiki.retriever import Retriever

from ui_qt.theme import build_light_qss, build_dark_qss
from ui_qt.sidebar import Sidebar
from ui_qt.chat_panel import ChatPanel
from ui_qt.preview import PreviewPanel


class _Bridge(QObject):
    """线程 → UI 信号桥。"""
    stream_content = Signal(str)
    stream_reasoning = Signal(str)
    chat_done = Signal(str, object)
    chat_error = Signal(str)
    ingest_progress = Signal(str, str)
    ingest_done = Signal(dict)


class MainWindow(QMainWindow):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.dark = config.get("theme", "light") == "dark"
        self.bridge = _Bridge()

        self.sm = SessionManager()
        self.conv = ConversationBuilder(config.snapshot())
        self.current_sid = None
        self.project = None
        self.chat_store = None
        self.cards = None
        self.retriever = None
        self._course_ctx = ""
        self._ctx_dirty = True

        self._build_ui()
        self._connect_bridge()
        self.apply_theme()
        self.refresh_sessions()

    def _build_ui(self):
        self.setWindowTitle("DeepSeek 学习助手")
        self.resize(1280, 800)
        self.setMinimumSize(1040, 660)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.sidebar = Sidebar(self)
        self.chat = ChatPanel(self, self.on_send)
        self.preview = PreviewPanel(self)
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.chat)
        self.splitter.addWidget(self.preview)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        self.splitter.setSizes([280, 640, 340])
        root.addWidget(self.splitter, 1)

        self.status = QStatusBar()
        self.status.setObjectName("StatusBar")
        self.status.showMessage("就绪")
        root.addWidget(self.status)

        self.sidebar.on_select_project = self.switch_session
        self.sidebar.on_new_project = self.create_session
        self.sidebar.on_upload = self.upload_files
        self.sidebar.on_ingest = self.run_ingest
        self.sidebar.on_open_page = self.open_page
        self.sidebar.on_open_file = self.preview_file
        self.sidebar.on_remove_file = self.remove_file
        self.sidebar.on_cards = self.open_cards

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("TopBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 10, 20, 10)

        self.title_label = QLabel("DeepSeek 学习助手")
        self.title_label.setObjectName("AppTitle")
        lay.addWidget(self.title_label)
        self.sub_label = QLabel("")
        self.sub_label.setObjectName("AppSub")
        lay.addWidget(self.sub_label)
        lay.addStretch(1)

        def icon_btn(text, tip, slot):
            b = QToolButton()
            b.setObjectName("TopIcon")
            b.setText(text)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(slot)
            lay.addWidget(b)
            return b

        self.btn_ingest = icon_btn("✦", "整理知识库（LLM Wiki ingest）", self.run_ingest)
        self.btn_settings = icon_btn("⚙", "设置", self.open_settings)
        self.btn_theme = icon_btn("🌙", "切换深浅色", self.toggle_theme)
        return bar

    def apply_theme(self):
        if self.dark:
            self.setStyleSheet(build_dark_qss())
            self.btn_theme.setText("☀")
        else:
            self.setStyleSheet(build_light_qss())
            self.btn_theme.setText("🌙")
        self.preview.set_dark(self.dark)

    def toggle_theme(self):
        self.dark = not self.dark
        self.config.set("theme", "dark" if self.dark else "light")
        self.apply_theme()

    def refresh_sessions(self, keep: str = None):
        rows = self.sm.get_all()
        items = [(r["id"], r["name"]) for r in rows]
        self.sidebar.set_projects(items, keep or self.current_sid)
        if not items:
            self.title_label.setText("DeepSeek 学习助手")
            self.sub_label.setText("未选择课程")
            self.chat.clear_all()
            return
        if not self.current_sid or self.current_sid not in [i[0] for i in items]:
            self.switch_session(items[0][0])

    def switch_session(self, sid: str):
        self.current_sid = sid
        name = self.sm.get_name(sid)
        self.project = Project(sid, name)
        self.project.ensure_wiki(name)
        self.chat_store = ChatStore(sid)
        self.cards = CardSystem(sid)
        self.retriever = Retriever(self.project, top_k=int(self.config.get("top_k", 6)))
        self._ctx_dirty = True
        self.title_label.setText(name)
        self.sub_label.setText(f"{len(self.cards.get_cards())} 张卡片")
        self.sidebar.set_current_project(sid, name)
        self.refresh_wiki_tree()
        self.refresh_files()
        self.restore_chat()

    def create_session(self):
        name, ok = QInputDialog.getText(self, "新建课程", "课程名称：")
        if not ok or not name.strip():
            return
        sid = self.sm.create(name.strip())
        self.refresh_sessions(keep=sid)

    def open_settings(self):
        from ui_qt.dialogs import show_settings
        show_settings(self, self.config, on_save=self._after_settings)

    def _after_settings(self):
        self.conv = ConversationBuilder(self.config.snapshot())
        if self.current_sid:
            self.retriever = Retriever(self.project, top_k=int(self.config.get("top_k", 6)))
        self.status.showMessage("设置已保存")

    def refresh_wiki_tree(self):
        if not self.project:
            return
        self.sidebar.set_wiki_tree(self.project.list_wiki_pages())

    def refresh_files(self):
        if not self.project:
            return
        rows = self.project.db.fetchall(
            "SELECT * FROM knowledge_files WHERE session_id=?", (self.current_sid,))
        self.sidebar.set_files([dict(r) for r in rows])

    def open_page(self, rel: str):
        if not rel:
            return
        content = self.project.read_wiki_page(rel) or self.project.read_wiki(rel.replace("wiki/", ""))
        if content:
            self.preview.show_markdown(rel, content)

    def preview_file(self, name: str):
        if not name:
            return
        row = self.project.db.fetchone(
            "SELECT file_path FROM knowledge_files WHERE session_id=? AND file_name=?",
            (self.current_sid, name))
        if row and row["file_path"] and os.path.exists(row["file_path"]):
            from wiki.project import extract_text
            self.preview.show_plain(name, extract_text(row["file_path"]) or "（无文本内容）")

    def upload_files(self):
        if not self.project:
            self._warn("请先选择课程")
            return
        from PySide6.QtWidgets import QFileDialog
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择学习资料",
            filter="文档 (*.pdf *.docx *.pptx *.txt *.md *.markdown *.html);;所有文件 (*.*)")
        if not paths:
            return
        ok_n = 0
        for p in paths:
            if p.lower().endswith((".pdf", ".docx", ".pptx", ".txt", ".md", ".markdown", ".html")):
                ok, msg, _ = self.project.import_file(p)
                ok_n += 1 if ok else 0
            else:
                self.status.showMessage(f"不支持格式：{os.path.basename(p)}", 3000)
        self._ctx_dirty = True
        self.refresh_files()
        if ok_n:
            self.run_ingest()

    def run_ingest(self):
        client = self._client()
        if not client:
            self._warn("未配置 API Key，请先在设置中填写")
            return
        if not self.project:
            self._warn("请先选择课程")
            return
        self.status.showMessage("正在整理知识库…")

        def worker():
            engine = IngestEngine(self.project, client,
                                  language=self.config.get("ingest_language", "zh"))
            stats = engine.ingest_pending(on_progress=lambda info: self.bridge.ingest_progress.emit(
                info["name"], info["msg"]))
            self.bridge.ingest_done.emit(stats)

        threading.Thread(target=worker, daemon=True).start()

    def _client(self):
        key = self.config.get("api_key", "")
        if not key:
            return None
        return DeepSeekClient(key, model=self.config.get("model", "deepseek-v4-flash"))

    def _course_context(self) -> str:
        if not self._ctx_dirty or not self.project:
            return self._course_ctx
        parts = []
        purpose = self.project.read_wiki("purpose.md")
        if purpose:
            from core.tokenizer import trim_to_budget
            parts.append("【课程目标】\n" + trim_to_budget(purpose, 400))
        index = self.project.read_wiki("index.md")
        if index and index.strip():
            entries = [ln for ln in index.split("\n") if ln.strip().startswith("- [")]
            if entries:
                parts.append("【已学条目】\n" + "\n".join(entries[:20]))
        self._course_ctx = "\n\n".join(parts)
        self._ctx_dirty = False
        return self._course_ctx

    def on_send(self, user_text: str):
        client = self._client()
        if not client:
            self.chat.add_user(user_text)
            self.chat.add_ai_stream_start()
            self.chat.add_ai_done("未配置 API Key。请点击右上角 ⚙ 设置填写。", None)
            return
        if not self.current_sid:
            self._warn("请先选择课程")
            return
        self.chat.add_user(user_text)
        self.chat.set_busy(True)
        self.bridge.stream_reasoning.emit("")

        def worker():
            try:
                retrieval = self.retriever.retrieve(user_text)
                history = [(m["role"], m["content"]) for m in
                           self.chat_store.load_messages(limit=100)]
                summary = self.chat_store.get_summary()
                messages, stats = self.conv.build(
                    user_text=user_text,
                    retrieval_context=retrieval["context"],
                    course_context=self._course_context(),
                    summary=summary,
                    history=history,
                )
                full, reasoning, usage = "", "", None
                for kind, chunk in client.chat_stream(messages):
                    if kind == "reasoning":
                        reasoning += chunk
                        if len(reasoning) > 3000:
                            reasoning = reasoning[:3000]
                    elif kind == "content":
                        full += chunk
                        self.bridge.stream_content.emit(chunk)
                    elif kind == "usage":
                        usage = chunk
                if reasoning:
                    self.bridge.stream_reasoning.emit(reasoning)
                self.chat_store.save_message("user", user_text)
                self.chat_store.save_message("assistant", full)
                self._maybe_compress(history + [("user", user_text), ("assistant", full)])
                self.bridge.chat_done.emit(full or "(无输出)", usage)
            except Exception as e:
                self.bridge.chat_error.emit(str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _maybe_compress(self, history: list):
        try:
            if not self.conv.needs_compress(history):
                return
            keep_part, block_text = self.conv.compress_blocks(history)
            if not block_text:
                return
            client = self._client()
            if not client:
                return
            messages = [{"role": "system", "content": "你是对话摘要器。"},
                        {"role": "user", "content": self.conv.__class__.COMPRESS_PROMPT.format(history=block_text)}]
            result = client.chat_once(messages, temperature=0.1, max_tokens=400)
            if result.content.strip():
                self.chat_store.save_summary(result.content.strip(), self.chat_store.last_message_id())
        except Exception:
            pass

    def remove_file(self, name: str):
        if not name:
            return
        if QMessageBox.question(self, "移除文件", f"移除「{name}」？") == QMessageBox.Yes:
            self.project.remove_file(name)
            self._ctx_dirty = True
            self.refresh_files()
            self.refresh_wiki_tree()

    def open_cards(self):
        if not self.project:
            self._warn("请先选择课程")
            return
        from ui_qt.dialogs import manage_cards
        manage_cards(self, self.cards, self.sidebar.set_card_stat)

    def restore_chat(self):
        self.chat.clear_all()
        if not self.chat_store:
            return
        for m in self.chat_store.load_messages(limit=40):
            if m["role"] == "user":
                self.chat.add_user(m["content"])
            elif m["role"] == "assistant":
                self.chat.add_ai_static(m["content"])

    def _warn(self, text: str):
        QMessageBox.information(self, "提示", text)

    def _connect_bridge(self):
        self.bridge.stream_content.connect(self.chat.add_ai_stream_chunk)
        self.bridge.stream_reasoning.connect(self.chat.add_ai_thinking)
        self.bridge.chat_done.connect(self._chat_done)
        self.bridge.chat_error.connect(self._chat_error)
        self.bridge.ingest_progress.connect(
            lambda name, msg: self.status.showMessage(f"整理中：{name} {msg}"))
        self.bridge.ingest_done.connect(self._ingest_done)

    def _chat_done(self, text, usage):
        self.chat.add_ai_done(text, usage)
        self.chat.set_busy(False)

    def _chat_error(self, msg):
        self.chat.add_ai_done(f"出错了：{msg}", None)
        self.chat.set_busy(False)
        self.status.showMessage("错误", 3000)

    def _ingest_done(self, stats):
        self.status.showMessage(
            f"整理完成：新增 {stats['processed']} / 跳过 {stats['skipped']} / 失败 {stats['failed']}", 6000)
        self._ctx_dirty = True
        self.refresh_wiki_tree()
        self.refresh_files()
