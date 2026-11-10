# -*- coding: utf-8 -*-
"""
极简 MIDI 写入器（手写字节流，无第三方库）
Format 1 / PPQ 480 / 60 BPM = 每秒 480 tick
轨道 0 = tempo + 段落标记，轨道 1-3 = 钟声 / 拨弦 / 铺底
"""
import struct

PPQ = 480
TEMPO_US = 1000000          # 60 BPM


def vlq(n):
    """可变长度量"""
    out = bytearray([n & 0x7F])
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


def _meta(kind, payload):
    return b"\xff" + bytes([kind]) + vlq(len(payload)) + payload


def _track(events):
    """events: [(tick, priority, bytes)] -> MTrk chunk"""
    events = sorted(events, key=lambda e: (e[0], e[1]))
    data = bytearray()
    last = 0
    for tick, _pri, payload in events:
        tick = max(tick, last)
        data += vlq(tick - last) + payload
        last = tick
    data += vlq(0) + b"\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(data)) + bytes(data)


def _note_events(evts, channel, prog, name, vol, pan, vel_fn, len_fn):
    e = []
    e.append((0, 0, _meta(0x03, name.encode("utf-8"))))
    e.append((0, 1, bytes([0xC0 | channel, prog & 0x7F])))
    e.append((0, 1, bytes([0xB0 | channel, 7, vol & 0x7F])))
    e.append((0, 1, bytes([0xB0 | channel, 10, pan & 0x7F])))
    for item in evts:
        t0, midi, amp = item[0], item[1], item[2]
        dur = len_fn(item)
        on = int(round(t0 * PPQ))
        off = int(round((t0 + dur) * PPQ))
        v = max(1, min(127, int(round(vel_fn(amp)))))
        e.append((on, 3, bytes([0x90 | channel, int(midi) & 0x7F, v])))
        e.append((off, 2, bytes([0x80 | channel, int(midi) & 0x7F, 0])))
    return e


def build(BELL, PLUCK, PAD, EGG, path, bpm=60.0):
    tempo = int(round(60000000.0 / bpm))

    # ---- 轨道 0：tempo / 拍号 / 调号 / 段落标记 ----
    t0 = []
    t0.append((0, 0, _meta(0x03, "三小时 · Three Hours".encode("utf-8"))))
    t0.append((0, 0, _meta(0x51, struct.pack(">I", tempo)[1:])))
    t0.append((0, 0, _meta(0x58, bytes([4, 2, 24, 8]))))          # 4/4
    t0.append((0, 0, _meta(0x59, bytes([0, 0]))))                 # D 多利亚（无升降号）
    for sec, label in ((0.0, "I 子夜 00:00"), (60.0, "II 破晓 01:00"), (120.0, "III 黎明 02:00")):
        t0.append((int(sec * PPQ), 0, _meta(0x06, label.encode("utf-8"))))

    # ---- 轨道 1：钟声（Tubular Bells, ch1）----
    tb = list(BELL) + [tuple(list(e) + []) for e in EGG]
    tr1 = _note_events(
        tb, 0, 14, "钟声 Bell", 96, 64,
        vel_fn=lambda a: 18 + a * 420,
        len_fn=lambda it: min(8.0, max(0.5, (it[3] if len(it) > 3 else 2.0) * 2.2)),
    )

    # ---- 轨道 2：拨弦（Grand Piano, ch2）----
    tr2 = _note_events(
        PLUCK, 1, 0, "拨弦 Pluck (KS)", 100, 64,
        vel_fn=lambda a: 14 + a * 620,
        len_fn=lambda it: min(6.0, max(0.35, it[4])),
    )

    # ---- 轨道 3：铺底（Warm Pad, ch3）----
    pad_evts = []
    for t0s, dur, notes, amp, atk, rel in PAD:
        for m in notes:
            pad_evts.append((t0s, m, amp, dur))
    tr3 = _note_events(
        pad_evts, 2, 89, "铺底 Pad", 82, 64,
        vel_fn=lambda a: 36 + a * 170,
        len_fn=lambda it: min(60.0, max(2.0, it[3])),
    )

    tracks = [_track(t0), _track(tr1), _track(tr2), _track(tr3)]
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), PPQ)
    with open(path, "wb") as f:
        f.write(header)
        for t in tracks:
            f.write(t)


# --------------------------------------------------------------------------
# 自检：把写出的文件重新解析一遍
# --------------------------------------------------------------------------
def selftest(path):
    with open(path, "rb") as f:
        data = f.read()
    assert data[:4] == b"MThd", "bad header"
    hlen, fmt, ntrk, div = struct.unpack(">IHHH", data[4:14])
    pos = 8 + hlen
    info = []
    for _ in range(ntrk):
        assert data[pos:pos + 4] == b"MTrk"
        ln = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        body = data[pos + 8:pos + 8 + ln]
        pos += 8 + ln
        # 走一遍事件流
        i, tick, notes = 0, 0, 0
        while i < len(body):
            d = 0
            while True:
                b = body[i]
                i += 1
                d = (d << 7) | (b & 0x7F)
                if not b & 0x80:
                    break
            tick += d
            st = body[i]
            if st == 0xFF:
                i += 1
                kind = body[i]
                i += 1
                l = 0
                while True:
                    b = body[i]
                    i += 1
                    l = (l << 7) | (b & 0x7F)
                    if not b & 0x80:
                        break
                i += l
                if kind == 0x2F:
                    break
            else:
                i += 1
                if (st & 0xF0) in (0x80, 0x90):
                    notes += 1
                    i += 2
                elif (st & 0xF0) in (0xC0, 0xD0):
                    i += 1
                else:
                    i += 2
        info.append((ln, notes, tick))
    print("  MIDI 自检: format=%d tracks=%d PPQ=%d" % (fmt, ntrk, div))
    for k, (ln, notes, tick) in enumerate(info):
        print("    track%d 字节=%d 事件=%d 末tick=%d (%.1fs)" % (k, ln, notes, tick, tick / div))
    return True
