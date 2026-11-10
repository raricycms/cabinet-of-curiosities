# -*- coding: utf-8 -*-
"""
《三小时》封面 — 1600×1600
深底 + 三条水平线（三个时辰）+ 极小的字形与刻度。构图克制，不用渐变。
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

S = 1600
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = r"C:\Windows\Fonts"

INK_950 = (8, 10, 15)
PAPER = (239, 232, 218)
TEXT = (230, 226, 216)
DIM = (152, 161, 172)
LINE = (42, 52, 66)
AMBER = (217, 160, 91)
CYAN = (111, 179, 168)


def f(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def track(d, xy, txt, font, fill, spacing=0):
    """带字距的文本"""
    if spacing <= 0:
        d.text(xy, txt, font=font, fill=fill)
        return
    x, y = xy
    for ch in txt:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + spacing


def track_w(d, txt, font, spacing=0):
    return sum(d.textlength(c, font=font) + spacing for c in txt) - (spacing if txt else 0)


def right(d, x_right, y, txt, font, fill, spacing=0):
    w = track_w(d, txt, font, spacing)
    track(d, (x_right - w, y), txt, font, fill, spacing)


def runs(d, x, y, parts, fill):
    """多字体混排：parts = [(文本, 字体, 字距)]"""
    cx = x
    for txt, font, sp in parts:
        track(d, (cx, y), txt, font, fill, sp)
        cx += track_w(d, txt, font, sp)
    return cx


def runs_w(d, parts, sp_extra=0):
    return sum(track_w(d, t, fo, sp) for t, fo, sp in parts)


def right_runs(d, x_right, y, parts, fill):
    runs(d, x_right - runs_w(d, parts), y, parts, fill)


def main():
    img = Image.new("RGB", (S, S), INK_950)
    d = ImageDraw.Draw(img)

    f_zh_big = f("STZHONGS.TTF", 168)
    f_zh_mid = f("STZHONGS.TTF", 40)
    f_zh_sm = f("NotoSerifSC-VF.ttf", 27)
    f_zh_tiny = f("NotoSerifSC-VF.ttf", 18)
    f_mono = f("CascadiaMono.ttf", 21)
    f_mono_s = f("CascadiaMono.ttf", 17)
    f_mono_xs = f("CascadiaMono.ttf", 13)

    M = 148                       # 页边
    R = S - M

    # ---------------- 顶部：编号 / 标题 / 副题 ----------------
    track(d, (M, 152), "N\u00b0 05", f_mono, AMBER, 3.0)
    d.line([(M, 190), (M + 52, 190)], fill=AMBER, width=2)

    d.text((M - 6, 214), "三小时", font=f_zh_big, fill=PAPER)

    track(d, (M + 2, 424), "THREE HOURS", f_mono, DIM, 9.0)
    d.text((M + 2, 462), "一分钟一个时辰", font=f_zh_sm, fill=DIM)

    # 右上：极小的说明（中英混排：中文用宋，编号用等宽）
    right_runs(d, R, 156, [("奇珍室", f_zh_tiny, 2.0),
                           (" \u00b7 A CABINET OF CURIOSITIES", f_mono_s, 1.2)], DIM)
    right_runs(d, R, 184, [("创造", f_zh_tiny, 2.0),
                           (" \u00b7 2026", f_mono_s, 1.2)], DIM)

    # ---------------- 中部：三条水平线 = 三个时辰 ----------------
    rows = [
        ("00:00", "01:00", "子夜", "sparse \u00b7 single tones \u00b7 silence"),
        ("01:00", "02:00", "破晓", "arpeggios \u00b7 polyphony \u00b7 warming"),
        ("02:00", "03:00", "黎明", "theme \u00b7 resolution \u00b7 long reverb"),
    ]
    y0 = 700
    gap = 176
    for i, (a, b, zh, en) in enumerate(rows):
        y = y0 + i * gap
        # 主线
        d.line([(M, y), (R, y)], fill=LINE, width=2)
        # 起点标记：一小段强调色
        d.line([(M, y), (M + 92, y)], fill=AMBER, width=2)
        d.ellipse([(M - 3, y - 3), (M + 3, y + 3)], fill=AMBER)

        # 线上方：时间码 + 时辰
        d.text((M, y - 56), "%s \u2014 %s" % (a, b), font=f_mono, fill=DIM)
        d.text((M + 178, y - 74), zh, font=f_zh_mid, fill=TEXT)
        right(d, R, y - 50, en, f_mono_xs, (108, 117, 128), 0.6)

        # 线下方：该时辰内的刻度（每 5 分钟一格，整 10 分钟稍长）
        for k in range(13):
            x = M + k * (R - M) / 12.0
            h = 13 if k % 2 == 0 else 7
            col = (86, 96, 110) if k % 2 == 0 else (54, 63, 76)
            d.line([(x, y + 11), (x, y + 11 + h)], fill=col, width=1)
            if k % 2 == 0 and k < 12:
                d.text((x + 6, y + 27), "%d" % (k * 5), font=f_mono_xs, fill=(70, 79, 92))

    # ---------------- 底部：一秒一刻度的总刻度尺 ----------------
    ry = 1330
    d.line([(M, ry), (R, ry)], fill=(30, 38, 50), width=1)
    for k in range(181):
        x = M + k * (R - M) / 180.0
        if k % 60 == 0:
            h, col = 18, AMBER
        elif k % 10 == 0:
            h, col = 11, (96, 106, 120)
        else:
            h, col = 5, (44, 53, 66)
        d.line([(x, ry - h), (x, ry)], fill=col, width=1)

    # 刻度尺下的三个分界注记
    for t, lab in ((0, "00:00"), (60, "01:00"), (120, "02:00"), (180, "03:00")):
        x = M + t * (R - M) / 180.0
        w = d.textlength(lab, font=f_mono_xs)
        xx = min(max(x - w / 2, M), R - w)
        d.text((xx, ry + 12), lab, font=f_mono_xs, fill=(120, 129, 142))

    # ---------------- 页脚 ----------------
    fy = 1452
    d.line([(M, fy - 30), (R, fy - 30)], fill=(26, 33, 44), width=1)
    runs(d, M, fy, [("D ", f_mono_s, 1.0), ("多利亚", f_zh_tiny, 1.5),
                    (" \u00b7 60 BPM \u00b7 180 s", f_mono_s, 1.0)], DIM)
    right(d, R, fy, "N\u00b0 05 / 10", f_mono_s, AMBER, 1.4)

    # ---------------- 极轻的颗粒（避免纯数字平的呆板，不用渐变） ----------------
    rng = np.random.default_rng(5)
    grain = rng.integers(-3, 4, size=(S, S, 1), dtype=np.int16)
    arr = np.asarray(img, dtype=np.int16)
    arr = np.clip(arr + grain, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGB")

    out = os.path.join(HERE, "封面.png")
    img.save(out, optimize=True)
    print("写出 %s  %.2f MB" % (out, os.path.getsize(out) / 1048576))


if __name__ == "__main__":
    main()
