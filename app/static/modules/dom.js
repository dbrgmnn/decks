export const $ = s => document.querySelector(s);
export const root = document.documentElement;
export const el = (tag, text = '', cls = '') => {
  const node = document.createElement(tag);
  node.textContent = text;
  if (cls) node.className = cls;
  return node;
};

export const errText = async r => {
  const data = await r.json().catch(() => ({}));
  return typeof data.detail === 'string' ? data.detail : 'Invalid input';
};

export const TRASH_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14M10 11v6M14 11v6"/></svg>';
