# -*- coding: utf-8 -*-
"""会话管理（课程列表 + 消息持久化，从原 SessionManager 迁移）。"""

import uuid
from datetime import datetime

from core.database import Database
from wiki.project import Project


class SessionManager:
    def __init__(self):
        self.db = Database()

    def get_all(self) -> list[dict]:
        return self.db.fetchall(
            "SELECT * FROM sessions ORDER BY updated_at DESC")

    def create(self, name: str = "新课程") -> str:
        sid = uuid.uuid4().hex[:12]
        now = datetime.now().isoformat()
        self.db.execute(
            "INSERT INTO sessions (id, name, created_at, updated_at) VALUES (?,?,?,?)",
            (sid, name, now, now))
        self.db.commit()
        Project(sid, name).init_wiki(topic=name)
        return sid

    def rename(self, sid: str, name: str):
        self.db.execute("UPDATE sessions SET name=?, updated_at=? WHERE id=?",
                        (name, datetime.now().isoformat(), sid))
        self.db.commit()

    def delete(self, sid: str):
        self.db.execute("DELETE FROM sessions WHERE id=?", (sid,))
        self.db.commit()
        import shutil
        from core.config import SESSIONS_DIR
        import os
        d = os.path.join(SESSIONS_DIR, sid)
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)

    def get_name(self, sid: str) -> str:
        row = self.db.fetchone("SELECT name FROM sessions WHERE id=?", (sid,))
        return row["name"] if row else "未命名"

    def update_time(self, sid: str):
        self.db.execute("UPDATE sessions SET updated_at=? WHERE id=?",
                        (datetime.now().isoformat(), sid))
        self.db.commit()


class ChatStore:
    """消息持久化 + 对话窗口裁剪 + 滚动摘要（Reasonix 式压缩）。"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.db = Database()

    def save_message(self, role: str, content: str) -> int:
        cur = self.db.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?,?,?,?)",
            (self.session_id, role, content, datetime.now().isoformat()))
        self.db.commit()
        return cur.lastrowid

    def load_messages(self, limit: int = 100) -> list[dict]:
        rows = self.db.fetchall(
            "SELECT * FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (self.session_id, limit))
        return list(reversed([dict(r) for r in rows]))

    def last_message_id(self) -> int:
        row = self.db.fetchone(
            "SELECT MAX(id) AS m FROM messages WHERE session_id=?", (self.session_id,))
        return row["m"] or 0

    def get_summary(self) -> str:
        row = self.db.fetchone(
            "SELECT summary FROM chat_summaries WHERE session_id=? ORDER BY id DESC LIMIT 1",
            (self.session_id,))
        return row["summary"] if row else ""

    def save_summary(self, summary: str, up_to_id: int):
        self.db.execute(
            "INSERT INTO chat_summaries (session_id, summary, up_to_message_id, created_at) VALUES (?,?,?,?)",
            (self.session_id, summary, up_to_id, datetime.now().isoformat()))
        self.db.commit()

    def count(self) -> int:
        row = self.db.fetchone(
            "SELECT COUNT(*) AS c FROM messages WHERE session_id=?", (self.session_id,))
        return row["c"] or 0
