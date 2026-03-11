"""
单向通知工具 - 从任意脚本发消息到手机微信

用法:
    # 命令行
    python notify.py "任务完成！"

    # 代码中
    from notify import notify
    notify("APS 处理完成，共 15 张图纸")
"""

import itchat
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_logged_in = False


def login():
    global _logged_in
    if not _logged_in:
        def qr_callback(uuid, status, qrcode):
            qr_path = os.path.join(_HERE, 'QR_login.png')
            with open(qr_path, 'wb') as f:
                f.write(qrcode)
            print(f"请扫码: {qr_path}")
            os.startfile(qr_path)

        itchat.auto_login(hotReload=True, qrCallback=qr_callback)
        _logged_in = True


def notify(msg: str):
    """发送文字通知到文件传输助手"""
    try:
        login()
        itchat.send(msg, toUserName='filehelper')
        print(f"[微信通知] {msg}")
    except Exception as e:
        print(f"[通知失败] {e}")


def notify_image(path: str):
    """发送图片通知"""
    try:
        login()
        itchat.send_image(path, toUserName='filehelper')
        print(f"[图片通知] {path}")
    except Exception as e:
        print(f"[通知失败] {e}")


if __name__ == '__main__':
    msg = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else '测试通知'
    notify(msg)
