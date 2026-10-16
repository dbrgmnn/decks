// Register the app-shell worker. Offline support is progressive: it needs a
// secure context (HTTPS or localhost), so plain-HTTP LAN testing skips it.
export function initServiceWorker() {
  if (!('serviceWorker' in navigator) || !window.isSecureContext) return;

  addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // A failed registration must never break the app.
    });
  });
}
