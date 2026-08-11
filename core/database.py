# -*- coding: utf-8 -*-
"""SQLite 数据库 — WAL + FTS5（保留原设计的会话/消息/知识块/卡片表，
新增 wiki 页面索引与 ingest 增量缓存表）。"""

import os
import sqlite3
import threading
from datetime import datetime

from core.config import DB_PATH

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- 会话（= 课程 = LLM Wiki 项目）
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '未命名',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    card_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    token_count INTEGER DEFAULT 0
);

-- 对话历史滚动压缩摘要（Reasonix 式：旧对话压成摘要，保留最近 N 轮原文）
CREATE TABLE IF NOT EXISTS chat_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    up_to_message_id INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

-- 知识块（FTS5 混合检索的粗筛层）
-- 注意：FTS5 表采用「只增不删」策略（本环境 SQLite 的 FTS5 'delete' 命令报
-- SQL logic error）。删除/覆盖时只删主表，FTS 脏行由 JOIN 主表过滤，
-- 定期调用 rebuild_fts() 重建清理。
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    source_file TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunks_fts USING fts5(
    content, tokenize='unicode61'
);

CREATE TABLE IF NOT EXISTS knowledge_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER DEFAULT 0,
    sha256 TEXT DEFAULT '',
    chunk_count INTEGER DEFAULT 0,
    added_at TEXT NOT NULL
);

-- ingest 增量缓存：文件 SHA256 → 已处理标记（llm_wiki 式增量，省 token）
CREATE TABLE IF NOT EXISTS ingest_cache (
    session_id TEXT NOT NULL,
    source_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    processed_at TEXT NOT NULL,
    PRIMARY KEY (session_id, source_path)
);

-- wiki 页面元数据（LLM 生成的页面，供检索精排与图谱）
CREATE TABLE IF NOT EXISTS wiki_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    rel_path TEXT NOT NULL,          -- wiki/entities/xxx.md
    page_type TEXT DEFAULT 'page',   -- source | entity | concept | topic | overview | synthesis
    title TEXT DEFAULT '',
    sha256 TEXT DEFAULT '',
    updated_at TEXT NOT NULL,
    UNIQUE (session_id, rel_path)
);

-- 学习卡片
CREATE TABLE IF NOT EXISTS study_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    question TEXT,
    answer TEXT NOT NULL,
    category TEXT DEFAULT '通用',
    tags TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    review_count INTEGER DEFAULT 0,
    difficulty INTEGER DEFAULT 3
);
"""


class Database:
    """SQLite 管理 — 单例 + 线程锁（Tkinter 多线程安全）。

    默认单例使用 DB_PATH；显式传入不同 path 时创建独立实例（测试/多库用）。
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, path: str = None):
        path = path or DB_PATH
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init(path)
                return cls._instance
            if os.path.abspath(cls._instance.path) == os.path.abspath(path):
                return cls._instance
            # 显式不同路径 → 独立实例（不缓存）
            inst = super().__new__(cls)
            inst._init(path)
            return inst

    def _init(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA_SQL)
        # 清理旧版 FTS 触发器（v3 曾用触发器同步 FTS；现改只增策略，
        # 触发器中的 FTS5 'delete' 在本环境 SQLite 下报 SQL logic error）
        for t in ("knowledge_chunks_ai", "knowledge_chunks_ad", "knowledge_chunks_au"):
            self._conn.execute(f"DROP TRIGGER IF EXISTS {t}")
        self._conn.commit()
        self._tlock = threading.Lock()

    def get_conn(self):
        return self._conn

    def execute(self, sql, params=None):
        with self._tlock:
            cur = self._conn.execute(sql, params or ())
            return cur

    def fetchall(self, sql, params=None):
        with self._tlock:
            return self._conn.execute(sql, params or ()).fetchall()

    def fetchone(self, sql, params=None):
        with self._tlock:
            return self._conn.execute(sql, params or ()).fetchone()

    def commit(self):
        with self._tlock:
            self._conn.commit()

    def close(self):
        with self._tlock:
            self._conn.close()
