// 奇珍室 · 明信片 A4 排印稿 -> PDF
// 用法: node _assets/build_postcards.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SHOTS = path.join(ROOT, '_assets', 'shots');
const OUT_HTML = path.join(ROOT, '_assets', 'postcards.html');
const OUT_PDF = path.join(ROOT, '奇珍室_明信片.pdf');

const CARDS = [
  { img: 'ripple_crop.png', name: '涟漪', en: 'RIPPLE',
    line: '点一下水面。', note: '它不回答，只是记住。' },
  { img: 'crystal_crop.png', name: '晶园', en: 'CRYSTAL GARDEN',
    line: '种一颗晶核。', note: '剩下的交给扩散与时间。' },
  { img: 'star_crop.png', name: '数字星图', en: 'NUMERICAL STAR ATLAS',
    line: '用质数观测夜空。', note: '规则足够简单，尺度足够大。' },
  { img: 'oracle_crop.png', name: '预言机', en: 'THE ORACLE',
    line: '问它一件事。', note: '同一个问题，永远得到同一支签。' },
];

const exists = p => { try { return fs.existsSync(p); } catch { return false; } };
const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;');

const fronts = CARDS.map(c => `
  <div class="card front">
    <img src="../_assets/shots/${c.img}" alt="">
    <div class="shade"></div>
    <div class="cap">
      <span class="nm">${esc(c.name)}</span>
      <span class="en">${c.en}</span>
    </div>
  </div>`).join('\n');

const backs = CARDS.map((c, i) => `
  <div class="card back">
    <div class="bk-top">
      <div class="bk-brand">奇珍室<br><span>A CABINET OF CURIOSITIES</span></div>
      <div class="stamp">
        <svg viewBox="0 0 24 24" fill="none" stroke="#8d372d" stroke-width="1" stroke-linecap="round">
          <circle cx="12" cy="12" r="2.2"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="9.6"/>
        </svg>
        <span>POSTAGE</span>
      </div>
    </div>
    <div class="bk-quote">
      <p>${esc(c.line)}</p>
      <p>${esc(c.note)}</p>
    </div>
    <div class="bk-lines">
      <i></i><i></i><i></i>
      <div class="bk-foot">N°${'0' + (i + 1)} / 创造 · 2026</div>
    </div>
  </div>`).join('\n');

const html = `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>奇珍室 · 明信片</title>
<style>
  @page{ size:A4 landscape; margin:0; }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0;background:#fff;-webkit-print-color-adjust:exact;print-color-adjust:exact;}
  .page{width:297mm;height:210mm;position:relative;display:grid;padding:5mm;
    grid-template-columns:143.5mm 143.5mm;grid-template-rows:100mm 100mm;
    page-break-after:always;break-after:page;background:#fff}
  .page:last-child{page-break-after:auto;break-after:auto}
  .card{position:relative;overflow:hidden}
  .front{background:#080a0f;border:.2pt solid #3a3f46}
  .front img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
  .shade{position:absolute;inset:0;
    background:linear-gradient(180deg,rgba(4,6,10,.10) 0%,transparent 42%,rgba(4,6,10,.78) 100%)}
  .cap{position:absolute;left:9mm;bottom:7mm;color:#efe8da}
  .cap .nm{display:block;font-family:"Noto Serif SC","STZhongsong","SimSun",serif;
    font-size:15pt;letter-spacing:.16em;margin-bottom:1.5mm}
  .cap .en{display:block;font-family:"Cascadia Mono","Consolas",monospace;
    font-size:6pt;letter-spacing:.34em;color:rgba(239,232,218,.62)}
  /* 背面 */
  .back{background:linear-gradient(160deg,#f6f0e4,#ece3d2 70%,#e3d8c4);
    border:.2pt solid #b9ae98;padding:10mm 11mm;display:flex;flex-direction:column;
    color:#2b241a}
  .bk-top{display:flex;justify-content:space-between;align-items:flex-start}
  .bk-brand{font-family:"Noto Serif SC","STZhongsong","SimSun",serif;font-size:11pt;
    letter-spacing:.28em;color:#3a2f22;line-height:1.7}
  .bk-brand span{font-family:"Cascadia Mono","Consolas",monospace;font-size:5pt;
    letter-spacing:.24em;color:#8a7b62}
  .stamp{width:19mm;height:23mm;border:.4pt dashed #a2987f;display:grid;place-items:center;
    position:relative;background:rgba(255,255,255,.25)}
  .stamp svg{width:10mm;height:10mm;opacity:.55}
  .stamp span{position:absolute;bottom:2mm;font-family:"Cascadia Mono","Consolas",monospace;
    font-size:3.6pt;letter-spacing:.16em;color:#8a7b62}
  .bk-quote{margin-top:auto;margin-bottom:auto;padding:8mm 0 6mm;border-bottom:.3pt solid rgba(90,74,50,.18)}
  .bk-quote p{margin:0;font-family:"Noto Serif SC","STZhongsong","SimSun",serif;
    font-size:10.5pt;line-height:2;letter-spacing:.08em;color:#43382a}
  .bk-quote p + p{font-size:9pt;color:#6b5d49}
  .bk-lines{margin-top:9mm;position:relative}
  .bk-lines i{display:block;height:1px;background:rgba(90,74,50,.28);margin-bottom:9mm}
  .bk-lines i:nth-child(1){width:82%}.bk-lines i:nth-child(2){width:70%}.bk-lines i:nth-child(3){width:56%}
  .bk-foot{position:absolute;right:0;bottom:-2mm;font-family:"Cascadia Mono","Consolas",monospace;
    font-size:4.6pt;letter-spacing:.24em;color:#9a8b72}
</style></head><body>
<section class="page">${fronts}</section>
<section class="page">${backs}</section>
</body></html>`;

fs.writeFileSync(OUT_HTML, html, 'utf8');
const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const url = 'file:///' + OUT_HTML.replace(/\\/g, '/');
spawnSync(CHROME, ['--headless=new','--disable-gpu','--no-pdf-header-footer',
  '--run-all-compositor-stages-before-draw','--virtual-time-budget=6000',
  '--user-data-dir=' + process.env.TEMP + '\\chr_pc',
  '--print-to-pdf=' + OUT_PDF, url], { encoding: 'utf8' });
console.log('pdf:', OUT_PDF, exists(OUT_PDF) ? fs.statSync(OUT_PDF).size + ' bytes' : 'MISSING');

