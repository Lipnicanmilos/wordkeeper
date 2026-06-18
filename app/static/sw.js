const CACHE_NAME = 'wordkeeper-v11';

const ASSETS_TO_CACHE = [
  '/manifest.json',
  '/favicon.ico',
  '/apple-touch-icon.png',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
];

self.addEventListener('install', (event) => {
  console.log('[SW] Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) return caches.delete(cacheName);
          return Promise.resolve();
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Cache-only static assets; do not interfere with admin/API.
  const isStaticAsset = url.pathname.startsWith('/static/') || url.pathname === '/manifest.json';

  // Explicitly do not fake/mask admin or any API.
  const isAdminApi = url.pathname.startsWith('/api/admin/');
  const isApi = url.pathname.startsWith('/api/');
  if (isApi || isAdminApi) {
    // Always try network.
    event.respondWith(fetch(event.request));
    return;
  }

  // For static assets: try cache then network.
  if (isStaticAsset) {
    event.respondWith(
      caches.match(event.request).then(async (cached) => {
        if (cached) return cached;
        const res = await fetch(event.request);
        if (res && res.status === 200) {
          const cache = await caches.open(CACHE_NAME);
          cache.put(event.request, res.clone());
        }
        return res;
      })
    );
    return;
  }

  // For everything else: network only.
  event.respondWith(fetch(event.request));
});

self.addEventListener('message', (event) => {
  if (!event.data) return;
  if (event.data.type === 'SKIP_WAITING') self.skipWaiting();
});

console.log('[SW] Service Worker v11 loaded');

