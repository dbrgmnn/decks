import {$, root, syncThemeColor} from './dom.js';

export function initTheme() {
  const button = $('#theme');
  if (!button) return;

  let flashTimer = null;

  const syncThemeButton = () => {
    const dark = root.dataset.theme === 'dark';
    button.setAttribute('aria-pressed', String(dark));
    button.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
    button.textContent = dark ? '◑' : '◐';
    syncThemeColor();
  };

  const saveTheme = theme => {
    try {
      localStorage.theme = theme;
    } catch {
      // Ignore storage errors and keep the theme in memory.
    }
  };

  const showFlash = () => {
    document.querySelector('.flash')?.remove();
    const flash = document.createElement('div');
    flash.className = 'flash';
    document.body.append(flash);
    clearTimeout(flashTimer);
    flashTimer = setTimeout(() => flash.remove(), 450);
  };

  syncThemeButton();

  button.onclick = () => {
    const nextTheme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = nextTheme;
    saveTheme(nextTheme);
    syncThemeButton();
    button.blur();
    showFlash();
  };
}
