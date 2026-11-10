# -*- coding: utf-8 -*-
"""把 peaks.json 注入 index.html（可重复执行）"""
import io
import json
import re

HERE = __file__.rsplit("\\src\\", 1)[0]
peaks = json.load(io.open(HERE + r"\src\peaks.json", encoding="utf-8"))
arr = "[" + ",".join(str(int(v)) for v in peaks) + "]"

path = HERE + r"\index.html"
html = io.open(path, encoding="utf-8").read()

if "/*__PEAKS__*/[]" in html:
    html = html.replace("/*__PEAKS__*/[]", arr)
else:
    new, n = re.subn(r"var PEAKS = \[[0-9,]*\];", "var PEAKS = " + arr + ";", html)
    assert n == 1, "PEAKS 替换失败 n=%d" % n
    html = new

io.open(path, "w", encoding="utf-8").write(html)
print("注入 %d 个波形峰值 -> index.html (%d 字节)" % (len(peaks), len(html)))
