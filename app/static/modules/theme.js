import {$, root} from './dom.js';

export function initTheme() {
  const button = $('#theme');
  if (!button) return;

  const syncThemeButton = () => {
    const dark = root.dataset.theme === 'dark';
    button.setAttribute('aria-pressed', String(dark));
    button.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
    button.textContent = dark ? '◑' : '◐';
  };

  syncThemeButton();

  button.onclick = () => {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    localStorage.theme = root.dataset.theme;
    syncThemeButton();
    button.blur();

    const flash = document.createElement('div');
    flash.className = 'flash';
    document.body.append(flash);
    setTimeout(() => flash.remove(), 450);
  };
}
