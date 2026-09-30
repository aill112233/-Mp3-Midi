#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成说明书封面背景 PNG（A4 @2x：1588×2245，Pillow 实现，无需 playwright/Edge）"""
from PIL import Image, ImageDraw
import math, random

W, H = 1588, 2245
img = Image.new("RGB", (W, H), "#f0f3f6")
d = ImageDraw.Draw(img, "RGBA")

random.seed(42)

# 柔和渐变底色（竖条渐变）
for y in range(H):
    t = y / H
    r = int(240 - 18 * t)
    g = int(243 - 14 * t)
    b = int(246 - 10 * t)
    d.line([(0, y), (W, y)], fill=(r, g, b))

# 顶部 & 底部色带（低饱和 Nordic Mist）
d.rectangle([0, 0, W, 46], fill=(107, 143, 163, 255))
d.rectangle([0, H - 46, W, H], fill=(107, 143, 163, 255))

# 左侧大圆角色块装饰
def rounded_rect(x0, y0, x1, y1, radius, fill):
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)

# 三个错落的半透明几何块（营造层次，不抢文字）
rounded_rect(60, 180, 520, 640, 90, (107, 143, 163, 60))   # 雾蓝
rounded_rect(1040, 120, 1520, 560, 90, (163, 181, 196, 70)) # 浅灰蓝
rounded_rect(880, 1560, 1500, 2050, 110, (196, 168, 130, 55)) # 沙金点缀

# 细装饰线
d.line([(80, 720), (520, 720)], fill=(107, 143, 163, 120), width=4)
d.line([(1040, 680), (1520, 680)], fill=(163, 181, 196, 130), width=4)

# 左下角小圆点阵列（点缀）
for i in range(5):
    x = 120 + i * 46
    d.ellipse([x, 1960, x + 14, 1974], fill=(107, 143, 163, 150))

# 右侧纵向装饰细线
d.line([(1520, 300), (1520, 2000)], fill=(107, 143, 163, 80), width=3)

# 淡噪点（提高质感）
for _ in range(2600):
    x = random.randint(0, W - 1)
    y = random.randint(0, H - 1)
    v = random.randint(0, 12)
    d.point((x, y), fill=(v, v, v + 4, random.randint(8, 26)))

img.save("/mnt/openclaw_home/.openclaw/workspace/downloads-hub/static/manual_cover.png", "PNG")
print("cover saved", img.size)
