# -*- coding: utf-8 -*-
"""
《奇珍室》图版语言 / PLATE LANGUAGE
N°06《数字星图》 与 N°09《字》 共用的一套"科学图版"绘制原语。

设计约定
--------
* 成品尺寸 2400 x 3600（竖版），所有线条 / 字形在 SS=4 倍画布上绘制，
  再用 LANCZOS 缩回 1x，得到真正抗锯齿的细线与文字；
* 星点等粒子场用高斯核累加（解析连续，本身不存在锯齿），直接落在 1x 浮点画布上；
* 合成方式为"加色"（深底上的光），最后统一夹紧到 0..1，加极轻的胶片颗粒与暗角。

作者：artist  |  固定随机种子，可重跑。
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --------------------------------------------------------------------------
# 基本尺寸
# --------------------------------------------------------------------------
W, H = 2400, 3600          # 成品尺寸
SS = 4                     # 超采样倍率
FRAME = (120, 120, 2280, 3480)   # 外框
FIELD = (150, 340, 2250, 2960)   # 图版区（图像所在矩形）

# --------------------------------------------------------------------------
# 色板（总纲）
# --------------------------------------------------------------------------
_HEX = dict(
    ink950=0x080a0f, ink900=0x0d1119, ink800=0x141a24, ink700=0x1e2633,
    line=0x2a3442, paper=0xefe8da, text=0xe6e2d8, dim=0x98a1ac,
    cyan=0x6fb3a8, amber=0xd9a05b, verm=0xc05b4d, lilac=0x9a8fb8,
)


def _rgb(v):
    return np.array(((v >> 16) & 255, (v >> 8) & 255, v & 255), np.float32) / 255.0


COL = {k: _rgb(v) for k, v in _HEX.items()}
BG = COL["ink950"]

# --------------------------------------------------------------------------
# 字体
# --------------------------------------------------------------------------
_FONT_PATHS = {
    "serif": r"C:\Windows\Fonts\NotoSerifSC-VF.ttf",
    "sans": r"C:\Windows\Fonts\NotoSansSC-VF.ttf",
    "mono": r"C:\Windows\Fonts\consola.ttf",
}
_FONT_CACHE: dict = {}


def font(kind: str, size: float, weight: str | None = None):
    """size 为成品像素；内部按 SS 放大后交给 FreeType。"""
    key = (kind, round(size * SS), weight)
    f = _FONT_CACHE.get(key)
    if f is None:
        f = ImageFont.truetype(_FONT_PATHS[kind], int(round(size * SS)))
        if weight:
            try:
                f.set_variation_by_name(weight)
            except Exception:
                pass
        _FONT_CACHE[key] = f
    return f


def measure(s: str, f, tracking: float = 0.0) -> float:
    """字距 tracking 以成品像素计。"""
    if not s:
        return 0.0
    return sum(f.getlength(ch) for ch in s) + tracking * SS * (len(s) - 1)


def draw_text(d, x, y, s, f, tracking=0.0, anchor="ls"):
    """逐字绘制以支持字距；返回结束位置 x（4x 坐标）。"""
    for ch in s:
        d.text((x, y), ch, font=f, fill=255, anchor=anchor)
        x += d.textlength(ch, font=f) + tracking * SS
    return x - tracking * SS


# --------------------------------------------------------------------------
# 画布：1x 浮点 RGB，加色合成
# --------------------------------------------------------------------------
class Canvas:
    def __init__(self, bg=BG):
        self.rgb = np.empty((H, W, 3), np.float32)
        self.rgb[:] = bg

    def add(self, mask, color, gain: float = 1.0):
        """mask: (H,W) float 0..1，color: 3 向量。"""
        if gain == 0.0:
            return
        self.rgb += mask[..., None] * (color.astype(np.float32) * gain)

    def multiply(self, m):
        self.rgb *= m[..., None]

    def save(self, path, grain=0.0, seed=0, vignette=0.0):
        rgb = self.rgb
        if grain > 0:
            rng = np.random.default_rng(seed)
            # 逐像素正态噪声（胶片颗粒），低频一点更耐看
            g = rng.normal(0.0, 1.0, (H, W)).astype(np.float32)
            g = (g + np.roll(g, 1, 0) + np.roll(g, 1, 1)) / 3.0
            rgb = rgb + g[..., None] * grain
        if vignette > 0:
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            nx = (xx - W / 2) / (W / 2)
            ny = (yy - H / 2) / (H / 2)
            r = np.sqrt(nx * nx * 0.72 + ny * ny * 0.9)
            rgb = rgb * (1.0 - vignette * np.clip(r, 0, 1) ** 2.2)[..., None]
        np.clip(rgb, 0.0, 1.0, out=rgb)
        Image.fromarray((rgb * 255.0 + 0.5).astype(np.uint8)).save(
            path, optimize=True, compress_level=7)


# --------------------------------------------------------------------------
# 线稿层：按颜色分组，在 4x 画布上绘制后 LANCZOS 缩小
# --------------------------------------------------------------------------
class Ink:
    def __init__(self):
        self.groups: dict = {}

    def add(self, color_name: str, fn, gain: float = 1.0):
        self.groups.setdefault((color_name, round(gain, 3)), []).append(fn)

    def composite(self, canvas: Canvas, gain: float = 1.0):
        for (name, g), fns in self.groups.items():
            im = Image.new("L", (W * SS, H * SS), 0)
            d = ImageDraw.Draw(im)
            for fn in fns:
                fn(d)
            m = np.asarray(im.resize((W, H), Image.LANCZOS), np.float32) / 255.0
            canvas.add(m, COL[name], g * gain)
            del im, m


# --- 基本图元（全部以成品像素为单位书写） ---------------------------------
def rect(d, box, w=1.0, fill=None):
    x0, y0, x1, y1 = box
    if fill:
        d.rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], fill=255)
    else:
        d.rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS],
                    outline=255, width=max(1, int(round(w * SS))))


def hline(d, x0, x1, y, w=1.0):
    d.rectangle([x0 * SS, y * SS - w * SS / 2, x1 * SS, y * SS + w * SS / 2], fill=255)


def vline(d, x, y0, y1, w=1.0):
    d.rectangle([x * SS - w * SS / 2, y0 * SS, x * SS + w * SS / 2, y1 * SS], fill=255)


def line(d, p0, p1, w=1.0):
    d.line([p0[0] * SS, p0[1] * SS, p1[0] * SS, p1[1] * SS],
           fill=255, width=max(1, int(round(w * SS))))


def dashed_line(d, p0, p1, dash=6.0, gap=6.0, w=1.0):
    p0 = np.array(p0, float)
    p1 = np.array(p1, float)
    L = float(np.hypot(*(p1 - p0)))
    if L <= 0:
        return
    u = (p1 - p0) / L
    t = 0.0
    while t < L:
        a = p0 + u * t
        b = p0 + u * min(t + dash, L)
        line(d, tuple(a), tuple(b), w)
        t += dash + gap


def circle(d, c, r, w=1.0, fill=None):
    box = [(c[0] - r) * SS, (c[1] - r) * SS, (c[0] + r) * SS, (c[1] + r) * SS]
    if fill:
        d.ellipse(box, fill=255)
    else:
        d.ellipse(box, outline=255, width=max(1, int(round(w * SS))))


def text(d, x, y, s, kind="sans", size=14, weight=None, tracking=0.0,
         anchor="ls", align="left"):
    # Consolas 没有汉字；含非 ASCII 字符时自动退回 Noto Sans SC，避免豆腐块
    if kind == "mono" and any(ord(c) > 127 for c in s):
        kind = "sans"
    f = font(kind, size, weight)
    if align == "right":
        x -= measure(s, f, tracking)
    elif align == "center":
        x -= measure(s, f, tracking) / 2.0
    draw_text(d, x * SS, y * SS, s, f, tracking, anchor)


# --------------------------------------------------------------------------
# 高斯点溅射（粒子场）
# --------------------------------------------------------------------------
def splat(xs, ys, sigma=1.0, sigma_y=None, gain=1.0, shape=(H, W)):
    """把点集累加成一张连续密度图（解析抗锯齿）。"""
    sy = sigma if sigma_y is None else sigma_y
    buf = np.zeros(shape, np.float32)
    if len(xs) == 0:
        return buf
    rx = max(1, int(np.ceil(3.0 * sigma)))
    ry = max(1, int(np.ceil(3.0 * sy)))
    ix = np.floor(np.asarray(xs)).astype(np.int32)
    iy = np.floor(np.asarray(ys)).astype(np.int32)
    ok = (ix >= rx) & (ix < shape[1] - rx) & (iy >= ry) & (iy < shape[0] - ry)
    ix = ix[ok]
    iy = iy[ok]
    if len(ix) == 0:
        return buf
    for oy in range(-ry, ry + 1):
        ky = np.exp(-0.5 * (oy / sy) ** 2)
        if ky < 0.008:
            continue
        for ox in range(-rx, rx + 1):
            kx = np.exp(-0.5 * (ox / sigma) ** 2)
            if kx < 0.008:
                continue
            np.add.at(buf, (iy + oy, ix + ox), np.float32(kx * ky * gain))
    return buf


def star_mask(xs, ys, core=0.75, halo=2.6, halo_gain=0.14, gain=1.0):
    """带轻微光晕的星点。"""
    m = splat(xs, ys, core, gain=gain)
    m += splat(xs, ys, halo, gain=gain * halo_gain)
    return m


# --------------------------------------------------------------------------
# 图版外壳：页眉 / 页脚 / 图版框 / 刻度
# --------------------------------------------------------------------------
def shell(ink: Ink, *, plate: str, series: str, algo: str, params: str,
          obs: str, log: str, legend: str = "", unit: str = "",
          accent: str = "cyan", series_no: str = "06",
          tick_x=(0, 100), tick_y=(0, 100),
          tick_x_labels=None, tick_y_labels=None, scale=None):
    """绘制整张海报的公共版式。

    plate       "01"          -> PLATE 01
    series      "数字星图"     -> 右侧小字
    algo        算法名（左下）
    params      参数（左下，等宽小字）
    obs         观测编号（右下）
    log         底部极小观测记录
    legend      图例小字（可选）
    scale       (长度像素, 标注文字) 比例尺
    """
    # --- 外框：双细线 + 四角套准 ---
    ink.add("line", lambda d: rect(d, FRAME, 1.0))
    ink.add("line", lambda d: rect(d, (FRAME[0] + 14, FRAME[1] + 14,
                                       FRAME[2] - 14, FRAME[3] - 14), 0.6))
    for (cx, cy, sx, sy) in [
        (FRAME[0], FRAME[1], 1, 1), (FRAME[2], FRAME[1], -1, 1),
        (FRAME[0], FRAME[3], 1, -1), (FRAME[2], FRAME[3], -1, -1)]:
        ink.add("dim", lambda d, cx=cx, cy=cy, sx=sx, sy=sy: (
            line(d, (cx + 34 * sx, cy + 34 * sy), (cx + 34 * sx + 22 * sx, cy + 34 * sy), 1.0),
            line(d, (cx + 34 * sx, cy + 34 * sy), (cx + 34 * sx, cy + 34 * sy + 22 * sy), 1.0)))

    # --- 页眉 ---
    ink.add("paper", lambda d: text(d, 168, 208, "奇珍室制字所", "serif", 33, "SemiBold", 7.5))
    ink.add("dim", lambda d: text(d, 168, 248, "TYPE FOUNDRY", "sans", 13.5,
                                  "Medium", 5.2))
    ink.add("paper", lambda d: text(d, 2232, 206, f"PLATE {plate}", "mono", 21, None, 5.0,
                                    align="right"))
    ink.add("dim", lambda d: text(d, 2232, 248, f"N°{series_no} · {series}", "sans", 13.5, "Medium",
                                  3.0, align="right"))
    ink.add("line", lambda d: hline(d, 150, 2250, 292, 1.0))

    # --- 图版区边框 + 刻度 ---
    x0, y0, x1, y1 = FIELD
    ink.add("line", lambda d: rect(d, FIELD, 1.0))
    for c in [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]:
        ink.add("dim", lambda d, c=c: (
            line(d, (c[0] - 9, c[1]), (c[0] + 9, c[1]), 0.9),
            line(d, (c[0], c[1] - 9), (c[0], c[1] + 9), 0.9)))

    tx0, tx1 = tick_x
    k = 0
    x = x0
    while x <= x1 + 0.01:
        long = (k % 5 == 0)
        ln = 11 if long else 6
        ink.add("dim" if long else "line",
                lambda d, x=x, ln=ln: line(d, (x, y1), (x, y1 + ln), 0.9))
        ink.add("dim" if long else "line",
                lambda d, x=x, ln=ln: line(d, (x, y0), (x, y0 - ln), 0.9))
        x += tx1
        k += 1
    ty0, ty1 = tick_y
    k = 0
    y = y0
    while y <= y1 + 0.01:
        long = (k % 5 == 0)
        ln = 11 if long else 6
        ink.add("dim" if long else "line",
                lambda d, y=y, ln=ln: line(d, (x0, y), (x0 - ln, y), 0.9))
        ink.add("dim" if long else "line",
                lambda d, y=y, ln=ln: line(d, (x1, y), (x1 + ln, y), 0.9))
        y += ty1
        k += 1

    # 刻度数字（少量，克制）
    if tick_x_labels:
        for (xx, s) in tick_x_labels:
            ink.add("dim", lambda d, xx=xx, s=s: text(d, xx, y1 + 30, s, "mono", 11.5,
                                                      None, 1.2, anchor="ls", align="center"))
    if tick_y_labels:
        for (yy, s) in tick_y_labels:
            ink.add("dim", lambda d, yy=yy, s=s: text(d, x0 - 26, yy + 4, s, "mono", 11.5,
                                                      None, 1.2, align="right"))

    # --- 比例尺 ---
    if scale:
        L, lab = scale
        sx, sy = x0 + 42, y1 - 58
        ink.add("dim", lambda d: (
            line(d, (sx, sy), (sx + L, sy), 1.0),
            line(d, (sx, sy - 6), (sx, sy + 6), 1.0),
            line(d, (sx + L, sy - 6), (sx + L, sy + 6), 1.0),
            line(d, (sx + L / 2, sy - 4), (sx + L / 2, sy + 4), 0.8)))
        ink.add("dim", lambda d: text(d, sx + L / 2, sy + 30, lab, "mono", 11.5, None, 1.6,
                                      align="center"))
    if unit:
        ink.add("dim", lambda d: text(d, x1 - 26, y1 - 40, unit, "mono", 11.5, None, 1.6,
                                      align="right"))

    # --- 图下说明区 ---
    ink.add("paper", lambda d: text(d, 168, 3042, algo, "serif", 27, "Medium", 1.5))
    ink.add("dim", lambda d: text(d, 168, 3086, params, "mono", 14.0, None, 1.0))
    ink.add(accent, lambda d: text(d, 2232, 3040, obs, "mono", 15.0, None, 2.2, align="right"))
    ink.add("line", lambda d: hline(d, 150, 2250, 3124, 0.8))
    if legend:
        ink.add("dim", lambda d: text(d, 168, 3166, legend, "sans", 12.5, "Regular", 1.6))
    ink.add("dim", lambda d: text(d, 2232, 3166, "奇珍室 · 创造 2026", "sans", 12.5,
                                  "Regular", 2.4, align="right"))
    # 底部观测记录
    ink.add("dim", lambda d: text(d, 168, 3402, log, "mono", 12.0, None, 1.4))


# --------------------------------------------------------------------------
# 图版区内的辅助标记
# --------------------------------------------------------------------------
def field_cross(ink: Ink, x, y, r=7, color="dim"):
    ink.add(color, lambda d: (line(d, (x - r, y), (x + r, y), 0.8),
                              line(d, (x, y - r), (x, y + r), 0.8)))


def field_label(ink: Ink, x, y, s, size=12.0, color="dim", tracking=2.0, align="left",
                kind="mono"):
    ink.add(color, lambda d: text(d, x, y, s, kind, size, None, tracking, align=align))


def knockout(canvas: Canvas, box, amount=0.5, feather=16):
    """在星场上"挖"出一块柔边的暗底，供小字压在其上（图版标注的常规做法）。"""
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, x1), min(H, y1)
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx = np.minimum(xx - x0, x1 - 1 - xx)
    dy = np.minimum(yy - y0, y1 - 1 - yy)
    m = np.clip(np.minimum(dx, dy) / max(1.0, feather), 0.0, 1.0)
    canvas.rgb[y0:y1, x0:x1] *= (1.0 - amount * m)[..., None]


def field_note(ink: Ink, x, y, s, size=11.5, color="dim", tracking=1.6, align="left"):
    ink.add(color, lambda d: text(d, x, y, s, "sans", size, "Regular", tracking, align=align))


# --------------------------------------------------------------------------
# 数学工具
# --------------------------------------------------------------------------
def sieve(n: int) -> np.ndarray:
    """厄拉多塞筛，返回长度 n+1 的布尔数组（True = 质数）。"""
    is_p = np.ones(n + 1, bool)
    is_p[:2] = False
    for i in range(2, int(n ** 0.5) + 1):
        if is_p[i]:
            is_p[i * i::i] = False
    return is_p


def ca1d(rule: int, cells: np.ndarray, steps: int) -> np.ndarray:
    """一维元胞自动机（周期边界），返回 (steps, n) 的 0/1 矩阵。"""
    table = np.array([(rule >> i) & 1 for i in range(8)], np.uint8)
    n = len(cells)
    out = np.empty((steps, n), np.uint8)
    s = cells.astype(np.uint8).copy()
    for t in range(steps):
        idx = ((np.roll(s, 1) << 2) | (s << 1) | np.roll(s, -1)).astype(np.uint8)
        s = table[idx]
        out[t] = s
    return out


def pi_digits(n: int) -> str:
    """Chudnovsky 二进制分裂算法（纯整数运算），返回前 n 位十进制数字，含开头的 3。

    1/π = 12 · Σ (-1)^k (6k)!(13591409+545140134k) / ((3k)!(k!)^3 (640320)^(3k+3/2))
    """
    import sys
    from math import isqrt

    if hasattr(sys, "set_int_max_str_digits"):
        sys.set_int_max_str_digits(0)   # 允许超长整数转字符串（3.11+）

    C3_OVER_24 = 640320 ** 3 // 24

    def bs(a, b):
        if b - a == 1:
            if a == 0:
                Pab = Qab = 1
            else:
                Pab = (6 * a - 5) * (2 * a - 1) * (6 * a - 1)
                Qab = a * a * a * C3_OVER_24
            Tab = Pab * (13591409 + 545140134 * a)
            if a & 1:
                Tab = -Tab
            return Pab, Qab, Tab
        m = (a + b) // 2
        Pam, Qam, Tam = bs(a, m)
        Pmb, Qmb, Tmb = bs(m, b)
        return Pam * Pmb, Qam * Qmb, Tam * Qmb + Pam * Tmb

    prec = n + 20
    terms = prec // 14 + 2
    P, Q, T = bs(0, terms)
    one = 10 ** (2 * prec)
    sqrt10005 = isqrt(10005 * one)
    val = (Q * 426880 * sqrt10005) // T
    st = str(val)
    return st[:n]
