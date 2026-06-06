#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek 学习助手 - AI 智能问答桌面应用
Powered by DeepSeek API
"""

import json
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime
import re

import requests
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledFrame

# ── 常量 ──────────────────────────────────────────────────────────────
APP_NAME = "DeepSeek 学习助手"
APP_VERSION = "1.0.0"
APP_ICON = "📚"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# ── 学习助手系统提示词 ─────────────────────────────────────────────
SYSTEM_PROMPT = """你是 DeepSeek 学习助手，一位专业、耐心、循循善诱的 AI 导师。

你的核心原则：
1. 用清晰易懂的语言解释复杂概念，辅以生动的类比和例子
2. 鼓励式教学：先肯定学生的思考，再引导他们找到正确答案
3. 对于不会的问题，坦诚地说"我不确定"而非胡乱猜测
4. 输出使用 Markdown 格式（标题、列表、代码块等）使内容结构清晰
5. 主动追问学生是否理解，提供进一步解释的意愿

请开始你的辅导吧！"""

# ── 颜色方案 ──────────────────────────────────────────────────────────
COLORS = {
    "user_bg": "#d4f0d4",        # 用户气泡 - 浅绿
    "assistant_bg": "#ffffff",   # AI 气泡 - 白色
    "system_bg": "#f0f0f0",      # 系统消息
    "code_bg": "#f5f5f5",        # 代码块背景
    "user_tag": "#4caf50",       # 用户标签色
    "assistant_tag": "#2196f3",  # AI 标签色
}

# ── 配置管理 ──────────────────────────────────────────────────────────
def load_config():
    """加载配置文件"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"api_key": "", "model": DEFAULT_MODEL}

def save_config(config):
    """保存配置文件"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# ── DeepSeek API 调用 ────────────────────────────────────────────────
class DeepSeekClient:
    """DeepSeek API 客户端"""

    def __init__(self, api_key, model=DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def chat(self, messages, stream=True):
        """发送聊天请求"""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "temperature": 0.7,
            "max_tokens": 4096,
        }
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=self.headers,
            json=payload,
            stream=stream,
            timeout=60
        )
        response.raise_for_status()

        if stream:
            return self._parse_stream(response)
        else:
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def _parse_stream(self, response):
        """解析 SSE 流式响应"""
        full_content = ""
        for line in response.iter_lines(decode_unicode=True):
            if line:
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        full_content += content
                        yield content
                    except (json.JSONDecodeError, KeyError):
                        continue
        return full_content


# ── Markdown 渲染辅助 ────────────────────────────────────────────────
def extract_code_blocks(text):
    """将文本分割为普通内容和代码块"""
    pattern = r"```(\w*)\n(.*?)```"
    parts = []
    last_end = 0
    for match in re.finditer(pattern, text, re.DOTALL):
        if match.start() > last_end:
            parts.append(("text", text[last_end:match.start()]))
        lang = match.group(1) or ""
        code = match.group(2)
        parts.append(("code", code, lang))
        last_end = match.end()
    if last_end < len(text):
        parts.append(("text", text[last_end:]))
    return parts


# ── 主应用 ────────────────────────────────────────────────────────────
class DeepSeekLearnerApp:
    def __init__(self):
        self.config = load_config()
        self.client = None
        self.messages = []  # [{"role": ..., "content": ...}]
        self.is_loading = False
        self.current_ai_widget = None

        # 初始化窗口
        self.root = ttkb.Window(
            title=f"{APP_NAME} v{APP_VERSION}",
            themename="litera",
            size=(900, 680),
            minsize=(600, 450),
        )
        self.root.iconbitmap(default="")  # 无图标
        self._setup_ui()

        # 检查 API Key
        if self.config.get("api_key"):
            self.client = DeepSeekClient(
                self.config["api_key"],
                self.config.get("model", DEFAULT_MODEL)
            )
            self._add_system_message("DeepSeek API 已就绪，开始学习吧！📖")
        else:
            self._add_system_message("请先点击右上角 ⚙ 设置 DeepSeek API Key")
            self.open_settings()

        # 绑定键盘事件
        self.root.bind("<Control-Return>", lambda e: self.send_message())

    # ── UI 构建 ────────────────────────────────────────────────────
    def _setup_ui(self):
        """构建用户界面"""
        # 主容器
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # ── 标题栏 ──
        title_frame = ttkb.Frame(self.root, padding=(15, 8))
        title_frame.grid(row=0, column=0, sticky="ew")
        title_frame.grid_columnconfigure(1, weight=1)

        ttkb.Label(
            title_frame, text=f"{APP_ICON} {APP_NAME}",
            font=("Microsoft YaHei UI", 14, "bold"),
            bootstyle="inverse-primary"
        ).pack(side=LEFT, padx=5)

        # 状态指示器
        self.status_label = ttkb.Label(
            title_frame, text="● 未连接",
            font=("Microsoft YaHei UI", 9),
            bootstyle="secondary"
        )
        self.status_label.pack(side=RIGHT, padx=10)

        # 设置按钮
        ttkb.Button(
            title_frame, text="⚙ 设置",
            bootstyle="outline-secondary",
            command=self.open_settings,
            width=8
        ).pack(side=RIGHT, padx=5)

        # 清空对话按钮
        ttkb.Button(
            title_frame, text="🗑 新对话",
            bootstyle="outline-info",
            command=self.clear_chat,
            width=8
        ).pack(side=RIGHT, padx=5)

        # ── 聊天区 ──
        chat_frame = ttkb.Frame(self.root, padding=(10, 0))
        chat_frame.grid(row=1, column=0, sticky="nsew")
        chat_frame.grid_rowconfigure(0, weight=1)
        chat_frame.grid_columnconfigure(0, weight=1)

        # 聊天画布 + 滚动条
        self.chat_canvas = tk.Canvas(chat_frame, highlightthickness=0, bg="#f0f2f5")
        scrollbar = ttk.Scrollbar(chat_frame, orient=VERTICAL, command=self.chat_canvas.yview)
        self.chat_canvas.configure(yscrollcommand=scrollbar.set)

        # 消息容器 (放在 Canvas 内)
        self.msg_frame = ttkb.Frame(self.chat_canvas, padding=10)
        self.msg_frame.bind("<Configure>", lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all")))

        self.canvas_window = self.chat_canvas.create_window(
            (0, 0), window=self.msg_frame, anchor="nw", width=self.chat_canvas.winfo_width()
        )
        self.chat_canvas.bind("<Configure>", self._on_canvas_resize)

        self.chat_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # ── 输入区 ──
        input_frame = ttkb.Frame(self.root, padding=(10, 8))
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.input_text = scrolledtext.ScrolledText(
            input_frame,
            height=4,
            wrap=WORD,
            font=("Microsoft YaHei UI", 10),
            padx=10,
            pady=8,
            relief="flat",
            borderwidth=1,
        )
        self.input_text.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.input_text.bind("<Return>", self._on_enter_key)

        self.send_btn = ttkb.Button(
            input_frame, text="发送 ▶",
            bootstyle="success",
            command=self.send_message,
            width=10,
        )
        self.send_btn.grid(row=0, column=1, sticky="ns")

        # 底部提示
        ttkb.Label(
            input_frame, text="Enter 发送 | Shift+Enter 换行 | Ctrl+Enter 快速发送",
            font=("Microsoft YaHei UI", 8),
            bootstyle="secondary"
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def _on_canvas_resize(self, event):
        """画布大小改变时调整内部 frame 宽度"""
        self.chat_canvas.itemconfig(self.canvas_window, width=event.width)

    # ── 消息气泡渲染 ─────────────────────────────────────────────
    def _create_bubble(self, role, content, is_streaming=False):
        """创建聊天气泡"""
        is_user = role == "user"
        is_system = role == "system"

        # 气泡容器
        bubble_frame = ttkb.Frame(self.msg_frame)
        bubble_frame.pack(fill=X, pady=(0, 8), padx=5)

        # 对齐
        inner_frame = ttkb.Frame(bubble_frame)
        if is_user:
            inner_frame.pack(anchor="e")
        else:
            inner_frame.pack(anchor="w")

        # 角色标签
        tag_text = "👤 你" if is_user else ("🤖 DeepSeek" if not is_system else "📌 系统")
        tag_color = COLORS["user_tag"] if is_user else COLORS["assistant_tag"]

        tag_label = ttkb.Label(
            inner_frame, text=tag_text,
            font=("Microsoft YaHei UI", 9, "bold"),
            foreground=tag_color,
        )
        tag_label.pack(anchor="w" if not is_user else "e", padx=5, pady=(0, 2))

        # 气泡主体
        bg_color = COLORS["user_bg"] if is_user else (COLORS["assistant_bg"] if not is_system else COLORS["system_bg"])

        if is_streaming or is_user or is_system:
            # 文本气泡
            text_widget = tk.Text(
                inner_frame,
                wrap=WORD,
                font=("Microsoft YaHei UI", 10),
                bg=bg_color,
                relief="flat",
                padx=14,
                pady=10,
                height=1,
                width=55,
                highlightthickness=0,
                borderwidth=1,
            )
            text_widget.pack()

            # 设置内容
            text_widget.insert("1.0", content)
            text_widget.configure(state="normal" if is_streaming else DISABLED)
            text_widget.tag_configure("code_bg", background=COLORS["code_bg"])

            # 禁用选择和高亮
            text_widget.bind("<Button-1>", lambda e: "break" if is_streaming else None)

            # 时间戳
            time_str = datetime.now().strftime("%H:%M")
            time_label = ttkb.Label(
                inner_frame, text=time_str,
                font=("Microsoft YaHei UI", 8),
                bootstyle="secondary"
            )
            if is_user:
                time_label.pack(anchor="e", padx=5, pady=(2, 0))
            else:
                time_label.pack(anchor="w", padx=5, pady=(2, 0))

            return text_widget
        return None

    def _add_message(self, role, content):
        """添加普通消息气泡"""
        if role == "assistant":
            self.messages.append({"role": "assistant", "content": content})
        self._create_bubble(role, content)

    def _add_system_message(self, text):
        """添加系统消息"""
        self._create_bubble("system", text)

    # ── 发送消息 ──────────────────────────────────────────────────
    def send_message(self):
        """发送用户消息"""
        if self.is_loading:
            return

        text = self.input_text.get("1.0", "end-1c").strip()
        if not text:
            return

        if not self.client or not self.config.get("api_key"):
            messagebox.showwarning("提示", "请先设置 DeepSeek API Key")
            self.open_settings()
            return

        # 清空输入
        self.input_text.delete("1.0", END)

        # 显示用户消息
        self._create_bubble("user", text)
        self.messages.append({"role": "user", "content": text})

        # 自动滚动到底部
        self.root.after(100, self._scroll_to_bottom)

        # 发送到 API
        self.is_loading = True
        self.send_btn.configure(text="响应中...", state=DISABLED)
        self._update_status("思考中", "warning")

        # 在单独的线程中执行
        thread = threading.Thread(target=self._do_chat, daemon=True)
        thread.start()

    def _do_chat(self):
        """在线程中执行 API 调用"""
        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.extend(self.messages)

            # 创建流式响应气泡（在主线程）
            self.root.after(0, self._create_streaming_bubble)

            # 流式获取响应
            full_response = ""
            for chunk in self.client.chat(messages, stream=True):
                full_response += chunk
                self.root.after(0, self._update_streaming_text, full_response)

            # 完成
            self.root.after(0, self._finish_chat, full_response)

        except requests.exceptions.HTTPError as e:
            error_msg = f"API 请求失败 (HTTP {e.response.status_code})"
            if e.response.status_code == 401:
                error_msg = "API Key 无效，请检查设置"
            elif e.response.status_code == 429:
                error_msg = "请求过于频繁，请稍后再试"
            self.root.after(0, self._handle_error, error_msg)

        except requests.exceptions.ConnectionError:
            self.root.after(0, self._handle_error, "无法连接到 DeepSeek API，请检查网络连接")

        except requests.exceptions.Timeout:
            self.root.after(0, self._handle_error, "请求超时，请稍后重试")

        except Exception as e:
            self.root.after(0, self._handle_error, f"发生错误：{str(e)}")

    def _create_streaming_bubble(self):
        """创建流式响应气泡"""
        # 创建 AI 气泡
        inner_frame = ttkb.Frame(self.msg_frame)
        inner_frame.pack(fill=X, pady=(0, 8), padx=5)

        bubble_container = ttkb.Frame(inner_frame)
        bubble_container.pack(anchor="w")

        ttkb.Label(
            bubble_container, text="🤖 DeepSeek",
            font=("Microsoft YaHei UI", 9, "bold"),
            foreground=COLORS["assistant_tag"],
        ).pack(anchor="w", padx=5, pady=(0, 2))

        text_widget = tk.Text(
            bubble_container,
            wrap=WORD,
            font=("Microsoft YaHei UI", 10),
            bg=COLORS["assistant_bg"],
            relief="flat",
            padx=14,
            pady=10,
            height=3,
            width=55,
            highlightthickness=0,
            borderwidth=1,
        )
        text_widget.pack()
        text_widget.configure(state="normal")

        # 闪烁光标动画
        text_widget.insert("1.0", "▊")
        self.current_streaming_icon = "▊"

        # 存储引用
        self.current_ai_frame = inner_frame
        self.current_ai_widget = text_widget
        self.current_ai_container = bubble_container

        self.root.after(200, self._blink_streaming_cursor)
        self._scroll_to_bottom()

    def _blink_streaming_cursor(self):
        """闪烁光标动画"""
        if self.current_ai_widget and self.is_loading:
            content = self.current_ai_widget.get("1.0", "end-1c")
            if content.endswith("▊"):
                self.current_ai_widget.delete("end-2c", "end-1c")
                self.current_ai_widget.insert(END, "▌")
            elif content.endswith("▌"):
                self.current_ai_widget.delete("end-2c", "end-1c")
                self.current_ai_widget.insert(END, "▊")
            elif content and not content.endswith(("▊", "▌")):
                pass  # 已经有内容了
            self.root.after(400, self._blink_streaming_cursor)

    def _update_streaming_text(self, text):
        """更新流式文本"""
        if self.current_ai_widget:
            self.current_ai_widget.configure(state="normal")
            self.current_ai_widget.delete("1.0", END)
            self.current_ai_widget.insert("1.0", text + "▊")

            # 自动调整文本框高度
            line_count = int(self.current_ai_widget.index("end-1c").split(".")[0])
            new_height = min(max(line_count + 1, 3), 20)
            self.current_ai_widget.configure(height=new_height)

            self._scroll_to_bottom()

    def _finish_chat(self, full_response):
        """完成聊天"""
        if self.current_ai_widget:
            self.current_ai_widget.configure(state="normal")
            self.current_ai_widget.delete("1.0", END)
            self.current_ai_widget.insert("1.0", full_response)
            self.current_ai_widget.configure(state=DISABLED)

            # 添加时间戳
            time_str = datetime.now().strftime("%H:%M")
            time_label = ttkb.Label(
                self.current_ai_container, text=time_str,
                font=("Microsoft YaHei UI", 8),
                bootstyle="secondary"
            )
            time_label.pack(anchor="w", padx=5, pady=(2, 0))

        self.messages.append({"role": "assistant", "content": full_response})
        self._reset_input_state()
        self._scroll_to_bottom()

    def _handle_error(self, msg):
        """处理错误"""
        if self.current_ai_widget:
            self.current_ai_widget.configure(state="normal")
            self.current_ai_widget.delete("1.0", END)
            self.current_ai_widget.insert("1.0", f"❌ {msg}")
            self.current_ai_widget.configure(state=DISABLED)

            time_str = datetime.now().strftime("%H:%M")
            time_label = ttkb.Label(
                self.current_ai_container, text=time_str,
                font=("Microsoft YaHei UI", 8),
                bootstyle="secondary"
            )
            time_label.pack(anchor="w", padx=5, pady=(2, 0))

        self._reset_input_state()

    def _reset_input_state(self):
        """重置输入状态"""
        self.is_loading = False
        self.send_btn.configure(text="发送 ▶", state=NORMAL)
        self.current_ai_widget = None
        self.current_ai_frame = None
        self.current_ai_container = None
        self._update_status("就绪", "success")

    def _update_status(self, text, style="secondary"):
        """更新状态栏"""
        self.status_label.configure(text=f"● {text}", bootstyle=style)

    def _scroll_to_bottom(self):
        """滚动到聊天底部"""
        self.chat_canvas.yview_moveto(1.0)
        self.root.update_idletasks()

    def _on_enter_key(self, event):
        """Enter 键处理"""
        if event.state & 0x1:  # Shift 键按下
            # Shift+Enter 插入换行
            return
        else:
            # Enter 发送
            self.send_message()
            return "break"

    # ── 清空对话 ──────────────────────────────────────────────────
    def clear_chat(self):
        """清空当前对话"""
        if self.is_loading:
            return
        if self.messages:
            if not messagebox.askyesno("新对话", "确定要清空当前对话吗？"):
                return

        # 清空消息列表
        self.messages = []

        # 清空界面
        for widget in self.msg_frame.winfo_children():
            widget.destroy()

        self._add_system_message("已开启新对话，有什么想学的吗？📖")

    # ── 设置窗口 ──────────────────────────────────────────────────
    def open_settings(self):
        """打开设置窗口"""
        settings_win = ttkb.Toplevel(self.root)
        settings_win.title("设置 - DeepSeek 学习助手")
        settings_win.geometry("520x350")
        settings_win.resizable(False, False)
        settings_win.transient(self.root)
        settings_win.grab_set()

        main_frame = ttkb.Frame(settings_win, padding=20)
        main_frame.pack(fill=BOTH, expand=True)

        # 标题
        ttkb.Label(
            main_frame, text="⚙ 设置",
            font=("Microsoft YaHei UI", 14, "bold")
        ).pack(anchor="w", pady=(0, 20))

        # API Key
        ttkb.Label(
            main_frame, text="DeepSeek API Key",
            font=("Microsoft YaHei UI", 10)
        ).pack(anchor="w")

        api_frame = ttkb.Frame(main_frame)
        api_frame.pack(fill=X, pady=(4, 5))

        api_entry = ttkb.Entry(api_frame, font=("Consolas", 10), show="*")
        api_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        api_entry.insert(0, self.config.get("api_key", ""))

        toggle_btn = ttkb.Button(
            api_frame, text="👁",
            bootstyle="outline-secondary",
            width=3,
            command=lambda: self._toggle_api_key_visibility(api_entry, toggle_btn)
        )
        toggle_btn.pack(side=RIGHT)

        # 获取 Key 提示
        ttkb.Label(
            main_frame, text="👉 在 platform.deepseek.com 获取 API Key",
            font=("Microsoft YaHei UI", 8),
            bootstyle="info"
        ).pack(anchor="w", pady=(0, 12))

        # 模型选择
        ttkb.Label(
            main_frame, text="模型选择",
            font=("Microsoft YaHei UI", 10)
        ).pack(anchor="w")

        model_combo = ttkb.Combobox(
            main_frame,
            values=["deepseek-chat", "deepseek-reasoner"],
            state="readonly",
            font=("Microsoft YaHei UI", 10)
        )
        model_combo.pack(fill=X, pady=(4, 5))
        model_combo.set(self.config.get("model", DEFAULT_MODEL))

        ttkb.Label(
            main_frame, text="deepseek-chat: 通用对话 | deepseek-reasoner: 深度推理",
            font=("Microsoft YaHei UI", 8),
            bootstyle="secondary"
        ).pack(anchor="w", pady=(0, 16))

        # 按钮区
        btn_frame = ttkb.Frame(main_frame)
        btn_frame.pack(fill=X)

        ttkb.Button(
            btn_frame, text="保存",
            bootstyle="success",
            command=lambda: self._save_settings(
                settings_win, api_entry.get().strip(), model_combo.get()
            ),
            width=12
        ).pack(side=RIGHT, padx=(5, 0))

        ttkb.Button(
            btn_frame, text="取消",
            bootstyle="secondary-outline",
            command=settings_win.destroy,
            width=12
        ).pack(side=RIGHT)

        # 底部提示
        ttkb.Label(
            main_frame, text="API Key 保存在本地配置文件 config.json 中",
            font=("Microsoft YaHei UI", 8),
            bootstyle="secondary"
        ).pack(anchor="w", pady=(16, 0))

        # 居中
        settings_win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - settings_win.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - settings_win.winfo_height()) // 2
        settings_win.geometry(f"+{x}+{y}")

    def _toggle_api_key_visibility(self, entry, btn):
        """切换 API Key 可见性"""
        if entry.cget("show") == "*":
            entry.configure(show="")
            btn.configure(text="🙈")
        else:
            entry.configure(show="*")
            btn.configure(text="👁")

    def _save_settings(self, window, api_key, model):
        """保存设置"""
        if not api_key:
            messagebox.showwarning("提示", "请输入 DeepSeek API Key")
            return

        self.config["api_key"] = api_key
        self.config["model"] = model
        save_config(self.config)

        self.client = DeepSeekClient(api_key, model)
        self._update_status("已连接", "success")

        # 如果没有对话，添加提示
        if not self.messages:
            self._add_system_message("DeepSeek API 已配置成功！开始学习吧 🚀")

        window.destroy()

    # ── 启动 ──────────────────────────────────────────────────────
    def run(self):
        self.root.mainloop()


# ── 入口 ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = DeepSeekLearnerApp()
    app.run()
