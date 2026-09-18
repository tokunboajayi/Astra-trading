/**
 * chart.js: the SVG price chart (line, line + highs/lows, candlesticks). Owned by F.
 * It only ever draws the bars it is given, and the server only sends bars up to today, so the
 * future is never on screen. The y-axis is fitted to what is visible for the same reason.
 * makeScale/niceStep are pure; renderChart writes SVG markup with numeric values only.
 */

import { usd } from './format.js';

export const VIEW = { w: 800, h: 340, l: 60, r: 24, t: 18, b: 34 };

export function niceStep(range, target = 5) {
  const raw = range / target;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const n = raw / mag;
  return (n < 1.5 ? 1 : n < 3 ? 2 : n < 7 ? 5 : 10) * mag;
}

/** Scales for the visible bars. x is fixed to the whole replay length so the line grows rightward. */
export function makeScale(bars, totalDays, extras = []) {
  let lo = Math.min(...bars.map((b) => b.l), ...extras);
  let hi = Math.max(...bars.map((b) => b.h), ...extras);
  const pad = (hi - lo || hi * 0.02) * 0.1;
  lo -= pad;
  hi += pad;
  const step = niceStep(hi - lo);
  const x = (i) => VIEW.l + (i / Math.max(1, totalDays - 1)) * (VIEW.w - VIEW.l - VIEW.r);
  const y = (p) => VIEW.h - VIEW.b - ((p - lo) / (hi - lo)) * (VIEW.h - VIEW.t - VIEW.b);
  const ticks = [];
  for (let p = Math.ceil(lo / step) * step; p <= hi; p += step) ticks.push(Math.round(p * 100) / 100);
  return { x, y, lo, hi, step, ticks };
}

const f = (n) => n.toFixed(1);

/** Text alternative for screen readers. */
export function chartSummary({ symbol, bars, mode }) {
  const last = bars[bars.length - 1];
  const kind = { line: 'line chart', line_levels: 'line chart with highs and lows', candles: 'candlestick chart' }[mode] ?? 'chart';
  return last ? `${symbol} ${kind}, day ${last.day}, last close ${usd(last.c)}. Days after today are hidden.` : `${symbol} chart`;
}

/** renderChart(svg, { bars, totalDays, mode, entry, stop, signals }). mode: line | line_levels | candles. */
export function renderChart(svg, { bars, totalDays, mode = 'line', entry = null, stop = null, signals = [] }) {
  svg.setAttribute('viewBox', `0 0 ${VIEW.w} ${VIEW.h}`);
  if (!bars.length) { svg.replaceChildren(); return; }
  const s = makeScale(bars, totalDays, [entry, stop].filter((v) => v != null));
  const right = VIEW.w - VIEW.r;
  const bottom = VIEW.h - VIEW.b;
  const lastX = s.x(bars.length - 1);
  const last = bars[bars.length - 1];
  const out = [];

  for (const p of s.ticks) {
    out.push(`<line class="grid" x1="${VIEW.l}" x2="${right}" y1="${f(s.y(p))}" y2="${f(s.y(p))}"/>`,
      `<text class="axis" x="${VIEW.l - 8}" y="${f(s.y(p) + 4)}" text-anchor="end">$${p.toFixed(s.step >= 1 ? 0 : 2)}</text>`);
  }
  for (let d = 1; d <= totalDays; d += 15) {
    out.push(`<text class="axis" x="${f(s.x(d - 1))}" y="${bottom + 20}" text-anchor="middle">Day ${d}</text>`);
  }
  if (lastX < right - 60) {
    out.push(`<rect class="future" x="${f(lastX)}" y="${VIEW.t}" width="${f(right - lastX)}" height="${bottom - VIEW.t}"/>`,
      `<text class="future-label" x="${f((lastX + right) / 2)}" y="${f((VIEW.t + bottom) / 2)}" text-anchor="middle">The future is hidden</text>`);
  }

  if (mode === 'candles') {
    const w = Math.max(2, Math.min(9, ((VIEW.w - VIEW.l - VIEW.r) / totalDays) * 0.62));
    for (const [i, b] of bars.entries()) {
      const up = b.c >= b.o;
      const x = s.x(i);
      out.push(`<line class="${up ? 'wick-up' : 'wick-down'}" x1="${f(x)}" x2="${f(x)}" y1="${f(s.y(b.h))}" y2="${f(s.y(b.l))}"/>`,
        `<rect class="${up ? 'body-up' : 'body-down'}" x="${f(x - w / 2)}" y="${f(Math.min(s.y(b.o), s.y(b.c)))}" width="${f(w)}" height="${f(Math.max(1.5, Math.abs(s.y(b.o) - s.y(b.c))))}"/>`);
    }
  } else {
    const pts = bars.map((b, i) => `${f(s.x(i))} ${f(s.y(b.c))}`);
    out.push(`<path class="area" d="M ${f(s.x(0))} ${bottom} L ${pts.join(' L ')} L ${f(lastX)} ${bottom} Z"/>`,
      `<path class="line" d="M ${pts.join(' L ')}"/>`);
  }

  if (mode === 'line_levels' && bars.length >= 3) {
    const hi = Math.max(...bars.map((b) => b.c));
    const lo = Math.min(...bars.map((b) => b.c));
    out.push(`<line class="level" x1="${VIEW.l}" x2="${right}" y1="${f(s.y(hi))}" y2="${f(s.y(hi))}"/>`,
      `<text class="level-label" x="${right}" y="${f(s.y(hi) - 5)}" text-anchor="end">High so far ${usd(hi)}</text>`,
      `<line class="level" x1="${VIEW.l}" x2="${right}" y1="${f(s.y(lo))}" y2="${f(s.y(lo))}"/>`,
      `<text class="level-label" x="${right}" y="${f(s.y(lo) + 14)}" text-anchor="end">Low so far ${usd(lo)}</text>`);
  }

  for (const g of signals) {
    const b = bars[g.bar];
    if (!b) continue;
    const x = s.x(g.bar);
    out.push(g.side === 'BUY'
      ? `<polygon class="sig-buy" points="${f(x)},${f(s.y(b.l) + 4)} ${f(x - 6)},${f(s.y(b.l) + 15)} ${f(x + 6)},${f(s.y(b.l) + 15)}"><title>Buy signal, day ${g.day}</title></polygon>`
      : `<polygon class="sig-sell" points="${f(x)},${f(s.y(b.h) - 4)} ${f(x - 6)},${f(s.y(b.h) - 15)} ${f(x + 6)},${f(s.y(b.h) - 15)}"><title>Sell signal, day ${g.day}</title></polygon>`);
  }

  if (entry != null) {
    out.push(`<line class="entry" x1="${VIEW.l}" x2="${right}" y1="${f(s.y(entry))}" y2="${f(s.y(entry))}"/>`,
      `<text class="entry-label" x="${VIEW.l + 6}" y="${f(s.y(entry) - 5)}">Your entry ${usd(entry)}</text>`);
  }
  if (stop != null) {
    out.push(`<line class="stop" x1="${VIEW.l}" x2="${right}" y1="${f(s.y(stop))}" y2="${f(s.y(stop))}"/>`,
      `<text class="stop-label" x="${VIEW.l + 6}" y="${f(s.y(stop) + 14)}">Safety net ${usd(stop)}</text>`);
  }

  const labelLeft = lastX > VIEW.w - 130;
  out.push(`<line class="cursor" x1="${f(lastX)}" x2="${f(lastX)}" y1="${VIEW.t}" y2="${bottom}"/>`,
    `<circle class="cursor-dot" cx="${f(lastX)}" cy="${f(s.y(last.c))}" r="5.5"/>`,
    `<text class="cursor-label" x="${f(lastX + (labelLeft ? -10 : 10))}" y="${f(s.y(last.c) - 10)}" text-anchor="${labelLeft ? 'end' : 'start'}">Day ${last.day} · ${usd(last.c)}</text>`);
  svg.innerHTML = out.join('');
}
