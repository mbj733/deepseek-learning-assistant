# -*- coding: utf-8 -*-
"""混合检索管线（借鉴 llm_wiki 的 multi-phase retrieval + budget control）。

  Phase 1  FTS5 粗筛
  Phase 2  Wiki 页面精排：FTS 命中 → 关联 sources 摘要页 + index 匹配
  Phase 3  预算装填：按 token 预算依次装载，超出裁剪（保头，利于前缀缓存）
"""

import re
import sqlite3

from core.database import Database
from core.tokenizer import approx_tokens, trim_to_budget


class Retriever:
    def __init__(self, project, budget_tokens: int = 4800, top_k: int = 6):
        self.project = project
        self.db = Database()
        self.budget_tokens = budget_tokens
        self.top_k = top_k

    def _fts_search(self, query: str) -> list[dict]:
        try:
            q = self._build_fts_query(query)
            rows = self.db.fetchall("""
                SELECT kc.content, kc.source_file, kc.chunk_index,
                       rank_bm25(knowledge_chunks_fts) AS score
                FROM knowledge_chunks_fts
                JOIN knowledge_chunks kc ON knowledge_chunks_fts.rowid = kc.id
                WHERE knowledge_chunks_fts MATCH ?
                  AND kc.session_id = ?
                ORDER BY score
                LIMIT ?
            """, (q, self.project.session_id, self.top_k * 2))
            results = []
            seen = set()
            for r in rows:
                key = f"{r['source_file']}:{r['chunk_index']}"
                if key in seen:
                    continue
                seen.add(key)
                results.append({
                    "text": r["content"],
                    "source": r["source_file"],
                    "score": -r["score"],
                })
            return results[:self.top_k]
        except sqlite3.OperationalError:
            return []

    def _build_fts_query(self, query: str) -> str:
        """中英混排分词：中文按双字切，英文按词。"""
        tokens = []
        for token in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2}", query):
            if len(token) <= 1:
                continue
            if re.fullmatch(r"[\u4e00-\u9fff]+", token):
                for i in range(0, len(token) - 1):
                    tokens.append(token[i:i + 2])
            else:
                tokens.append(token)
        return " OR ".join(tokens[:20]) if tokens else ""

    def _source_summary_path(self, source_file: str) -> str:
        base = re.sub(r"\.(pdf|docx|pptx|txt|md|markdown)$", "", source_file, flags=re.I)
        return f"wiki/sources/{base}.md"

    def _read(self, rel: str) -> str:
        return self.project.read_wiki_page(rel) if rel.startswith("wiki/") else ""

    def retrieve(self, query: str) -> dict:
        """返回 {context, cited, budget_used, budget_total}。"""
        hits = self._fts_search(query)
        pages: list[dict] = []
        seen_paths = set()

        for h in hits:
            rel = self._source_summary_path(h["source"])
            if rel in seen_paths:
                continue
            content = self._read(rel)
            if content:
                seen_paths.add(rel)
                pages.append({"rel": rel, "content": content, "score": h["score"], "kind": "source"})
            else:
                seen_paths.add("chunk:" + h["source"] + ":" + str(h["chunk_index"]))
                pages.append({"rel": f"原文:{h['source']}", "content": h["text"],
                              "score": h["score"], "kind": "chunk"})

        index = self._read("wiki/index.md")
        if index:
            pages.append({"rel": "wiki/index.md", "content": index, "score": 0.0, "kind": "index"})

        cited: list[str] = []
        parts: list[str] = []
        used = 0
        for p in sorted(pages, key=lambda x: -x["score"]):
            content = p["content"]
            room = self.budget_tokens - used
            if room <= 0:
                break
            if approx_tokens(content) > room:
                content = trim_to_budget(content, room)
            parts.append(f"【{p['rel']}】\n{content}")
            cited.append(p["rel"])
            used += approx_tokens(content)

        return {
            "context": "\n\n".join(parts),
            "cited": cited,
            "budget_used": used,
            "budget_total": self.budget_tokens,
            "chunks": hits,
        }
