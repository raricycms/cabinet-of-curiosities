// 奇珍室 · 展品审计工具 (CDP)
// 用法: node _assets/audit.mjs <html路径1> <html路径2> ...
// 对每个页面: 桌面 1440x900 / 移动 390x844 截图, 捕获 JS 异常与控制台错误
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PORT = 9333;
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = process.argv[2] === '--out' ? process.argv[3] : path.join(HERE, 'shots');
const pages = process.argv.slice(process.argv[2] === '--out' ? 4 : 2);
const PROFILE = process.env.TEMP + '\\chr_audit_profile';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function waitFor(fn, timeout = 15000, interval = 200) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    try { const v = await fn(); if (v) return v; } catch (e) {}
    await sleep(interval);
  }
  throw new Error('timeout');
}

class CDP {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.pending = new Map(); this.listeners = [];
    ws.addEventListener('message', (ev) => {
      let msg; try { msg = JSON.parse(ev.data); } catch { return; }
      if (msg.id != null && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      } else if (msg.method) {
        for (const fn of this.listeners) fn(msg);
      }
    });
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
      setTimeout(() => { if (this.pending.has(id)) { this.pending.delete(id); reject(new Error('cdp timeout ' + method)); } }, 20000);
    });
  }
  on(fn) { this.listeners.push(fn); return () => { this.listeners = this.listeners.filter(x => x !== fn); }; }
}

async function connect(url) {
  const ws = new WebSocket(url);
  await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', rej); });
  return new CDP(ws);
}

async function auditPage(htmlPath) {
  const fileUrl = pathToFileURL(htmlPath).href;
  const name = path.basename(path.dirname(htmlPath)) + '__' + path.basename(htmlPath, '.html');
  const target = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
  const cdp = await connect(target.webSocketDebuggerUrl);
  const errors = [];
  cdp.on((msg) => {
    if (msg.method === 'Runtime.exceptionThrown') {
      const d = msg.params.exceptionDetails;
      errors.push('EXCEPTION: ' + (d.exception?.description || d.text) + ' @' + (d.url || ''));
    } else if (msg.method === 'Runtime.consoleAPICalled' && (msg.params.type === 'error' || msg.params.type === 'warning')) {
      errors.push('CONSOLE.' + msg.params.type + ': ' + msg.params.args.map(a => a.value ?? a.description ?? a.type).join(' '));
    } else if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error') {
      errors.push('LOG: ' + msg.params.entry.text + ' @' + (msg.params.entry.url || ''));
    }
  });
  await cdp.send('Runtime.enable');
  await cdp.send('Log.enable');
  await cdp.send('Page.enable');
  await cdp.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });

  const out = { page: name, file: htmlPath, errors };
  for (const vp of [{ k: 'desk', w: 1440, h: 900, mobile: false }, { k: 'mob', w: 390, h: 844, mobile: true }]) {
    await cdp.send('Emulation.setDeviceMetricsOverride', { width: vp.w, height: vp.h, deviceScaleFactor: 1, mobile: vp.mobile });
    await cdp.send('Page.navigate', { url: fileUrl });
    await sleep(400);
    try {
      await waitFor(() => cdp.send('Runtime.evaluate', { expression: 'document.readyState', returnByValue: true }).then(r => r.result.value === 'complete'));
    } catch (e) { errors.push('LOAD TIMEOUT'); }
    await sleep(1600);
    let info = {};
    try {
      const r = await cdp.send('Runtime.evaluate', {
        expression: `JSON.stringify({title:document.title, sw:document.documentElement.scrollWidth, cw:document.documentElement.clientWidth, sh:document.documentElement.scrollHeight, links:[...document.querySelectorAll('a')].map(a=>a.getAttribute('href')).filter(h=>h&&!h.startsWith('#')&&!h.startsWith('http')).slice(0,6)})`,
        returnByValue: true
      });
      info = JSON.parse(r.result.value);
    } catch (e) { errors.push('EVAL FAIL'); }
    out[vp.k] = info;
    if (info.sw > info.cw + 1) errors.push(`OVERFLOW-X(${vp.k}): scrollWidth ${info.sw} > clientWidth ${info.cw}`);
    try {
      const shot = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
      fs.writeFileSync(path.join(OUT, `${name}_${vp.k}.png`), Buffer.from(shot.data, 'base64'));
      const full = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
      fs.writeFileSync(path.join(OUT, `${name}_${vp.k}_full.png`), Buffer.from(full.data, 'base64'));
    } catch (e) { errors.push('SHOT FAIL: ' + e.message); }
  }
  cdp.ws.close();
  await fetch(`http://127.0.0.1:${PORT}/json/close/${target.id}`).catch(() => {});
  return out;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const chrome = spawn(CHROME, [
    '--headless=new', '--disable-gpu', '--hide-scrollbars', '--mute-audio',
    '--no-first-run', '--no-default-browser-check',
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`, 'about:blank'
  ], { stdio: 'ignore', windowsHide: true });
  try {
    await waitFor(() => fetch(`http://127.0.0.1:${PORT}/json/version`).then(r => r.ok), 20000);
    const results = [];
    for (const p of pages) {
      try {
        const r = await auditPage(p);
        results.push(r);
        console.log(JSON.stringify(r));
      } catch (e) {
        console.log(JSON.stringify({ file: p, fatal: e.message }));
      }
    }
    fs.writeFileSync(path.join(OUT, '..', 'audit_report.json'), JSON.stringify(results, null, 2));
  } finally {
    chrome.kill();
  }
})();
