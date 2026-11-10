# -*- coding: utf-8 -*-
"""交付前自检：格式 / 峰值 / 静音 / 爆音 / 淡变 / 循环接缝 / 彩蛋"""
import os
import sys
import wave
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(HERE, "三小时.wav")

with wave.open(P, "rb") as w:
    nch, sw, sr, nfr = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
    x = np.frombuffer(w.readframes(nfr), dtype="<i2").astype(np.float64).reshape(-1, nch) / 32768.0

mono = x.mean(axis=1)
print("=== 格式 ===")
print("  时长 %.4f s (期望 180.000) / %d Hz / %d 声道 / %d bit" % (nfr / sr, sr, nch, sw * 8))
print("  采样点 %d (期望 7938000)" % nfr)
print("  NaN %s / Inf %s / 削波 %d" % (
    bool(np.isnan(x).any()), bool(np.isinf(x).any()), int((np.abs(x) > 0.9999).sum())))

pk = float(np.abs(x).max())
print("\n=== 电平 ===")
print("  峰值 %.5f = %.2f dBFS (期望 -1.00)" % (pk, 20 * np.log10(pk)))
print("  总 RMS %.2f dBFS / 左右平衡 %.3f dB" % (
    20 * np.log10(np.sqrt(np.mean(mono ** 2))),
    20 * np.log10(np.sqrt(np.mean(x[:, 0] ** 2)) / np.sqrt(np.mean(x[:, 1] ** 2)))))
print("  直流偏移 L %+.6f / R %+.6f" % (x[:, 0].mean(), x[:, 1].mean()))

print("\n=== 爆音检测 ===")
d = np.abs(np.diff(mono))
i = int(np.argmax(d))
loc = np.sqrt(np.mean(mono[max(0, i - 441):i + 441] ** 2))
print("  最大相邻样点跳变 %.4f @ %.3f s (局部 RMS %.4f, 比 %.2f)" % (
    d[i], i / sr, loc, d[i] / max(1e-9, loc)))
print("  >0.15 的跳变数: %d" % int((d > 0.15).sum()))

print("\n=== 淡变 / 接缝 ===")
n15 = int(1.5 * sr)
print("  首样点 %.6f / 第 1.5s 样点 %.4f" % (abs(mono[0]), abs(mono[n15])))
print("  末样点 %.6f / 倒数 1.5s 样点 %.4f" % (abs(mono[-1]), abs(mono[-n15])))
print("  循环接缝跳变 |末-首| = %.6f" % abs(mono[-1] - mono[0]))
fi = np.abs(mono[:n15]).max()
print("  淡入段最大 %.4f (应远小于全曲峰值)" % fi)

print("\n=== 结构 ===")
sec = sr
rms = np.array([np.sqrt(np.mean(mono[i * sec:(i + 1) * sec] ** 2)) for i in range(180)])
db = 20 * np.log10(np.maximum(rms, 1e-9))
for nm, a, b in (("子夜", 0, 60), ("破晓", 60, 120), ("黎明", 120, 180)):
    s = db[a:b]
    print("  %s  RMS %.1f dB (范围 %.1f ~ %.1f)" % (nm, 20 * np.log10(np.sqrt(np.mean(mono[a*sec:b*sec]**2))), s.min(), s.max()))
quiet = db < -55
run = best = 0
for q in quiet:
    run = run + 1 if q else 0
    best = max(best, run)
print("  最长低于 -55 dB 的连续段 %.1f s" % best)

print("\n=== 彩蛋 ===")
i0 = int(120.0 * sr)
w0 = mono[i0:i0 + int(0.35 * sr)]
print("  02:00.000 起 0.35s 峰值 %.4f (%.1f dBFS)，该处音乐 RMS %.1f dBFS" % (
    np.abs(w0).max(), 20 * np.log10(np.abs(w0).max()),
    20 * np.log10(np.sqrt(np.mean(mono[i0 - sr // 2:i0 + sr // 2] ** 2)))))

print("\n=== 文件 ===")
for n in ("三小时.wav", "三小时.mid", "封面.png", "index.html", "README.md"):
    p = os.path.join(HERE, n)
    if os.path.exists(p):
        print("  %-12s %8.2f KB" % (n, os.path.getsize(p) / 1024))
    else:
        print("  %-12s 缺失!" % n)
