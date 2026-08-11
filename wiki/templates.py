# -*- coding: utf-8 -*-
"""wiki 模板 — 借鉴 llm-wiki skill 模板，精简为课程学习场景。"""

SCHEMA_TEMPLATE = """# Wiki Schema（知识库配置规范）

> 这个文件告诉 AI 如何维护这个课程的知识库。可随时和用户一起调整。

- 主题：{topic}
- 语言：{language}
- 版本：1.0

## 目录结构

```
{wiki_root}/
├── raw/sources/       # 原始学习资料（只读，不修改）
├── wiki/
│   ├── sources/       # 资料摘要页（每个资料一篇）
│   ├── entities/      # 实体页（概念、人物、方法、术语）
│   ├── topics/        # 主题页（知识领域）
│   ├── synthesis/     # 综合页（跨资料分析）
├── schema.md          # 本文件
├── purpose.md         # 课程目标
├── index.md           # 内容索引（导航入口）
├── log.md             # 操作日志
└── overview.md        # 知识库全貌总览
```

## 页面规范

- 每页必须有 YAML frontmatter：`type`, `title`, `created`, `updated`, `sources[]`
- 页面间用 `[[wikilink]]` 交叉引用（Obsidian 兼容）
- 实体页：`wiki/entities/{名称}.md`；资料摘要：`wiki/sources/{日期}-{短标题}.md`
- 每个页面底部维护「相关页面」列表

## Ingest 规则

处理一个新资料（raw/sources/ 下的文件）：

1. **摘要页**（必须）：生成 `wiki/sources/` 下的资料摘要页，含核心要点、关键概念、疑难点
2. **实体/概念**：提取 3-8 个关键概念；已存在的实体页追加补充，新概念创建实体页
3. **主题页**：如资料属于新的知识领域，创建 `wiki/topics/` 页面
4. **index.md**：添加新条目
5. **log.md**：记录操作
6. **overview.md**：如有必要，更新总览

短资料（< 500 字）：只做摘要页 + 提取概念 + 更新 index/log，跳过主题页与 overview。

## Query 规则

1. 先读 index.md 定位相关条目
2. 读取相关页面后综合回答
3. 回答标注来源页面
4. 有价值的问答保存到 `wiki/synthesis/`

## Lint 规则

定期抽查：孤立页面、缺失概念页（被 [[链接]] 但不存在）、index 一致性、交叉引用缺失。
"""

PURPOSE_TEMPLATE = """# 课程目标（Purpose）

> LLM 每次 ingest 和 query 时都会读这个文件，用于理解"为什么学"。

## 目标
- {topic}

## 关键问题
（学习中要持续回答的核心问题，随学习进度更新）

## 学习范围
- 教材/资料：见 raw/sources/
- 关注深度：概念理解 > 记忆细节

## 当前进展
（随学习更新：学到的知识领域、薄弱点、待解决问题）
"""

SOURCE_TEMPLATE = """---
type: source
title: {title}
created: {created}
updated: {updated}
sources: [{source_file}]
---

# {title}

> 一句话摘要

## 核心要点

- 

## 关键概念

- [[概念1]]
- [[概念2]]

## 疑难点 / 待深挖

- 

## 相关页面

- [[索引]]
"""

ENTITY_TEMPLATE = """---
type: entity
title: {title}
created: {created}
updated: {updated}
sources: [{sources}]
---

# {title}

> 一句话定义

## 详细说明

## 与其它概念的关系

- 

## 相关页面

- [[索引]]
"""

INDEX_TEMPLATE = """# 知识索引

> 这是知识库的导航入口。每个条目链接到对应 wiki 页面。

## 主题

## 实体/概念

## 资料摘要

- {sources}

## 综合/问答

"""

LOG_TEMPLATE = """# 操作日志

| 时间 | 操作 | 对象 | 说明 |
|------|------|------|------|
"""

OVERVIEW_TEMPLATE = """# 知识库总览

> 自动更新：反映当前知识库全貌。

## 主题领域

## 核心实体

## 学习进度
"""


def fill(template: str, **kwargs) -> str:
    """安全填充模板：缺失变量置空，避免 KeyError。"""
    import string

    class _SafeDict(dict):
        def __missing__(self, key):
            return ""

    return string.Formatter().vformat(template, (), _SafeDict(kwargs))
