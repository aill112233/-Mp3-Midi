# 📦 Downloads Hub — 安装包整合下载站

一个轻量的**软件安装包整合下载站**：集中展示安装包、一键下载、支持用户上传、自动绑定使用说明书，并可通过 Windows 控制端远程启停。基于 Flask + systemd + Pinggy 隧道，适合在 Linux 虚拟机/NAS/内网服务器上自托管。

![界面预览](docs/screenshot.png)

> 截图：网站首页（深色卡片式界面，含下载/上传/说明书区块）

## ✨ 功能特性

- 📥 **安装包下载**：卡片式展示，一键下载（内置包 + 用户上传包）
- 📤 **上传安装包**：支持 .exe/.msi/.zip/.apk/.dmg 等常见格式，最大 2GB，自动去重命名
- 📄 **使用说明书**：每个软件可绑定说明书（.docx/.pdf/.md/.txt），随包一起打包下载（zip）
- 🌐 **公网访问**：通过 Pinggy SSH 反向隧道，无需公网 IP 即可公网访问
- 🖥️ **Windows 控制端**（exe）：远程启停网站/隧道、查看状态、打开网站，地址自动更新
- 🚀 **开机自启**：systemd 服务托管，网站+隧道+控制服务全自动恢复
- 📡 **JSON API**：`/api/packages` 便于与其他系统对接

## 🗂 项目结构

```
downloads-hub/
├── app.py                    # 主网站 Flask 应用（端口 8000）
├── control_server.py         # 控制服务（端口 8001，常驻）+ 隧道 watchdog
├── control_exe/
│   └── downloads_hub_control.py   # Windows 控制端源码（PyInstaller 打包）
├── templates/
│   ├── index.html            # 首页模板
│   └── _manual_snippet.html  # 说明书内嵌片段（自动生成）
├── static/                   # 静态资源（封面图、说明书下载等）
├── manuals/                  # 各软件的使用说明书（docx）
├── gen_cover.py              # 生成封面背景图
├── gen_manual.py             # 生成网站总说明书
├── gen_software_manuals.py   # 生成各软件说明书
├── systemd/
│   ├── downloads-hub.service     # 网站服务（开机自启）
│   └── control-server.service    # 控制服务（开机自启，永不停止）
├── packages/                 # 内置安装包目录（自行放入）
├── uploads/                  # 用户上传的安装包（运行时生成）
└── meta.json                 # 上传元数据（运行时生成）
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install flask flask-cors python-docx
```

### 2. 放置安装包

把安装包放入 `packages/` 目录，然后在 `app.py` 的 `BUILTIN_PACKAGES` 列表里添加对应条目：

```python
BUILTIN_PACKAGES = [
    {
        "id": "myapp",
        "name": "我的软件",
        "desc": "软件简介",
        "file": "MyApp_Setup_1.0.0.exe",
        "src": "packages/MyApp_Setup_1.0.0.exe",
        "version": "1.0.0",
        "builtin": True,
        "manual": "MyApp_使用说明书.docx",   # 可选，放 manuals/
    },
]
```

### 3. 启动

```bash
python3 app.py          # 网站 → http://localhost:8000
python3 control_server.py  # 控制服务 → http://localhost:8001（可选）
```

### 4. systemd 开机自启（可选）

```bash
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now control-server.service downloads-hub.service
```

## 🌐 公网访问（Pinggy 隧道）

无需公网 IP，通过 [Pinggy](https://pinggy.io) 免费隧道暴露服务：

```bash
# 网站隧道（8000）
ssh -o StrictHostKeyChecking=no -p 443 -R0:localhost:8000 a.pinggy.io
# 控制隧道（8001，可选）
ssh -o StrictHostKeyChecking=no -p 443 -R0:localhost:8001 a.pinggy.io
```

启动后会输出类似 `https://xxxx-xxx.run.pinggy-free.link` 的公网地址。
> 免费隧道约 60 分钟过期，重启后地址会变。控制端 exe 会自动追踪新地址。

## 🖥️ Windows 控制端

`control_exe/downloads_hub_control.py` 是 tkinter GUI，可用 PyInstaller 打包：

```bash
pyinstaller --onefile --windowed --name DownloadsHubControl downloads_hub_control.py
```

功能：启动/停止/重启网站、重启隧道、打开网站、状态监控。
**地址自愈**：优先读取共享目录 `tunnel_url.txt`（watchdog 实时维护），隧道换地址后自动恢复连接。

## 📡 API

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/packages` | GET | 获取安装包列表（JSON） |
| `/control/status` | GET | 网站/隧道状态 |
| `/control/start` | POST | 启动网站 |
| `/control/stop` | POST | 停止网站 |
| `/control/restart` | POST | 重启网站 |
| `/control/tunnel` | POST | 重启公网隧道 |
| `/bundle/<id>` | GET | 打包下载（安装包+说明书 zip） |

## 🔧 常见问题

- **隧道地址变了怎么办**：控制端点「重启隧道」或重启 `control-server.service`，watchdog 会自动更新地址文件
- **上传大文件失败**：检查 `app.config["MAX_CONTENT_LENGTH"]`（默认 2GB）
- **systemd 找不到 flask**：在 service 文件里显式设置 `PYTHONPATH` 和 Python 绝对路径（见 systemd/ 示例）

## 📄 License

MIT
