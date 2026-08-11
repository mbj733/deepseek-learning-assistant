# -*- coding: utf-8 -*-
"""Token 估算与预算分配 — 借鉴 llm_wiki 的 Budget Control 与 Reasonix 的缓存感知。

- 中文按字符、英文按词估算，无需依赖分词库（离线、零依赖）。
- 提供预算分配：检索内容 / 历史 / 系统 / 预留 四部分，比例可配。
"""

import math

# 近似 token 数（经验值，用于预算裁剪；精确计费以 API usage 为准）
_CHAR_PER_TOKEN = 1.6   # 中文约 1 字符 ≈ 0.6~1 token
_WORD_PER_TOKEN = 0.75  # 英文约 1 词 ≈ 1.3 token


def approx_tokens(text: str) -> int:
    """粗略估算 token 数：中英混排加权。"""
    if not text:
        return 0
    cjk = sum(1 for ch in text if _is_cjk(ch))
    other = max(0, len(text) - cjk)
    return int(cjk / _CHAR_PER_TOKEN + other * _WORD_PER_TOKEN) + 1


def _is_cjk(ch: str) -> bool:
    o = ord(ch)
    return (0x4E00 <= o <= 0x9FFF) or (0x3400 <= o <= 0x4DBF)


def trim_to_budget(text: str, budget_tokens: int, keep_head: bool = True) -> str:
    """把文本裁剪到预算 token 内。

    keep_head=True 保留开头（对 RAG 片段：保留正文主体）；
    保留开头对前缀缓存更友好——稳定内容保持字节一致。
    """
    if budget_tokens <= 0 or approx_tokens(text) <= budget_tokens:
        return text
    target_chars = int(budget_tokens * _CHAR_PER_TOKEN * 0.9)
    if keep_head:
        return text[:target_chars]
    return text[-target_chars:]


def trim_middle(text: str, budget_tokens: int, keep_head_ratio: float = 0.5) -> str:
    """中间裁剪：保留头尾，砍中间（适合日志/长文）。"""
    if budget_tokens <= 0 or approx_tokens(text) <= budget_tokens:
        return text
    total_chars = len(text)
    keep_chars = int(budget_tokens * _CHAR_PER_TOKEN * 0.9)
    head = int(keep_chars * keep_head_ratio)
    tail = keep_chars - head
    return text[:head] + "\n\n…[中间已省略]…\n\n" + text[-tail:]


class Budget:
    """上下文预算分配器（llm_wiki 风格：60% 检索 / 20% 历史 / 5% 索引 / 15% 系统）。"""

    def __init__(self, total: int, retrieval_ratio: float = 0.6,
                 history_ratio: float = 0.2, index_ratio: float = 0.05):
        self.total = total
        self.retrieval_budget = int(total * retrieval_ratio)
        self.history_budget = int(total * history_ratio)
        self.index_budget = int(total * index_ratio)
        self.system_budget = total - self.retrieval_budget - self.history_budget - self.index_budget

    def allocate(self) -> dict:
        return {
            "retrieval": self.retrieval_budget,
            "history": self.history_budget,
            "index": self.index_budget,
            "system": self.system_budget,
        }
