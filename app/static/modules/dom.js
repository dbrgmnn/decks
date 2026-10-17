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
  return typeof data.detail === 'string' ? data.detail : 'Invalid input';
};

// Keep the browser/status-bar chrome in step with the chosen theme.
export const syncThemeColor = () => {
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = root.dataset.theme === 'dark' ? '#111' : '#f4f4f0';
};

export const TRASH_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14M10 11v6M14 11v6"/></svg>';

const ARROW_PATHS = {
  up: '<path d="M12 5.5v13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/><path d="M5.5 12 12 5.5 18.5 12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>',
  down: '<path d="M12 5.5v13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/><path d="M5.5 12 12 18.5 18.5 12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>',
  left: '<path d="M5.5 12h13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/><path d="M12 5.5 5.5 12 12 18.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>',
  right: '<path d="M5.5 12h13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/><path d="M12 5.5 18.5 12 12 18.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>',
};

// Move arrows used while reordering decks and folders.
export const arrowSvg = axis => `<svg viewBox="0 0 24 24" aria-hidden="true">${ARROW_PATHS[axis] || ARROW_PATHS.right}</svg>`;
