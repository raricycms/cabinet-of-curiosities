# -*- coding: utf-8 -*-
"""
N°06《数字星图》 / DIGITAL STAR ATLAS
三张 2400x3600 竖版生成艺术海报：质数螺旋、元胞自动机时空图、π 星尘。

    python generate.py            # 全部重绘
    python generate.py --only 1   # 只画某一张

固定随机种子 SEED，同一台机器上重跑结果逐像素一致。
"""

import argparse
import os
import time

import numpy as np
from PIL import Image, ImageDraw

import platelib as P

OUT = os.path.dirname(os.path.abspath(__file__))
SEED = 20261109
ACC = "cyan"          # 本展品强调色：湖青


# ==========================================================================
# 1. 质数螺旋
# ==========================================================================
def ulam_coords(nmax: int):
    """方形螺旋（乌拉姆螺旋）坐标：n=1 在原点，向右起绕。返回 1..nmax 的 (x,y)。"""
    xs = np.zeros(nmax + 1, np.int32)
    ys = np.zeros(nmax + 1, np.int32)
    dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    n, x, y = 2, 1, 0
    xs[1], ys[1] = 0, 0
    if nmax >= 2:
        xs[2], ys[2] = 1, 0
    d = 1
    while n <= nmax:
        dx, dy = dirs[d % 4]
        L = d // 2 + 1
        m = min(L, nmax - n + 1)
        if m > 0:
            xs[n:n + m] = x + dx * np.arange(1, m + 1)
            ys[n:n + m] = y + dy * np.arange(1, m + 1)
            x += dx * m
            y += dy * m
            n += m
        d += 1
    return xs, ys


def poster_primes(path: str):
    """萨克斯螺旋（Sacks spiral）：r = √n, θ = 2π√n，只标出素数。"""
    t0 = time.time()
    NMAX = 250_000
    R = 960.0                        # 图上半径
    cx, cy = 1200.0, 1650.0

    is_p = P.sieve(NMAX)
    p = np.nonzero(is_p)[0]
    p = p[p >= 2]
    r = np.sqrt(p)
    th = 2.0 * np.pi * np.sqrt(p)
    scale = R / np.sqrt(NMAX)
    px = cx + r * np.cos(th) * scale
    py = cy - r * np.sin(th) * scale

    # 间隔 g = p_next - p
    nxt = np.empty(len(p), np.int64)
    nxt[:-1] = p[1:]
    nxt[-1] = p[-1] + 100
    gaps = (nxt - p).astype(np.float64)
    gaps[-1] = gaps[-2]

    b = np.clip((np.log(gaps) - np.log(2.0)) / (np.log(46.0) - np.log(2.0)), 0.0, 1.0) ** 0.75
    # 半径越外、素数越稀：让亮度随 r 略微抬升，形成自然的"核心—外围"层次
    b = np.clip(b * (0.72 + 0.42 * (r / r.max()) ** 0.6), 0.0, 1.0)

    canvas = P.Canvas()
    ink = P.Ink()

    # ---- 星云底光：把点阵压成极暗的连续光，显出抛物线弧 ----
    glow = P.splat(px, py, 9.0, gain=1.0)
    glow = glow / max(1e-6, np.percentile(glow[glow > 0], 99.5))
    canvas.add(np.clip(glow, 0, 1) ** 1.1, P.COL["cyan"], 0.085)
    canvas.add(np.clip(glow, 0, 1) ** 2.6, P.COL["cyan"], 0.155)

    # ---- 星点 ----
    lo = b < 0.42
    canvas.add(P.star_mask(px[lo], py[lo], core=0.58, halo=1.9, halo_gain=0.10,
                           gain=0.145), P.COL["cyan"], 1.0)
    hi = ~lo
    for k in range(4):
        sel = hi & (b >= 0.42 + 0.145 * k) & (b < 0.565 + 0.145 * k)
        if sel.sum() == 0:
            continue
        canvas.add(P.star_mask(px[sel], py[sel], core=0.62, halo=2.1,
                               halo_gain=0.14, gain=0.34 + 0.21 * k), P.COL["paper"], 1.0)
    top = np.argsort(b)[-6:]
    canvas.add(P.star_mask(px[top], py[top], core=0.9, halo=5.0, halo_gain=0.22,
                           gain=0.9), P.COL["amber"], 1.0)

    # ---- 星座：欧拉多项式 k²+k+41 的 40 个连续素数，在图上连成一条抛物线 ----
    kk = np.arange(0, 40)
    euler = kk * kk + kk + 41
    er = np.sqrt(euler)
    eth = 2.0 * np.pi * np.sqrt(euler)
    ex = cx + er * np.cos(eth) * scale
    ey = cy - er * np.sin(eth) * scale
    for i in range(len(ex) - 1):
        ink.add("amber", lambda d, i=i: P.line(d, (ex[i], ey[i]), (ex[i + 1], ey[i + 1]), 1.1))
    for i in range(len(ex)):
        ink.add("amber", lambda d, i=i: P.circle(d, (ex[i], ey[i]), 3.2, 0.9))
    ink.add("amber", lambda d: P.circle(d, (ex[0], ey[0]), 8.0, 0.8))
    ink.add("amber", lambda d: P.circle(d, (ex[-1], ey[-1]), 8.0, 0.8))
    # 引出线 + 标注，让核心处的小星座可读
    ink.add("amber", lambda d: P.line(d, (ex[-1] + 6, ey[-1] + 3), (1326, 1738), 0.8),
            gain=0.65)
    ink.add("paper", lambda d: P.text(d, 1336, 1743, "k²+k+41", "mono", 11.0, None, 1.2),
            gain=0.8)
    ink.add("dim", lambda d: P.text(d, 1336, 1764, "k = 0…39，40 个连续素数", "sans", 10.5,
                                    None, 0.9), gain=0.95)

    # 记录间隔星：编号环（不连线，避免把星场划成碎块）
    rec = np.argsort(b)[-5:][::-1]
    for n_, i in enumerate(rec):
        ink.add("paper", lambda d, i=i: P.circle(d, (px[i], py[i]), 8.5, 0.8), gain=0.5)
        ink.add("paper", lambda d, i=i: P.circle(d, (px[i], py[i]), 3.0, 0.8), gain=0.85)
        ink.add("dim", lambda d, i=i, n_=n_: P.text(d, px[i] + 14, py[i] - 10,
                                                    f"R{n_+1}", "mono", 9.5, None, 0.8))

    # ---- 圆形天区的边界、方位刻度（RA 风格） ----
    ink.add("line", lambda d: P.circle(d, (cx, cy), R, 0.9))
    ink.add("line", lambda d: P.circle(d, (cx, cy), R + 9, 0.5))
    for i in range(24):
        a = 2 * np.pi * i / 24.0
        c, s = np.cos(a), np.sin(a)
        r0 = R + 2
        r1 = R + (16 if i % 2 == 0 else 8)
        ink.add("dim" if i % 2 == 0 else "line",
                lambda d, c=c, s=s, r0=r0, r1=r1: P.line(d, (cx + c * r0, cy - s * r0),
                                                         (cx + c * r1, cy - s * r1), 0.8))
        if i % 2 == 0:
            lx = cx + c * (R + 38)
            ly = cy - s * (R + 38)
            ink.add("dim", lambda d, lx=lx, ly=ly, i=i: P.text(d, lx, ly + 4, f"{i}h",
                                                               "mono", 10.5, None, 0.6,
                                                               align="center"))
    # 圆心十字
    ink.add("dim", lambda d: (P.line(d, (cx - 9, cy), (cx + 9, cy), 0.7),
                              P.line(d, (cx, cy - 9), (cx, cy + 9), 0.7)))

    # ---- 图版外壳 ----
    P.shell(ink, plate="01", series="数字星图",
            algo="素数螺旋 · SACKS SPIRAL",
            params=f"r = √n  ·  θ = 2π√n  ·  n ≤ {NMAX:,}  ·  素数 {len(p):,} 枚",
            obs="OBS 06-01 / 2026-11-09",
            log="曝光 1/4000 s · 视宁度 1.2″ · 天气：不可观测 · 温度 −13 °C · 乾板 No.11",
            legend="● 亮度 = 素数间隔 g · ○ 环 = 间隔纪录星 · ─ 细线 = 记录星连成的星官 · 琥珀 = k²+k+41 弧",
            unit="投影：极坐标 (r, θ) → 天球平面",
            accent=ACC,
            tick_x=(0, 105), tick_y=(0, 131),
            scale=(200, "200 px ≈ √n 的 0.104 单位"))

    # ---- 图内注记 ----
    P.field_note(ink, 150, 412, "图 1 ｜ 第 n 个整数落在半径 √n、极角 2π√n 的螺线上，"
                                "仅标出素数。", 13.5, "dim", 1.6)
    P.field_note(ink, 150, 448, "素数并非均匀散落：它们沿抛物线的弧聚集，"
                                "对应形如 4k²+bk+c 的二次多项式。", 12.5, "dim", 1.2)
    P.field_note(ink, 150, 480, "琥珀折线为欧拉多项式 k²+k+41：k = 0…39 全部为素数。",
                 12.5, "dim", 1.2)
    P.field_label(ink, 2250, 412, "FIG. 1", 12.0, ACC, 3.0, align="right")

    # 观测失败彩蛋：极小字，index 不解释
    P.field_label(ink, 2250, 2836, "OBJ-06a", 10.0, "dim", 2.4, align="right")
    P.field_label(ink, 2250, 2858, "观测失败 · 该天体不存在", 9.5, "dim", 1.0, align="right")
    ink.add("dim", lambda d: P.circle(d, (2124, 2800), 13, 0.7))
    ink.add("dim", lambda d: (P.line(d, (2101, 2800), (2111, 2800), 0.8),
                              P.line(d, (2137, 2800), (2147, 2800), 0.8),
                              P.line(d, (2124, 2777), (2124, 2787), 0.8),
                              P.line(d, (2124, 2813), (2124, 2823), 0.8)))

    # 标注暗底（压住星场，让小字可读）
    P.knockout(canvas, (1320, 1716, 1600, 1780), 0.62, 18)

    ink.composite(canvas)
    canvas.save(path, grain=0.007, seed=SEED + 1, vignette=0.26)
    print(f"  -> {os.path.basename(path)}  {time.time()-t0:.1f}s")


# ==========================================================================
# 2. 一维元胞自动机时空图
# ==========================================================================
def ca_fixed(rule: int, cells: np.ndarray, steps: int) -> np.ndarray:
    """零边界（不环绕）的一维元胞自动机，返回 (steps, n) 的 0/1 矩阵。"""
    table = np.array([(rule >> i) & 1 for i in range(8)], np.uint8)
    n = len(cells)
    out = np.empty((steps, n), np.uint8)
    s = cells.astype(np.uint8).copy()
    for t in range(steps):
        l = np.empty_like(s)
        l[0] = 0
        l[1:] = s[:-1]
        r = np.empty_like(s)
        r[-1] = 0
        r[:-1] = s[1:]
        s = table[((l << 2) | (s << 1) | r).astype(np.uint8)]
        out[t] = s
    return out


def poster_ca(path: str):
    """规则 90 的时空图：横轴为时间，纵轴为空间；只取一段窗口。"""
    t0 = time.time()
    RULE = 90
    NCELL = 4096
    STEPS = 1800
    SEED_AT = 1024
    T_WIN = (0, 1600)          # 时间窗口：只取其中一段
    C_WIN = (700, 1900)        # 空间窗口：只取其中一段

    init = np.zeros(NCELL, np.uint8)
    init[SEED_AT] = 1
    M = ca_fixed(RULE, init, STEPS)[T_WIN[0]:T_WIN[1], C_WIN[0]:C_WIN[1]]

    X0, X1, Y0, Y1 = 150, 2250, 520, 2740
    fw, fh = X1 - X0, Y1 - Y0
    tt, cc = np.nonzero(M)
    xs = X0 + (tt + 0.5) / M.shape[0] * fw
    ys = Y0 + (cc + 0.5) / M.shape[1] * fh

    canvas = P.Canvas()
    ink = P.Ink()

    # ---- 微光层：把点阵压成极淡的连续光，让"山体"有体积 ----
    glow = P.splat(xs, ys, 7.0, gain=1.0)
    glow = glow / max(1e-6, np.percentile(glow[glow > 0], 99.5))
    canvas.add(np.clip(glow, 0, 1) ** 1.3, P.COL["cyan"], 0.115)

    # ---- 星点：按局部密度分档，稀疏处湖青、稠密处宣纸 ----
    dens = P.splat(xs, ys, 6.0, gain=1.0)
    ix = np.clip(xs.astype(int), 0, P.W - 1)
    iy = np.clip(ys.astype(int), 0, P.H - 1)
    dv = dens[iy, ix]
    qs = np.quantile(dv, [0.45, 0.75, 0.92])
    bins = np.digitize(dv, qs)
    cols = ["cyan", "cyan", "paper", "paper"]
    gains = [0.15, 0.24, 0.36, 0.58]
    for k in range(4):
        sel = bins == k
        if sel.sum() == 0:
            continue
        canvas.add(P.star_mask(xs[sel], ys[sel], core=0.62, halo=1.9,
                               halo_gain=0.12, gain=gains[k]), P.COL[cols[k]], 1.0)
    # 极少数最亮处点琥珀（模拟过曝的恒星）
    top = np.argsort(dv)[-40:]
    canvas.add(P.star_mask(xs[top], ys[top], core=0.9, halo=4.5, halo_gain=0.2,
                           gain=0.75), P.COL["amber"], 1.0)

    # ---- 初始扰动标记 ----
    sx0 = X0 + 18
    sy0 = Y0 + (SEED_AT - C_WIN[0] + 0.5) / M.shape[1] * fh
    ink.add(ACC, lambda d: (P.circle(d, (sx0 + 6, sy0), 9, 0.8),
                            P.line(d, (sx0 + 15, sy0), (sx0 + 62, sy0), 0.8)), gain=0.85)
    ink.add("dim", lambda d: P.text(d, sx0 + 70, sy0 + 4, "t = 0 · 单一初始扰动",
                                    "sans", 10.5, None, 1.2), gain=0.95)

    # ---- 时间轴（图内底部） ----
    ay = Y1 + 34
    ink.add("line", lambda d: P.line(d, (X0, ay), (X1, ay), 0.8), gain=0.9)
    for tval in range(T_WIN[0], T_WIN[1] + 1, 200):
        xx = X0 + (tval - T_WIN[0]) / (T_WIN[1] - T_WIN[0]) * fw
        ink.add("line", lambda d, xx=xx: P.line(d, (xx, ay), (xx, ay + 7), 0.8), gain=0.9)
        ink.add("dim", lambda d, xx=xx, tval=tval: P.text(d, xx, ay + 24, f"{tval}",
                                                          "mono", 10.5, None, 0.8,
                                                          align="center"))
    ink.add("dim", lambda d: P.text(d, X1, ay + 24, "t →", "mono", 10.5, None, 1.2,
                                    align="right"))
    ink.add("dim", lambda d: P.text(d, X0 - 14, Y0 - 12, "空间 x", "sans", 10.5, None,
                                    1.2, align="right"))

    # ---- 图版外壳 ----
    P.shell(ink, plate="02", series="数字星图",
            algo="一维元胞自动机 · RULE 90",
            params=f"规则 {RULE:08b}（二进制） · 格数 {NCELL:,} · 步数 {STEPS:,} · "
                   f"窗口 t∈[{T_WIN[0]},{T_WIN[1]}) × x∈[{C_WIN[0]},{C_WIN[1]})",
            obs="OBS 06-02 / 2026-11-09",
            log="曝光 12 s · 视宁度 0.8″ · 天气：不可观测 · 温度 −13 °C · 乾板 No.12",
            legend="● 亮度 = 局部密度 · ○ 环 = 初始扰动 · 横轴为时间，纵轴为空间；"
                   "每格为 0/1 状态",
            unit="投影：时空图 (t, x)",
            accent=ACC,
            tick_x=(0, 105), tick_y=(0, 131),
            scale=(210, "210 px ≈ 160 步"))

    # ---- 图内注记（右下空区） ----
    P.field_note(ink, 150, 412, "图 2 ｜ 单个格点的初始扰动在 1600 步内展开的时空图；"
                                "横向为时间，纵向为空间。", 13.5, "dim", 1.4)
    P.field_note(ink, 150, 448, "规则 90 是线性的：任意初态都是单个扰动的叠加，"
                                "于是时空图长成了分形。", 12.5, "dim", 1.2)
    P.field_label(ink, 2250, 412, "FIG. 2", 12.0, ACC, 3.0, align="right")

    # 观测失败彩蛋放在第 3 张
    ink.composite(canvas)
    canvas.save(path, grain=0.007, seed=SEED + 2, vignette=0.24)
    print(f"  -> {os.path.basename(path)}  {time.time()-t0:.1f}s")


# ==========================================================================
# 3. π 星尘云
# ==========================================================================
def poster_pi(path: str):
    """π 的数字序列驱动的极坐标游走：10 条旋臂 + 数字直方图。"""
    t0 = time.time()
    rng = np.random.default_rng(SEED + 3)
    DIGITS = P.pi_digits(200_000)
    dg = (np.frombuffer(DIGITS.encode("ascii"), np.uint8) - 48).astype(np.float32)
    dg[0] = 3.0                     # 首位整数 3

    cx, cy = 1200.0, 1600.0
    ARMS, STEPS = 10, 18_000
    RMAX = 980.0

    canvas = P.Canvas()
    ink = P.Ink()

    # ---- 尘埃盘：低亮度背景，由数字给出角度 ----
    nd = 70_000
    ii = np.arange(nd) % len(dg)
    rad = np.sqrt(rng.random(nd)) * RMAX
    ang = np.deg2rad(dg[ii] * 36.0) + ii * 2.399963
    dx = cx + rad * np.cos(ang)
    dy = cy - rad * np.sin(ang)
    canvas.add(P.splat(dx, dy, 1.6, gain=1.0), P.COL["cyan"], 0.022)

    # ---- 10 条旋臂：每条用一段 π 的数字做角向湍流 ----
    walk_k = np.exp(-0.5 * (np.arange(-500, 501) / 210.0) ** 2)
    walk_k /= walk_k.sum()
    t = np.arange(STEPS, dtype=np.float32)
    r = 34.0 * np.exp(t * (np.log(RMAX / 34.0) / STEPS))
    for k in range(ARMS):
        d = dg[k * STEPS:(k + 1) * STEPS]
        if len(d) < STEPS:
            d = np.resize(d, STEPS)
        walk = np.convolve(np.cumsum(d - 4.5), walk_k, mode="same")
        th = (2 * np.pi * k / ARMS + 4.55 * np.log(r / 34.0)
              + 0.0022 * walk + 0.12 * np.sin(t * 0.004 + k))
        rr = r * (1.0 + 0.05 * np.sin(t * 0.011 + 2.0 * k))
        xs = cx + rr * np.cos(th) + rng.normal(0, 2.6, STEPS)
        ys = cy - rr * np.sin(th) + rng.normal(0, 2.6, STEPS)
        b = np.clip(1.0 - r / RMAX, 0.15, 1.0)
        inner = r < RMAX * 0.30
        canvas.add(P.star_mask(xs[inner], ys[inner], core=0.62, halo=2.0,
                               halo_gain=0.13, gain=0.20), P.COL["paper"], 1.0)
        outer = ~inner
        canvas.add(P.star_mask(xs[outer], ys[outer], core=0.62, halo=2.0,
                               halo_gain=0.12, gain=0.165), P.COL["cyan"], 1.0)

    # ---- 核心：亮核 + 极少数琥珀结 ----
    canvas.add(P.star_mask([cx], [cy], core=2.2, halo=16.0, halo_gain=0.16,
                           gain=0.5), P.COL["paper"], 1.0)
    knot = rng.choice(STEPS * ARMS, 5, replace=False)
    kx = cx + rng.uniform(-700, 700, 5)
    ky = cy + rng.uniform(-700, 700, 5)
    canvas.add(P.star_mask(kx, ky, core=1.1, halo=7.0, halo_gain=0.25,
                           gain=0.8), P.COL["amber"], 1.0)

    # ---- 图版外壳 ----
    P.shell(ink, plate="03", series="数字星图",
            algo="π 星尘 · POLAR WALK",
            params="π 前 200,000 位 · 10 条旋臂 × 18,000 步 · θ = θ₀ + 4.55·ln r + 数字湍流",
            obs="OBS 06-03 / 2026-11-09",
            log="曝光 1/2000 s · 视宁度 0.6″ · 天气：不可观测 · 温度 −13 °C · 乾板 No.13",
            legend="● 亮度随半径衰减 · 角度由 π 的数字决定 · 直方图为 0–9 的出现频率",
            unit="投影：极坐标 (r, θ) → 天球平面",
            accent=ACC,
            tick_x=(0, 105), tick_y=(0, 131),
            scale=(200, "200 px"))

    # ---- 天区边界与方位刻度 ----
    ink.add("line", lambda d: P.circle(d, (cx, cy), RMAX, 0.9))
    for i in range(24):
        a = 2 * np.pi * i / 24.0
        c, s = np.cos(a), np.sin(a)
        r0, r1 = RMAX + 2, RMAX + (16 if i % 2 == 0 else 8)
        ink.add("dim" if i % 2 == 0 else "line",
                lambda d, c=c, s=s, r0=r0, r1=r1: P.line(d, (cx + c * r0, cy - s * r0),
                                                         (cx + c * r1, cy - s * r1), 0.8))

    # ---- 旋臂标注 ----
    for k, lab in [(0, "A"), (2, "B"), (5, "C")]:
        a = 2 * np.pi * k / ARMS + 4.55 * np.log(0.72)
        lx = cx + RMAX * 0.74 * np.cos(a)
        ly = cy - RMAX * 0.74 * np.sin(a)
        ink.add("dim", lambda d, lx=lx, ly=ly, lab=lab: P.text(d, lx, ly, f"ARM {lab}",
                                                               "mono", 9.5, None, 1.4,
                                                               align="center"), gain=0.85)

    # ---- 图内注记 ----
    P.field_note(ink, 150, 412, "图 3 ｜ π 的每一位数字决定下一步转多少度；"
                                "十万步之后，它自己绕成了一团星尘。", 13.5, "dim", 1.4)
    P.field_note(ink, 150, 448, "十条旋臂各取一段不同的数字，所以它们不会重复；"
                                "这是 π 的一次指纹。", 12.5, "dim", 1.2)
    P.field_label(ink, 2250, 412, "FIG. 3", 12.0, ACC, 3.0, align="right")

    # ---- 数字直方图（极小，像图版边角的附表） ----
    counts = np.bincount(dg.astype(int), minlength=10) / len(dg)
    bx, by, bw, bh = 152, 2700, 30, 110
    ink.add("line", lambda d: P.line(d, (bx - 10, by + bh), (bx + 10 * bw + 6, by + bh), 0.8),
            gain=0.8)
    for i in range(10):
        hgt = (counts[i] - 0.095) / 0.012 * (bh * 0.22) + bh * 0.5
        hgt = float(np.clip(hgt, 6, bh))
        ink.add("dim", lambda d, i=i, hgt=hgt: P.rect(d, (bx + i * bw + 4, by + bh - hgt,
                                                         bx + i * bw + bw - 6, by + bh),
                                                      fill=True), gain=0.5)
        ink.add("dim", lambda d, i=i: P.text(d, bx + i * bw + bw / 2 - 1, by + bh + 16,
                                             str(i), "mono", 9.5, None, 0.8, align="center"))
    ink.add("dim", lambda d: P.text(d, bx, by - 14, "数字频率 0–9（几乎平坦）", "sans",
                                    10.0, None, 1.2), gain=0.9)

    ink.composite(canvas)
    canvas.save(path, grain=0.007, seed=SEED + 3, vignette=0.26)
    print(f"  -> {os.path.basename(path)}  {time.time()-t0:.1f}s")


# ==========================================================================
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    print("N°06 数字星图")
    if a.only in ("", "1"):
        poster_primes(os.path.join(OUT, "poster_01_质数.png"))
    if a.only in ("", "2"):
        poster_ca(os.path.join(OUT, "poster_02_元胞自动机.png"))
    if a.only in ("", "3"):
        poster_pi(os.path.join(OUT, "poster_03_圆周率.png"))
