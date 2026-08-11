# DeepSeek 学习助手 v5 🎓

基于 **DeepSeek API（deepseek-v4）** 的现代桌面学习助手：LLM Wiki 自动知识库、省 token 检索、PySide6 精致 UI。

## 功能特性

- **🤖 AI 智能问答** — deepseek-v4-flash / deepseek-v4-pro 流式对话，支持思考过程显示
- **📁 课程即项目** — 每个课程是一个 LLM Wiki 项目（raw/ + wiki/ + schema + purpose）
- **✦ 自动知识库（LLM Wiki ingest）** — 上传学习资料 → 两步 CoT 自动生成摘要页/实体页/主题页，SHA256 增量缓存跳过未变文件
- **🔍 混合检索** — SQLite FTS5 粗筛 + wiki 页面精排 + token 预算装填
- **💰 省 token** — DeepSeek 前缀缓存稳定设计（缓存命中 90% 折扣）、对话滚动压缩、检索预算控制
- **🎴 学习卡片** — 知识点卡片 + 难度分级复习
- **🖼️ 文档图片理解** — 可选（qwen / gemini / paddle 后端）
- **🌗 深浅色主题** — PySide6 + QSS 现代界面（圆角卡片 / 悬停反馈 / 空状态引导）

## 快速开始

```bash
# 1. 安装依赖（PySide6 建议用阿里云镜像加速）
pip install -r requirements.txt

# 2. 运行
python app.py
```

首次使用：点击右上角 ⚙ 设置 → 填入 DeepSeek API Key（[platform.deepseek.com](https://platform.deepseek.com/)）→ 选择模型 → 保存。

## 使用流程

1. 左侧 **＋** 新建课程（= 一个 LLM Wiki 项目）
2. **上传** 学习资料（PDF / Word / PPT / TXT / Markdown）
3. 点 **整理知识**：LLM 自动把资料整理成知识库（摘要 / 实体 / 主题页）
4. 中间对话区提问，底部实时显示 **缓存命中率** 与 token 用量
5. 左侧 **知识** 标签浏览 wiki 页面，**学习卡片** 管理知识点

## 项目结构

```
deepseek-learning-assistant/
├── app.py               # 入口
├── core/                # 配置 / 数据库 / token 预算 / DeepSeek 客户端 / 省 token 对话组装
├── wiki/                # LLM Wiki：模板 / 项目 / 两步 CoT ingest / 混合检索
├── features/            # 会话 / 学习卡片 / 图片理解
└── ui_qt/               # PySide6 界面：主题 / 侧栏 / 聊天 / 预览 / 对话框
```

## 技术栈

- **PySide6 + QSS**（现代圆角 UI，深浅主题）
- **DeepSeek API**（deepseek-v4-flash / deepseek-v4-pro，1M 上下文）
- **SQLite + FTS5** 全文检索
- **markdown** 渲染

## 许可证

MIT
