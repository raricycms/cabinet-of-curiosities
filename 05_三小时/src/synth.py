# -*- coding: utf-8 -*-
"""
《三小时》— 手写 DSP 合成引擎
纯 numpy 实现：非谐分音钟声 / Karplus-Strong 拨弦 / 微失谐铺底 /
Schroeder 混响 / 一极点低通扫频。无第三方音频库、无网络。
"""
import numpy as np

FS = 44100


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
def env_ad(n, attack, release, shape=1.0):
    """升余弦 attack / release 包络。"""
    e = np.ones(n, dtype=np.float64)
    a = int(max(1, min(n, round(attack * FS))))
    r = int(max(1, min(n, round(release * FS))))
    if a > 1:
        e[:a] *= (0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)) ** shape
    if r > 1:
        e[-r:] *= (0.5 + 0.5 * np.cos(np.pi * np.arange(r) / r)) ** shape
    return e


def pan_gains(pan):
    """等功率声像。"""
    p = (float(np.clip(pan, -1.0, 1.0)) + 1.0) * np.pi / 4.0
    return float(np.cos(p)), float(np.sin(p))


def tail_fade(x, dur=0.05):
    """给单音缓冲加尾部淡出，避免截断爆音。"""
    n = int(dur * FS)
    if n > 1 and n < len(x):
        x[-n:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(n) / n)
    return x


def add_to(buf, sig, t, pan=0.0, gain=1.0):
    """把单声道信号按时间 / 声像叠加进立体声总线。"""
    i = int(round(t * FS))
    n = len(sig)
    if i < 0:
        sig = sig[-i:]
        n = len(sig)
        i = 0
    if i >= buf.shape[0]:
        return
    n = min(n, buf.shape[0] - i)
    if n <= 0:
        return
    gl, gr = pan_gains(pan)
    buf[i:i + n, 0] += sig[:n] * (gain * gl)
    buf[i:i + n, 1] += sig[:n] * (gain * gr)


# --------------------------------------------------------------------------
# 1. 钟声 — 非谐分音 + 指数衰减 + 轻微 detune
# --------------------------------------------------------------------------
# (分音比, 相对幅度, 衰减系数)
BELL_PARTIALS = [
    (1.00, 1.000, 1.00),
    (2.00, 0.300, 0.74),
    (2.76, 0.430, 0.58),
    (4.07, 0.130, 0.44),
    (5.40, 0.245, 0.36),
    (8.93, 0.085, 0.26),
    (13.34, 0.038, 0.17),
]


def bell(freq, dur, tau=2.0, rng=None, detune_cents=1.7, strike=0.10):
    """非谐钟声。返回峰值归一化的单声道缓冲。"""
    if rng is None:
        rng = np.random.default_rng(0)
    n = int(dur * FS)
    t = np.arange(n, dtype=np.float64) / FS
    out = np.zeros(n)
    for ratio, amp, dk in BELL_PARTIALS:
        fp = freq * ratio
        if fp > FS * 0.45:
            continue
        tp = max(0.02, tau * dk)
        for d in (-1.0, 1.0):                      # 一对微失谐副本 -> 缓慢拍音
            fd = fp * (1.0 + d * detune_cents / 1200.0)
            ph = rng.uniform(0.0, 2.0 * np.pi)
            out += (0.5 * amp) * np.exp(-t / tp) * np.sin(2.0 * np.pi * fd * t + ph)

    # 敲击瞬态：极短的滤波噪声
    if strike > 0:
        ns = min(n, int(0.013 * FS))
        if ns > 8:
            nz = rng.standard_normal(ns)
            nz = np.convolve(nz, np.ones(4) / 4.0, mode="same")
            nz *= np.exp(-np.arange(ns) / (0.0028 * FS))
            out[:ns] += strike * nz

    # 3ms 起音，避免爆音
    a = min(n, int(0.003 * FS))
    if a > 1:
        out[:a] *= np.linspace(0.0, 1.0, a)
    peak = np.abs(out).max()
    if peak > 0:
        out /= peak
    return tail_fade(out, 0.04)


# --------------------------------------------------------------------------
# 2. 拨弦 — Karplus-Strong 延迟线（块向量化 + 线性插值小数延迟）
# --------------------------------------------------------------------------
def pluck(freq, dur, bright=0.5, t60=2.6, rng=None, damp=0.55):
    """
    Karplus-Strong。环路内两点评均低通，小数延迟用线性插值。
    分块处理：块长 B <= D，则块内所有读取都落在已算好的样本上。
    """
    if rng is None:
        rng = np.random.default_rng(0)
    n_ex = FS / freq                      # 精确延迟（采样）
    d = n_ex - 0.5 * damp                 # 补偿环路低通的群延迟
    b = max(1, int(np.floor(d)) - 1)      # 块长，保证 B <= D
    n = int(dur * FS) + int(np.ceil(n_ex)) + 16

    # 激励：确定性的短脉冲（频谱平滑单调，基频必定占优）+ 少量噪声给拨弦质感
    nfill = min(n, b + 2)
    L = nfill
    tt = np.arange(L, dtype=np.float64) / FS
    T = min(0.00065, 0.62 * L / FS)
    if T < 1.5 / FS:
        T = 1.5 / FS
    env = np.where(tt < T, np.sin(np.pi * np.minimum(tt, T) / T) ** 2, 0.0)
    k = max(1, int(round(3 + 9 * (1.0 - float(np.clip(bright, 0.0, 1.0))))))
    nz = rng.standard_normal(L)
    nz = np.convolve(nz, np.ones(k) / k, mode="same")
    nz -= nz.mean()
    nz /= max(1e-12, np.abs(nz).max())
    exc = env * (1.0 + 0.30 * nz)
    exc -= exc.mean()
    m = np.abs(exc).max()
    if m > 0:
        exc /= m

    y = np.zeros(n)
    y[:L] = exc

    # 环路增益：由 T60 反解，并补偿环路低通在基频处的损耗
    loop_loss = (1.0 - damp) + damp * np.cos(np.pi * freq / FS)
    g = 10.0 ** (-3.0 * n_ex / (t60 * FS)) / max(0.35, loop_loss)
    g = min(g, 0.99995)

    s = nfill
    while s < n:
        e = min(s + b, n)
        idx = np.arange(s, e, dtype=np.float64)
        p = idx - d
        i0 = np.floor(p).astype(np.int64)
        np.maximum(i0, 0, out=i0)
        fr = p - i0
        v = (1.0 - fr) * y[i0] + fr * y[np.minimum(i0 + 1, n - 1)]
        p2 = p - 1.0
        j0 = np.floor(p2).astype(np.int64)
        np.maximum(j0, 0, out=j0)
        fr2 = p2 - j0
        v2 = (1.0 - fr2) * y[j0] + fr2 * y[np.minimum(j0 + 1, n - 1)]
        y[s:e] = g * ((1.0 - damp) * v + damp * 0.5 * (v + v2))
        s = e

    out = y[:int(dur * FS)]
    peak = np.abs(out).max()
    if peak > 0:
        out /= peak
    return tail_fade(out, 0.08)


# --------------------------------------------------------------------------
# 3. 铺底 pad — 多个微失谐正弦 + 慢起音
# --------------------------------------------------------------------------
def pad_chord(freqs, dur, attack, release, amp=0.25, fc=6000.0,
              nharm=6, detune=6.0, rng=None):
    if rng is None:
        rng = np.random.default_rng(0)
    n = int(dur * FS)
    t = np.arange(n, dtype=np.float64) / FS
    out = np.zeros(n)
    fmax = min(fc * 1.6, 11000.0)
    for f in freqs:
        for dc in (-detune, 0.0, detune):
            fd = f * 2.0 ** (dc / 1200.0)
            for h in range(1, nharm + 1):
                fh = fd * h
                if fh > fmax:
                    break
                a = (1.0 / h ** 1.3) / (1.0 + (fh / fc) ** 2)
                ph = rng.uniform(0.0, 2.0 * np.pi)
                out += a * np.sin(2.0 * np.pi * fh * t + ph)

    # 极慢的呼吸（约 27 秒一个周期），让长音不死板
    breath = 1.0 + 0.05 * np.sin(2.0 * np.pi * 0.037 * t + rng.uniform(0.0, 6.283))
    out *= breath * env_ad(n, attack, release, shape=1.0)
    peak = np.abs(out).max()
    if peak > 0:
        out /= peak
    return out * amp


# --------------------------------------------------------------------------
# 4. 一极点低通扫频（分段 LTI，块内用 FFT 做精确 IIR 卷积）
# --------------------------------------------------------------------------
def onepole_sweep(x, fc_fn, seg=0.5):
    """
    y[n] = (1-a)x[n] + a*y[n-1], a = exp(-2*pi*fc/FS)。
    截止频率按段常数变化（每 seg 秒更新一次），段内是 LTI，
    用核 h[j]=(1-a)a^j 的 FFT 卷积 + 初始状态项精确求解。
    """
    n = len(x)
    L = max(1, int(seg * FS))
    y = np.zeros(n, dtype=np.float64)
    z = 0.0
    for s in range(0, n, L):
        e = min(s + L, n)
        ln = e - s
        fc = float(fc_fn((s + e) * 0.5 / FS))
        fc = min(max(fc, 10.0), FS * 0.45)
        a = float(np.exp(-2.0 * np.pi * fc / FS))
        a = min(a, 0.999995)
        j = np.arange(ln)
        h = (1.0 - a) * a ** j
        nfft = 1
        while nfft < 2 * ln:
            nfft <<= 1
        conv = np.fft.irfft(np.fft.rfft(x[s:e], nfft) * np.fft.rfft(h, nfft), nfft)[:ln]
        y[s:e] = conv + z * a ** (j + 1)
        z = y[e - 1]
    return y


# --------------------------------------------------------------------------
# 5. 混响 — Schroeder：4 并联梳状 + 2 串联全通，立体声去相关
# --------------------------------------------------------------------------
COMB_L = (1777, 1867, 1951, 2039)
COMB_R = (1801, 1891, 1979, 2063)
AP_L = (556, 441)
AP_R = (579, 464)


def _comb_add(x, out, D, g):
    n = len(x)
    y = np.zeros(n)
    for s in range(0, n, D):
        e = min(s + D, n)
        L = e - s
        y[s:e] = x[s:e]
        if s >= D:
            y[s:e] += g * y[s - D:s - D + L]
    out += y


def _allpass(x, D, g):
    n = len(x)
    y = np.zeros(n)
    for s in range(0, n, D):
        e = min(s + D, n)
        L = e - s
        y[s:e] = -g * x[s:e]
        if s >= D:
            y[s:e] += x[s - D:s - D + L] + g * y[s - D:s - D + L]
    return y


def _lp(x, passes=2):
    k = np.array([0.25, 0.5, 0.25])
    for _ in range(passes):
        x = np.convolve(x, k, mode="same")
    return x


def reverb(stereo, feedback=0.94, damp=2):
    """输入立体声干声，返回同长度湿声（含 6 秒尾）。"""
    n = stereo.shape[0]
    out = np.zeros((n, 2))
    for ch, combs, aps in ((0, COMB_L, AP_L), (1, COMB_R, AP_R)):
        src = _lp(stereo[:, ch].copy(), damp)
        acc = np.zeros(n)
        for D in combs:
            _comb_add(src, acc, D, feedback)
        acc /= len(combs)
        for D in aps:
            acc = _allpass(acc, D, 0.55)
        out[:, ch] = _lp(acc, 1)
    return out


# --------------------------------------------------------------------------
# 6. 母线处理
# --------------------------------------------------------------------------
def highpass(x, fc=28.0):
    """一阶高通（整段 FFT，零相位）。"""
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / FS)
    r = f / fc
    H = r / np.sqrt(1.0 + r * r)
    return np.fft.irfft(X * H, n)


def write_wav(path, x, fs=FS):
    import wave
    y = np.clip(x, -1.0, 1.0)
    i16 = np.round(y * 32767.0).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(fs)
        w.writeframes(i16.tobytes())
