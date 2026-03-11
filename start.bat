@echo off
cd /d %~dp0
:: 如果环境变量里没有设置 API Key，在这里填写
:: set ANTHROPIC_API_KEY=sk-ant-你的key

echo 启动微信远程控制守护进程...
pythonw daemon.py
echo 已在后台运行，查看 wechat_chat.log 监控对话
