/**
 * app.js: state coordinator for the browser. Owned by F.
 * The server is the only source of truth: every action goes to the API, the response carries the
 * full new state, and the screen is redrawn from it. localStorage only keeps the server's action
 * log, so a restarted server can be rebuilt by replaying it (SPEC.md section 6).
 */

import { h, usd, signedUsd, pct } from './format.js';
import { renderChart, chartSummary } from './chart.js';
import { mountTicket } from './order-ticket.js';
import { getHint, attachHintButtons, renderCheck } from './hint.js';
import { describeMoneyFlow, renderMoneyFlow } from './money-flow.js';
import { showSafetyNetPrompt, hideSafetyNetPrompt } from './safety-net.js';
import {
  renderOnboarding, renderTierScrub, chartModeFor, strategyOverlayOn, customSafetyNetOn, shortName,
} from './tier-picker.js';

// Where the API lives. Same origin when FastAPI serves this page (port 8000); otherwise the local
// server. Override with ?api=https://... or window.RICHHER_API for a hosted backend.
const params = new URLSearchParams(location.search);
const API = params.get('api') ?? window.RICHHER_API ?? (location.port === '8000' ? '' : 'http://127.0.0.1:8000');
const STORE_KEY = 'richher.session.v1';
const FAST_FORWARD_MAX = 30;

const $ = (id) => document.getElementById(id);
let S = null;                                                    // latest server state
let content = { tiers: [], hints: {}, checks: {} };
let previewTier = null;                                          // a locked tier being previewed
let lastCheck = null;                                            // { id, result } for the quick check card
let busy = false;
let modalKey = null;
let toastTimer = null;

const viewTier = () => previewTier ?? S?.tier ?? 'beginner';
const tierOf = (id) => content.tiers.find((t) => t.id === id);

class ApiFailure extends Error {
  constructor(status, code, message, data = {}) { super(message); Object.assign(this, { status, code, data }); }
}

async function call(method, path, body) {
  let res;
  try {
    res = await fetch(API + path, {
      method, body: body === undefined ? undefined : JSON.stringify(body),
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    });
  } catch (_) {
    throw new ApiFailure(0, 'OFFLINE', `Cannot reach the Rich-HER server at ${API || location.origin}. Start it with: uvicorn server.main:app --port 8000`);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiFailure(res.status, data.error ?? 'ERROR', data.message ?? res.statusText, data);
  return data;
}

/** One user action: send it, adopt the state it returns, or show why it failed. Returns the reply or null. */
async function act(method, path, body) {
  if (busy) return null;
  busy = true;
  renderControls();
  try {
    const data = await call(method, path, body);
    if (data.state) apply(data.state);
    return data;
  } catch (e) {
    notify(e.message, 'bad');
    if (e.code === 'STALE_CURSOR' || e.code === 'PROMPT_PENDING') await refresh();
    return null;
  } finally {
    busy = false;
    renderControls();
  }
}

async function refresh() {
  try { apply(await call('GET', '/api/state')); } catch (e) { notify(e.message, 'bad'); }
}

function apply(state) {
  S = state;
  try { localStorage.setItem(STORE_KEY, JSON.stringify({ boot_id: state.boot_id, log: state.replay_log })); } catch (_) { /* storage may be blocked */ }
  render();
}

function notify(message, kind = 'info') {
  const el = $('toast');
  el.textContent = message;
  el.className = `toast show ${kind}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.className = 'toast'; }, 6000);
}

function showFatal(message) {
  $('app').hidden = true;
  $('onboarding').hidden = true;
  const card = $('fatal');
  card.hidden = false;
  card.replaceChildren(h('h2', { text: 'The replay cannot start' }), h('p', { text: message }),
    h('button', { type: 'button', class: 'btn btn-primary', text: 'Try again', onclick: () => location.reload() }));
}

// ------------------------------------------------------------------ render

function render() {
  const s = S;
  $('fatal').hidden = true;
  $('app').hidden = !s.onboarded;
  if (!s.onboarded) {
    if ($('onboarding').hidden) {
      renderOnboarding($('onboarding'), { symbols: s.symbols, startingCash: s.starting_cash, onStart: (choice) => act('POST', '/api/onboarding', choice) });
    }
  } else {
    $('onboarding').hidden = true;
  }
  renderTierScrub($('tierScrub'), {
    tiers: content.tiers, active: s.tier, unlocked: s.tiers_unlocked, previewTier,
    onPreview: (id) => { previewTier = id; render(); },
  });
  if (!s.onboarded) { hideSafetyNetPrompt($('safetyModal')); modalKey = null; return; }
  renderBanner();
  renderStats();
  renderChartPanel();
  renderMoneyFlow($('moneyFlow'), describeMoneyFlow(s));
  ticket.update({ state: s, tier: viewTier(), tiers: content.tiers, hints: content.hints, previewing: !!previewTier });
  renderCheckCard();
  renderOrders();
  renderFeed();
  renderControls();
  renderSafety();
}

function renderBanner() {
  const banner = $('banner');
  if (previewTier) {
    const t = tierOf(previewTier);
    banner.className = 'banner banner-preview';
    banner.replaceChildren(h('span', { text: `Previewing ${t.title}. You have not unlocked it yet: ${t.how_to_unlock}` }),
      h('button', { type: 'button', class: 'btn btn-ghost', text: 'Exit preview', onclick: () => { previewTier = null; render(); } }));
    banner.hidden = false;
  } else if (S.finished) {
    banner.className = 'banner banner-done';
    banner.replaceChildren(h('span', { text: `Replay finished. You ended with ${usd(S.equity)} (${pct(S.total_pnl_pct)}). The worst drop in this replay was ${pct(S.fixture_meta.max_drawdown_pct)}. These prices are synthetic.` }),
      h('button', { type: 'button', class: 'btn btn-primary', text: 'Play again', onclick: reset }));
    banner.hidden = false;
  } else {
    banner.hidden = true;
  }
}

const tone = (n) => (n > 0 ? 'up' : n < 0 ? 'down' : 'flat');

function renderStats() {
  const s = S;
  const pos = s.positions[0];
  $('valCash').textContent = usd(s.cash);
  $('valPosition').textContent = pos ? `${pos.qty} × ${pos.symbol}` : 'No position';
  $('subPosition').textContent = pos
    ? `Avg ${usd(pos.avg_price)} · ${pos.protected ? `safety net sells at ${usd(pos.stop_price)}` : 'no safety net'}`
    : 'Nothing at risk yet';
  $('subPosition').className = `stat-sub ${pos && !pos.protected ? 'warn' : ''}`;
  $('valEquity').textContent = usd(s.equity);
  $('subEquity').textContent = `${signedUsd(s.total_pnl)} since start (${pct(s.total_pnl_pct)})`;
  $('valPnl').textContent = signedUsd(s.unrealized_pnl);
  $('valPnl').className = `stat-value tone-${tone(s.unrealized_pnl)}`;
  $('subPnl').textContent = pos ? `${pct(s.unrealized_pnl_pct)} on your ${pos.symbol}. Paper loss until you sell.` : 'No open position';
  const shadow = $('shadowLine');
  shadow.hidden = !s.shadow.active;
  if (s.shadow.active) {
    const saved = s.shadow.saved_by_safety_net;
    $('shadowText').textContent = `Without your safety net you would have ${usd(s.shadow.equity)}: it ${saved >= 0 ? `saved you ${usd(saved)}` : `cost you ${usd(-saved)}`} so far.`;
  }
}

function renderChartPanel() {
  const s = S;
  const tier = viewTier();
  const mode = chartModeFor(content.tiers, tier);
  const overlay = strategyOverlayOn(content.tiers, tier);
  const pos = s.positions[0];
  $('chartName').textContent = `${s.symbol} · synthetic replay`;
  $('chartBadge').textContent = { line: 'Line', line_levels: 'Line + highs and lows', candles: 'Candlesticks' }[mode];
  $('chartTitle').dataset.hint = { line: 'chart.line', line_levels: 'chart.levels', candles: 'chart.candlestick' }[mode];
  $('valPrice').textContent = usd(s.price);
  $('valDay').textContent = `Day ${s.day} of ${s.total_days}`;
  $('chartLegend').hidden = !overlay;
  $('legendText').textContent = `▲ ${s.strategy.name}: fast average crossed above slow (buy signal). ▼ crossed below (sell signal).`;
  renderChart($('chart'), {
    bars: s.bars, totalDays: s.total_days, mode, entry: pos?.avg_price ?? null, stop: pos?.stop_price ?? null,
    signals: overlay ? s.strategy.signals : [],
  });
  $('chart').setAttribute('aria-label', chartSummary({ symbol: s.symbol, bars: s.bars, mode }));
}

function renderControls() {
  const off = !S?.onboarded || S.finished || S.prompts.length > 0 || busy;
  for (const id of ['btnAdv1', 'btnAdv5', 'btnFast']) $(id).disabled = off;
  $('replayNote').textContent = !S?.onboarded ? '' : S.finished ? 'The replay is over.'
    : S.prompts.length ? 'Answer the safety-net prompt to keep going.'
      : 'Fast-forward stops the moment something happens: a fill or a safety-net alert.';
}

function renderCheckCard() {
  const card = $('checkCard');
  const pending = S.pending_check;
  const id = pending ?? (lastCheck?.result?.correct ? lastCheck.id : null);
  if (!id) { card.hidden = true; return; }
  const result = lastCheck?.id === id ? lastCheck.result : null;
  card.hidden = false;
  renderCheck(card, {
    check: content.checks[id], result,
    unlockedTitle: result?.unlocked_tier ? tierOf(result.unlocked_tier).title : null,
    onSubmit: async (choice) => {
      const data = await act('POST', '/api/comprehension', { check_id: id, choice });
      if (!data) return;
      lastCheck = { id, result: data };
      if (data.unlocked_tier) notify(`Unlocked ${tierOf(data.unlocked_tier).title}`, 'good');
      render();
    },
    onDone: () => { lastCheck = null; render(); },
  });
}

const describeOrder = (o) => (o.safety_net
  ? `Safety net: sells ${o.qty} ${o.symbol} if the price falls to ${usd(o.stop_price)}`
  : `${o.type[0]}${o.type.slice(1).toLowerCase()} ${o.side.toLowerCase()}: ${o.qty} × ${o.symbol} at ${usd(o.limit_price ?? o.stop_price)}`);

function renderOrders() {
  $('ordersCard').hidden = S.open_orders.length === 0;
  $('ordersList').replaceChildren(...S.open_orders.map((o) => h('li', {},
    h('span', { text: describeOrder(o) }),
    h('button', { type: 'button', class: 'btn btn-ghost small', text: 'Cancel', onclick: () => act('DELETE', `/api/orders/${o.id}`) }))));
}

function renderFeed() {
  $('feedList').replaceChildren(...S.events.slice(-8).reverse().map((e) => h('li', { class: `ev ev-${e.type}`, text: e.message })));
}

function renderSafety() {
  const overlay = $('safetyModal');
  const c = S.prompts[0];
  if (!c) { if (modalKey) { hideSafetyNetPrompt(overlay); modalKey = null; } return; }
  const key = `${c.symbol}:${S.cursor}:${c.qty}:${c.price}`;
  if (key === modalKey) return;
  modalKey = key;
  showSafetyNetPrompt(overlay, c, {
    custom: customSafetyNetOn(content.tiers, S.tier),
    hint: getHint(content.hints, 'safety_net.prompt', S.tier),
    onAccept: (percent) => act('POST', '/api/safety-net', { symbol: c.symbol, decision: 'accept', ...(percent !== 10 ? { percent } : {}) }),
    onSell: () => act('POST', '/api/orders', { symbol: c.symbol, side: 'SELL', type: 'MARKET', qty: c.qty, as_of: S.cursor }),
    onDismiss: () => act('POST', '/api/safety-net', { symbol: c.symbol, decision: 'dismiss' }),
  });
}

// ------------------------------------------------------------------ actions

const ticket = mountTicket($('ticket'), {
  async onSubmit(payload) {
    const data = await act('POST', '/api/orders', payload);
    if (!data) throw new Error('order not placed');
    const f = data.fills[0];
    notify(f ? `${f.side === 'BUY' ? 'Bought' : 'Sold'} ${f.qty} ${f.symbol} at ${usd(f.price)}.` : 'Order placed. It waits until the price reaches it.');
  },
});

async function advance(n) {
  const data = await act('POST', '/api/advance', { n });
  const notable = data?.events.filter((e) => ['FILL', 'CANCEL', 'END'].includes(e.type)).at(-1);
  if (notable) notify(notable.message, /safety net/.test(notable.message) ? 'good' : 'info');
}

async function reset() {
  try {
    const data = await call('POST', '/api/reset');
    previewTier = null; lastCheck = null; modalKey = null;
    apply(data.state);
    notify('Demo reset. Ready for the next person.');
  } catch (e) { notify(e.message, 'bad'); }
}

/** After a server restart the browser replays the action log the server gave it, rebuilding the session. */
async function restore(log) {
  notify('The server restarted. Restoring your session…');
  try {
    for (const step of log) await call(step.method, step.path, step.body ?? undefined);
  } catch (e) {
    await call('POST', '/api/reset').catch(() => {});
    notify('Could not restore your last session, so you are starting fresh.', 'bad');
  }
  return call('GET', '/api/state');
}

async function boot() {
  try {
    const [tiers, hints, checks] = await Promise.all(['tiers.json', 'hints.json', 'checks.json']
      .map((f) => fetch(f).then((r) => { if (!r.ok) throw new Error(f); return r.json(); })));
    content = { tiers, hints, checks };
  } catch (e) {
    return showFatal(`Could not load ${e.message}. Serve the web/ folder over HTTP (see the README); opening the file directly will not work.`);
  }
  attachHintButtons(document, { getHints: () => content.hints, getTier: viewTier, pop: $('hintPop') });
  $('btnAdv1').onclick = () => advance(1);
  $('btnAdv5').onclick = () => advance(5);
  $('btnFast').onclick = () => advance(FAST_FORWARD_MAX);
  $('btnReset').onclick = reset;
  try {
    let state = await call('GET', '/api/state');
    let stored = null;
    try { stored = JSON.parse(localStorage.getItem(STORE_KEY)); } catch (_) { /* none */ }
    if (!state.onboarded && stored?.log?.length && stored.boot_id !== state.boot_id) state = await restore(stored.log);
    apply(state);
  } catch (e) {
    showFatal(e.message);
  }
}

boot();
