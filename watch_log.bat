@echo off
cd /d %~dp0
echo 实时监控对话日志（Ctrl+C 退出）...
python -c "
import time, os
log = os.path.join(os.path.dirname(os.path.abspath('.')), 'wechat_remote_control', 'wechat_chat.log')
if not os.path.exists(log):
    open(log, 'w', encoding='utf-8').close()
with open(log, encoding='utf-8') as f:
    f.seek(0, 2)
    while True:
        line = f.readline()
        if line:
            print(line, end='', flush=True)
        else:
            time.sleep(0.5)
"
