# -*- coding: utf-8 -*-
"""PySide6 对话框：设置 / 学习卡片。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox,
    QTextEdit,
)


def show_settings(parent, config, on_save):
    dlg = QDialog(parent)
    dlg.setWindowTitle("设置")
    dlg.setMinimumWidth(440)
    lay = QVBoxLayout(dlg)
    lay.setSpacing(10)

    def field(label, widget):
        lay.addWidget(QLabel(label))
        lay.addWidget(widget)

    api = QLineEdit(config.get("api_key", ""))
    api.setEchoMode(QLineEdit.Password)
    field("DeepSeek API Key", api)
    model = QComboBox()
    model.addItems(["deepseek-v4-flash", "deepseek-v4-pro"])
    model.setCurrentText(config.get("model", "deepseek-v4-flash"))
    field("模型", model)
    tip = QLabel("其余参数（上下文预算 / 对话窗口 / 检索）已自动设为最优默认。")
    tip.setStyleSheet("color: #6B7280; font-size: 11px;")
    lay.addWidget(tip)

    btns = QHBoxLayout()
    btns.addStretch(1)
    cancel = QPushButton("取消")
    cancel.clicked.connect(dlg.reject)
    btns.addWidget(cancel)
    save = QPushButton("保存")
    save.setObjectName("Primary")
    save.clicked.connect(lambda: _save())
    btns.addWidget(save)
    lay.addLayout(btns)

    def _save():
        config.update({
            "api_key": api.text().strip(),
            "model": model.currentText(),
        })
        on_save()
        dlg.accept()

    dlg.exec()


def manage_cards(parent, cards, on_stat):
    dlg = QDialog(parent)
    dlg.setWindowTitle("学习卡片")
    dlg.resize(560, 460)
    lay = QVBoxLayout(dlg)
    top = QHBoxLayout()
    add_btn = QPushButton("＋ 新建卡片")
    add_btn.setObjectName("Primary")
    add_btn.clicked.connect(lambda: _add())
    top.addWidget(add_btn)
    top.addStretch(1)
    lay.addLayout(top)
    lst = QListWidget()
    lst.setObjectName("FileList")
    lay.addWidget(lst, 1)

    def _refresh():
        lst.clear()
        for c in cards.get_cards():
            it = QListWidgetItem(f"【{c['category']}】{c['title']}  （难度 {c['difficulty']}）")
            it.setData(Qt.UserRole, c["id"])
            lst.addItem(it)
        on_stat(len(cards.get_cards()))

    def _add():
        ad = QDialog(dlg)
        ad.setWindowTitle("新建学习卡片")
        al = QVBoxLayout(ad)
        al.addWidget(QLabel("标题"))
        t = QLineEdit()
        al.addWidget(t)
        al.addWidget(QLabel("知识点"))
        a = QTextEdit()
        a.setFixedHeight(140)
        al.addWidget(a)
        al.addWidget(QLabel("分类"))
        cat = QLineEdit("通用")
        al.addWidget(cat)
        row = QHBoxLayout()
        row.addStretch(1)
        ok = QPushButton("保存")
        ok.setObjectName("Primary")

        def _do():
            if t.text().strip() and a.toPlainText().strip():
                cards.add_card(t.text().strip(), a.toPlainText().strip(),
                               category=cat.text().strip() or "通用")
                ad.accept()
                _refresh()

        ok.clicked.connect(_do)
        row.addWidget(ok)
        al.addLayout(row)
        ad.exec()

    def _delete():
        item = lst.currentItem()
        if not item:
            return
        if QMessageBox.question(dlg, "删除", "删除这张卡片？") == QMessageBox.Yes:
            cards.delete_card(item.data(Qt.UserRole))
            _refresh()

    row = QHBoxLayout()
    row.addStretch(1)
    del_btn = QPushButton("删除选中")
    del_btn.setObjectName("Danger")
    del_btn.clicked.connect(_delete)
    row.addWidget(del_btn)
    close = QPushButton("关闭")
    close.clicked.connect(dlg.accept)
    row.addWidget(close)
    lay.addLayout(row)
    _refresh()
    dlg.exec()
