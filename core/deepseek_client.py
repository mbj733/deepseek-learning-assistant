# -*- coding: utf-8 -*-
"""DeepSeek API 客户端 — 流式 + reasoning + usage 统计。

省 token 关键设计（借鉴 Reasonix 的缓存感知）：
- 返回每个请求的 prompt_cache_hit_tokens / prompt_cache_miss_tokens，
  UI 据此显示缓存命中率；命中率越高，真实成本越低（命中 ≈ 1/10 价格）。
- 调用方应保证系统提示与历史前缀稳定，最大化命中。
"""

import json
import time
from dataclasses import dataclass, field

import requests

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_hit_tokens: int = 0
    cache_miss_tokens: int = 0
    latency_ms: int = 0

    @property
    def hit_ratio(self) -> float:
        total = self.cache_hit_tokens + self.cache_miss_tokens
        return (self.cache_hit_tokens / total) if total else 0.0

    def cost_yuan(self, model: str = "") -> float:
        return 0.0


@dataclass
class ChatResult:
    content: str = ""
    reasoning: str = ""
    usage: Usage = field(default_factory=Usage)


class DeepSeekClient:
    def __init__(self, api_key: str, model: str = "deepseek-v4-flash",
                 base_url: str = None, timeout: int = 180):
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or DEEPSEEK_API_URL).rstrip("/") + "/chat/completions"
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    @property
    def is_reasoning(self) -> bool:
        return "reasoner" in self.model.lower() or "r1" in self.model.lower()

    def chat_stream(self, messages: list, temperature: float = 0.3,
                    max_tokens: int = 4096):
        """流式生成，产出 (kind, text) 序列；结束时产出 ("usage", Usage)。"""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream_options": {"include_usage": True},
        }
        start = time.monotonic()
        resp = requests.post(self.base_url, headers=self.headers,
                             json=payload, stream=True, timeout=self.timeout)
        resp.raise_for_status()

        usage = Usage()
        try:
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if not line.startswith("data: "):
                    continue
                d = line[6:].strip()
                if d == "[DONE]":
                    break
                try:
                    data = json.loads(d)
                except json.JSONDecodeError:
                    continue
                choices = data.get("choices") or []
                if choices:
                    delta = choices[0].get("delta", {}) or {}
                    reasoning = delta.get("reasoning_content", "")
                    if reasoning:
                        yield ("reasoning", reasoning)
                    content = delta.get("content", "")
                    if content:
                        yield ("content", content)
                u = data.get("usage")
                if u:
                    usage.prompt_tokens = u.get("prompt_tokens", 0)
                    usage.completion_tokens = u.get("completion_tokens", 0)
                    usage.cache_hit_tokens = u.get("prompt_cache_hit_tokens", 0)
                    usage.cache_miss_tokens = u.get("prompt_cache_miss_tokens", 0)
        finally:
            resp.close()
        usage.latency_ms = int((time.monotonic() - start) * 1000)
        yield ("usage", usage)

    def chat_once(self, messages: list, temperature: float = 0.2,
                  max_tokens: int = 2048) -> ChatResult:
        """非流式调用（ingest 分析步、摘要压缩等内部用途）。"""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        start = time.monotonic()
        resp = requests.post(self.base_url, headers=self.headers,
                             json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        result = ChatResult()
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message", {}) or {}
        result.reasoning = msg.get("reasoning_content", "") or ""
        result.content = msg.get("content", "") or ""
        u = data.get("usage") or {}
        result.usage.prompt_tokens = u.get("prompt_tokens", 0)
        result.usage.completion_tokens = u.get("completion_tokens", 0)
        result.usage.cache_hit_tokens = u.get("prompt_cache_hit_tokens", 0)
        result.usage.cache_miss_tokens = u.get("prompt_cache_miss_tokens", 0)
        result.usage.latency_ms = int((time.monotonic() - start) * 1000)
        return result
