# -*- coding: utf-8 -*-
"""PySide6 预览面板：markdown 渲染（markdown 库 → QTextBrowser），跟随深浅色。"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextBrowser


class PreviewPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PreviewPanel")
        self.setFixedWidth(340)
        self.dark = False
        self._title = "预览"
        self._content = ""
        self._kind = "plain"
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(8)
        self.title = QLabel("预览")
        self.title.setObjectName("PreviewTitle")
        lay.addWidget(self.title)
        self.view = QTextBrowser()
        self.view.setObjectName("PreviewText")
        self.view.setOpenExternalLinks(True)
        lay.addWidget(self.view, 1)

    def set_dark(self, dark: bool):
        self.dark = dark
        if self._content:
            self._rerender()

    def _rerender(self):
        if self._kind == "markdown":
            self.show_markdown(self._title, self._content)
        else:
            self.show_plain(self._title, self._content)

    def _to_html(self, md: str) -> str:
        try:
            import markdown
            body = markdown.markdown(md, extensions=["fenced_code", "tables", "nl2br"])
        except ImportError:
            import html as _h
            body = "<pre>" + _h.escape(md) + "</pre>"
        if self.dark:
            bg = "#232428"; fg = "#e8eaed"; muted = "#9aa0a6"
        else:
            bg = "#ffffff"; fg = "#1f2329"; muted = "#6b7280"
        return f"""<html><head><style>
body {{ font-family: 'Segoe UI','Microsoft YaHei UI',sans-serif; font-size: 13.5px;
       color: {fg}; background: {bg}; line-height: 1.75; margin: 0; }}
h1 {{ font-size: 20px; margin: 6px 0; }} h2 {{ font-size: 17px; margin: 6px 0; }}
h3 {{ font-size: 15px; margin: 6px 0; }}
code {{ background: {muted}22; padding: 1px 5px; border-radius: 4px; }}
pre {{ background: {muted}18; padding: 10px; border-radius: 8px; overflow-x: auto; }}
blockquote {{ border-left: 3px solid {muted}66; margin: 6px 0; padding-left: 10px; color: {muted}; }}
table {{ border-collapse: collapse; margin: 8px 0; }}
th, td {{ border: 1px solid {muted}44; padding: 5px 10px; }}
hr {{ border: none; border-top: 1px solid {muted}44; margin: 10px 0; }}
a {{ color: #E2563A; }}
</style></head><body>{body}</body></html>"""

    def show_markdown(self, title: str, content: str):
        self._title = title
        self._content = content
        self._kind = "markdown"
        self.title.setText(title)
        self.view.setHtml(self._to_html(content))

    def show_plain(self, title: str, content: str):
        self._title = title
        self._content = content
        self._kind = "plain"
        self.title.setText(title)
        self.view.setPlainText(content)

    def clear(self):
        self._title = "预览"
        self._content = ""
        self.title.setText("预览")
        self.view.clear()
