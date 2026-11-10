// 奇珍室 · 图录生成器
// 用法: node _assets/build_catalogue.mjs
// 读取 _assets/shots/*_desk.png 作为图版, 生成 A4 排印稿, 再用 Chrome 打印为 PDF
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SHOTS = path.join(ROOT, '_assets', 'shots');
const OUT_HTML = path.join(ROOT, '_assets', 'catalogue.html');
const OUT_PDF = path.join(ROOT, '奇珍室_图录.pdf');

const EX = [
  { n: '01', dir: '01_涟漪', name: '涟漪', en: 'RIPPLE', accent: '#6fb3a8', plate: 'plate_01.png',
    concept: '一片没有边界的水面。点击是投石，涟漪会相遇、干涉、衰减。',
    ops: '移动鼠标拂动水面，点击投石；左下角可开启声音。',
    tech: '二维波动方程数值解 · ImageData 逐像素折射着色 · WebAudio 泛音合成' },
  { n: '02', dir: '02_晶园', name: '晶园', en: 'CRYSTAL GARDEN', accent: '#6fb3a8',
    concept: '一杯过饱和溶液。点一下，种下晶核，晶体以扩散限制聚集的方式缓慢生长。',
    ops: '点击溶液任意处种晶核；可切换六方对称、加速、清空与导出。',
    tech: 'DLA 随机游走 · 极角色相映射 · 自动取景' },
  { n: '03', dir: '03_造物机', name: '造物机', en: 'THE FORGE', accent: '#d9a05b',
    concept: '输入任何文字作种子，它吐出一只不存在的生物的博物学图版。',
    ops: '输入种子后回车，或按空格再摇一次；可分享链接、导出图版、收进图鉴。',
    tech: 'mulberry32 种子化 PRNG · 参数化 SVG 生物 · 程序化命名' },
  { n: '04', dir: '04_不存在的图书馆', name: '不存在的图书馆', en: 'THE UNWRITTEN LIBRARY', accent: '#c05b4d',
    concept: '一座只收藏"从未被写出的书"的图书馆。每一本都有借阅卡。',
    ops: '点击书脊抽出一本，Esc 收回；「重构图书馆」换一批。',
    tech: '种子化中文语料与句式模板 · CSS 书脊透视 · 借阅记录生成' },
  { n: '05', dir: '05_三小时', name: '三小时', en: 'THREE HOURS', accent: '#d9a05b',
    concept: '把三小时压进三分钟，一分钟一个时辰：子夜、破晓、黎明。',
    ops: '点击播放，建议戴耳机；可循环、可拖动进度。',
    tech: 'numpy 手写加法合成 / Karplus-Strong / Schroeder 混响 · 44.1kHz WAV · MIDI' },
  { n: '06', dir: '06_星图', name: '数字星图', en: 'NUMERICAL STAR ATLAS', accent: '#6fb3a8',
    concept: '用质数螺旋、元胞自动机与圆周率，观测三个不存在的夜空。',
    ops: '在画廊中点开任一幅，观看细节。',
    tech: 'Python + numpy + Pillow · 高分辨率超采样 · 固定随机种子' },
  { n: '07', dir: '07_万物说明书', name: '万物说明书', en: 'MANUAL OF EVERYTHING', accent: '#c05b4d',
    concept: '二十五件不存在之物的使用、保养与保修条款。',
    ops: '按左侧目录跳转；最后一条是给读者本人的。',
    tech: '原创文本 · Python 生成 DOCX · 排印式 HTML 阅读页' },
  { n: '08', dir: '08_留白', name: '留白', en: 'THE BLANK', accent: '#9a8fb8',
    concept: '一篇关于"没做完的东西"的小说：一家只修未用之物的铺子。',
    ops: '直接阅读，约六千四百字，十八分钟。',
    tech: '原创小说 · 首行缩进 2 字符 · 行高 1.9 的书页排版' },
  { n: '09', dir: '09_字', name: '字', en: 'GLYPHS', accent: '#c05b4d',
    concept: '两个汉字被当作两种材料：一颗是星尘，一枚是等高线。',
    ops: '在画廊中点开观看细节。',
    tech: '字形蒙版 · 粒子密度场 / 距离场等值线 · Pillow + numpy' },
  { n: '10', dir: '10_时间胶囊', name: '时间胶囊', en: 'TIME CAPSULE', accent: '#c05b4d',
    concept: '一封封存至 2027 年 1 月 1 日的信。在此之前，它只是被折叠的文字。',
    ops: '等待；或点击「尝试启封」，看它拒绝你。',
    tech: '日期派生密钥流异或 · 到达日期自动启封 · 逐字显示' },
  { n: '11', dir: '11_预言机', name: '预言机', en: 'THE ORACLE', accent: '#c05b4d', plate: 'probe_11.png',
    concept: '写下你想问的一件事，摇一支签。它不回答你，只把问题翻译成另一种说法。',
    ops: '写下问题后回车，或点击签筒随机抽一支；签会收进本机签筒。',
    tech: 'FNV-1a + mulberry32 确定性映射 · 24 支手写签 · Canvas 印记 · 竖排签条' },
  { n: '12', dir: '12_回声', name: '回声', en: 'THE ECHO', accent: '#d9a05b', plate: 'plate_12.png',
    concept: '一句话被一遍遍传下去。每次只差一点，二十次之后它成了另一句话。',
    ops: '写下一句话，回车；看它在二十次转述里逐渐变质。',
    tech: '字符级衰减模型（漏字 / 换位 / 同句替换 / 虚词混入）· 编辑距离与相似度 · 种子化随机' },
];

const exists = (p) => { try { return fs.existsSync(p); } catch { return false; } };

function imgFor(e) {
  if (e.plate) {
    const p = path.join(SHOTS, e.plate);
    return exists(p) ? `../_assets/shots/${e.plate}` : null;
  }
  const p = path.join(SHOTS, `${e.dir}__index_desk.png`);
  return exists(p) ? `../_assets/shots/${e.dir}__index_desk.png` : null;
}

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');

const plates = EX.map(e => {
  const img = imgFor(e);
  return `
  <section class="page plate">
    <header class="ph">
      <div class="pnum">N°${e.n}</div>
      <div class="ptitle"><b>${esc(e.name)}</b><em>${e.en}</em></div>
      <div class="prule" style="background:${e.accent}"></div>
    </header>
    ${img ? `<div class="frame"><img src="${img}" alt=""></div>` : `<div class="frame frame--empty"><span>图版暂缺</span></div>`}
    <div class="pbody">
      <div class="row"><span class="k">概念</span><p>${esc(e.concept)}</p></div>
      <div class="row"><span class="k">操作</span><p>${esc(e.ops)}</p></div>
      <div class="row"><span class="k">技术</span><p class="mono">${esc(e.tech)}</p></div>
    </div>
    <div class="ghost-rule" aria-hidden="true"></div>
    <div class="ghost-no" aria-hidden="true">${e.n}</div>
    <footer class="pf"><span>奇珍室 · A CABINET OF CURIOSITIES</span><span>创造 · 2026</span></footer>
  </section>`;
}).join('\n');

const html = `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>奇珍室 · 图录</title>
<style>
  @page{ size:A4; margin:0; }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0;background:#080a0f;
    -webkit-print-color-adjust:exact;print-color-adjust:exact;}
  :root{
    --paper:#efe8da;--text:#e6e2d8;--dim:#98a1ac;--line:#2a3442;--amber:#d9a05b;
    --serif:"Noto Serif SC","Source Han Serif SC","STZhongsong","SimSun",serif;
    --sans:"Noto Sans SC","Microsoft YaHei","Segoe UI",sans-serif;
    --mono:"Cascadia Mono","Consolas",monospace;
  }
  .page{width:210mm;height:297mm;position:relative;overflow:hidden;
    background:#080a0f;color:var(--text);page-break-after:always;break-after:page;}
  .page:last-child{page-break-after:auto;break-after:auto;}

  /* 封面 */
  .cover{padding:24mm 22mm;display:flex;flex-direction:column;justify-content:space-between}
  .cover .top{font-family:var(--mono);font-size:8pt;letter-spacing:.3em;color:var(--dim);
    display:flex;justify-content:space-between;border-bottom:.4pt solid var(--line);padding-bottom:5mm}
  .cover .mid{padding-top:6mm}
  .cover .eyebrow{font-family:var(--mono);font-size:8pt;letter-spacing:.32em;color:var(--amber);margin-bottom:8mm}
  .cover h1{font-family:var(--serif);font-size:64pt;font-weight:600;letter-spacing:.1em;
    margin:0 0 5mm;color:var(--paper);line-height:1.05}
  .cover .en{font-family:var(--mono);font-size:9pt;letter-spacing:.42em;color:var(--dim);margin-bottom:14mm}
  .cover .rule{width:34mm;height:1.2mm;background:var(--amber);margin-bottom:10mm}
  .cover .lede{font-family:var(--serif);font-size:12pt;line-height:2.1;color:#c9c6bc;max-width:118mm}
  .cover .sig{font-family:var(--mono);font-size:8pt;letter-spacing:.26em;color:var(--dim);
    display:flex;justify-content:space-between;border-top:.4pt solid var(--line);padding-top:5mm}
  .ripple{position:absolute;right:-30mm;bottom:34mm;width:120mm;height:120mm;opacity:.5}

  /* 前言 */
  .preface{padding:24mm 22mm 18mm;display:flex;flex-direction:column}
  .preface .kick{font-family:var(--mono);font-size:8pt;letter-spacing:.3em;color:var(--amber);margin-bottom:7mm}
  .preface h2{font-family:var(--serif);font-size:23pt;font-weight:600;letter-spacing:.08em;margin:0 0 8mm;color:var(--paper)}
  .preface p{font-family:var(--serif);font-size:10.4pt;line-height:2.15;color:#c6c2b8;
    margin:0 0 5.5mm;text-align:justify}
  .preface p .em{color:var(--paper);border-bottom:.4pt solid rgba(217,160,91,.6)}
  .toc{margin-top:auto;border-top:.4pt solid var(--line);padding-top:6mm;columns:2;column-gap:14mm}
  .toc .it{display:flex;gap:4mm;font-size:9pt;line-height:2.05;break-inside:avoid}
  .toc .it i{font-family:var(--mono);font-style:normal;font-size:7.6pt;color:var(--dim);letter-spacing:.1em;min-width:9mm}
  .toc .it b{font-family:var(--serif);font-weight:500;color:#d9d4c8}
  .chapter{font-family:var(--mono);font-size:7.4pt;letter-spacing:.3em;color:var(--amber);
    margin:0 0 2.5mm;break-inside:avoid}
  .toc .chapter:nth-of-type(2){margin-top:4mm}

  /* 图版 */
  .plate{padding:15mm 15mm 11mm;display:flex;flex-direction:column}
  .ph{display:grid;grid-template-columns:24mm 1fr;grid-template-rows:auto auto;align-items:end;gap:0 4mm;margin-bottom:5mm}
  .pnum{grid-row:1/3;font-family:var(--mono);font-size:8pt;letter-spacing:.16em;color:var(--dim);align-self:start;padding-top:1mm}
  .ptitle{display:flex;align-items:baseline;gap:5mm}
  .ptitle b{font-family:var(--serif);font-size:17pt;font-weight:600;letter-spacing:.06em;color:var(--paper)}
  .ptitle em{font-family:var(--mono);font-style:normal;font-size:6.6pt;letter-spacing:.26em;color:var(--dim)}
  .prule{grid-column:2;height:.8mm;width:22mm;margin-top:2mm}
  .frame{border:.4pt solid var(--line);padding:2.2mm;background:#0b0f15}
  .frame img{display:block;width:100%;height:auto}
  .frame--empty{height:104mm;display:grid;place-items:center;font-family:var(--mono);font-size:8pt;color:#4b5563;letter-spacing:.2em}
  .pbody{margin-top:8mm;flex:0 0 auto}
  .ghost-no{position:absolute;right:11mm;bottom:20mm;font-family:var(--serif);font-weight:600;
    font-size:150pt;line-height:.8;color:rgba(239,232,218,.045);letter-spacing:-.02em;
    pointer-events:none;user-select:none}
  .ghost-rule{position:absolute;right:22mm;bottom:20mm;width:1px;height:150mm;
    background:linear-gradient(180deg,transparent,rgba(239,232,218,.09) 30%,rgba(239,232,218,.09) 70%,transparent);pointer-events:none}
  .pbody .row{display:grid;grid-template-columns:16mm 1fr;gap:4mm;margin-bottom:3.2mm;align-items:start}
  .pbody .k{font-family:var(--mono);font-size:6.8pt;letter-spacing:.2em;color:var(--dim);padding-top:1.2mm}
  .pbody p{margin:0;font-family:var(--serif);font-size:9.6pt;line-height:1.85;color:#cfcabf}
  .pbody p.mono{font-family:var(--mono);font-size:7.4pt;line-height:1.9;color:#9aa3ae;letter-spacing:.02em}
  .pf{display:flex;justify-content:space-between;font-family:var(--mono);font-size:6.4pt;
    letter-spacing:.22em;color:#5b6470;border-top:.4pt solid var(--line);padding-top:3mm;margin-top:auto}

  /* 尾页 */
  .colophon{padding:24mm 22mm;display:flex;flex-direction:column;justify-content:space-between}
  .colophon h2{font-family:var(--serif);font-size:26pt;font-weight:600;letter-spacing:.1em;color:var(--paper);margin:0 0 8mm}
  .colophon p{font-family:var(--serif);font-size:10pt;line-height:2.1;color:#bcb7ac;max-width:128mm;margin:0 0 5mm}
  .colophon .mono{font-family:var(--mono);font-size:7.4pt;letter-spacing:.16em;line-height:2.1;color:#7f8892}
  .colophon .end{font-family:var(--mono);font-size:7pt;letter-spacing:.3em;color:#5b6470;
    border-top:.4pt solid var(--line);padding-top:5mm;display:flex;justify-content:space-between}
</style></head>
<body>

<section class="page cover">
  <div class="top"><span>创造 · 2026</span><span>十二件展品 / CATALOGUE</span></div>
  <div class="mid">
    <div class="eyebrow">一间私人的陈列室</div>
    <h1>奇珍室</h1>
    <div class="en">A CABINET OF CURIOSITIES</div>
    <div class="rule"></div>
    <div class="lede">有人把一只空文件夹放在桌上，说：给你三个小时，随便创造点什么，只要它值得留下。<br><br>
    于是有了这十件展品。它们不解释自己；你碰一下，它们就动。</div>
  </div>
  <div class="sig"><span>交互 · 生成艺术 · 声音 · 文学 · 装置</span><span>全部离线</span></div>
  <svg class="ripple" viewBox="0 0 200 200" fill="none" stroke="#6fb3a8" stroke-width=".35" opacity=".55">
    ${[12,26,40,54,68,82].map(r => `<circle cx="100" cy="100" r="${r}"/>`).join('')}
  </svg>
</section>

<section class="page preface">
  <div class="kick">策展前言 / PREFACE</div>
  <h2>三个小时能留下什么</h2>
  <p>有人交来一个空文件夹，和一个具体的期限。于是我们决定不去做"大"的东西，而是做十二件<span class="em">活的</span>东西：水会记住触碰，晶体会自己长成花园，书会从从未被写出的地方被抽出来，音乐会分成三个时辰，一封信会等到 2027 年才肯打开，一个问题会变成一支签。</p>
  <p>这间屋子没有一件展品需要网络。断网、拔掉网线、把整个文件夹拷到一只旧 U 盘里，它们仍然完好。作品的全部依赖只有浏览器本身。</p>
  <p>如果一定要说它有什么价值——大概不是"完成度"，而是<span class="em">每一件都试图解决一个只属于它自己的小问题</span>。这些问题不值得立项，也不该被 KPI 衡量；它们只是有人愿意花时间，把"没有"变成"有一个，哪怕很小"。</p>
  <p>你可以从任意一页开始。没有正确的观看顺序。</p>
  <div class="toc">
    <div class="chapter">卷一 · 手与算法</div>
    ${EX.slice(0, 4).map(e => `<div class="it"><i>${e.n}</i><b>${e.name}</b></div>`).join('')}
    <div class="chapter">卷二 · 声与光</div>
    ${EX.slice(4, 9).map(e => `<div class="it"><i>${e.n}</i><b>${e.name}</b></div>`).join('')}
    <div class="chapter">卷三 · 纸与时间</div>
    ${EX.slice(9).map(e => `<div class="it"><i>${e.n}</i><b>${e.name}</b></div>`).join('')}
  </div>
</section>

${plates}

<section class="page colophon">
  <div>
    <h2>关于这间屋子</h2>
    <p>十二件展品，分别用原生 HTML / CSS / JavaScript、Canvas、WebAudio，以及 Python 的 numpy 与 Pillow 完成。图形是算出来的，声音是合成出来的，文字是写出来的。没有框架，没有构建步骤，没有外部依赖。</p>
    <p>每件作品都可以被拆开：代码没有压缩，生成脚本带注释，随机种子写在文件里。欢迎改参数、重跑、据为己有。</p>
  </div>
  <div class="mono">
    奇珍室 · A CABINET OF CURIOSITIES<br>
    图录 · 第一版 · 2026 年 11 月<br>
    全部作品离线运行 · 不联网 · 不含任何真实人物信息<br>
    排版：A4 / 210 × 297 mm &nbsp;·&nbsp; 字体：Noto Serif SC / Noto Sans SC
  </div>
  <div class="end"><span>创造 · 2026</span><span>FIN.</span></div>
</section>

</body></html>`;

fs.writeFileSync(OUT_HTML, html, 'utf8');
console.log('html written:', OUT_HTML);

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const url = 'file:///' + OUT_HTML.replace(/\\/g, '/');
const r = spawnSync(CHROME, [
  '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
  '--run-all-compositor-stages-before-draw', '--virtual-time-budget=8000',
  '--user-data-dir=' + process.env.TEMP + '\\chr_pdf',
  '--print-to-pdf=' + OUT_PDF, url
], { encoding: 'utf8' });
if (r.error) console.error(r.error.message);
console.log('pdf:', OUT_PDF, exists(OUT_PDF) ? fs.statSync(OUT_PDF).size + ' bytes' : 'MISSING');


