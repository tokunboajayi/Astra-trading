/**
 * tier-picker.js: onboarding, the tier scrub (preview what you unlock) and tier helpers. Owned by V2.
 * The helpers are pure and read the same tiers.json the server enforces, so what the screen
 * offers and what the server allows can only disagree if someone edits one side.
 */

import { h, mount, usd } from './format.js';

const find = (tiers, id) => tiers.find((t) => t.id === id);

export const orderTypeAllowed = (tiers, tierId, type) => !!find(tiers, tierId)?.unlocks.order_types.includes(type);
export const chartModeFor = (tiers, tierId) => find(tiers, tierId)?.unlocks.chart ?? 'line';
export const strategyOverlayOn = (tiers, tierId) => !!find(tiers, tierId)?.unlocks.strategy_overlay;
export const customSafetyNetOn = (tiers, tierId) => !!find(tiers, tierId)?.unlocks.custom_safety_net;
export const tierNumber = (tiers, tierId) => tiers.findIndex((t) => t.id === tierId) + 1;
/** The first tier that allows an order type (where a locked option says it unlocks). */
export const firstTierAllowing = (tiers, type) => tiers.find((t) => t.unlocks.order_types.includes(type));
export const shortName = (tier) => tier.title.replace(/^Tier \d+:\s*/, '');

/** Three buttons. Locked tiers are a preview: tap to look, tap again to leave. */
export function renderTierScrub(nav, { tiers, active, unlocked, previewTier, onPreview }) {
  mount(nav,
    h('span', { class: 'scrub-label', text: 'Tiers' }),
    tiers.map((t, i) => {
      const locked = !unlocked.includes(t.id);
      const state = t.id === active ? 'active' : locked ? 'locked' : 'done';
      return h('button', {
        type: 'button', 'data-tier': t.id, 'aria-pressed': String(t.id === (previewTier ?? active)),
        class: `tier-chip is-${state}${t.id === previewTier ? ' is-previewing' : ''}`,
        title: locked ? `Preview what unlocks at ${t.title}` : t.title,
        onclick: () => onPreview(locked && t.id !== previewTier ? t.id : null),
      }, `${i + 1}. ${shortName(t)}`, locked ? h('span', { class: 'chip-note', text: 'preview' }) : null);
    }),
  );
}

/** The welcome card. onStart({ experience, symbol }). */
export function renderOnboarding(overlay, { symbols, startingCash, onStart }) {
  const fallback = symbols[0]?.symbol;
  const radio = (name, value, checked, label, sub) => h('label', { class: 'choice' },
    h('input', { type: 'radio', name, value, checked: checked ? true : null }),
    h('span', { class: 'choice-body' }, h('strong', { text: label }), sub ? h('small', { text: sub }) : null));

  // Read what the form ACTUALLY holds at submit. Tracking the selection in a closure via
  // onchange desynced whenever a radio was checked by any route that does not fire change,
  // and the screen then disagreed with the request.
  const submit = (e) => {
    e.preventDefault();
    const picked = new FormData(e.target);
    onStart({ experience: picked.get('experience') || 'new', symbol: picked.get('symbol') || fallback });
  };

  mount(overlay, h('form', { class: 'modal-card onboarding', onsubmit: submit },
    h('h2', { id: 'obTitle', text: 'Learn what you could lose first' }),
    h('p', { class: 'modal-body', text: 'Most trading apps sell you the upside. Rich-HER shows the downside first. You get pretend money and a price replay where the future is hidden - nothing here is real and nothing can follow you home.' }),
    h('fieldset', {}, h('legend', { text: 'How much have you invested before?' }),
      radio('experience', 'new', true, "I'm brand new", 'Start at Tier 1: Foundation'),
      radio('experience', 'experienced', false, "I've traded before", 'Start at Tier 2: Tactical Protection')),
    h('fieldset', {}, h('legend', { text: 'Pick something to practice on' }),
      h('div', { class: 'choice-grid' }, symbols.map((s, i) => radio('symbol', s.symbol, i === 0,
        `${s.symbol} · ${usd(s.start_cash ?? startingCash)} to practise with`,
        i === 0 ? `Recommended. ${s.blurb}` : s.blurb)))),
    h('button', { type: 'submit', id: 'btnStart', class: 'btn btn-primary', text: 'Start the replay' }),
    h('p', { class: 'fineprint', text: 'Prices are synthetic replay data, not real market prices. This is an educational simulator, not financial advice.' })));
  overlay.hidden = false;
  overlay.querySelector('#btnStart')?.focus();
}
