# -*- coding: utf-8 -*-
"""
Downloads Hub - 安装包整合下载站
三个内置安装包 + 上传区（上传的安装包自动出现在下载列表）
"""
import os
import re
import json
import time
import uuid
import hashlib
import threading

from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, abort, flash
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
PKG_DIR = os.path.join(BASE_DIR, "packages")
MANUAL_DIR = os.path.join(BASE_DIR, "manuals")
META_FILE = os.path.join(BASE_DIR, "meta.json")

# 内置安装包（保持相对路径，便于迁移）
BUILTIN_PACKAGES = [
    {
        "id": "avtools",
        "name": "AVTools 音视频工具箱",
        "desc": "一站式音视频处理工具：格式转换、剪辑、音轨提取、批量处理，覆盖日常音视频需求。",
        "file": "AVTools_Setup_1.0.0.exe",
        "src": "packages/AVTools_Setup_1.0.0.exe",
        "version": "1.0.0",
        "builtin": True,
        "manual": "AVTools_使用说明书.docx",
    },
    {
        "id": "compresstool",
        "name": "极致压缩工具",
        "desc": "高性能文件压缩工具：高压缩率、多格式支持、极速解压，让文件更小、传输更快。",
        "file": "CompressTool_Setup_1.0.0.exe",
        "src": "packages/CompressTool_Setup_1.0.0.exe",
        "version": "1.0.0",
        "builtin": True,
        "manual": "极致压缩工具_使用说明书.docx",
    },
    {
        "id": "gamemodtranslator",
        "name": "游戏 Mod AI 翻译器",
        "desc": "AI 驱动的游戏 Mod 翻译工具：自动识别文本并高质量翻译，让海量 Mod 无障碍游玩。",
        "file": "GameModTranslator-Setup-1.0.exe",
        "src": "packages/GameModTranslator-Setup-1.0.exe",
        "version": "1.0",
        "builtin": True,
        "manual": "游戏ModAI翻译器_使用说明书.docx",
    },
]

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024 * 1024  # 2GB 上限
app.secret_key = "downloads-hub-secret"
CORS(app)

_lock = threading.Lock()


def load_meta():
    """读取上传包的元数据"""
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_meta(meta):
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def human_size(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024


def stat_file(path):
    try:
        return os.path.getsize(path), time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(path)))
    except OSError:
        return 0, "-"


def get_packages():
    pkgs = []
    # 内置包
    for p in BUILTIN_PACKAGES:
        path = os.path.join(BASE_DIR, p["src"])
        if os.path.exists(path):
            size, mtime = stat_file(path)
            manual = None
            m_path = os.path.join(MANUAL_DIR, p.get("manual", ""))
            if p.get("manual") and os.path.exists(m_path):
                manual = {"file": p["manual"], "size": human_size(os.path.getsize(m_path))}
            pkgs.append({**p, "size": human_size(size), "size_raw": size, "mtime": mtime, "uploaded": False, "manual": manual})
    # 上传包
    meta = load_meta()
    for m in meta:
        path = os.path.join(UPLOAD_DIR, m["file"])
        if os.path.exists(path):
            size, mtime = stat_file(path)
            manual = None
            if m.get("manual"):
                m_path = os.path.join(MANUAL_DIR, m["manual"])
                if os.path.exists(m_path):
                    manual = {"file": m["manual"], "size": human_size(os.path.getsize(m_path))}
            pkgs.append({
                "id": m["id"],
                "name": m.get("name", os.path.splitext(m["file"])[0]),
                "desc": m.get("desc", "用户上传的安装包"),
                "file": m["file"],
                "src": "uploads/" + m["file"],
                "version": m.get("version", "-"),
                "builtin": False,
                "uploaded": True,
                "uploader": m.get("uploader", ""),
                "size": human_size(size),
                "size_raw": size,
                "mtime": mtime,
                "manual": manual,
            })
    # 新版优先
    pkgs.sort(key=lambda x: x["size_raw"], reverse=True)
    return pkgs


@app.route("/")
def index():
    return render_template("index.html", packages=get_packages())


@app.route("/download/manual.docx")
def download_manual():
    path = os.path.join(BASE_DIR, "static", "使用说明书.docx")
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name="使用说明书.docx")
    abort(404)


@app.route("/download/<path:src>")
def download(src):
    # 防路径穿越
    if ".." in src or src.startswith("/"):
        abort(404)
    full = os.path.join(BASE_DIR, src)
    if not os.path.exists(full):
        abort(404)
    return send_file(full, as_attachment=True, download_name=os.path.basename(full))


@app.route("/download/manual/<path:src>")
def download_manual_file(src):
    if ".." in src or src.startswith("/"):
        abort(404)
    full = os.path.join(MANUAL_DIR, os.path.basename(src))
    if not os.path.exists(full):
        abort(404)
    return send_file(full, as_attachment=True, download_name=os.path.basename(full))


@app.route("/bundle/<pid>")
def bundle(pid):
    """打包下载：安装包 + 绑定的说明书，打包成 zip"""
    import io
    import zipfile

    pkg = None
    for p in get_packages():
        if p["id"] == pid:
            pkg = p
            break
    if not pkg:
        abort(404)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        pkg_path = os.path.join(BASE_DIR, pkg["src"])
        if os.path.exists(pkg_path):
            zf.write(pkg_path, arcname=os.path.basename(pkg_path))
        if pkg.get("manual") and pkg["manual"].get("file"):
            m_path = os.path.join(MANUAL_DIR, pkg["manual"]["file"])
            if os.path.exists(m_path):
                zf.write(m_path, arcname=pkg["manual"]["file"])
    buf.seek(0)
    safe = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", pkg["name"])
    return send_file(buf, mimetype="application/zip", as_attachment=True,
                     download_name=f"{safe}_安装包+说明书.zip")


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        flash("没有选择文件", "error")
        return redirect(url_for("index"))
    f = request.files["file"]
    if not f or not f.filename:
        flash("没有选择文件", "error")
        return redirect(url_for("index"))

    name = (request.form.get("name") or "").strip()
    desc = (request.form.get("desc") or "").strip()
    version = (request.form.get("version") or "").strip()
    uploader = (request.form.get("uploader") or "").strip()

    # 说明书文件（可选绑定）
    manual_name = None
    mf = request.files.get("manual")
    if mf and mf.filename:
        mext = os.path.splitext(mf.filename)[1].lower()
        if mext not in (".docx", ".doc", ".pdf", ".md", ".txt"):
            flash(f"说明书格式不支持：{mext}（支持 .docx / .doc / .pdf / .md / .txt）", "error")
            return redirect(url_for("index"))
        with _lock:
            mraw = mf.read()
            if not mraw:
                flash("说明书文件内容为空", "error")
                return redirect(url_for("index"))
            muid = uuid.uuid4().hex[:8]
            mdigest = hashlib.md5(mraw).hexdigest()[:10]
            manual_name = f"manual_{time.strftime('%Y%m%d')}_{mdigest}_{muid}{mext}"
            with open(os.path.join(MANUAL_DIR, manual_name), "wb") as out:
                out.write(mraw)

    # 限制扩展名
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in (".exe", ".msi", ".zip", ".7z", ".rar", ".apk", ".dmg", ".pkg", ".run", ".tar", ".gz", ".xz", ".deb", ".rpm", ".appx", ".sh"):
        flash(f"不支持的文件类型：{ext or '(无扩展名)'}", "error")
        return redirect(url_for("index"))

    # 保存文件（唯一文件名）
    with _lock:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        raw = f.read()
        if not raw:
            flash("文件内容为空", "error")
            return redirect(url_for("index"))
        uid = uuid.uuid4().hex[:8]
        digest = hashlib.md5(raw).hexdigest()[:10]
        final_name = f"{time.strftime('%Y%m%d')}_{digest}_{uid}{ext}"
        save_path = os.path.join(UPLOAD_DIR, final_name)
        with open(save_path, "wb") as out:
            out.write(raw)

        meta = load_meta()
        meta.append({
            "id": uid,
            "file": final_name,
            "name": name or os.path.splitext(f.filename)[0],
            "desc": desc or "用户上传的安装包",
            "version": version or "-",
            "uploader": uploader or "匿名",
            "time": time.time(),
            "manual": manual_name,
        })
        save_meta(meta)

    flash(f"上传成功：{name or f.filename}", "success")
    return redirect(url_for("index"))


@app.route("/delete/<pid>", methods=["POST"])
def delete(pid):
    meta = load_meta()
    for m in meta:
        if m["id"] == pid:
            path = os.path.join(UPLOAD_DIR, m["file"])
            if os.path.exists(path):
                os.remove(path)
            # 同时删除绑定的说明书
            if m.get("manual"):
                mp = os.path.join(MANUAL_DIR, m["manual"])
                if os.path.exists(mp):
                    os.remove(mp)
            save_meta([x for x in meta if x["id"] != pid])
            flash(f"已删除：{m['name']}", "success")
            return redirect(url_for("index"))
    flash("未找到该安装包", "error")
    return redirect(url_for("index"))


@app.route("/api/packages")
def api_packages():
    return jsonify(get_packages())


@app.errorhandler(413)
def too_large(e):
    flash("文件过大（上限 2GB）", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(PKG_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=8000, debug=False)
