# -*- coding: utf-8 -*-
"""省 token 对话组装 — 借鉴 Reasonix 的「前缀缓存稳定」设计。

DeepSeek 对命中缓存的输入 token 收 1/10 价格（~90% 折扣）。
要让命中率高，请求体必须是「稳定前缀 + 尾部增量」结构。
"""

from core.tokenizer import approx_tokens, trim_to_budget, Budget

# 稳定身份：不含时间戳、不含统计数字等易变内容（变则会破坏前缀缓存）
STABLE_IDENTITY = """你是「DeepSeek 学习助手」，一位专业、耐心的 AI 导师，帮助用户学习课程资料。

回答规则：
1. 优先基于【参考资料】回答，标注引用来源（如 [来源: 文件名] 或 [[页面名]]）
2. 参考资料不足时，明确说明并基于通用知识回答
3. 使用结构化输出：要点列表、对比表格、公式（Markdown 格式）
4. 语言与用户一致（默认中文）
5. 诚实：不确定的地方明说，不编造
"""

COURSE_CONTEXT_TEMPLATE = """当前课程概况（仅作背景，具体引用以本轮参考资料为准）：
{context}
"""

# 滚动摘要的系统提示（压缩旧对话）
COMPRESS_PROMPT = """请把下面的对话历史压缩成一段 150 字以内的中文摘要，保留：
- 用户的学习目标与已提出的关键问题
- 已得到的重要结论（含知识点）
- 未解决/待追问的问题

对话历史：
---
{history}
---
只输出摘要正文，不要其他文字。"""


class ConversationBuilder:
    def __init__(self, config: dict):
        self.config = config
        self.budget = Budget(
            total=int(config.get("context_budget", 131072)),
            retrieval_ratio=float(config.get("retrieval_budget_ratio", 0.6)),
        )

    def windowed_history(self, history: list[dict]) -> list[dict]:
        """按轮次窗口裁剪。history 为 [(role, content)] 列表。"""
        window = max(2, int(self.config.get("history_window", 12)))
        if len(history) <= window:
            return history
        pairs = []
        current = []
        for role, content in reversed(history):
            current.insert(0, (role, content))
            if role == "user":
                pairs.insert(0, current)
                current = []
                if len(pairs) >= window:
                    break
        return [m for pair in pairs for m in pair]

    def needs_compress(self, history: list[dict]) -> bool:
        """历史 token 是否超过预算的 compress_threshold。"""
        if len(history) < 8:
            return False
        hist_tokens = sum(approx_tokens(c) for _, c in history)
        threshold = self.budget.history_budget * float(self.config.get("compress_threshold", 0.7))
        return hist_tokens > threshold

    def compress_blocks(self, history: list[dict], keep: int = 6) -> tuple[list[dict], str]:
        """把早期轮次摘成摘要，返回 (保留的新历史, 摘要文本)。"""
        keep = max(2, keep)
        if len(history) <= keep:
            return history, ""
        compress_part = history[:-keep]
        keep_part = history[-keep:]
        text = "\n".join(f"{r}: {c}" for r, c in compress_part)
        text = trim_to_budget(text, 6000)
        return keep_part, text

    def build(self, *, user_text: str, retrieval_context: str,
              course_context: str = "", summary: str = "",
              history: list[dict] | None = None) -> tuple[list[dict], dict]:
        """组装消息列表。返回 (messages, stats)。"""
        messages: list[dict] = []
        stats = {"system": 0, "history": 0, "retrieval": 0}

        identity = STABLE_IDENTITY
        messages.append({"role": "system", "content": identity})
        stats["system"] += approx_tokens(identity)

        if summary:
            messages.append({"role": "system", "content": f"【对话摘要】{summary}"})
            stats["system"] += approx_tokens(summary)

        if course_context:
            cc = COURSE_CONTEXT_TEMPLATE.format(context=course_context)
            messages.append({"role": "system", "content": cc})
            stats["system"] += approx_tokens(cc)

        hist = self.windowed_history(history or [])
        for role, content in hist:
            messages.append({"role": role, "content": content})
            stats["history"] += approx_tokens(content)

        ctx = retrieval_context or "（当前课程暂无相关学习资料）"
        last = f"【参考资料】\n{ctx}\n\n用户问题：{user_text}"
        messages.append({"role": "user", "content": last})
        stats["retrieval"] += approx_tokens(last)

        stats["total"] = sum(stats.values())
        return messages, stats
