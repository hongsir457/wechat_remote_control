"""
微信远程控制守护进程
手机微信文件传输助手 <-> Claude AI + 本地工具调用

用法:
    python daemon.py
后台运行（不占终端）:
    pythonw daemon.py
"""

import itchat
import anthropic
import subprocess
import os
import sys
import glob as glob_module
import textwrap
import time
import logging
from datetime import datetime

import config

# ── 日志初始化 ─────────────────────────────────────────────
os.makedirs(os.path.dirname(config.LOG_FILE) or '.', exist_ok=True)
_file_handler = logging.FileHandler(config.LOG_FILE, encoding='utf-8')
_file_handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
_stream_handler = logging.StreamHandler(sys.stdout)
_stream_handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
logging.basicConfig(level=logging.INFO, handlers=[_file_handler, _stream_handler])
logger = logging.getLogger('wechat_remote')

# ── 全局状态 ───────────────────────────────────────────────
if config.ANTHROPIC_API_KEY:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
else:
    client = anthropic.Anthropic()  # 读环境变量

conversation_history = []
_sent_messages = set()
_sent_times = {}

# ── 工具定义 ───────────────────────────────────────────────
TOOLS = [
    {
        "name": "take_photo",
        "description": "打开电脑摄像头拍一张照片并发送到微信",
        "input_schema": {
            "type": "object",
            "properties": {
                "camera_index": {"type": "integer", "description": "摄像头编号，默认0"},
                "warmup_frames": {"type": "integer", "description": "预热帧数，默认20"}
            }
        }
    },
    {
        "name": "screenshot",
        "description": "截取当前电脑屏幕并发送到微信",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "bash",
        "description": "执行shell命令，工作目录为配置的 WORK_DIR",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "shell命令"},
                "timeout": {"type": "integer", "description": "超时秒数，默认30"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "read_file",
        "description": "读取文件内容，路径可相对于 WORK_DIR",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "lines": {"type": "integer", "description": "最多读取行数，默认100"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "写入或追加文件内容",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "内容"},
                "mode": {"type": "string", "description": "'write'覆盖（默认）或'append'追加"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "search_files",
        "description": "用glob模式搜索文件，如 '**/*.py'",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "glob模式"}
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "grep",
        "description": "在文件中搜索文本内容",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "搜索文本或正则"},
                "path": {"type": "string", "description": "搜索目录，默认 WORK_DIR"},
                "file_pattern": {"type": "string", "description": "文件类型过滤，如 '*.py'"}
            },
            "required": ["pattern"]
        }
    }
]

# ── 工具执行 ───────────────────────────────────────────────
def _resolve_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(config.WORK_DIR, path)


def run_tool(name: str, inputs: dict) -> str:
    try:
        if name == "take_photo":
            import cv2
            idx = inputs.get("camera_index", 0)
            warmup = inputs.get("warmup_frames", 20)
            logger.info(f"[工具] take_photo camera={idx}")
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if not cap.isOpened():
                return "[错误] 无法打开摄像头"
            for _ in range(warmup):
                cap.read()
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return "[错误] 拍照失败"
            save_dir = os.path.dirname(config.LOG_FILE)
            path = os.path.join(save_dir, f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
            cv2.imwrite(path, frame)
            itchat.send_image(path, toUserName='filehelper')
            return f"照片已发送: {os.path.basename(path)}"

        elif name == "screenshot":
            from PIL import ImageGrab
            logger.info("[工具] screenshot")
            img = ImageGrab.grab()
            save_dir = os.path.dirname(config.LOG_FILE)
            path = os.path.join(save_dir, f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            img.save(path)
            itchat.send_image(path, toUserName='filehelper')
            return f"截图已发送: {os.path.basename(path)}"

        elif name == "bash":
            cmd = inputs["command"]
            timeout = inputs.get("timeout", 30)
            logger.info(f"[工具] bash: {cmd}")
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                               timeout=timeout, cwd=config.WORK_DIR,
                               encoding='utf-8', errors='ignore')
            out = (r.stdout + r.stderr).strip()
            return (out[:1500] + "\n...(已截断)") if len(out) > 1500 else (out or "(无输出)")

        elif name == "read_file":
            path = _resolve_path(inputs["path"])
            limit = inputs.get("lines", 100)
            logger.info(f"[工具] read_file: {path}")
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            if len(lines) > limit:
                return f"(共{len(lines)}行，显示最后{limit}行)\n" + "".join(lines[-limit:])
            return "".join(lines)

        elif name == "write_file":
            path = _resolve_path(inputs["path"])
            mode = 'a' if inputs.get("mode") == "append" else 'w'
            logger.info(f"[工具] write_file: {path}")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, mode, encoding='utf-8') as f:
                f.write(inputs["content"])
            return f"已写入: {path}"

        elif name == "search_files":
            pattern = inputs["pattern"]
            if not os.path.isabs(pattern):
                pattern = os.path.join(config.WORK_DIR, pattern)
            logger.info(f"[工具] search_files: {pattern}")
            matches = glob_module.glob(pattern, recursive=True)
            if not matches:
                return "未找到匹配文件"
            result = "\n".join(matches[:50])
            return result + (f"\n...(共{len(matches)}个)" if len(matches) > 50 else "")

        elif name == "grep":
            pat = inputs["pattern"]
            path = _resolve_path(inputs.get("path", config.WORK_DIR))
            fp = inputs.get("file_pattern", "")
            cmd = (f'grep -r --include="{fp}" -n "{pat}" "{path}"'
                   if fp else f'grep -r -n "{pat}" "{path}"')
            logger.info(f"[工具] grep: {cmd}")
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                               timeout=15, encoding='utf-8', errors='ignore')
            out = r.stdout.strip()
            return (out[:1500] + "\n...(已截断)") if len(out) > 1500 else (out or "未找到匹配内容")

    except subprocess.TimeoutExpired:
        return "[超时]"
    except FileNotFoundError as e:
        return f"[文件不存在] {e}"
    except Exception as e:
        return f"[工具错误] {e}"


# ── Claude Agent 循环 ──────────────────────────────────────
def _blocks_to_dict(content):
    if not isinstance(content, list):
        return content
    result = []
    for block in content:
        if hasattr(block, 'model_dump'):
            result.append(block.model_dump())
        elif hasattr(block, '__dict__'):
            result.append({k: v for k, v in block.__dict__.items() if not k.startswith('_')})
        else:
            result.append(block)
    return result


def ask_claude(user_msg: str) -> str:
    conversation_history.append({"role": "user", "content": user_msg})
    try:
        while True:
            response = client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=2048,
                system=config.SYSTEM_PROMPT,
                tools=TOOLS,
                messages=conversation_history
            )
            tool_calls = [b for b in response.content if b.type == "tool_use"]
            text_parts = [b.text for b in response.content if b.type == "text"]

            if response.stop_reason == "end_turn" or not tool_calls:
                reply = "\n".join(text_parts).strip() or "(完成)"
                conversation_history.append({"role": "assistant", "content": reply})
                return reply

            conversation_history.append({
                "role": "assistant",
                "content": _blocks_to_dict(response.content)
            })
            send_wechat(f"正在执行: {', '.join(t.name for t in tool_calls)}...", is_status=True)

            tool_results = []
            for tool in tool_calls:
                result = run_tool(tool.name, tool.input)
                logger.info(f"[结果] {tool.name}: {str(result)[:80]}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool.id,
                    "content": result
                })
            conversation_history.append({"role": "user", "content": tool_results})

    except Exception as e:
        while conversation_history and conversation_history[-1]["role"] != "user":
            conversation_history.pop()
        if conversation_history:
            conversation_history.pop()
        return f"[Claude 错误] {e}"


# ── 消息发送 ───────────────────────────────────────────────
def _log_chat(role: str, text: str):
    prefix = "【用户】" if role == "user" else "【Claude】"
    line = f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {prefix}\n{text}\n{'─'*40}"
    with open(config.LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line)


def send_wechat(msg: str, is_status=False):
    if is_status:
        wrapped = f"⚙️ {msg}"
    else:
        wrapped = f"🤖 Claude [{datetime.now().strftime('%H:%M')}]\n{'─'*20}\n{msg}"

    parts = ([wrapped] if len(wrapped) <= config.MAX_MSG_LEN
             else textwrap.wrap(wrapped, config.MAX_MSG_LEN,
                                break_long_words=False, replace_whitespace=False))
    for i, part in enumerate(parts):
        text = f"[{i+1}/{len(parts)}]\n{part}" if len(parts) > 1 else part
        _sent_messages.add(text.strip())
        _sent_times[text.strip()] = time.time()
        itchat.send(text, toUserName='filehelper')

    if not is_status:
        _log_chat("assistant", msg)


def _is_own_message(text: str) -> bool:
    now = time.time()
    for k in [k for k, t in _sent_times.items() if now - t > config.SENT_MSG_TTL]:
        _sent_messages.discard(k)
        del _sent_times[k]
    return text in _sent_messages


# ── 特殊指令 ───────────────────────────────────────────────
def handle_cmd(text: str):
    cmd = text.strip()
    if cmd == '/clear':
        conversation_history.clear()
        return "对话历史已清空。"
    if cmd == '/status':
        r = subprocess.run('curl -s http://localhost:8000/health', shell=True,
                           capture_output=True, text=True, timeout=5,
                           encoding='utf-8', errors='ignore')
        return f"[后端状态]\n{r.stdout.strip() or '无响应'}"
    if cmd == '/workdir':
        return f"当前工作目录:\n{config.WORK_DIR}"
    if cmd == '/help':
        return (
            "微信远程控制助手\n"
            "━━━━━━━━━━━━\n"
            "直接发消息 → Claude AI（自动调用工具）\n\n"
            "示例:\n"
            "  帮我拍一张照片\n"
            "  截一张屏幕\n"
            "  查看最新日志\n"
            "  git log 最近5条\n"
            "  现在有哪些进程在跑\n\n"
            "特殊指令:\n"
            "/clear    清空对话历史\n"
            "/status   检查后端服务\n"
            "/workdir  查看工作目录\n"
            "/help     显示此帮助"
        )
    return None


# ── 消息处理 ───────────────────────────────────────────────
@itchat.msg_register(itchat.content.TEXT)
def on_message(msg):
    if msg['ToUserName'] != 'filehelper':
        return
    text = msg['Text'].strip()
    if not text or _is_own_message(text):
        return

    _log_chat("user", text)
    logger.info(f"收到: {text[:80]}")

    try:
        result = handle_cmd(text)
        if result is None:
            send_wechat("⏳ 思考中...", is_status=True)
            result = ask_claude(text)
        send_wechat(result)
    except Exception as e:
        send_wechat(f"[错误] {e}")


# ── 启动 ───────────────────────────────────────────────────
def main():
    logger.info("=" * 50)
    logger.info("微信远程控制守护进程启动")
    logger.info(f"工作目录: {config.WORK_DIR}")
    logger.info(f"对话日志: {config.LOG_FILE}")
    logger.info("=" * 50)

    def qr_callback(uuid, status, qrcode):
        qr_path = os.path.join(os.path.dirname(config.LOG_FILE), 'QR_login.png')
        with open(qr_path, 'wb') as f:
            f.write(qrcode)
        logger.info(f"请扫码登录: {qr_path}")
        os.startfile(qr_path)

    itchat.auto_login(hotReload=True, qrCallback=qr_callback)
    send_wechat(
        "远程控制助手已启动\n"
        "━━━━━━━━━━━━\n"
        "直接说话即可，例如：\n"
        "  帮我拍一张照片\n"
        "  截一张屏幕\n"
        "  查看系统进程\n"
        "发 /help 查看全部功能"
    )
    logger.info("登录成功，开始监听...")
    itchat.run(blockThread=True)


if __name__ == '__main__':
    main()
