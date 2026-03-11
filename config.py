"""
配置文件 - 修改这里来适配不同项目
"""
import os

# ── 核心配置（必填）──────────────────────────────────────
# Anthropic API Key（也可通过环境变量 ANTHROPIC_API_KEY 设置）
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Claude 模型
CLAUDE_MODEL = "claude-sonnet-4-6"

# ── 工作目录配置 ──────────────────────────────────────────
# bash / read_file / search_files 等工具的默认工作目录
# 设为你想远程控制的项目路径，或直接用 C:/ 控制整个电脑
WORK_DIR = os.environ.get(
    "WECHAT_WORK_DIR",
    r"C:\Users\86139\Desktop\appdevelopment\smart-qto-system"
)

# ── 日志 ──────────────────────────────────────────────────
# 对话日志保存路径
LOG_FILE = os.path.join(os.path.dirname(__file__), "wechat_chat.log")

# ── System Prompt ─────────────────────────────────────────
# 告诉 Claude 它的身份和工作背景，可自由修改
SYSTEM_PROMPT = f"""你是用户电脑的 AI 远程助手，可以直接操作电脑上的文件和命令。

当前工作目录: {WORK_DIR}

你有以下工具：bash、read_file、write_file、search_files、grep、take_photo、screenshot。
回复要简洁，适合手机阅读。执行操作后告诉用户结果。"""

# ── 微信消息设置 ──────────────────────────────────────────
# 单条消息最大长度（超出自动分段）
MAX_MSG_LEN = 1000

# 发出消息的防重复窗口（秒）
SENT_MSG_TTL = 10
