# 微信远程控制系统

通过微信文件传输助手，用手机随时随地与 Claude AI 交互、远程指挥电脑。

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

**修复 itchat 在 Python 3.10+ 的兼容性 bug**（只需做一次）：

找到 `site-packages/itchat/utils.py`，在 `htmlParser = HTMLParser()` 后加：
```python
import html as _html_module
htmlParser.unescape = staticmethod(_html_module.unescape)
```

### 2. 配置

编辑 `config.py`：
- 填写 `ANTHROPIC_API_KEY`（或设置同名环境变量）
- 修改 `WORK_DIR` 为你想控制的项目目录
- 按需修改 `SYSTEM_PROMPT` 告诉 Claude 你的项目背景

### 3. 启动

```bash
# 前台运行（看日志）
python daemon.py

# 后台运行（不占终端）
pythonw daemon.py

# 双击启动
start.bat
```

首次启动会弹出二维码图片，**用手机微信扫码**（登录网页版协议）。
扫码后状态保存到 `itchat.pkl`，之后重启无需再扫。

---

## 手机端使用

打开微信 → **文件传输助手** → 直接发消息

### 自然语言（Claude 自动调用工具）

```
帮我拍一张照片
截一张屏幕
查看最新日志
git log 最近5条提交
现在有哪些 Python 进程在跑
搜索所有 .py 文件里包含 "error" 的地方
```

### 特殊指令

| 指令 | 功能 |
|------|------|
| `/help` | 显示帮助 |
| `/clear` | 清空对话历史 |
| `/status` | 检查 localhost:8000 服务 |
| `/workdir` | 查看当前工作目录 |

### 消息格式

- 你发的：右侧气泡，无前缀
- Claude 回复：`🤖 Claude [HH:MM]` + 分隔线
- 执行状态：`⚙️ 正在执行...` / `⏳ 思考中...`

---

## 电脑端监控

```bash
# 实时查看对话日志
watch_log.bat

# 或手动
python -c "
import time
with open('wechat_chat.log', encoding='utf-8') as f:
    f.seek(0, 2)
    while True:
        line = f.readline()
        if line: print(line, end='')
        else: time.sleep(0.5)
"
```

---

## 在其他项目中集成单向通知

```python
import sys
sys.path.insert(0, r'C:\Users\86139\Desktop\appdevelopment\wechat_remote_control')
from notify import notify

notify("任务完成！共处理 15 张图纸")
```

---

## 文件说明

```
wechat_remote_control/
├── daemon.py          # 主程序（启动这个）
├── config.py          # 配置文件（修改这里）
├── notify.py          # 单向通知工具
├── requirements.txt   # 依赖列表
├── start.bat          # Windows 快速启动
├── watch_log.bat      # 实时监控对话日志
├── README.md          # 本文件
├── itchat.pkl         # 微信登录缓存（自动生成，勿删）
├── QR_login.png       # 扫码图片（首次生成）
└── wechat_chat.log    # 对话日志（自动生成）
```

---

## 架构

```
手机微信文件传输助手
       │  （微信加密通道，无需暴露公网端口）
       ▼
  itchat（网页版微信协议）
       │
       ├─ /help /clear /status  → 直接处理
       │
       └─ 自然语言  → Anthropic Claude API
                           │
                      工具调用循环
                           ├─ bash         执行命令
                           ├─ read_file    读取文件
                           ├─ write_file   写入文件
                           ├─ search_files 搜索文件
                           ├─ grep         内容搜索
                           ├─ take_photo   摄像头拍照
                           └─ screenshot   屏幕截图
```

## 已知限制

- 桌面版微信看不到 itchat 发的消息（两个独立 session），用 `watch_log.bat` 在电脑监控
- 手机显示"网页版微信登录"提示属正常现象
- 需手动启动，或加入 Windows 任务计划程序实现开机自启
