/**
 * format.js: number formatting and a tiny DOM builder shared by every module. Owned by F.
 * Imported by pure modules too, so nothing here touches `document` at import time.
 */

const USD = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
const sign = (n) => (n > 0 ? '+' : n < 0 ? '−' : '');

export const usd = (n) => USD.format(n);
export const signedUsd = (n) => sign(n) + USD.format(Math.abs(n));
export const pct = (n, digits = 1) => `${sign(n)}${Math.abs(n).toFixed(digits)}%`;

/** Replaces parent's children. Unlike replaceChildren, it flattens arrays and skips null/false
 *  (replaceChildren would print the word "null" and stringify arrays). */
export function mount(parent, ...kids) {
  parent.replaceChildren(...kids.flat().filter((kid) => kid != null && kid !== false));
}

/** h('div', { class: 'x', onclick }, 'text', childNode) -> HTMLElement. Text is never parsed as HTML. */
export function h(tag, attrs = {}, ...kids) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value == null || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? '' : value);
  }
  for (const kid of kids.flat()) if (kid != null && kid !== false) node.append(kid);
  return node;
}
