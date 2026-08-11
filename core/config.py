# -*- coding: utf-8 -*-
"""配置管理 — 借鉴 llm_wiki 的 Settings 持久化思路。

所有配置集中在 config.yaml（随应用目录存放，支持 PyInstaller 打包）。
"""

import json
import os
import sys
from dataclasses import dataclass, field, asdict

DEFAULT_CONFIG = {
    "api_key": "",
    "model": "deepseek-v4-flash",    # 最新模型：v4-flash / v4-pro（旧 chat/reasoner 别名已弃用）
    "base_url": "https://api.deepseek.com",
    "vision_backend": "",          # "" | qwen | gemini | paddle
    "vision_key": "",
    "theme": "light",              # light | dark
    "language": "zh",
    # ── 省 token 预算（最优默认，不暴露在设置 UI） ──
    "context_budget": 131072,       # 128K：充分利用 v4 的 1M 上下文（检索按相关度装填，不会硬塞满）
    "history_window": 12,           # 保留最近 12 轮完整消息，更早的自动压缩为摘要
    "compress_threshold": 0.7,      # 历史超过预算 70% 时压缩旧对话
    "retrieval_budget_ratio": 0.6,  # 检索内容占预算比例
    "top_k": 6,                     # 检索返回片段数
    # ── ingest ──
    "ingest_auto": True,           # 放入 raw/sources 自动 ingest
    "ingest_language": "zh",
    # ── 成本 ──
    "show_cost": True,             # 显示 token 用量与缓存命中率
}


def app_dir() -> str:
    """应用数据目录：exe 打包时用 exe 同目录，否则用源码目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CONFIG_FILE = os.path.join(app_dir(), "config.yaml")
DB_PATH = os.path.join(app_dir(), "sessions.db")
SESSIONS_DIR = os.path.join(app_dir(), "sessions")


class Config:
    """应用配置：JSON 存储，自动合并默认值。"""

    def __init__(self, path: str = None):
        self.path = path or CONFIG_FILE
        self._data: dict = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    # 只合入已知键，未知键忽略（兼容旧配置）
                    for k in DEFAULT_CONFIG:
                        if k in loaded:
                            self._data[k] = loaded[k]
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def get(self, key: str, default=None):
        return self._data.get(key, default if default is not None else DEFAULT_CONFIG.get(key))

    def set(self, key: str, value):
        self._data[key] = value
        self.save()

    def update(self, mapping: dict):
        for k, v in mapping.items():
            if k in DEFAULT_CONFIG:
                self._data[k] = v
        self.save()

    def snapshot(self) -> dict:
        return dict(self._data)
