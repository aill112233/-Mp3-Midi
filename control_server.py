#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载站控制服务（独立常驻，端口 8001，永不停止）
- 通过 systemd 控制主网站（downloads-hub.service）的启停
- exe 控制端通过它操作，避免"网站停了就失去控制"的悖论
"""
import os
import re
import sys
import time
import threading
import subprocess

from flask import Flask, jsonify, request

# 通过环境变量可配置，默认相对当前目录
BASE_DIR = os.environ.get("HUB_BASE_DIR", os.path.dirname(os.path.abspath(__file__)))
# 共享目录（可选，用于写入 tunnel 地址供控制端 exe 读取）
SHARE_DIR = os.environ.get("HUB_SHARE_DIR", os.path.join(BASE_DIR, "share"))
TUNNEL_WEB_LOG = os.path.join(BASE_DIR, "tunnel_web.log")   # 网站隧道(8000)
TUNNEL_CTRL_LOG = os.path.join(BASE_DIR, "tunnel_ctrl.log")  # 控制隧道(8001)
HOST_CMD_DIR = os.environ.get("HOST_CMD_DIR", "/opt/openclaw/app/skills/host-command")

app = Flask(__name__)

# systemd 服务名
SERVICE = "downloads-hub.service"


def is_website_up():
    try:
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "5", "http://127.0.0.1:8000/"],
            capture_output=True, text=True, timeout=10,
        )
        return r.stdout.strip() == "200"
    except Exception:
        return False


def is_tunnel_up():
    try:
        r = subprocess.run(["pgrep", "-f", "a.pinggy.io"], capture_output=True, text=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def get_tunnel_url(log_path):
    """从隧道日志提取最新地址，优先 run.pinggy-free.link 主域名"""
    if not os.path.exists(log_path):
        return None
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        urls = re.findall(r"https://[\w.-]+\.(?:pinggy-free\.link|free\.pinggy\.net)", text)
        if not urls:
            return None
        # 优先主域名 run.pinggy-free.link
        for u in reversed(urls):
            if "run.pinggy-free.link" in u:
                return u
        return urls[-1]
    except Exception:
        return None


def write_tunnel_url():
    web_url = get_tunnel_url(TUNNEL_WEB_LOG)
    ctrl_url = get_tunnel_url(TUNNEL_CTRL_LOG)
    targets = [
        os.path.join(SHARE_DIR),
        os.path.join(SHARE_DIR, "Downloads"),
        os.path.join(SHARE_DIR, "wz"),
    ]
    try:
        os.makedirs(SHARE_DIR, exist_ok=True)
        for d in targets:
            try:
                os.makedirs(d, exist_ok=True)
                with open(os.path.join(d, "tunnel_url_web.txt"), "w") as f:
                    f.write(web_url or "")
                with open(os.path.join(d, "tunnel_url.txt"), "w") as f:
                    f.write(ctrl_url or web_url or "")
            except Exception:
                pass
    except Exception:
        pass
    return ctrl_url or web_url


def tunnel_watchdog():
    """后台守护：每 20 秒检查隧道地址，变化则更新共享文件"""
    last = None
    while True:
        try:
            cur = write_tunnel_url()
            if cur and cur != last:
                print(f"[watchdog] 隧道地址更新: {cur}", flush=True)
                last = cur
        except Exception:
            pass
        time.sleep(20)


def systemctl(action):
    # failed 状态需要先 reset-failed 才能 start/restart
    if action in ("start", "restart"):
        subprocess.run(["sudo", "systemctl", "reset-failed", SERVICE],
                       capture_output=True, text=True, timeout=15)
    return subprocess.run(
        ["sudo", "systemctl", action, SERVICE],
        capture_output=True, text=True, timeout=60,
    )


def run_async(fn, delay=0):
    """后台线程延迟执行，让 HTTP 请求立即返回"""
    def _run():
        if delay:
            time.sleep(delay)
        try:
            fn()
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()


@app.route("/control/status")
def status():
    url = write_tunnel_url()
    return jsonify({
        "ok": True,
        "website": is_website_up(),
        "tunnel": is_tunnel_up(),
        "public_url": url,
        "local_url": "http://127.0.0.1:8000",
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/control/start", methods=["POST"])
def start():
    if is_website_up():
        return jsonify({"ok": True, "msg": "网站已在运行"})
    run_async(lambda: systemctl("start"))
    return jsonify({"ok": True, "msg": "启动指令已发送，请稍候刷新状态"})


@app.route("/control/restart", methods=["POST"])
def restart():
    run_async(lambda: systemctl("restart"))
    return jsonify({"ok": True, "msg": "重启指令已发送，请稍候刷新状态"})


@app.route("/control/stop", methods=["POST"])
def stop():
    run_async(lambda: systemctl("stop"))
    return jsonify({"ok": True, "msg": "停止指令已发送，请稍候刷新状态"})


@app.route("/control/tunnel", methods=["POST"])
def tunnel_action():
    action = (request.get_json(silent=True) or {}).get("action", "restart")
    if action == "restart":
        def _do():
            subprocess.run(["pkill", "-f", "a.pinggy.io"], timeout=10)
            time.sleep(1)
            start_tunnels()
            time.sleep(10)
            write_tunnel_url()
        threading.Thread(target=_do, daemon=True).start()
        return jsonify({"ok": True, "msg": "隧道重启指令已发送，新地址稍后生效"})
    return jsonify({"ok": False, "msg": "未知操作"})


def start_tunnels():
    """拉起两条隧道（8000 网站 + 8001 控制），各自独立日志"""
    cmd = (
        "setsid nohup ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 "
        "-o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -T -p 443 "
        "-R0:localhost:8000 a.pinggy.io >> " + TUNNEL_WEB_LOG + " 2>&1 & "
        "setsid nohup ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 "
        "-o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes -T -p 443 "
        "-R0:localhost:8001 a.pinggy.io >> " + TUNNEL_CTRL_LOG + " 2>&1 &"
    )
    subprocess.Popen(["/bin/sh", "-c", cmd], cwd=BASE_DIR)


if __name__ == "__main__":
    # 无条件拉起隧道（幂等：重复启动无害，已存在的会自动退出）
    start_tunnels()
    time.sleep(8)
    write_tunnel_url()
    threading.Thread(target=tunnel_watchdog, daemon=True).start()
    app.run(host="0.0.0.0", port=8001, debug=False, threaded=True)
