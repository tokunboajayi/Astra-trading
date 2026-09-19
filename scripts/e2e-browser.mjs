/**
 * scripts/e2e-browser.mjs: drives the real UI in a headless Edge/Chrome over the DevTools
 * Protocol and fails on any console error. Owned by B (Backend).
 *
 *   node scripts/e2e-browser.mjs [screenshotDir]
 *
 * Needs Node 22+ and Edge or Chrome (set BROWSER=/path/to/it if it is not found). It starts its
 * own server on :8000 and a static server on :5500, and it RESETS the session and QA log: run it
 * on a scratch machine or with the demo server stopped, never against the one you present from.
 */
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PY = process.env.PYTHON ?? (process.platform === 'win32' ? 'python' : 'python3');
const OUT = process.argv[2] ?? path.join(os.tmpdir(), 'richher-e2e');
fs.mkdirSync(OUT, { recursive: true });
const BROWSER = [
  process.env.BROWSER,
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', 'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/microsoft-edge',
].find((p) => p && fs.existsSync(p));
if (typeof WebSocket === 'undefined') { console.error('This needs Node 22 or newer (built-in WebSocket).'); process.exit(2); }
if (!BROWSER) { console.error('No Edge or Chrome found. Set BROWSER=/path/to/browser.'); process.exit(2); }
for (const port of [8000, 5500]) {
  if (await fetch(`http://127.0.0.1:${port}/`).then(() => true, () => false)) {
    console.error(`Something is already listening on :${port}. This test resets the server it uses, so stop that first.`);
    process.exit(2);
  }
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const results = [];
const problems = [];          // console errors, exceptions, failed requests

function check(name, ok, detail = '') {
  results.push({ name, ok });
  console.log(`${ok ? '  ok  ' : '  FAIL'} ${name}${ok ? '' : `   -> ${detail}`}`);
}

// ---------------------------------------------------------------- processes
let server = null;
const startServer = () => { server = spawn(PY, ['-m', 'uvicorn', 'server.main:app', '--port', '8000'], { cwd: REPO, stdio: 'ignore' }); };
const stopServer = async () => { server?.kill(); await sleep(800); };
async function waitHttp(url, ms = 20000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) { try { if ((await fetch(url)).ok) return; } catch (_) { /* not up yet */ } await sleep(250); }
  throw new Error(`server not up: ${url}`);
}

// ---------------------------------------------------------------- CDP
class CDP {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.pending = new Map(); this.handlers = [];
    ws.onmessage = (e) => {
      const m = JSON.parse(e.data);
      if (m.id) { const p = this.pending.get(m.id); this.pending.delete(m.id); if (p) (m.error ? p.reject(new Error(JSON.stringify(m.error))) : p.resolve(m.result)); }
      else this.handlers.forEach((fn) => fn(m));
    };
  }
  send(method, params = {}) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }));
  }
}

const userDir = fs.mkdtempSync(path.join(os.tmpdir(), 'richher-edge-'));
const edge = spawn(BROWSER, ['--headless=new', '--remote-debugging-port=9333', `--user-data-dir=${userDir}`,
  '--no-first-run', '--no-default-browser-check', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });

let cdp;
async function connect() {
  let target;
  for (let i = 0; i < 60 && !target; i++) {
    try { target = (await (await fetch('http://127.0.0.1:9333/json/list')).json()).find((t) => t.type === 'page'); } catch (_) { /* wait */ }
    if (!target) await sleep(250);
  }
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => { ws.onopen = r; });
  cdp = new CDP(ws);
  cdp.handlers.push((m) => {
    const p = m.params;
    if (m.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(p.type)) problems.push(`console.${p.type}: ${p.args.map((a) => a.value ?? a.description).join(' ')}`);
    if (m.method === 'Runtime.exceptionThrown') problems.push(`exception: ${p.exceptionDetails.text} ${p.exceptionDetails.exception?.description ?? ''}`);
    if (m.method === 'Log.entryAdded' && ['error', 'warning'].includes(p.entry.level)) problems.push(`log.${p.entry.level}: ${p.entry.text} ${p.entry.url ?? ''}`);
  });
  for (const d of ['Runtime', 'Log', 'Page', 'Network']) await cdp.send(`${d}.enable`);
}

const ev = async (expression) => {
  const r = await cdp.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(`eval failed: ${expression}\n${r.exceptionDetails.exception?.description ?? r.exceptionDetails.text}`);
  return r.result.value;
};
const q = (sel) => `document.querySelector(${JSON.stringify(sel)})`;
const text = (sel) => ev(`${q(sel)}?.textContent ?? null`);
const visible = (sel) => ev(`(() => { const e = ${q(sel)}; return !!e && !e.hidden && e.getClientRects().length > 0; })()`);
const click = (sel) => ev(`(() => { const e = ${q(sel)}; if (!e) return false; e.click(); return true; })()`);
const disabled = (sel) => ev(`${q(sel)}?.disabled ?? null`);
async function waitFor(expr, label, ms = 8000) {
  const t0 = Date.now();
  for (;;) {
    let v = false;
    try { v = await ev(expr); } catch (_) { /* page mid-load */ }
    if (v) return;
    if (Date.now() - t0 > ms) throw new Error(`timeout waiting for: ${label}`);
    await sleep(100);
  }
}
async function goto(url) {
  await cdp.send('Page.navigate', { url });
  await waitFor(`document.readyState === 'complete'`, `load ${url}`);
  await sleep(300);
}
async function shot(name, w = 1280, h = 900, mobile = false) {
  await ev(`document.getElementById('toast').className = 'toast'`);    // keep transient toasts out of the picture
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: mobile ? 2 : 1, mobile });
  await sleep(250);
  const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  fs.writeFileSync(path.join(OUT, `${name}.png`), Buffer.from(data, 'base64'));
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
}
const $$ = (sel) => ev(`document.querySelectorAll(${JSON.stringify(sel)}).length`);
const has = (s, part) => typeof s === 'string' && s.includes(part);

// ---------------------------------------------------------------- the run
try {
  startServer();
  await waitHttp('http://127.0.0.1:8000/api/state');
  await connect();
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });

  console.log('\nA. fresh load and onboarding');
  await goto('http://127.0.0.1:8000/');
  await ev(`localStorage.clear(); fetch('/api/reset', { method: 'POST' }).then(r => r.ok)`);
  await goto('http://127.0.0.1:8000/');
  check('onboarding card is shown', await visible('#onboarding'));
  check('app is hidden until onboarded', !(await visible('#app')));
  check('every practice symbol is offered', (await $$('#onboarding input[name=symbol]')) === 6);
  check('no external fonts or CDN referenced', !(await ev(`[...document.querySelectorAll('link,script')].some(e => /googleapis|gstatic|cdn\\./.test(e.href || e.src))`)));
  await shot('01-onboarding');
  // NVX is the pre-selected guided walk-through; this section drives the TIER demo, which
  // runs on HLX. Pick it explicitly so the test does not depend on the default.
  await ev(`${q('input[name=symbol][value=HLX]')}.click()`);
  await click('#btnStart');
  await waitFor(`!${q('#app')}.hidden`, 'app visible after onboarding');
  check('cash starts at $10,000.00', (await text('#valCash')) === '$10,000.00', await text('#valCash'));
  check('replay starts on day 41 of 90', has(await text('#valDay'), 'Day 41 of 90'), await text('#valDay'));
  check('price is $168.00', (await text('#valPrice')) === '$168.00');
  check('Tier 1 chip is active', has(await ev(`${q('.tier-chip.is-active')}.textContent`), '1. Foundation'));
  check('chart shows the line and hides the future', (await $$('#chart .line')) === 1 && has(await text('#chart'), 'The future is hidden'));
  check('no candles at Tier 1', (await $$('#chart .body-up, #chart .body-down')) === 0);

  console.log('\nB. tap-to-explain hint popover');
  await click('.stat h2[data-hint="portfolio.cash"] .info');
  check('cash (i) opens a downside-first hint', (await visible('#hintPop')) && has(await text('#hintPop'), 'inflation'), await text('#hintPop'));
  await ev(`document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))`);
  check('Escape closes it', !(await visible('#hintPop')));

  console.log('\nC. buy with the tap-to-explain ticket');
  check('ticket starts idle (no risk box yet)', !(await visible('#ticketRisk')));
  await click('#btnBuy');
  check('tapping Buy opens the downside box', await visible('#ticketRisk'));
  check('Confirm is locked at first', (await disabled('#btnConfirm')) === true && has(await text('#btnConfirm'), 'Read the risk'), await text('#btnConfirm'));
  check('downside line names the loss', has(await text('#ticketHint .hint-downside'), 'lose'), await text('#ticketHint .hint-downside'));
  check('max potential loss is 10 x $168 = $1,680.00', has(await text('#ticketLoss'), '$1,680.00'), await text('#ticketLoss'));
  check('Limit is locked at Tier 1 and says where it unlocks', await ev(`(() => { const o = [...document.querySelectorAll('#ticketType option')].find(o => o.value === 'LIMIT'); return o.disabled && /unlocks at Tier 2/.test(o.textContent); })()`));
  await sleep(1700);
  check('Confirm unlocks after 1.5 s', (await disabled('#btnConfirm')) === false, await text('#btnConfirm'));
  await click('#btnConfirm');
  await waitFor(`${q('#valCash')}.textContent === '$8,320.00'`, 'cash after buy');
  check('cash is $8,320.00 and position is 10 x HLX', has(await text('#valPosition'), '10'), await text('#valPosition'));
  check('position card warns there is no safety net', has(await text('#subPosition'), 'no safety net'), await text('#subPosition'));
  check('money-flow line leads with what can be lost', has(await text('#moneyFlow'), 'can lose value'), await text('#moneyFlow'));
  check('entry line drawn on the chart', has(await text('#chart'), 'Your entry $168.00'));

  console.log('\nD. comprehension check unlocks Tier 2');
  await waitFor(`!${q('#checkCard')}.hidden`, 'check card');
  check('quick check appears after the first trade', has(await text('#checkCard'), 'your downside'));
  await ev(`${q('#checkCard input[value="0"]')}.click()`); await click('#checkCard button[type=submit]');
  await waitFor(`${q('#checkCard .check-result.bad')}`, 'wrong-answer explanation');
  check('wrong answer explains and offers another go', has(await text('#checkCard'), 'Try again'));
  await ev(`${q('#checkCard input[value="2"]')}.click()`); await click('#checkCard button[type=submit]');
  await waitFor(`${q('#checkCard .check-unlock')}`, 'unlock message');
  check('right answer unlocks Tier 2', has(await text('#checkCard'), 'Tier 2: Tactical Protection'));
  check('Tier 2 chip is now active', has(await ev(`${q('.tier-chip.is-active')}.textContent`), '2.'));
  check('Limit orders are now allowed', await ev(`![...document.querySelectorAll('#ticketType option')].find(o => o.value === 'LIMIT').disabled`));
  await click('#checkCard .btn-ghost');
  check('chart gained highs/lows at Tier 2', (await $$('#chart .level')) === 2);

  console.log('\nE. tier scrub previews Tier 3, then exits');
  await click('.tier-chip[data-tier="advanced"]');
  check('preview banner is shown', (await visible('#banner')) && has(await text('#banner'), 'Previewing Tier 3'), await text('#banner'));
  check('chart switched to candlesticks', (await $$('#chart .body-up, #chart .body-down')) > 0);
  check('ticket is read-only in a preview', await ev(`${q('#ticket fieldset')}.disabled`));
  await shot('02-preview-candles');
  await click('#banner .btn');
  check('exiting the preview restores the chart', !(await visible('#banner')) && (await $$('#chart .level')) === 2);

  console.log('\nF. fast-forward into the drawdown');
  await click('#btnFast');
  await waitFor(`!${q('#safetyModal')}.hidden`, 'safety-net prompt');
  const title = await text('#snTitle');
  check('prompt says the position is down 8.2%', has(title, 'down 8.2%'), title);
  const body = await text('#safetyModal .modal-body');
  check('prompt numbers come from the position ($168.00 -> $154.17, -$138.30)', has(body, '$168.00') && has(body, '$154.17') && has(body, '$138.30'), body);
  check('prompt offers the $151.20 stop with one label', has(await text('#btnProtect'), 'Protect my position (sell at $151.20)'), await text('#btnProtect'));
  check('Tier 2 can choose its own stop distance', (await $$('#stopPercent')) === 1);
  check('replay is frozen while the prompt is open', (await disabled('#btnFast')) === true && has(await text('#valDay'), 'Day 54 of 90'), await text('#valDay'));
  await shot('03-safety-net-prompt');
  await shot('03m-safety-net-prompt-phone', 390, 844, true);

  console.log('\nG. accept the safety net');
  await click('#btnProtect');
  await waitFor(`${q('#safetyModal')}.hidden`, 'modal closes');
  check('position card shows the net at $151.20', has(await text('#subPosition'), 'safety net sells at $151.20'), await text('#subPosition'));
  check('stop line drawn on the chart', has(await text('#chart'), 'Safety net $151.20'));
  await waitFor(`!${q('#checkCard')}.hidden`, 'second check');
  check('stop-loss check appears', has(await text('#checkCard'), 'the safety net'));
  await ev(`${q('#checkCard input[value="1"]')}.click()`); await click('#checkCard button[type=submit]');
  await waitFor(`${q('#checkCard .check-unlock')}`, 'tier 3 unlock');
  check('right answer unlocks Tier 3', has(await text('#checkCard'), 'Tier 3: Strategic Mastery'));
  await click('#checkCard .btn-ghost');

  console.log('\nH. the stop fires, then on to the trough');
  await click('#btnAdv1');
  await waitFor(`${q('#valPosition')}.textContent === 'No position'`, 'position sold');
  check('cash is $9,832.00 after the stop fills', (await text('#valCash')) === '$9,832.00', await text('#valCash'));
  check('toast announces the safety net', has(await text('#toast'), 'safety net'), await text('#toast'));
  check('money-flow explains the locked-in loss', has(await text('#moneyFlow'), 'sold 10 HLX at $151.20') && has(await text('#moneyFlow'), '$168.00 loss'), await text('#moneyFlow'));
  await click('#btnAdv5'); await waitFor(`${q('#btnAdv5')}.disabled === false`, 'idle'); await click('#btnAdv1');
  await waitFor(`${q('#valDay')}.textContent.includes('Day 61')`, 'trough day');
  check('price is $132.96 at the trough', (await text('#valPrice')) === '$132.96', await text('#valPrice'));
  check('shadow benchmark says the net saved $182.40', has(await text('#shadowText'), 'saved you $182.40'), await text('#shadowText'));
  check('Tier 3 chart: candles and strategy legend', (await $$('#chart .body-up, #chart .body-down')) > 0 && (await visible('#chartLegend')));
  check('Stop orders are allowed at Tier 3', await ev(`![...document.querySelectorAll('#ticketType option')].find(o => o.value === 'STOP').disabled`));
  await shot('04-trough-desktop');
  await shot('04m-trough-phone', 390, 844, true);

  console.log('\nI. reset, then the alternate onboarding branch');
  await click('#btnReset');
  await waitFor(`!${q('#onboarding')}.hidden`, 'onboarding after reset');
  check('reset returns to onboarding and hides the app', !(await visible('#app')));
  check('reset cleared the saved action log', await ev(`JSON.parse(localStorage.getItem('richher.session.v1')).log.length === 0`));
  await ev(`${q('input[name=experience][value=experienced]')}.click(); ${q('input[name=symbol][value=VLT]')}.click()`);
  await click('#btnStart');
  await waitFor(`!${q('#app')}.hidden`, 'app for the experienced branch');
  check('experienced branch starts at Tier 2 on VLT, day 16', has(await ev(`${q('.tier-chip.is-active')}.textContent`), '2.') && has(await text('#valDay'), 'Day 16'), await text('#valDay'));
  check('tier-gated ticket: Limit allowed, Stop locked', await ev(`(() => { const o = [...document.querySelectorAll('#ticketType option')]; return !o.find(x => x.value === 'LIMIT').disabled && o.find(x => x.value === 'STOP').disabled && /unlocks at Tier 3/.test(o.find(x => x.value === 'STOP').textContent); })()`));
  await click('#btnBuy'); await sleep(1700); await click('#btnConfirm');
  await waitFor(`${q('#valPosition')}.textContent.includes('VLT')`, 'VLT bought');
  const cashBefore = await text('#valCash');
  const posBefore = await text('#valPosition');

  console.log('\nJ. server restart: the browser restores the session by replaying its log');
  await stopServer();
  startServer();
  await waitHttp('http://127.0.0.1:8000/api/state');
  await goto('http://127.0.0.1:8000/');
  await waitFor(`!${q('#app')}.hidden`, 'session restored after restart', 15000);
  check('same cash and position after the restart', (await text('#valCash')) === cashBefore && (await text('#valPosition')) === posBefore, `${await text('#valCash')} / ${await text('#valPosition')}`);
  await click('#btnReset');
  await waitFor(`!${q('#onboarding')}.hidden`, 'onboarding after reset');
  await goto('http://127.0.0.1:8000/');
  check('an intentional reset is NOT resurrected on reload', (await visible('#onboarding')) && !(await visible('#app')));

} catch (e) {
  check('run completed without an unexpected error', false, e.stack ?? String(e));
} finally {
  // ---------------------------------------------------------------- two-server flow
  try {
    await stopServer();                     // never leave the first server running under the second
    startServer();
    await waitHttp('http://127.0.0.1:8000/api/state');
    const staticSrv = spawn(PY, ['-m', 'http.server', '5500', '--directory', path.join(REPO, 'web')], { stdio: 'ignore' });
    await waitHttp('http://127.0.0.1:5500/index.html');
    console.log('\nL. two-server flow (static server on 5500, API on 8000)');
    await ev(`localStorage.clear()`).catch(() => {});
    await goto('http://127.0.0.1:5500/');
    await ev(`fetch('http://127.0.0.1:8000/api/reset', { method: 'POST' }).then(r => r.ok)`);
    await goto('http://127.0.0.1:5500/');
    check('onboarding loads from the static server via CORS', await visible('#onboarding'));
    await ev(`${q('input[name=symbol][value=HLX]')}.click()`);
    await click('#btnStart');
    await waitFor(`!${q('#app')}.hidden`, 'app on the static server', 10000);
    check('the replay runs across origins', has(await text('#valDay'), 'Day 41 of 90'));
    console.log('\nM. server unreachable shows a friendly error');
    await stopServer();
    await goto('http://127.0.0.1:5500/');
    await waitFor(`!${q('#fatal')}.hidden`, 'fatal card', 10000);
    check('offline card explains how to start the server', has(await text('#fatal'), 'uvicorn server.main:app'), await text('#fatal'));
    staticSrv.kill();
  } catch (e) {
    check('two-server / offline checks ran', false, e.stack ?? String(e));
  }

  console.log('\nconsole errors, warnings, exceptions, failed requests during the whole run:');
  const filtered = problems.filter((p) => !/ERR_CONNECTION_REFUSED|Failed to fetch|Failed to load resource: net::ERR_CONNECTION_REFUSED/.test(p));
  const expected = problems.length - filtered.length;
  check(`zero unexpected console problems (${expected} connection-refused lines ignored: the server was stopped on purpose)`, filtered.length === 0, filtered.join(' | '));
  await stopServer();
  edge.kill();
  try { fs.rmSync(userDir, { recursive: true, force: true, maxRetries: 3 }); } catch (_) { /* temp dir, best effort */ }
  const failed = results.filter((r) => !r.ok).length;
  console.log(`\n${results.length - failed} passed, ${failed} failed`);
  process.exit(failed ? 1 : 0);
}
