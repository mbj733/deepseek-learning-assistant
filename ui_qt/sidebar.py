# -*- coding: utf-8 -*-
"""PySide6 侧栏：课程列表 + 知识/文件双标签 + 底部卡片区。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QTreeWidget, QTreeWidgetItem, QTabWidget, QFrame,
    QToolButton, QMenu,
)


class Sidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(272)
        self._project_items: dict[str, QListWidgetItem] = {}
        self._page_map: dict[QTreeWidgetItem, str] = {}
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 14, 10, 10)
        lay.setSpacing(8)
        head = QHBoxLayout()
        t = QLabel("课程（项目）")
        t.setObjectName("SidebarTitle")
        head.addWidget(t)
        head.addStretch(1)
        self.btn_new = QToolButton()
        self.btn_new.setText("＋")
        self.btn_new.setObjectName("TopIcon")
        self.btn_new.setToolTip("新建课程")
        self.btn_new.setCursor(Qt.PointingHandCursor)
        self.btn_new.clicked.connect(lambda: self.on_new_project and self.on_new_project())
        head.addWidget(self.btn_new)
        lay.addLayout(head)
        self.project_list = QListWidget()
        self.project_list.setObjectName("ProjectList")
        self.project_list.itemClicked.connect(self._project_clicked)
        lay.addWidget(self.project_list)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("SideTabs")
        self.tabs.setDocumentMode(True)
        self.tree = QTreeWidget()
        self.tree.setObjectName("WikiTree")
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self._page_double)
        self.tabs.addTab(self.tree, "知识")
        files_w = QWidget()
        fv = QVBoxLayout(files_w)
        fv.setContentsMargins(0, 4, 0, 0)
        fv.setSpacing(6)
        fh = QHBoxLayout()
        fl = QLabel("学习资料")
        fl.setObjectName("SidebarTitle")
        fh.addWidget(fl)
        fh.addStretch(1)
        self.btn_upload = QPushButton("上传")
        self.btn_upload.setCursor(Qt.PointingHandCursor)
        self.btn_upload.setToolTip("上传学习资料（PDF / Word / PPT / TXT / Markdown）")
        self.btn_upload.clicked.connect(lambda: self.on_upload and self.on_upload())
        fh.addWidget(self.btn_upload)
        fv.addLayout(fh)
        self.file_list = QListWidget()
        self.file_list.setObjectName("FileList")
        self.file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self._file_menu)
        self.file_list.itemDoubleClicked.connect(
            lambda item: self.on_open_file and self.on_open_file(item.text()))
        fv.addWidget(self.file_list)
        self.tabs.addTab(files_w, "文件")
        lay.addWidget(self.tabs, 1)
        foot = QHBoxLayout()
        foot.setContentsMargins(4, 8, 4, 4)
        self.btn_cards = QPushButton("▦ 学习卡片")
        self.btn_cards.setObjectName("GhostBtn")
        self.btn_cards.setCursor(Qt.PointingHandCursor)
        self.btn_cards.setToolTip("管理学习卡片（创建 / 复习 / 删除）")
        self.btn_cards.clicked.connect(lambda: self.on_cards and self.on_cards())
        foot.addWidget(self.btn_cards)
        self.card_stat = QLabel("0 张")
        self.card_stat.setObjectName("AppSub")
        foot.addWidget(self.card_stat)
        foot.addStretch(1)
        self.btn_ingest = QPushButton("整理知识")
        self.btn_ingest.setObjectName("Primary")
        self.btn_ingest.setCursor(Qt.PointingHandCursor)
        self.btn_ingest.setToolTip("把课程资料整理成知识库（LLM Wiki ingest）")
        self.btn_ingest.clicked.connect(lambda: self.on_ingest and self.on_ingest())
        foot.addWidget(self.btn_ingest)
        lay.addLayout(foot)

    def set_projects(self, items: list[tuple[str, str]], current: str = None):
        self.project_list.clear()
        self._project_items = {}
        for sid, name in items:
            it = QListWidgetItem(name)
            it.setData(Qt.UserRole, sid)
            self.project_list.addItem(it)
            self._project_items[sid] = it
        if current and current in self._project_items:
            self.project_list.setCurrentItem(self._project_items[current])

    def set_current_project(self, sid: str, name: str):
        if sid in self._project_items:
            self.project_list.setCurrentItem(self._project_items[sid])

    def _project_clicked(self, item):
        sid = item.data(Qt.UserRole)
        if sid and self.on_select_project:
            self.on_select_project(sid)

    def set_wiki_tree(self, pages: list[dict]):
        self.tree.clear()
        self._page_map = {}
        grouped = {}
        for p in pages:
            grouped.setdefault(p["type"], []).append(p)
        labels = {"topics": "主题", "entities": "实体 / 概念",
                  "sources": "资料摘要", "synthesis": "综合"}
        for gtype in ("topics", "entities", "sources", "synthesis"):
            items = grouped.get(gtype, [])
            if not items:
                continue
            g = QTreeWidgetItem([labels.get(gtype, gtype)])
            g.setFlags(Qt.ItemIsEnabled)
            for p in items:
                child = QTreeWidgetItem([p["title"]])
                g.addChild(child)
                self._page_map[child] = p["rel"]
            self.tree.addTopLevelItem(g)
            g.setExpanded(True)

    def _page_double(self, item, _col):
        rel = self._page_map.get(item)
        if rel and self.on_open_page:
            self.on_open_page(rel)

    def set_files(self, files: list[dict]):
        self.file_list.clear()
        for f in files:
            size = f"{f['file_size']/1024:.0f} KB" if f.get("file_size") else ""
            it = QListWidgetItem(f"{f['file_name']}" + (f"  ({size})" if size else ""))
            it.setData(Qt.UserRole, f["file_name"])
            self.file_list.addItem(it)

    def _file_menu(self, pos):
        item = self.file_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        menu.addAction("移除")
        if menu.exec(self.file_list.mapToGlobal(pos)):
            self.on_remove_file and self.on_remove_file(item.data(Qt.UserRole))

    def set_card_stat(self, count: int):
        self.card_stat.setText(f"{count} 张")
