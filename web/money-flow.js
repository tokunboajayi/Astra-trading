/**
 * money-flow.js: the one-line "where is my money" report. Owned by V1.
 * describeMoneyFlow is pure (state in, words out); it always leads with what can be lost.
 */

import { h, mount, usd, signedUsd, pct } from './format.js';

/** describeMoneyFlow(state) -> { tone, headline, detail, note, segments }.
 *  tone is 'flat' | 'up' | 'down' | 'protected'. */
export function describeMoneyFlow(s) {
  const pos = s.positions?.[0];
  if (pos) {
    const pnl = pos.unrealized_pnl;
    const detail = pnl < 0
      ? `You are down ${usd(-pnl)} (${pct(pos.unrealized_pnl_pct)}): ${pos.symbol} is ${usd(pos.avg_price - pos.price)} a share below your ${usd(pos.avg_price)} entry.`
      : pnl > 0
        ? `You are up ${usd(pnl)} on paper. A fall back to your ${usd(pos.avg_price)} entry would erase it.`
        : `A 10% fall from here would cost about ${usd(pos.market_value * 0.1)}.`;
    return {
      tone: pnl < 0 ? 'down' : pnl > 0 ? 'up' : 'flat',
      headline: `${usd(pos.market_value)} of your ${usd(s.equity)} is in ${pos.symbol}, and that part can lose value.`,
      detail,
      note: pos.protected
        ? `Safety net on: it sells at ${usd(pos.stop_price)}, capping this position's loss near ${usd((pos.avg_price - pos.stop_price) * pos.qty)}.`
        : null,
      segments: [{ label: 'Cash', value: s.cash, kind: 'cash' }, { label: `${pos.symbol} shares`, value: pos.market_value, kind: 'stock' }],
    };
  }
  const net = [...(s.trades ?? [])].reverse().find((t) => t.reason === 'SAFETY_NET');
  if (net && s.shadow?.active) {
    const saved = s.shadow.saved_by_safety_net;
    return {
      tone: saved > 0 ? 'protected' : 'down',
      headline: net.realized_pnl < 0
        ? `Your safety net sold ${net.qty} ${net.symbol} at ${usd(net.price)}, locking in a ${usd(-net.realized_pnl)} loss.`
        : `Your safety net sold ${net.qty} ${net.symbol} at ${usd(net.price)}, locking in a ${usd(net.realized_pnl)} gain.`,
      detail: saved > 0
        ? `Had you kept those shares you would be ${usd(saved)} worse off today.`
        : saved < 0
          ? `Had you kept those shares you would be ${usd(-saved)} better off today. That gap is the price of protection.`
          : 'Keeping those shares would have left you in the same place today.',
      note: null,
      segments: [{ label: 'Cash', value: s.cash, kind: 'cash' }],
    };
  }
  if ((s.trades ?? []).length) {
    return {
      tone: s.total_pnl < 0 ? 'down' : s.total_pnl > 0 ? 'up' : 'flat',
      headline: `You are all in cash: ${usd(s.cash)}, ${signedUsd(s.total_pnl)} since you started.`,
      detail: 'Nothing is at risk right now, and nothing can grow either.',
      note: null,
      segments: [{ label: 'Cash', value: s.cash, kind: 'cash' }],
    };
  }
  return {
    tone: 'flat',
    headline: `You have ${usd(s.cash)} in cash. Nothing is at risk yet.`,
    detail: 'Every share you buy can lose value, so decide how much you could stand to lose first.',
    note: null,
    segments: [{ label: 'Cash', value: s.cash, kind: 'cash' }],
  };
}

export function renderMoneyFlow(container, flow) {
  container.className = `money-flow tone-${flow.tone}`;
  mount(container,
    h('div', { class: 'mf-bar', role: 'img', 'aria-label': flow.segments.map((g) => `${g.label} ${usd(g.value)}`).join(', ') },
      flow.segments.map((g) => h('span', { class: `mf-seg mf-${g.kind}`, style: `flex-grow:${Math.max(g.value, 1)}` }, `${g.label} ${usd(g.value)}`))),
    h('p', { class: 'mf-headline', text: flow.headline }),
    h('p', { class: 'mf-detail', text: flow.detail }),
    flow.note ? h('p', { class: 'mf-note', text: flow.note }) : null);
}
