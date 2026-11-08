# -*- coding: utf-8 -*-
"""生成与原版同年风格的图标：纯白模板印刷感，无着色、无辉光、无叠加装饰。

原版的快速破解图标就是「白色字形 + 透明背景」（见 quickhacks_icons.inkatlas 里的
MemoryWipe / Broadcast / ForceIgnoreTargets 等）。我们之前给图标染色、加辉光、
叠几何装饰，风格因此偏离。

字形选择：
  Self-Erase  -> ForceIgnoreTargets  蒙眼人头 + 感知波纹 = 「让目标忽略」
  Hack Spread -> Broadcast           卫星天线 + 外扩波   = 「向外扩散」

图集部件名不变（VH_SelfEraseIcon / VH_HackSpreadIcon），所以 TweakDB 记录不用改，
只需重打图标 archive。
"""
import os
import numpy as np
from PIL import Image

SRC = r"D:\dsh\2077MOD\.build\icons\png\base\gameplay\gui\common\icons\quickhacks_icons.inkatlas\2160p"
OUT = r"D:\dsh\2077MOD\.build\icons\importsrc2"
PREV = r"D:\dsh\2077MOD\.build\icons\preview\new"
SIZE = 64

os.makedirs(OUT, exist_ok=True)
os.makedirs(PREV, exist_ok=True)


def load_white(name):
    """原版字形直接取 alpha，颜色强制纯白（原图本身已是白字，这里只是保险）。"""
    im = Image.open(os.path.join(SRC, name + ".png")).convert("RGBA")
    a = np.asarray(im).astype(np.uint8).copy()
    a[:, :, 0] = 255
    a[:, :, 1] = 255
    a[:, :, 2] = 255
    return Image.fromarray(a, "RGBA")


def save(img, out_name):
    small = img.resize((SIZE, SIZE), Image.LANCZOS)
    small.save(os.path.join(OUT, out_name + ".png"))
    img.resize((256, 256), Image.LANCZOS).save(os.path.join(PREV, out_name + "_preview.png"))
    return small


se = load_white("ForceIgnoreTargets")
sp = load_white("Broadcast")

save(se, "vh_se_icon")
save(sp, "vh_sp_icon")

print("source glyphs: Self-Erase=ForceIgnoreTargets, Spread=Broadcast")
print("written to:", OUT)
