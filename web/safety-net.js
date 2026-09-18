/**
 * safety-net.js: the one-tap prompt shown when a position is down 8%. Copy by V1, wired in by F.
 * Every number comes from the server's candidate object, so the words can never drift from the
 * demo. buildSafetyNetPrompt is pure.
 */

import { h, mount, usd, pct } from './format.js';
import { renderHintBody } from './hint.js';

export const STOP_CHOICES = [5, 10, 15, 20];   // percent below entry, offered from Tier 2
const DEFAULT_PERCENT = 10;                     // the fixed one-tap choice at every tier

const stopFor = (c, percent) =>
  percent === DEFAULT_PERCENT ? c.stop_price : Math.round(c.avg_price * (1 - percent / 100) * 100) / 100;

/** buildSafetyNetPrompt(candidate, { percent }) -> the exact words and labels for the modal. */
export function buildSafetyNetPrompt(c, { percent = DEFAULT_PERCENT } = {}) {
  const stop = stopFor(c, percent);
  const canProtect = stop < c.price;
  const title = `Your ${c.symbol} position is down ${Math.abs(c.loss_pct).toFixed(1)}%`;
  const body = `You bought ${c.qty} ${c.symbol} at ${usd(c.avg_price)}. It is now ${usd(c.price)}, so you are down ${usd(-c.loss_dollars)} (${pct(c.loss_pct)}). Prices can keep falling.`;
  if (canProtect) {
    return {
      title, body, canProtect, stop,
      callout: `If ${c.symbol} falls to ${usd(stop)} (${percent}% below your entry), your shares are sold automatically. That caps this loss at ${usd((c.avg_price - stop) * c.qty)}. If it dips there and bounces back, you will have sold at the bottom.`,
      primary: `Protect my position (sell at ${usd(stop)})`,
      secondary: 'Keep holding (accept the full risk)',
    };
  }
  return {
    title, body, canProtect, stop,
    callout: `${c.symbol} has already fallen past the ${percent}% safety line (${usd(stop)}), so a safety net would sell immediately. You can sell now to stop the loss growing, or keep holding and accept the risk.`,
    primary: `Sell my ${c.qty} shares now (${usd(c.price)} each)`,
    secondary: 'Keep holding (accept the full risk)',
  };
}

/** Shows the modal. Handlers: onAccept(percent), onSell(), onDismiss(). `custom` adds the % picker (Tier 2+). */
export function showSafetyNetPrompt(overlay, candidate, { custom, hint, onAccept, onSell, onDismiss }) {
  let percent = DEFAULT_PERCENT;
  const card = h('div', { class: 'modal-card', role: 'document' });
  const hintBox = h('div', { class: 'hint-box' });
  if (hint) renderHintBody(hintBox, hint);

  const draw = () => {
    const copy = buildSafetyNetPrompt(candidate, { percent });
    const picker = custom
      ? h('label', { class: 'field' }, h('span', { text: 'How far may it fall before I sell?' }),
          h('select', { id: 'stopPercent', onchange: (e) => { percent = Number(e.target.value); draw(); } },
            STOP_CHOICES.map((p) => h('option', { value: p, selected: p === percent ? true : null }, `${p}% below my entry`))))
      : null;
    mount(card,
      h('span', { class: 'modal-badge', text: 'Downside alert' }),
      h('h2', { id: 'snTitle', text: copy.title }),
      h('p', { class: 'modal-body', text: copy.body }),
      picker,
      h('div', { class: 'modal-callout' }, h('p', { text: copy.callout })),
      h('div', { class: 'modal-actions' },
        h('button', { type: 'button', id: 'btnProtect', class: 'btn btn-primary',
                      onclick: () => (copy.canProtect ? onAccept(percent) : onSell()), text: copy.primary }),
        h('button', { type: 'button', id: 'btnKeepHolding', class: 'btn btn-ghost', onclick: onDismiss, text: copy.secondary })),
      hintBox);
  };
  draw();
  mount(overlay, card);
  overlay.hidden = false;
  overlay.querySelector('#btnProtect')?.focus();
}

export function hideSafetyNetPrompt(overlay) {
  overlay.hidden = true;
  overlay.replaceChildren();
}
