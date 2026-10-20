import {t} from './i18n.js';

export const $ = selector => document.querySelector(selector);
export const root = document.documentElement;

export const el = (tag, text = '', cls = '') => {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (cls) node.className = cls;
  return node;
};

export const errText = async response => {
  const data = await response.json().catch(() => ({}));
  return typeof data.detail === 'string' ? data.detail : t('common.invalid_input');
};

// Keep the browser/status-bar chrome in step with the chosen theme.
export const syncThemeColor = () => {
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = root.dataset.theme === 'dark' ? '#111' : '#f4f4f0';
};

export const TRASH_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14M10 11v6M14 11v6"/></svg>';

export const insideRect = (rect, x, y) => (
  x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom
);

// Where a dragged item should land relative to the item under the pointer.
// The dead zone around the centre prevents the two slots from flickering when
// the layout shifts under a finger that has not moved.
export const afterCenterX = (rect, x, margin = 12) => {
  const dx = x - (rect.left + rect.width / 2);
  return Math.abs(dx) < margin ? null : dx > 0;
};

export const afterCenterY = (rect, y, margin = 12) => {
  const dy = y - (rect.top + rect.height / 2);
  return Math.abs(dy) < margin ? null : dy > 0;
};
