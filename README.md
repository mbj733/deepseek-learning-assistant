# DeepSeek 学习助手 📚

基于 DeepSeek API 的 Windows 桌面学习助手，支持多课程、知识库 RAG、学习卡片和文档图片理解。

## 功能特性

- **💬 AI 智能问答** — 基于 DeepSeek V4 模型的流式对话
- **📁 多课程管理** — 不同科目独立会话，互不干扰
- **📄 知识库 RAG** — 上传教材自动建索引，问答严格基于资料
- **🎴 学习卡片** — 创建知识点卡片，分级复习
- **🖼️ 文档图片理解** — 支持通义千问 VL / Gemini / PaddleOCR 三种后端
- **📎 多格式支持** — PDF / Word / PPT / TXT / Markdown
- **🌙 深色模式** — 一键切换护眼暗色主题
- **💾 对话持久化** — 关闭重开，历史记录不丢失

## 快速开始

### 下载运行（推荐）

从 [Releases](https://github.com/mbj733/deepseek-learning-assistant/releases) 下载 `DeepSeek学习助手.exe`，双击运行。

> ⚠️ **首次使用**：需在 ⚙ 设置中填入 DeepSeek API Key
> 1. 访问 [platform.deepseek.com](https://platform.deepseek.com/) 注册账号
> 2. 创建 API Key（新用户有免费额度）
> 3. 粘贴到软件设置中即可使用

### 从源码运行

```bash
# 1. 安装依赖
pip install ttkbootstrap requests PyMuPDF python-docx python-pptx pyyaml

# 2. 运行
python deepseek_learner_v3.py
```

### 获取 API Key

1. **DeepSeek API** — [platform.deepseek.com](https://platform.deepseek.com/)（必需）
2. **通义千问 VL**（图片理解，国内推荐）— [dashscope.aliyun.com](https://dashscope.aliyun.com/)
3. **Gemini**（图片理解，海外）— [aistudio.google.com](https://aistudio.google.com/)

## 项目结构

```
D:.
├── deepseek_learner_v3.py    # 主程序
├── document_vision.py        # 文档图片理解模块
├── config.yaml               # 配置文件（自动生成）
├── sessions.db               # 会话数据库（自动生成）
└── sessions/                 # 上传的文件（自动生成）
```

## 截图

<!-- 可以放截图，比如：
![主界面](screenshots/main.png)
-->

## 技术栈

- **Python 3.11+** / Tkinter / ttkbootstrap
- **DeepSeek API**（deepseek-v4-flash / deepseek-v4-pro）
- **SQLite + FTS5** 全文搜索
- **PyMuPDF** PDF 处理
- **通义千问 VL / Gemini** 图片理解

## 许可证

MIT
