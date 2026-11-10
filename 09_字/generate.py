# -*- coding: utf-8 -*-
"""
N°09《字》 / THE CHARACTER
汉字「创」「造」的双联生成海报，2400x3600 竖版。

    python generate.py            # 全部重绘
    python generate.py --only 1   # 只画「创」

做法：先用系统字体把字渲染成 1400px 高的蒙版（4x 超采样），
再用 numpy 把它变成材料——「创」变成粒子场，「造」变成地形等高线。
固定随机种子 SEED，可重跑。
"""

import argparse
import os
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import platelib as P

OUT = os.path.dirname(os.path.abspath(__file__))
SEED = 20261109
ACC = "verm"        # 本展品强调色：朱砂


# ==========================================================================
# 字形蒙版
# ==========================================================================
def glyph_mask(ch: str, target_h: int = 1400, weight: str = "Bold"):
    """返回 (mask, w, h)：0..1 的字形蒙版，1x 尺寸、4x 超采样后缩小。"""
    f = ImageFont.truetype(P._FONT_PATHS["serif"], 1600 * P.SS)
    f.set_variation_by_name(weight)
    bbox = f.getbbox(ch)                    # 4x 坐标
    w4, h4 = bbox[2] - bbox[0], bbox[3] - bbox[1]
    im = Image.new("L", (w4 + 16, h4 + 16), 0)
    ImageDraw.Draw(im).text((8 - bbox[0], 8 - bbox[1]), ch, font=f, fill=255)
    new_h = target_h
    new_w = max(1, int(round((w4 + 16) * target_h / (h4 + 16))))
    im = im.resize((new_w, new_h), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255.0


def gblur(a: np.ndarray, sigma: float) -> np.ndarray:
    """FFT 高斯模糊（不依赖 scipy）。"""
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    g = np.exp(-2.0 * (np.pi ** 2) * (sigma ** 2) * (fx ** 2 + fy ** 2))
    return np.fft.irfft2(np.fft.rfft2(a) * g, s=(h, w)).astype(np.float32)


def place(mask: np.ndarray, cx: float, cy: float):
    """把字形蒙版按中心放进整幅画布的坐标里，返回 (mask_full, x0, y0, w, h)。"""
    h, w = mask.shape
    x0 = int(round(cx - w / 2))
    y0 = int(round(cy - h / 2))
    full = np.zeros((P.H, P.W), np.float32)
    full[y0:y0 + h, x0:x0 + w] = mask
    return full, x0, y0, w, h


def seal(canvas, box, ch, gain=0.9):
    """朱砂方印：实心色块，字为阴文（挖空）。"""
    x0, y0, x1, y1 = box
    m = glyph_mask(ch, target_h=int((y1 - y0) * 0.70), weight="Bold")
    h, w = m.shape
    sq = np.zeros((P.H, P.W), np.float32)
    sq[y0:y1, x0:x1] = 1.0
    ox = x0 + (x1 - x0 - w) // 2
    oy = y0 + (y1 - y0 - h) // 2
    sq[oy:oy + h, ox:ox + w] -= m * 0.95
    canvas.add(np.clip(sq, 0, 1), P.COL["verm"], gain)
    # 外框留一道细边
    ink_box = np.zeros((P.H, P.W), np.float32)
    ink_box[y0 - 5:y0 - 2, x0 - 5:x1 + 5] = 1
    ink_box[y1 + 2:y1 + 5, x0 - 5:x1 + 5] = 1
    ink_box[y0 - 5:y1 + 5, x0 - 5:x0 - 2] = 1
    ink_box[y0 - 5:y1 + 5, x1 + 2:x1 + 5] = 1
    canvas.add(ink_box, P.COL["verm"], gain * 0.55)


# ==========================================================================
# 1.「创」——字变成粒子场
# ==========================================================================
def poster_chuang(path: str):
    t0 = time.time()
    rng = np.random.default_rng(SEED + 1)
    m = glyph_mask("创", 1400, "Bold")
    full, x0, y0, w, h = place(m, 1200, 1600)

    canvas = P.Canvas()
    ink = P.Ink()

    # ---- 字内：按蒙版密度撒粒子（笔画内部最密） ----
    n_try = 620_000
    xs = rng.uniform(x0, x0 + w, n_try)
    ys = rng.uniform(y0, y0 + h, n_try)
    pr = full[np.clip(ys.astype(int), 0, P.H - 1), np.clip(xs.astype(int), 0, P.W - 1)]
    keep = rng.random(n_try) < (pr ** 1.35) * 0.92
    xin, yin = xs[keep], ys[keep]

    # ---- 字外：逸散的星尘（密度随距离衰减） ----
    halo = gblur(full, 115.0)
    halo = halo / max(1e-6, halo.max())
    n_try2 = 520_000
    xs2 = rng.uniform(x0 - 620, x0 + w + 620, n_try2)
    ys2 = rng.uniform(y0 - 620, y0 + h + 620, n_try2)
    hh = halo[np.clip(ys2.astype(int), 0, P.H - 1), np.clip(xs2.astype(int), 0, P.W - 1)]
    keep2 = rng.random(n_try2) < np.clip(hh * 1.8, 0, 1) ** 1.6 * 0.85
    xout, yout = xs2[keep2], ys2[keep2]

    # ---- 底层墨光：让字在缩略图下依然可读 ----
    canvas.add(np.clip(gblur(full, 5.0) * 1.6, 0, 1) ** 1.2, P.COL["paper"], 0.055)
    canvas.add(np.clip(gblur(full, 26.0) * 2.2, 0, 1) ** 1.3, P.COL["verm"], 0.075)

    # ---- 粒子 ----
    canvas.add(P.star_mask(xout, yout, core=0.62, halo=1.9, halo_gain=0.12,
                           gain=0.155), P.COL["cyan"], 1.0)
    canvas.add(P.star_mask(xin, yin, core=0.60, halo=1.7, halo_gain=0.10,
                           gain=0.20), P.COL["paper"], 1.0)
    # 笔画骨架更亮一点
    core = pr[keep] > 0.985
    canvas.add(P.star_mask(xin[core], yin[core], core=0.55, halo=2.4, halo_gain=0.16,
                           gain=0.45), P.COL["paper"], 1.0)
    # 少量朱砂粒子：像印泥的碎屑
    ns = int(len(xin) * 0.012)
    sel = rng.choice(len(xin), ns, replace=False)
    canvas.add(P.star_mask(xin[sel], yin[sel], core=0.8, halo=3.0, halo_gain=0.2,
                           gain=0.55), P.COL["verm"], 1.0)

    # ---- 版式 ----
    P.shell(ink, plate="01", series="字", series_no="09",
            algo="创 · CHUÀNG",
            params=f"字形 1400 px · 粒子 {len(xin):,} + 逸散 {len(xout):,} · "
                   f"采样 ∝ 蒙版密度",
            obs="OBS 09-01 / 2026-11-09",
            log="曝光 1/60 s · 光源：单一烛火 · 天气：不可观测 · 温度 −13 °C · 宣纸 No.4",
            legend="● 笔画内部粒子密度高 · ○ 字外为逸散星尘 · 朱砂点为印泥碎屑",
            unit="单位：px（字高 1400）",
            accent=ACC,
            tick_x=(0, 105), tick_y=(0, 131),
            scale=(210, "210 px"))

    P.field_note(ink, 150, 412, "图 1 ｜ 「创」：把字形蒙版当成密度场，"
                                "笔画内部撒得最密，越往外越稀。", 13.5, "dim", 1.4)
    P.field_note(ink, 150, 448, "1400 px 高的字，约 46 万颗粒子；"
                                "缩小时它退回成一个字，放大时是一团星尘。", 12.5, "dim", 1.2)
    P.field_label(ink, 2250, 412, "FIG. 1", 12.0, ACC, 3.0, align="right")

    # 字高标注
    ink.add("dim", lambda d: (P.line(d, (x0 - 44, y0), (x0 - 44, y0 + h), 0.8),
                              P.line(d, (x0 - 52, y0), (x0 - 36, y0), 0.8),
                              P.line(d, (x0 - 52, y0 + h), (x0 - 36, y0 + h), 0.8)), gain=0.8)
    ink.add("dim", lambda d: P.text(d, x0 - 58, y0 + h / 2, "1400", "mono", 11.0, None, 1.4,
                                    align="right"), gain=0.9)

    # 角落：拼音 / 笔画 / 印章
    ink.add("paper", lambda d: P.text(d, 1600, 2612, "chuàng", "mono", 26.0, None, 3.0))
    ink.add("dim", lambda d: P.text(d, 1600, 2648, "创 · 六画 · 阴平", "sans", 13.0, None, 2.4))
    ink.add("dim", lambda d: P.text(d, 1600, 2676, "SERIES OF CHARACTERS · PLATE I",
                                    "sans", 10.0, None, 2.2), gain=0.9)

    seal(canvas, (2050, 2540, 2200, 2690), "创")

    ink.composite(canvas)
    canvas.save(path, grain=0.007, seed=SEED + 11, vignette=0.26)
    print(f"  -> {os.path.basename(path)}  {time.time()-t0:.1f}s")


# ==========================================================================
# 2.「造」——字变成地形等高线
# ==========================================================================
def poster_zao(path: str):
    t0 = time.time()
    m = glyph_mask("造", 1400, "Bold")
    full, x0, y0, w, h = place(m, 1200, 1600)

    canvas = P.Canvas()
    ink = P.Ink()

    # 高度场：字形经高斯模糊后成为一座"岛"，等值线即等高线
    Hf = gblur(full, 34.0)
    Hf = Hf / max(1e-6, Hf.max())
    gy, gx = np.gradient(Hf)
    g = np.hypot(gx, gy) + 1e-5

    levels = np.concatenate([
        np.linspace(0.035, 0.30, 9),      # 外圈：稀疏
        np.linspace(0.33, 0.72, 12),      # 山腰：密
        np.linspace(0.75, 0.96, 6),       # 山顶：稀疏
    ])
    lines = np.zeros_like(Hf)
    for lv in levels:
        wpx = 0.62 + 0.25 * (1.0 - lv)
        lines = np.maximum(lines, np.exp(-0.5 * ((Hf - lv) / (g * wpx)) ** 2))

    # 山的体积：极淡的填色
    canvas.add(np.clip(Hf * 1.5, 0, 1) ** 1.4, P.COL["verm"], 0.055)
    canvas.add(np.clip(gblur(full, 6.0) * 1.5, 0, 1) ** 1.3, P.COL["paper"], 0.05)
    canvas.add(lines, P.COL["verm"], 0.52)
    canvas.add(np.clip(lines - 0.35, 0, 1) ** 1.2, P.COL["paper"], 0.16)

    # 海岸线（字形边缘）更亮
    edge = np.clip(1.0 - np.abs(Hf - 0.5) / (g * 0.9 + 1e-6), 0, 1) ** 0.6
    canvas.add(edge * 0.9, P.COL["paper"], 0.30)

    # 涟漪：以字形中心为源的极淡同心圆
    yy, xx = np.mgrid[0:P.H, 0:P.W].astype(np.float32)
    rr = np.hypot(xx - 1200, yy - 1600)
    ripple = (0.5 + 0.5 * np.cos(rr * 0.055)) ** 6 * np.exp(-rr / 900.0)
    canvas.add(ripple * 0.5, P.COL["verm"], 0.05)

    # ---- 版式 ----
    P.shell(ink, plate="02", series="字", series_no="09",
            algo="造 · ZÀO",
            params=f"字形 1400 px · 高度场 σ=34 px · 等值线 {len(levels)} 级",
            obs="OBS 09-02 / 2026-11-09",
            log="曝光 1/30 s · 光源：单一烛火 · 天气：不可观测 · 温度 −13 °C · 宣纸 No.5",
            legend="● 等高线 = 字形距离场的等值线 · 亮线 = 海岸线（字形边缘）",
            unit="等高距：σ 归一化 0.03",
            accent=ACC,
            tick_x=(0, 105), tick_y=(0, 131),
            scale=(210, "210 px"))

    P.field_note(ink, 150, 412, "图 2 ｜ 「造」：字形先被模糊成一座岛，"
                                "再按等值线切成地形图。", 13.5, "dim", 1.4)
    P.field_note(ink, 150, 448, "笔画越密的地方坡越陡，等高线也越挤；"
                                "字的重心，是这座山的最高点。", 12.5, "dim", 1.2)
    P.field_label(ink, 2250, 412, "FIG. 2", 12.0, ACC, 3.0, align="right")

    # 高程标注
    for (lx, ly, s) in [(x0 + 40, y0 + 120, "1240"), (x0 + w - 120, y0 + 300, "0870"),
                        (x0 + 120, y0 + h - 130, "0520")]:
        ink.add("dim", lambda d, lx=lx, ly=ly: P.circle(d, (lx, ly), 2.2, 0.8), gain=0.8)
        ink.add("dim", lambda d, lx=lx, ly=ly, s=s: P.text(d, lx + 8, ly + 4, s, "mono",
                                                           9.5, None, 1.0), gain=0.85)

    # 字高标注
    ink.add("dim", lambda d: (P.line(d, (x0 - 44, y0), (x0 - 44, y0 + h), 0.8),
                              P.line(d, (x0 - 52, y0), (x0 - 36, y0), 0.8),
                              P.line(d, (x0 - 52, y0 + h), (x0 - 36, y0 + h), 0.8)), gain=0.8)
    ink.add("dim", lambda d: P.text(d, x0 - 58, y0 + h / 2, "1400", "mono", 11.0, None, 1.4,
                                    align="right"), gain=0.9)

    # 角落：拼音 / 笔画 / 印章
    ink.add("paper", lambda d: P.text(d, 1600, 2612, "zào", "mono", 26.0, None, 3.0))
    ink.add("dim", lambda d: P.text(d, 1600, 2648, "造 · 十画 · 去声", "sans", 13.0, None, 2.4))
    ink.add("dim", lambda d: P.text(d, 1600, 2676, "SERIES OF CHARACTERS · PLATE II",
                                    "sans", 10.0, None, 2.2), gain=0.9)

    seal(canvas, (2050, 2540, 2200, 2690), "造")

    ink.composite(canvas)
    canvas.save(path, grain=0.007, seed=SEED + 12, vignette=0.26)
    print(f"  -> {os.path.basename(path)}  {time.time()-t0:.1f}s")


# ==========================================================================
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    print("N°09 字")
    if a.only in ("", "1"):
        poster_chuang(os.path.join(OUT, "poster_01_创.png"))
    if a.only in ("", "2"):
        poster_zao(os.path.join(OUT, "poster_02_造.png"))
