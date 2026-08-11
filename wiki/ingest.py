# -*- coding: utf-8 -*-
"""两步 Chain-of-Thought Ingest（借鉴 llm_wiki + Karpathy 模式）+ SHA256 增量缓存。

流程（每个新文件）：
  Step 1 分析：LLM 读资料 → 输出结构化 JSON（实体/概念/连接/矛盾/建议）
  Step 2 生成：LLM 拿分析 → 输出 wiki 页面（分隔符协议，代码负责落盘）
"""

import json
import re
from datetime import datetime

from core.tokenizer import approx_tokens, trim_to_budget, trim_middle

ANALYZE_PROMPT = """你是知识库的「分析器」。阅读下面的学习资料，输出严格 JSON（不要多余文字）。

JSON 字段：
{{
  "title": "资料标题",
  "summary": "80字以内的核心要点概括",
  "key_concepts": ["概念1", "概念2", ...],       // 3-8 个
  "entity_pages": [{{"title": "概念/术语名", "definition": "一句话定义", "detail": "扩展说明"}}],
  "connections": ["与已有知识的联系，或跨概念关系", ...],
  "difficulties": ["疑难点/需要深挖的问题", ...],
  "topic": "所属主题领域（用于主题页归类）"
}}

资料内容：
---
{source_text}
---
"""

GENERATE_PROMPT = """你是知识库的「生成器」。基于下面的分析结果，生成课程 wiki 页面。

输出格式：多个文件用分隔符分隔，文件名是相对 wiki/ 的路径：
===FILE: wiki/sources/{source_file_base}.md===
（资料摘要页：YAML frontmatter(type/title/created/updated/sources[]) + 核心要点 + 关键概念 [[链接]] + 疑难点）
===FILE: wiki/entities/概念名.md===
（实体页，只对值得建页的概念；已有概念不必重复）
===FILE: wiki/topics/主题名.md===
（如分析中主题是新的，建主题页；否则省略）
===FILE: META===
{{"index_entries": ["- [[xxx]]", ...], "log": "一行操作记录", "overview": "总览更新段落或空串"}}

规则：
- 语言：{language}
- 摘要页必须生成；实体页 1-5 个；主题页按需
- 页面用 [[wikilink]] 互相引用，sources 指向原文文件名
- 不要输出分析 JSON 本身，直接输出文件内容
- META 必须是最后一个文件

分析结果：
---
{analysis_json}
---
"""


class IngestEngine:
    """串行 ingest 引擎：处理 pending 文件，失败不阻塞后续。"""

    def __init__(self, project, client, language: str = "zh", max_source_tokens: int = 4000):
        self.project = project
        self.client = client
        self.language = language
        self.max_source_tokens = max_source_tokens
        self.stats = {"processed": 0, "skipped": 0, "failed": 0, "cost": 0.0}

    def ingest_pending(self, on_progress=None) -> dict:
        """处理所有未完成 ingest 的文件。on_progress(dict) 每文件回调。"""
        self.stats = {"processed": 0, "skipped": 0, "failed": 0, "cost": 0.0}
        files = self.project.pending_files()
        for info in files:
            self._ingest_one(info, on_progress)
        return dict(self.stats)

    def _ingest_one(self, info: dict, on_progress=None):
        name, path, sha = info["name"], info["path"], info["sha256"]
        if self.project.is_processed(name, sha):
            self.stats["skipped"] += 1
            if on_progress:
                on_progress({"name": name, "status": "skipped", "msg": "未变化，跳过"})
            return

        if on_progress:
            on_progress({"name": name, "status": "analyzing", "msg": "分析中…"})
        try:
            analysis = self._analyze(path)
            if not analysis:
                raise ValueError("分析结果为空")
        except Exception as e:
            self.stats["failed"] += 1
            if on_progress:
                on_progress({"name": name, "status": "failed", "msg": f"分析失败: {e}"})
            return

        if on_progress:
            on_progress({"name": name, "status": "generating", "msg": "生成 wiki 页面…"})
        try:
            self._generate(analysis, name)
        except Exception as e:
            self.stats["failed"] += 1
            if on_progress:
                on_progress({"name": name, "status": "failed", "msg": f"生成失败: {e}"})
            return

        self.project.mark_processed(name, sha)
        self.stats["processed"] += 1
        if on_progress:
            on_progress({"name": name, "status": "done", "msg": "完成"})

    def _analyze(self, path: str) -> dict:
        from wiki.project import extract_text
        content = extract_text(path)
        if not content:
            raise ValueError("无法提取文本")
        source_text = trim_to_budget(content, self.max_source_tokens)

        messages = [{
            "role": "system",
            "content": "输出必须是合法 JSON，不要包含 JSON 之外的任何文本。",
        }, {
            "role": "user",
            "content": ANALYZE_PROMPT.format(source_text=source_text),
        }]
        result = self.client.chat_once(messages, temperature=0.1, max_tokens=2000)
        return _parse_json_loose(result.content)

    def _generate(self, analysis: dict, source_file: str):
        source_base = re.sub(r"\.(pdf|docx|pptx|txt|md|markdown)$", "", source_file, flags=re.I)
        prompt = GENERATE_PROMPT.format(
            source_file_base=source_base,
            language=self.language,
            analysis_json=json.dumps(analysis, ensure_ascii=False, indent=1),
        )
        messages = [{
            "role": "system",
            "content": "严格按分隔符协议输出 wiki 文件。",
        }, {
            "role": "user",
            "content": prompt,
        }]
        result = self.client.chat_once(messages, temperature=0.2, max_tokens=6000)
        self._apply_files(result.content, source_file)

    def _apply_files(self, output: str, source_file: str):
        """解析分隔符协议并落盘。"""
        sections = re.split(r"===FILE:\s*(\S+?)\s*===", output)
        meta = {"index_entries": [], "log": "", "overview": ""}
        for i in range(1, len(sections) - 1, 2):
            fname = sections[i].strip()
            content = sections[i + 1].strip("\n")
            if not content:
                continue
            if fname.upper() == "META":
                meta = _parse_meta(content)
                continue
            if fname.startswith("wiki/"):
                rel = fname[len("wiki/"):]
                self.project.write_wiki(rel, content)
        if meta["index_entries"]:
            self._update_index(meta["index_entries"])
        self.project.append_log("ingest", source_file, meta["log"] or "导入资料")
        if meta["overview"]:
            self._update_overview(meta["overview"])
        self._ensure_source_summary(source_file)

    def _update_index(self, entries: list):
        p = self.project.wiki_root / "index.md"
        content = p.read_text(encoding="utf-8") if p.exists() else "# 知识索引\n\n## 资料摘要\n\n"
        added = []
        for e in entries:
            line = e.strip().lstrip("- ")
            if line and f"[[{line}]]" not in content and line not in content:
                added.append(f"- [[{line}]]")
        if added:
            content = content.rstrip() + "\n" + "\n".join(added) + "\n"
            p.write_text(content, encoding="utf-8")

    def _update_overview(self, para: str):
        p = self.project.wiki_root / "overview.md"
        content = p.read_text(encoding="utf-8") if p.exists() else "# 知识库总览\n"
        content = content.rstrip() + "\n\n" + para.strip() + "\n"
        p.write_text(content, encoding="utf-8")

    def _ensure_source_summary(self, source_file: str):
        """兜底：保证每个源文件都有摘要页。"""
        base = re.sub(r"\.(pdf|docx|pptx|txt|md|markdown)$", "", source_file, flags=re.I)
        if (self.project.wiki_root / "sources" / f"{base}.md").exists():
            return
        from wiki import templates
        p = self.project.wiki_root / "sources" / f"{base}.md"
        p.write_text(templates.fill(templates.SOURCE_TEMPLATE,
                                    title=base,
                                    created=datetime.now().strftime("%Y-%m-%d"),
                                    updated=datetime.now().strftime("%Y-%m-%d"),
                                    source_file=source_file),
                     encoding="utf-8")


def _parse_json_loose(text: str) -> dict:
    """容忍 LLM 输出前后有多余文字/代码围栏。"""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        text = text[start:end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        text = re.sub(r",\s*([}\]]) ", r"\1", text)
        data = json.loads(text)
    return data if isinstance(data, dict) else {}


def _parse_meta(content: str) -> dict:
    meta = {"index_entries": [], "log": "", "overview": ""}
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            meta["index_entries"] = data.get("index_entries") or []
            meta["log"] = str(data.get("log", ""))
            meta["overview"] = str(data.get("overview", ""))
    except (json.JSONDecodeError, ValueError):
        pass
    return meta
