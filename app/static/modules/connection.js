import {$, root} from './dom.js';
import {t} from './i18n.js';

// Keep the app usable when the connection drops: cover it with a small
// placeholder that retries on demand, when the browser reports that the
// network is back, and on a slow background timer.
export function initConnectionGuard() {
  const overlay = $('#offline');
  if (!overlay) return;

  const retry = $('#offline-retry');
  const status = $('#offline-status');
  let checking = false;
  let timer = null;

  const show = () => {
    if (!overlay.hidden) return;
    status.textContent = '';
    overlay.hidden = false;
    root.classList.add('offline-open');
    retry?.focus({preventScroll: true});
    clearInterval(timer);
    timer = setInterval(check, 10000);
  };

  const hide = () => {
    overlay.hidden = true;
    root.classList.remove('offline-open');
    status.textContent = '';
    clearInterval(timer);
    timer = null;
  };

  async function check() {
    if (checking) return;
    checking = true;
    if (retry) retry.disabled = true;
    status.textContent = t('offline.checking');
    try {
      const response = await fetch('/healthz', {cache: 'no-store'});
      if (response.ok) hide();
      else status.textContent = t('offline.still');
    } catch {
      status.textContent = t('offline.still');
    } finally {
      checking = false;
      if (retry) retry.disabled = false;
    }
  }

  retry?.addEventListener('click', check);
  addEventListener('offline', show);
  addEventListener('online', () => {
    if (!overlay.hidden) check();
  });

  if (!navigator.onLine) show();
}
