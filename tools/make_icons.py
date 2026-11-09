# -*- coding: utf-8 -*-
"""演示：拿原版快速破解图标做程序化改造，生成两枚自制图标。"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SRC = r"D:\dsh\2077MOD\.build\icons\png\base\gameplay\gui\common\icons\quickhacks_icons.inkatlas\2160p"
OUT = r"D:\dsh\2077MOD\icons"
PREV = os.path.join(OUT, "preview")
os.makedirs(PREV, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

UP = 8              # 64 -> 512 再缩回，保证线条平滑
CANVAS = 64 * UP


def load_tinted(name, tint, boost=1.35):
    im = Image.open(os.path.join(SRC, name + ".png")).convert("RGBA")
    im = im.resize((CANVAS, CANVAS), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    rgb, alpha = a[:, :, :3], a[:, :, 3]
    gray = rgb.max(axis=2) / 255.0
    gray = np.clip(gray * boost, 0, 1)
    out = np.zeros_like(a)
    for i in range(3):
        out[:, :, i] = gray * tint[i]
    out[:, :, 3] = alpha
    return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGBA")


def add_glow(img, color, radius=18, strength=0.85):
    a = img.split()[3].filter(ImageFilter.GaussianBlur(radius))
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    solid = Image.new("RGBA", img.size, color + (0,))
    glow = Image.composite(solid, glow, a)
    glow.putalpha(a.point(lambda v: int(v * strength)))
    return Image.alpha_composite(glow, img)


def save(img, name):
    small = img.resize((64, 64), Image.LANCZOS)
    small.save(os.path.join(OUT, name + ".png"))
    big = img.resize((256, 256), Image.LANCZOS)
    big.save(os.path.join(PREV, name + "_preview.png"))
    return small


# ---------------------------------------------------------------- 自我擦除
# 原版「记忆清除」= 头部 + 波纹，改成冷紫青色，并在头部斜切一道“划掉”
se = load_tinted("MemoryWipe", (150, 120, 255))
d = ImageDraw.Draw(se, "RGBA")
w = CANVAS
# 斜切划痕（带暗色描边，保证在任何背景上都看得清）
pad = int(w * 0.16)
d.line([(pad, w - pad), (w - pad, pad)], fill=(12, 8, 20, 235), width=int(w * 0.115))
d.line([(pad, w - pad), (w - pad, pad)], fill=(190, 210, 255, 255), width=int(w * 0.062))
# 划痕两端的端点
r = int(w * 0.052)
for cx, cy in [(pad, w - pad), (w - pad, pad)]:
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(200, 220, 255, 255))
se = add_glow(se, (120, 90, 255))
save(se, "SelfErase")

# ---------------------------------------------------------------- 破解扩散
# 原版「连带传染」= 手掌 + 毒雾，改成琥珀色，并向外扩三圈波纹
sp = load_tinted("Contagion", (255, 176, 64))
d = ImageDraw.Draw(sp, "RGBA")
cx, cy = int(CANVAS * 0.50), int(CANVAS * 0.50)
for i, (rad, alpha, width) in enumerate([
        (int(CANVAS * 0.30), 235, int(CANVAS * 0.055)),
        (int(CANVAS * 0.40), 170, int(CANVAS * 0.042)),
        (int(CANVAS * 0.49), 110, int(CANVAS * 0.032))]):
    box = [cx - rad, cy - rad, cx + rad, cy + rad]
    # 只画右上半圈，避免和小臂重叠
    d.arc(box, start=200, end=340, fill=(255, 214, 130, alpha), width=width)
sp = add_glow(sp, (255, 140, 20))
save(sp, "Spread")

print("已生成:", os.listdir(OUT))
