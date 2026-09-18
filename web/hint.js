/**
 * hint.js: tap-to-explain hints and the comprehension check. Owned by V1.
 * Every hint is downside-first: [What you could lose]. [What it does].
 * getHint is pure; the rest builds DOM.
 */

import { h, mount } from './format.js';

export const TIER_ORDER = ['beginner', 'intermediate', 'advanced'];

const GENERIC = {
  downside: 'Any investment can lose value, and you could lose some or all of the money you put in.',
  text: 'No plain-English explanation has been written for this yet.',
};

/** getHint(hints, actionId, tier) -> { downside, text, more? }.
 *  Falls back to the nearest lower tier, then the nearest higher one, then a generic downside. */
export function getHint(hints, actionId, tier = 'beginner') {
  const at = Math.max(0, TIER_ORDER.indexOf(tier));
  const order = [...TIER_ORDER.slice(0, at + 1).reverse(), ...TIER_ORDER.slice(at + 1)];
  for (const t of order) {
    const hit = hints?.[`${actionId}.${t}`];
    if (hit) return hit;
  }
  return GENERIC;
}

/** Fills `container` with the downside (amber), the purpose and the optional extra. */
export function renderHintBody(container, hint) {
  mount(container,
    h('p', { class: 'hint-downside', text: hint.downside }),
    h('p', { class: 'hint-text', text: hint.text }),
    hint.more ? h('p', { class: 'hint-more', text: hint.more }) : null);
}

/** Adds an (i) button next to every [data-hint="actionId"] element. The popover reads the
 *  attribute and the tier at click time, so it always matches what is on screen. */
export function attachHintButtons(root, { getHints, getTier, pop }) {
  const close = () => { pop.hidden = true; pop.dataset.for = ''; };
  root.querySelectorAll('[data-hint]').forEach((host) => {
    if (host.dataset.hintReady) return;
    host.dataset.hintReady = '1';
    const btn = h('button', { type: 'button', class: 'info', 'aria-label': 'Explain this in plain English', text: 'i' });
    btn.addEventListener('click', (event) => {
      event.stopPropagation();
      if (!pop.hidden && pop.dataset.for === host.dataset.hint) return close();
      renderHintBody(pop, getHint(getHints(), host.dataset.hint, getTier()));
      pop.dataset.for = host.dataset.hint;
      pop.hidden = false;
      const r = btn.getBoundingClientRect();
      pop.style.top = `${window.scrollY + r.bottom + 8}px`;
      pop.style.left = `${Math.max(8, Math.min(window.scrollX + r.left - 8, window.innerWidth - pop.offsetWidth - 8))}px`;
    });
    host.append(' ', btn);
  });
  document.addEventListener('click', (e) => { if (!pop.contains(e.target)) close(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
}

/** The quick comprehension check. `result` is the last answer for this check, or null. */
export function renderCheck(container, { check, result, unlockedTitle, onSubmit, onDone }) {
  const head = [h('h3', { text: check.title }), h('p', { class: 'check-q', text: check.prompt })];
  if (result?.correct) {
    mount(container, head,
      h('p', { class: 'check-result good', text: result.explanation }),
      unlockedTitle ? h('p', { class: 'check-unlock', text: `Unlocked: ${unlockedTitle}` }) : null,
      h('button', { type: 'button', class: 'btn btn-ghost', text: 'Got it', onclick: onDone }));
    return;
  }
  const options = check.options.map((label, i) => h('label', { class: 'check-option' },
    h('input', { type: 'radio', name: 'choice', value: String(i), required: true }), h('span', { text: label })));
  const form = h('form', { class: 'check-form' },
    h('fieldset', {}, h('legend', { class: 'sr-only', text: check.prompt }), options),
    result ? h('p', { class: 'check-result bad', text: result.explanation }) : null,
    h('button', { type: 'submit', class: 'btn btn-primary', text: result ? 'Try again' : 'Check my answer' }));
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const picked = form.querySelector('input[name="choice"]:checked');
    if (picked) onSubmit(Number(picked.value));
  });
  mount(container, head, form);
}
