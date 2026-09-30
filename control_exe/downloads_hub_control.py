#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载站控制端（Windows 单文件 exe）
通过公网控制 API 启停/查看 网站
"""
import os
import sys
import json
import time
import threading
import urllib.request
import urllib.error

import tkinter as tk
from tkinter import ttk, messagebox

APP_TITLE = "下载站控制端"
# 地址读取优先级：
# 1. D:\Program Files\wz\（共享目录，VM watchdog 实时维护，永远最新）
# 2. exe 同目录
# 3. 宿主 Downloads / Desktop（旧部署遗留）
EXE_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
TUNNEL_URL_PATHS = [
    r"D:\Program Files\wz\tunnel_url.txt",
    os.path.join(EXE_DIR, "tunnel_url.txt"),
    r"C:\Users\Administrator\Downloads\tunnel_url.txt",
    r"C:\Users\Administrator\Desktop\tunnel_url.txt",
]
TUNNEL_WEB_URL_PATHS = [
    r"D:\Program Files\wz\tunnel_url_web.txt",
    os.path.join(EXE_DIR, "tunnel_url_web.txt"),
    r"C:\Users\Administrator\Downloads\tunnel_url_web.txt",
    r"C:\Users\Administrator\Desktop\tunnel_url_web.txt",
]


class ControlApp:
    def __init__(self, root):
        self.root = root
        root.title(APP_TITLE)
        root.geometry("520x430")
        root.resizable(False, False)
        root.configure(bg="#12141f")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#12141f")
        style.configure("TLabel", background="#12141f", foreground="#e8eaf6", font=("Microsoft YaHei", 10))
        style.configure("Title.TLabel", font=("Microsoft YaHei", 16, "bold"), foreground="#9db3ff")
        style.configure("Stat.TLabel", font=("Microsoft YaHei", 11))
        style.configure("TButton", font=("Microsoft YaHei", 11), padding=8)
        style.configure("Accent.TButton", background="#6c8cff", foreground="#ffffff", font=("Microsoft YaHei", 11, "bold"))
        style.map("Accent.TButton", background=[("active", "#8aa5ff")])
        style.configure("Danger.TButton", background="#f87171", foreground="#ffffff", font=("Microsoft YaHei", 11, "bold"))
        style.map("Danger.TButton", background=[("active", "#fca5a5")])

        main = ttk.Frame(root, padding=24)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="📦 下载站控制端", style="Title.TLabel").pack(anchor="w")

        self.status_label = ttk.Label(main, text="正在检测…", style="Stat.TLabel")
        self.status_label.pack(anchor="w", pady=(14, 4))
        self.url_label = ttk.Label(main, text="公网地址：--", style="Stat.TLabel", foreground="#9db3ff", wraplength=460)
        self.url_label.pack(anchor="w", pady=(0, 4))
        self.time_label = ttk.Label(main, text="", style="Stat.TLabel", foreground="#7a8299")
        self.time_label.pack(anchor="w")

        # 按钮区
        btns = ttk.Frame(main)
        btns.pack(fill="x", pady=(20, 0))
        self.btn_start = ttk.Button(btns, text="▶ 启动", style="Accent.TButton", command=lambda: self.action("start"))
        self.btn_start.grid(row=0, column=0, padx=6, pady=6, sticky="ew")
        self.btn_restart = ttk.Button(btns, text="🔄 重启", command=lambda: self.action("restart"))
        self.btn_restart.grid(row=0, column=1, padx=6, pady=6, sticky="ew")
        self.btn_stop = ttk.Button(btns, text="⏹ 停止", style="Danger.TButton", command=lambda: self.action("stop"))
        self.btn_stop.grid(row=0, column=2, padx=6, pady=6, sticky="ew")
        self.btn_tunnel = ttk.Button(btns, text="🔄 重启隧道", command=lambda: self.action("tunnel"))
        self.btn_tunnel.grid(row=1, column=0, padx=6, pady=6, sticky="ew")
        self.btn_open = ttk.Button(btns, text="🌐 打开网站", command=self.open_site)
        self.btn_open.grid(row=1, column=1, padx=6, pady=6, sticky="ew")
        self.btn_refresh = ttk.Button(btns, text="🔃 刷新状态", command=self.refresh)
        self.btn_refresh.grid(row=1, column=2, padx=6, pady=6, sticky="ew")
        for i in range(3):
            btns.columnconfigure(i, weight=1)

        ttk.Label(main, text="提示：控制端通过公网控制接口操作网站，请保持电脑联网。",
                  foreground="#7a8299", font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(18, 0))

        self.base_url = self.read_tunnel_url()
        self.refresh()

    def read_tunnel_url(self):
        for p in TUNNEL_URL_PATHS:
            try:
                if os.path.exists(p):
                    with open(p, "r") as f:
                        url = f.read().strip()
                        if url.startswith("http"):
                            return url
            except Exception:
                pass
        return None

    def read_web_url(self):
        for p in TUNNEL_WEB_URL_PATHS:
            try:
                if os.path.exists(p):
                    with open(p, "r") as f:
                        url = f.read().strip()
                        if url.startswith("http"):
                            return url
            except Exception:
                pass
        return self.read_tunnel_url()

    def api(self, path, method="GET"):
        # 尝试所有候选地址，直到有一个成功
        candidates = self.read_all_urls()
        if not candidates:
            return {"ok": False, "msg": "未找到公网地址"}
        last_err = ""
        for base in candidates:
            try:
                url = base.rstrip("/") + path
                req = urllib.request.Request(url, method=method)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                last_err = f"HTTP {e.code}"
                continue
            except Exception as e:
                last_err = str(e)
                continue
        return {"ok": False, "msg": last_err or "连接失败"}

    def read_all_urls(self):
        """收集所有候选地址（去重）"""
        urls = []
        for p in TUNNEL_URL_PATHS + TUNNEL_WEB_URL_PATHS:
            try:
                if os.path.exists(p):
                    with open(p, "r") as f:
                        u = f.read().strip()
                        if u.startswith("http") and u not in urls:
                            urls.append(u)
            except Exception:
                pass
        if self.base_url and self.base_url not in urls:
            urls.append(self.base_url)
        return urls

    def refresh(self):
        self.base_url = self.read_tunnel_url() or self.base_url
        d = self.api("/control/status")
        if d.get("ok"):
            ws = d.get("website")
            self.status_label.config(
                text="网站状态：" + ("🟢 运行中" if ws else "🔴 已停止"),
                foreground="#34d399" if ws else "#f87171",
            )
            url = d.get("public_url") or "--"
            self.url_label.config(text="公网地址：" + url)
            if url != "--":
                self.base_url = url
            self.time_label.config(text="检测时间：" + d.get("time", ""))
        else:
            self.status_label.config(text="⚠ 无法连接控制接口", foreground="#fbbf24")
            self.url_label.config(text="公网地址：未知（请点击「刷新状态」重试）")
            self.time_label.config(text=d.get("msg", ""))

    def action(self, act):
        def run():
            self.set_buttons(False)
            d = self.api(f"/control/{act}", method="POST")
            self.set_buttons(True)
            if act == "tunnel":
                url = d.get("public_url") or self.read_tunnel_url()
                msg = f"隧道已重启\n新地址：{url}" if d.get("ok") else f"隧道重启失败：{d.get('msg','')}"
            else:
                msg = d.get("msg", "操作完成")
            self.root.after(0, lambda: (self.refresh(), messagebox.showinfo("下载站控制端", msg)))
        threading.Thread(target=run, daemon=True).start()

    def open_site(self):
        url = self.read_web_url()
        if url:
            os.startfile(url)
        else:
            messagebox.showwarning("下载站控制端", "未找到网站公网地址，请先刷新状态")

    def set_buttons(self, enabled):
        state = "normal" if enabled else "disabled"
        for b in (self.btn_start, self.btn_restart, self.btn_stop, self.btn_tunnel, self.btn_open, self.btn_refresh):
            b.config(state=state)


def main():
    root = tk.Tk()
    ControlApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
