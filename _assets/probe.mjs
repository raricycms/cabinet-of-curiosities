// 展品交互探针: 加载页面 -> 执行一段 JS -> 等待 -> 截图
// 用法: node _assets/probe.mjs "<html路径>" "<输出名>" "<JS表达式>" [等待ms] [宽] [高]
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PORT = 9334;
const OUT = path.join(path.dirname(fileURLToPath(import.meta.url)), 'shots');
const [htmlPath, outName, expr = 'null', waitMs = '1500', w = '1440', h = '900'] = process.argv.slice(2);
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function waitFor(fn, timeout = 15000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    try { const v = await fn(); if (v) return v; } catch {}
    await sleep(150);
  }
  throw new Error('timeout');
}
class CDP {
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map(); this.logs = [];
    ws.addEventListener('message', (ev) => { let m; try { m = JSON.parse(ev.data); } catch { return; }
      if (m.id != null && this.pending.has(m.id)) { const p = this.pending.get(m.id); this.pending.delete(m.id);
        m.error ? p.reject(new Error(JSON.stringify(m.error))) : p.resolve(m.result); }
      else if (m.method === 'Runtime.exceptionThrown') this.logs.push('EXCEPTION: ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
      else if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') this.logs.push('CONSOLE: ' + m.params.args.map(a => a.value ?? a.description).join(' '));
    }); }
  send(method, params = {}) { const id = ++this.id; return new Promise((res, rej) => {
    this.pending.set(id, { resolve: res, reject: rej }); this.ws.send(JSON.stringify({ id, method, params }));
    setTimeout(() => { if (this.pending.has(id)) { this.pending.delete(id); rej(new Error('timeout ' + method)); } }, 20000); }); }
}

(async () => {
  const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--mute-audio', '--autoplay-policy=no-user-gesture-required',
    '--no-first-run', `--remote-debugging-port=${PORT}`, `--user-data-dir=${process.env.TEMP}\\chr_probe`, 'about:blank'], { stdio: 'ignore', windowsHide: true });
  try {
    await waitFor(() => fetch(`http://127.0.0.1:${PORT}/json/version`).then(r => r.ok), 20000);
    const target = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', rej); });
    const cdp = new CDP(ws);
    await cdp.send('Runtime.enable'); await cdp.send('Page.enable');
    await cdp.send('Emulation.setDeviceMetricsOverride', { width: +w, height: +h, deviceScaleFactor: 1, mobile: +w < 600 });
    await cdp.send('Page.navigate', { url: pathToFileURL(htmlPath).href });
    await sleep(500);
    await waitFor(() => cdp.send('Runtime.evaluate', { expression: 'document.readyState', returnByValue: true }).then(r => r.result.value === 'complete'));
    await sleep(900);
    const r = await cdp.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    console.log('EVAL:', JSON.stringify(r.result.value ?? r.exceptionDetails?.text));
    await sleep(+waitMs);
    const shot = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
    fs.writeFileSync(path.join(OUT, outName + '.png'), Buffer.from(shot.data, 'base64'));
    const state = await cdp.send('Runtime.evaluate', { expression: 'document.title', returnByValue: true });
    console.log('TITLE:', state.result.value);
    if (cdp.logs.length) console.log('LOGS:', cdp.logs.slice(0, 6).join(' | '));
    ws.close();
  } catch (e) { console.log('FATAL:', e.message); }
  finally { chrome.kill(); }
})();
