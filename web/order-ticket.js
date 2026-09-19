/**
 * order-ticket.js: the Tap-to-Explain order ticket. Owned by F.
 * Tap Buy or Sell -> the ticket opens with the downside first and Confirm locked for 1.5 s ->
 * adjust quantity and watch "most you could lose" -> Confirm executes. Changing the order type
 * re-locks Confirm because the downside just changed. maxPotentialLoss is pure.
 */

import { h, usd } from './format.js';
import { getHint, renderHintBody } from './hint.js';
import { orderTypeAllowed, firstTierAllowing, tierNumber } from './tier-picker.js';

export const CONFIRM_LOCK_MS = 1500;

const TYPES = [
  ['MARKET', 'Market: buy or sell now'],
  ['LIMIT', 'Limit: only at my price or better'],
  ['STOP', 'Stop: sell if the price falls to my level'],
];

/** The worst case for this order, in plain numbers: { label, amount, note }. */
export function maxPotentialLoss({ side, type, qty, price, limitPrice, stopPrice, position }) {
  if (side === 'BUY') {
    const amount = qty * (type === 'LIMIT' ? limitPrice : price);
    return { label: 'Most you could lose on this order', amount,
      note: `That is if the price fell to zero. A 10% fall would cost about ${usd(amount * 0.1)}.` };
  }
  const label = type === 'STOP' ? 'Loss if your stop triggers' : 'Loss you lock in by selling';
  if (!position) return { label, amount: 0, note: 'You do not hold any shares to sell.' };
  const unit = type === 'LIMIT' ? limitPrice : type === 'STOP' ? stopPrice : price;
  const loss = (position.avg_price - unit) * qty;
  return loss > 0
    ? { label, amount: loss, note: 'Selling makes this loss permanent.' }
    : { label, amount: 0, note: `${usd(unit)} is above your ${usd(position.avg_price)} entry, so no loss is locked in. If the price keeps rising you miss out.` };
}


/** A starting quantity that fits the account: about half of it, never more than 10.
 *  A fixed default of 10 is unaffordable on the $100 story account ($210 of a $21 share),
 *  so the first thing a new user saw was an error. Half the account also quietly models
 *  the sizing lesson instead of pushing her all in. */
export function defaultQty(cash, price) {
  if (!(price > 0)) return 1;
  return Math.max(1, Math.min(10, Math.floor(cash / price / 2)));
}

const actionFor = (side, type) => (type === 'LIMIT' ? 'order.limit' : type === 'STOP' ? 'order.stop' : side === 'BUY' ? 'order.buy' : 'order.sell');

/** mountTicket(root, { onSubmit(payload) -> Promise }) -> { update(ctx) }.
 *  ctx = { state, tier, tiers, hints, previewing }. tier is the tier being shown (may be a preview). */
export function mountTicket(root, { onSubmit }) {
  const ui = { mode: 'idle', side: 'BUY', type: 'MARKET', locked: false, busy: false, timer: null, ctx: null };

  const field = (text, input) => h('label', { class: 'field' }, h('span', { text }), input);
  const btnBuy = h('button', { type: 'button', id: 'btnBuy', class: 'btn side side-buy', text: 'Buy', onclick: () => open('BUY') });
  const btnSell = h('button', { type: 'button', id: 'btnSell', class: 'btn side side-sell', text: 'Sell', onclick: () => open('SELL') });
  const selType = h('select', { id: 'ticketType', onchange: onTypeChange },
    TYPES.map(([value, label]) => h('option', { value, text: label })));
  const inQty = h('input', { id: 'ticketQty', type: 'number', min: 1, step: 1, inputmode: 'numeric', oninput: refresh });
  const inLimit = h('input', { id: 'ticketLimit', type: 'number', min: 0.01, step: 0.01, oninput: refresh });
  const inStop = h('input', { id: 'ticketStop', type: 'number', min: 0.01, step: 0.01, oninput: refresh });
  const rowLimit = field('Limit price ($)', inLimit);
  const rowStop = field('Stop price ($)', inStop);
  const hintBox = h('div', { class: 'hint-box', id: 'ticketHint' });
  const lossLine = h('p', { class: 'loss-line', id: 'ticketLoss' });
  const estimate = h('p', { class: 'estimate', id: 'ticketEstimate' });
  const btnConfirm = h('button', { type: 'button', id: 'btnConfirm', class: 'btn btn-primary confirm', onclick: confirm });
  const btnCancel = h('button', { type: 'button', id: 'btnCancelTicket', class: 'btn btn-ghost', text: 'Cancel', onclick: cancel });
  const riskBox = h('div', { class: 'risk-box', id: 'ticketRisk', hidden: true },
    h('h4', { text: 'Downside first' }), hintBox, lossLine);
  const actions = h('div', { class: 'ticket-actions', hidden: true }, btnConfirm, btnCancel);
  const previewNote = h('p', { class: 'preview-note', hidden: true, text: 'Preview only. Unlock this tier to place these orders.' });
  const form = h('fieldset', { class: 'ticket-form' },
    h('div', { class: 'side-tabs' }, btnBuy, btnSell),
    field('Order type', selType), field('Quantity (shares)', inQty), rowLimit, rowStop, riskBox, estimate, actions);

  root.replaceChildren(
    h('h2', {}, 'Order ticket ', h('span', { class: 'badge', text: 'Tap to explain' })), previewNote, form);

  function startLock() {
    clearTimeout(ui.timer);
    ui.locked = true;
    btnConfirm.style.setProperty('--lock-ms', `${CONFIRM_LOCK_MS}ms`);
    btnConfirm.classList.remove('locking');
    void btnConfirm.offsetWidth;                       // restart the CSS animation
    btnConfirm.classList.add('locking');
    ui.timer = setTimeout(() => { ui.locked = false; btnConfirm.classList.remove('locking'); refresh(); }, CONFIRM_LOCK_MS);
  }

  function open(side) {
    if (ui.mode === 'review' && ui.side === side) return;
    ui.side = side;
    ui.mode = 'review';
    if (side === 'BUY' && ui.type === 'STOP') ui.type = 'MARKET';
    selType.value = ui.type;
    startLock();
    refresh();
  }

  function cancel() {
    clearTimeout(ui.timer);
    ui.mode = 'idle';
    ui.locked = false;
    refresh();
  }

  function onTypeChange() {
    ui.type = selType.value;
    const price = ui.ctx?.state.price;
    if (price && ui.type === 'LIMIT' && !inLimit.value) inLimit.value = price.toFixed(2);
    if (price && ui.type === 'STOP' && !inStop.value) inStop.value = (price * 0.95).toFixed(2);
    if (ui.mode === 'review') startLock();
    refresh();
  }

  function payload() {
    const p = { symbol: ui.ctx.state.symbol, side: ui.side, type: ui.type, qty: Number(inQty.value), as_of: ui.ctx.state.cursor };
    if (ui.type === 'LIMIT') p.limit_price = Number(inLimit.value);
    if (ui.type === 'STOP') p.stop_price = Number(inStop.value);
    return p;
  }

  async function confirm() {
    if (ui.locked || ui.busy) return;
    ui.busy = true;
    refresh();
    try {
      await onSubmit(payload());
      ui.mode = 'idle';
    } catch (_) { /* the app already showed the reason; keep the ticket open so it can be fixed */ }
    ui.busy = false;
    refresh();
  }

  function refresh() {
    const c = ui.ctx;
    if (!c) return;
    const { state: s, tier, tiers, hints, previewing } = c;
    const review = ui.mode === 'review' && !previewing && s.onboarded;
    const position = s.positions[0] ?? null;

    for (const opt of selType.options) {
      const allowed = orderTypeAllowed(tiers, tier, opt.value);
      const sellOnly = opt.value === 'STOP' && review && ui.side === 'BUY';
      const base = TYPES.find(([v]) => v === opt.value)[1];
      opt.disabled = !allowed || sellOnly;
      opt.textContent = !allowed ? `${base} (unlocks at Tier ${tierNumber(tiers, firstTierAllowing(tiers, opt.value).id)})` : sellOnly ? `${base} (sell only)` : base;
    }
    if (!orderTypeAllowed(tiers, tier, ui.type)) { ui.type = 'MARKET'; }
    selType.value = ui.type;
    rowLimit.hidden = ui.type !== 'LIMIT';
    rowStop.hidden = ui.type !== 'STOP';

    root.classList.toggle('is-preview', !!previewing);
    previewNote.hidden = !previewing;
    form.disabled = !!previewing || !s.onboarded;
    btnBuy.classList.toggle('is-active', review && ui.side === 'BUY');
    btnSell.classList.toggle('is-active', review && ui.side === 'SELL');
    riskBox.hidden = !review;
    actions.hidden = !review;

    const qty = Number(inQty.value);
    const price = s.price ?? 0;
    const limitPrice = Number(inLimit.value);
    const stopPrice = Number(inStop.value);
    const valid = Number.isInteger(qty) && qty >= 1
      && (ui.type !== 'LIMIT' || limitPrice > 0) && (ui.type !== 'STOP' || stopPrice > 0);
    const unit = ui.type === 'LIMIT' ? limitPrice : ui.type === 'STOP' ? stopPrice : price;
    estimate.textContent = valid ? `${ui.side === 'BUY' ? 'Estimated cost' : 'Estimated proceeds'}: ${usd(qty * unit)}` : 'Enter a whole number of shares.';

    if (review) {
      renderHintBody(hintBox, getHint(hints, actionFor(ui.side, ui.type), tier));
      const loss = maxPotentialLoss({ side: ui.side, type: ui.type, qty, price, limitPrice, stopPrice, position });
      lossLine.replaceChildren(`${loss.label}: `, h('strong', { text: usd(loss.amount) }), h('small', { text: ` ${loss.note}` }));
    }
    btnConfirm.disabled = ui.locked || ui.busy || !valid;
    btnConfirm.textContent = ui.busy ? 'Placing order…' : ui.locked ? 'Read the risk above…'
      : `Confirm ${ui.side.toLowerCase()} · ${valid ? qty : '?'} share${qty === 1 ? '' : 's'}`;
  }

  return {
    update(ctx) {
      ui.ctx = ctx;
      // Seed the quantity from the account the first time we see a live replay, and never
      // again - after that it is whatever the user typed.
      if (!ui.seeded && ctx.state?.onboarded && ctx.state.price > 0) {
        inQty.value = String(defaultQty(ctx.state.cash, ctx.state.price));
        ui.seeded = true;
      }
      if (ctx.previewing) ui.mode = 'idle';
      refresh();
    },
  };
}
