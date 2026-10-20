// Interface translations shared with the server. The catalog is embedded in
// the page as JSON (see _head.html), so there is no extra request and no flash
// of untranslated text. Card and deck text is never translated.

const node = typeof document !== 'undefined' ? document.getElementById('i18n') : null;
let catalog = {};
try {
  catalog = node ? JSON.parse(node.textContent) : {};
} catch {
  catalog = {};
}

export const lang = () => catalog.__lang || 'en';
export const locale = () => catalog.__locale || lang();

const fill = (text, vars) => text.replace(/\{(\w+)\}/g, (match, name) => (
  vars[name] === undefined || vars[name] === null ? match : String(vars[name])
));

export const t = (key, vars = {}) => {
  const value = catalog[key];
  if (typeof value === 'string') return fill(value, vars);
  // A plural entry used without a count falls back to its "other" form.
  if (value && typeof value === 'object' && typeof value.other === 'string') return fill(value.other, vars);
  return key;
};

export const n = (key, count, vars = {}) => {
  let forms = catalog[key];
  if (!forms || typeof forms !== 'object') {
    const one = catalog[`${key}.one`];
    const other = catalog[`${key}.other`];
    forms = one || other ? {one, other} : null;
  }
  if (!forms) return t(key, {count, ...vars});
  const category = new Intl.PluralRules(locale()).select(count);
  const value = forms[category] || forms.other || key;
  return fill(value, {count, ...vars});
};
