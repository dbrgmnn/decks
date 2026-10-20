// App-shell service worker.
//
// The app is server-rendered and server-authoritative, so the worker never
// caches pages or API answers. It only:
//   - serves /static/* network-first with a cache fallback, so the UI keeps its
//     look on a flaky connection, and
//   - answers navigation requests that fail offline with a small offline page.
const VERSION = 'decks-v7';
const STATIC_CACHE = `${VERSION}-static`;
const OFFLINE_URL = '/static/offline.html';
const PRECACHE = ['/static/tokens.css', OFFLINE_URL, '/static/offline.css'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then(cache => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches
      .keys()
      .then(keys => Promise.all(keys.filter(key => !key.startsWith(VERSION)).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const {request} = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith('/static/')) {
    event.respondWith(networkFirst(request, STATIC_CACHE));
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(networkFirstNavigation(request));
  }
});

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  // Cache by path so the ?v= cache-buster never piles up stale entries.
  const key = new Request(new URL(request.url).pathname);
  try {
    const response = await fetch(request);
    if (response.ok && response.type === 'basic') cache.put(key, response.clone());
    return response;
  } catch (error) {
    const cached = await cache.match(key);
    if (cached) return cached;
    throw error;
  }
}

async function networkFirstNavigation(request) {
  try {
    return await fetch(request);
  } catch {
    const cache = await caches.open(STATIC_CACHE);
    const offline = await cache.match(OFFLINE_URL);
    return offline ?? new Response('Offline', {status: 503, headers: {'Content-Type': 'text/plain'}});
  }
}
