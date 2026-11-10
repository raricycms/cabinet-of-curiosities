# -*- coding: utf-8 -*-
"""
《三小时》— 作曲 / 渲染 / 导出
60 BPM，1 拍 = 1 秒，1 小节 = 4 秒，45 小节 = 180 秒。
三个时辰各 60 秒 = 15 小节，分界在 00:60 / 02:00 整点。

固定动机 M0 = D4 A4 G4 F4（上行五度 + 两次下行级进），
全曲只做：调内移调 / 倒影 / 增值 / 逆行 四种变形。
"""
import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synth as S
import midiw

FS = S.FS
DUR = 180.0
N = int(FS * DUR)
BPM = 60.0
BEAT = 60.0 / BPM          # 1.0 s
BAR = 4 * BEAT             # 4.0 s
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

rng = np.random.default_rng(20261109)


def bar(b):
    """小节号(1-based) -> 秒"""
    return (b - 1) * BAR


# --------------------------------------------------------------------------
# 音阶 / 动机
# --------------------------------------------------------------------------
SCALE_PCS = [0, 2, 3, 5, 7, 9, 10]        # D 多利亚：D E F G A B C
ROOT = 62                                  # D4


def scale_notes(lo=24, hi=110):
    return [m for m in range(lo, hi + 1) if (m - ROOT) % 12 in SCALE_PCS]


SN = scale_notes()
SN_IDX = {n: i for i, n in enumerate(SN)}


def dia(m, steps):
    """调内（音阶级）移调。"""
    i = SN_IDX[int(m)] + int(steps)
    i = max(0, min(len(SN) - 1, i))
    return SN[i]


def motive_transpose(mot, steps):
    return [(dia(p, steps), d) for p, d in mot]


def motive_invert(mot, axis=ROOT):
    """以首音为轴的严格倒影。"""
    return [(2 * axis - p, d) for p, d in mot]


def motive_augment(mot, k=2.0):
    return [(p, d * k) for p, d in mot]


def motive_retro(mot):
    return [(p, d) for p, d in reversed(mot)]


def motive_render(mot, t0):
    """动机 -> (绝对时间, midi, 时值) 列表"""
    out, t = [], t0
    for p, d in mot:
        out.append((t, p, d * BEAT))
        t += d * BEAT
    return out


M0 = [(62, 1.5), (69, 0.5), (67, 1.0), (65, 2.0)]        # D4 A4 G4 F4
M1 = motive_transpose(M0, 3)                              # G4 D5 C5 B4
M2 = motive_invert(M0)                                    # D4 G3 A3 B3
M3 = motive_augment(M0, 2.0)                              # 增值
M4 = motive_retro(M0)                                     # 逆行 F4 G4 A4 D4


# --------------------------------------------------------------------------
# 和声
# --------------------------------------------------------------------------
CH = {
    "Dm7":   dict(pcs=[2, 5, 9, 0],  voicing=[38, 45, 53, 60]),
    "G":     dict(pcs=[7, 11, 2, 9], voicing=[43, 50, 57, 59]),
    "Fmaj7": dict(pcs=[5, 9, 0, 4],  voicing=[41, 48, 57, 64]),
    "Cadd9": dict(pcs=[0, 4, 7, 2],  voicing=[36, 43, 55, 62]),
    "Am7":   dict(pcs=[9, 0, 4, 7],  voicing=[45, 52, 60, 67]),
}

# (起始小节, 结束小节(不含), 和弦)
SCHED = [
    # 一、子夜  1-15
    (1, 5, "Dm7"), (5, 9, "G"), (9, 13, "Fmaj7"), (13, 16, "Cadd9"),
    # 二、破晓  16-30
    (16, 18, "Dm7"), (18, 20, "G"), (20, 22, "Fmaj7"), (22, 24, "Cadd9"),
    (24, 26, "Dm7"), (26, 28, "G"), (28, 30, "Fmaj7"), (30, 31, "Cadd9"),
    # 三、黎明  31-45
    (31, 33, "Dm7"), (33, 35, "G"), (35, 37, "Fmaj7"), (37, 39, "Cadd9"),
    (39, 41, "Dm7"), (41, 43, "G"), (43, 46, "Dm7"),
]


def chord_at(t):
    b = t / BAR + 1
    for s, e, name in SCHED:
        if s <= b < e:
            return name
    return "Dm7"


# --------------------------------------------------------------------------
# 事件表
# --------------------------------------------------------------------------
PAD = []      # (t, dur, midi_list, amp, attack, release)
BELL = []     # (t, midi, amp, tau, pan)
PLUCK = []    # (t, midi, amp, pan, dur, bright, t60, damp)
EGG = []      # 彩蛋

BELL_G = 0.82      # 钟声总线增益
PLUCK_G = 2.30     # 拨弦总线增益


def pad_amp(t):
    xs = [0.0, 60.0, 120.0, 150.0, 168.0, 180.0]
    ys = [0.11, 0.23, 0.30, 0.40, 0.34, 0.22]
    return float(np.interp(t, xs, ys))


def pad_cutoff(t):
    xs = [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 168.0, 180.0]
    ys = [230.0, 380.0, 560.0, 1050.0, 1900.0, 3700.0, 4400.0, 2600.0]
    return float(np.interp(t, xs, ys))


def build_pad():
    for s, e, name in SCHED:
        t0 = bar(s)
        t1 = min(bar(e), DUR)
        span = t1 - t0
        # 尾音互相咬合
        ext = 2.5 if t0 < 120 else 4.0
        dur = min(span + ext, DUR - t0 + 0.5)
        atk = 3.2 if t0 < 60 else (2.2 if t0 < 120 else 1.8)
        rel = 4.5 if t0 < 60 else (4.0 if t0 < 120 else 6.5)
        PAD.append((t0, dur, CH[name]["voicing"], pad_amp(t0), atk, rel))


def build_bells():
    # ---------------- 一、子夜：疏、远、像水滴与远处钟声 ----------------
    A = [
        (2.0,  50, 0.20, 4.2, -0.35),
        (11.0, 57, 0.13, 3.6,  0.30),
        (16.0, 62, 0.155, 3.2, -0.10),   # 动机首次露头
        (17.5, 69, 0.120, 3.0,  0.15),
        (18.0, 67, 0.110, 3.0, -0.20),
        (19.0, 65, 0.100, 3.6,  0.25),
        (30.0, 62, 0.160, 4.6,  0.00),
        (38.0, 74, 0.090, 3.0, -0.30),
        (47.0, 57, 0.140, 4.0,  0.20),
        (54.0, 69, 0.100, 3.6, -0.15),
    ]
    for t, m, a, tau, p in A:
        BELL.append((t, m, a, tau, p))

    # ---------------- 二、破晓：复调进入 ----------------
    B = [
        (60.0, 62, 0.180, 4.2,  0.00),
        (72.0, 67, 0.150, 3.6, -0.20),   # M1 上行四度
        (73.5, 74, 0.130, 3.4,  0.20),
        (75.0, 72, 0.120, 3.2, -0.10),
        (76.0, 71, 0.110, 4.2,  0.10),
        (84.0, 62, 0.160, 3.6,  0.00),   # M0 回归
        (85.5, 69, 0.130, 3.2,  0.20),
        (86.0, 67, 0.120, 3.0, -0.20),
        (87.0, 65, 0.110, 3.6,  0.10),
        (96.0, 62, 0.160, 4.2,  0.00),   # M2 倒影
        (96.5, 55, 0.120, 3.6, -0.20),
        (97.5, 57, 0.110, 3.2,  0.20),
        (98.5, 59, 0.100, 3.8, -0.10),
        (108.0, 74, 0.130, 3.2, 0.00),
        (112.0, 62, 0.140, 4.8, 0.00),
    ]
    for t, m, a, tau, p in B:
        BELL.append((t, m, a, tau, p))

    # ---------------- 三、黎明：主题展开与解决 ----------------
    C = [
        # 增值的 M0（2 倍时值）
        (124.0, 62, 0.230, 5.0,  0.00),
        (127.0, 69, 0.190, 4.4,  0.16),
        (128.0, 67, 0.175, 4.2, -0.16),
        (130.0, 65, 0.170, 5.0,  0.10),
        # M1
        (136.0, 67, 0.210, 4.6,  0.00),
        (138.25, 74, 0.170, 4.0, 0.20),
        (139.0, 72, 0.160, 3.8, -0.20),
        (140.5, 71, 0.150, 4.8, 0.10),
        # M2 倒影（低音区，全曲最深处）
        (148.0, 62, 0.240, 5.2,  0.00),
        (151.0, 55, 0.185, 4.6, -0.24),
        (152.0, 57, 0.175, 4.4,  0.24),
        (154.0, 59, 0.165, 5.0, -0.10),
        # 收束
        (160.0, 69, 0.150, 4.2,  0.18),
        (161.5, 67, 0.135, 4.0, -0.18),
        (163.0, 65, 0.120, 4.4,  0.10),
        # 逆行 M4：F G A D，最后落在主音
        (164.5, 65, 0.175, 4.6,  0.00),
        (167.5, 67, 0.150, 4.2,  0.18),
        (169.0, 69, 0.145, 4.0, -0.18),
        (170.5, 62, 0.215, 7.0,  0.00),
    ]
    for t, m, a, tau, p in C:
        BELL.append((t, m, a, tau, p))


def build_plucks():
    # 一、子夜：水滴（高、短、纯净）
    drops = [
        (6.5, 91, 0.150, 0.50), (9.25, 86, 0.120, -0.40),
        (13.5, 93, 0.110, 0.20), (23.0, 89, 0.135, -0.20),
        (26.75, 96, 0.095, 0.45), (33.0, 86, 0.125, 0.10),
        (35.5, 91, 0.105, -0.50), (41.0, 84, 0.115, 0.30),
        (44.5, 89, 0.095, -0.10), (50.0, 93, 0.105, 0.40),
        (53.0, 86, 0.095, -0.30), (57.5, 91, 0.085, 0.00),
    ]
    for t, m, a, p in drops:
        PLUCK.append((t, m, a, p, 3.0, 0.72, 2.6, 0.80))

    # 二、破晓 / 三、黎明：琶音（按和声走，音型为平滑拱形）
    segs = []
    for s, e, name in SCHED:
        if s < 16:
            continue
        t0, t1 = bar(s), min(bar(e), DUR)
        if t0 >= 180:
            continue
        segs.append((t0, t1, name))

    # 三、黎明：钟声主题陈述时，琶音让路（旋律说话时伴奏变稀）
    THEME_WIN = [(124.0, 134.5), (136.0, 144.0), (148.0, 158.5), (164.5, 172.5)]

    for t0, t1, name in segs:
        pcs = CH[name]["pcs"]
        pool = sorted(m for m in range(67, 92) if m % 12 in pcs)
        if len(pool) < 4:
            continue
        span = t1 - t0
        if t0 < 60:
            continue
        # 密度：破晓由疏到密，黎明保持流动，收束处变稀
        if t0 < 76:
            step, amp0 = 1.0, 0.086
        elif t0 < 92:
            step, amp0 = 0.75, 0.096
        elif t0 < 156:
            step, amp0 = 0.5, 0.112
        elif t0 < 168:
            step, amp0 = 0.75, 0.096
        else:
            step, amp0 = 1.5, 0.072

        mid = 0.5 * (t0 + t1)
        for a, b in THEME_WIN:
            if a - 1.0 <= mid <= b + 1.0:
                step = max(step, 0.75)
                amp0 *= 0.80
                break

        K = int(round(span / step))
        if K < 2:
            continue
        up = int((t0 / 8) % 2) == 0          # 相邻和弦交替上下行，形成呼吸
        for k in range(K):
            if k % 4 == 0 and k > 0 and rng.random() < 0.12:
                continue                      # 极少量留白
            ph = k / (K - 1)
            frac = (0.5 - 0.5 * np.cos(2 * np.pi * ph)) if up else (0.5 + 0.5 * np.cos(2 * np.pi * ph))
            idx = int(round(frac * (len(pool) - 1)))
            m = pool[idx]
            tt = t0 + k * step + rng.normal(0.0, 0.010)
            if tt > 174.5:                        # 最后六秒只留余响
                continue
            acc = 1.30 if (k % 4 == 0) else (1.08 if k % 2 == 0 else 1.0)
            amp = amp0 * acc * (1.0 + rng.normal(0.0, 0.07))
            pan = 0.30 * np.sin(2 * np.pi * ph * 1.0) * (1 if up else -1)
            bright = 0.42 + 0.28 * (0.5 - 0.5 * np.cos(2 * np.pi * ph))
            PLUCK.append((max(0.0, tt), m, max(0.02, amp), pan, 2.6, bright, 2.4, 0.45))

    # 三、黎明：用拨弦给钟声主题配三度下声部
    for t0, mot in ((124.0, M3), (136.0, motive_augment(M1, 1.5)),
                    (148.0, motive_augment(M2, 2.0)), (164.5, motive_augment(M4, 1.5))):
        for tt, m, d in motive_render(mot, t0):
            hm = dia(m, -2)
            PLUCK.append((tt + 0.012, hm, 0.115, -0.22, max(1.8, d), 0.50, 2.8, 0.42))
            PLUCK.append((tt + 0.020, m - 12, 0.075, 0.24, max(1.8, d), 0.45, 3.0, 0.40))


# --------------------------------------------------------------------------
# 彩蛋：02:00 整点报时（几乎听不见）
# --------------------------------------------------------------------------
def build_egg():
    t = 120.0
    EGG.append((t, 86, 0.0180, 0.75, 0.0))


# --------------------------------------------------------------------------
# 渲染
# --------------------------------------------------------------------------
def render():
    build_pad()
    build_bells()
    build_plucks()
    build_egg()

    print("事件数  pad=%d bell=%d pluck=%d" % (len(PAD), len(BELL), len(PLUCK)))

    pad_bus = np.zeros((N, 2))
    for t0, dur, notes, amp, atk, rel in PAD:
        freqs = [440.0 * 2.0 ** ((m - 69) / 12.0) for m in notes]
        sig = S.pad_chord(freqs, dur, atk, rel, amp=amp, fc=7000.0,
                          nharm=7, detune=6.5, rng=rng)
        pan = 0.0
        S.add_to(pad_bus, sig, t0, pan, 1.0)
    # 一极点低通扫频
    pad_bus[:, 0] = S.onepole_sweep(pad_bus[:, 0], pad_cutoff)
    pad_bus[:, 1] = S.onepole_sweep(pad_bus[:, 1], pad_cutoff)

    bell_bus = np.zeros((N, 2))
    for t, m, amp, tau, pan in BELL:
        f = 440.0 * 2.0 ** ((m - 69) / 12.0)
        sig = S.bell(f, min(tau * 3.0 + 0.6, DUR - t), tau=tau, rng=rng)
        S.add_to(bell_bus, sig, t, pan, amp * BELL_G)

    pluck_bus = np.zeros((N, 2))
    for t, m, amp, pan, dur, bright, t60, damp in PLUCK:
        f = 440.0 * 2.0 ** ((m - 69) / 12.0)
        d = min(dur, DUR - t)
        if d < 0.3:
            continue
        sig = S.pluck(f, d, bright=bright, t60=t60, rng=rng, damp=damp)
        S.add_to(pluck_bus, sig, t, pan, amp * PLUCK_G)

    for name, b in (("pad", pad_bus), ("bell", bell_bus), ("pluck", pluck_bus)):
        r = float(np.sqrt(np.mean(b ** 2)))
        print("  stem %-6s rms=%.5f peak=%.4f" % (name, r, float(np.abs(b).max())))

    dry = pad_bus + bell_bus + pluck_bus
    wet = S.reverb(dry, feedback=0.945, damp=2)
    rd = float(np.sqrt(np.mean(dry ** 2)))
    rw = float(np.sqrt(np.mean(wet ** 2)))
    if rw > 0:
        wet *= rd / rw
    print("  dry rms=%.5f  wet rms(归一后)=%.5f" % (rd, float(np.sqrt(np.mean(wet ** 2)))))
    WET = 0.32
    mix = dry + WET * wet

    # 母线：高通去直流 / 归一化 / 首尾淡变
    for ch in range(2):
        mix[:, ch] = S.highpass(mix[:, ch], 27.0)
    peak = float(np.abs(mix).max())
    mix *= 0.891 / peak                    # -1 dBFS
    nf = int(1.5 * FS)
    fade = 0.5 - 0.5 * np.cos(np.pi * np.arange(nf) / nf)
    mix[:nf] *= fade[:, None]
    mix[-nf:] *= fade[::-1, None]
    return mix, dry, pad_bus, bell_bus, pluck_bus


def add_egg(mix):
    before = mix.copy()
    for t, m, amp, tau, pan in EGG:
        f = 440.0 * 2.0 ** ((m - 69) / 12.0)
        sig = S.bell(f, tau * 4.0, tau=tau, rng=np.random.default_rng(7), strike=0.02)
        S.add_to(mix, sig, t, pan, amp)
    d = np.abs(mix - before).max(axis=1)
    k = int(np.argmax(d))
    print("  彩蛋注入: 起于样点 %d (= %.3f s) 峰值增量 %.5f (%.1f dBFS)" % (
        k, k / FS, float(d[k]), 20 * np.log10(max(1e-9, float(d[k])))))
    return mix


# --------------------------------------------------------------------------
# 分析
# --------------------------------------------------------------------------
def analyse(mix, path):
    import wave
    with wave.open(path, "rb") as w:
        nch, sw, sr, nfr = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(nfr)
    x = np.frombuffer(raw, dtype="<i2").astype(np.float64).reshape(-1, nch) / 32768.0
    print("\n=== WAV 读回 ===")
    print("  时长 %.3f s / 采样率 %d / 声道 %d / 位深 %d" % (nfr / sr, sr, nch, sw * 8))
    print("  峰值 %.4f (%.2f dBFS) / 总 RMS %.5f" % (
        np.abs(x).max(), 20 * np.log10(max(1e-9, np.abs(x).max())),
        np.sqrt(np.mean(x ** 2))))
    print("  NaN=%s  Inf=%s  削波样点=%d" % (
        bool(np.isnan(x).any()), bool(np.isinf(x).any()), int((np.abs(x) >= 0.9999).sum())))

    mono = x.mean(axis=1)
    seg = sr  # 1 秒
    nb = len(mono) // seg
    rms = np.array([np.sqrt(np.mean(mono[i * seg:(i + 1) * seg] ** 2)) for i in range(nb)])
    db = 20 * np.log10(np.maximum(rms, 1e-9))
    print("  逐秒 RMS: min %.1f dB / max %.1f dB" % (db.min(), db.max()))
    # 最长低于 -55 dB 的连续片段
    quiet = db < -55.0
    longest = cur = 0
    for q in quiet:
        cur = cur + 1 if q else 0
        longest = max(longest, cur)
    print("  最长静音段 %.1f s" % longest)

    def cent(t0, t1):
        s = mono[int(t0 * sr):int(t1 * sr)]
        w = np.hanning(len(s))
        sp = np.abs(np.fft.rfft(s * w))
        f = np.fft.rfftfreq(len(s), 1 / sr)
        m = f > 40
        return float((sp[m] * f[m]).sum() / max(1e-9, sp[m].sum()))

    print("\n=== 三段特征 ===")
    for nm, a, b in (("子夜 00:00-01:00", 0, 60), ("破晓 01:00-02:00", 60, 120), ("黎明 02:00-03:00", 120, 180)):
        s = mono[int(a * sr):int(b * sr)]
        print("  %s  RMS %.1f dB / 谱质心 %.0f Hz" % (
            nm, 20 * np.log10(max(1e-9, np.sqrt(np.mean(s ** 2)))), cent(a, b)))

    # 彩蛋位置
    i = int(120.0 * sr)
    print("\n  02:00 处 0.2s 窗口峰值: %.4f" % float(np.abs(mono[i:i + int(0.2 * sr)]).max()))

    # 静态波形（页面用）
    NB = 1120
    step = len(mono) / NB
    peaks = []
    for i in range(NB):
        a = int(i * step)
        b = max(a + 1, int((i + 1) * step))
        peaks.append(float(np.abs(mono[a:b]).max()))
    pk = max(peaks) or 1.0
    return [int(round(1000.0 * (p / pk) ** 0.72)) for p in peaks]


# --------------------------------------------------------------------------
def main():
    wav_path = os.path.join(HERE, "三小时.wav")
    mid_path = os.path.join(HERE, "三小时.mid")

    mix, dry, pad_bus, bell_bus, pluck_bus = render()
    mix = add_egg(mix)
    p = float(np.abs(mix).max())
    print("\n彩蛋后峰值 %.4f (%.2f dBFS)" % (p, 20 * np.log10(p)))
    if p > 0.8915:
        mix *= 0.8915 / p
        print("  重新归一化到 -1 dBFS")

    S.write_wav(wav_path, mix)
    print("写出 %s  %.2f MB" % (wav_path, os.path.getsize(wav_path) / 1048576))

    peaks = analyse(mix, wav_path)
    with open(os.path.join(HERE, "src", "peaks.json"), "w", encoding="utf-8") as f:
        json.dump(peaks, f)

    midiw.build(BELL, PLUCK, PAD, EGG, mid_path, BPM)
    midiw.selftest(mid_path)
    print("写出 %s  %.2f KB" % (mid_path, os.path.getsize(mid_path) / 1024))


if __name__ == "__main__":
    main()
