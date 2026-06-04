const CACHE_NAME = 'wordkeeper-v9';
const ASSETS_TO_CACHE = [
  '/manifest.json',
  '/favicon.ico',
  '/apple-touch-icon.png',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

// ✅ Offline fallback dáta pre API
const OFFLINE_FALLBACK_DATA = {
  categories: [],
  words: { words: [], total: 0 },
  user: { error: 'offline', offline: true },
  stats: {
    total_words: 0,
    total_categories: 0,
    tests_taken: 0,
    success_rate: 0,
    words_by_level: { dont_know: 0, learning: 0, know: 0 }
  }
};

// Inštalácia
self.addEventListener('install', (event) => {
  console.log('[SW] Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE).catch(err => {
        console.warn('[SW] Some assets failed to cache:', err);
      });
    })
  );
  self.skipWaiting();
});

// Aktivácia — vymazanie starej cache
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            console.log('[SW] Deleting old cache:', cache);
            return caches.delete(cache);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch handler
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);
  const isNavigate = event.request.mode === 'navigate';
  const isApi = url.pathname.startsWith('/api/');
  const isStatic = url.pathname.startsWith('/static/');
  const isManifest = url.pathname === '/manifest.json' || url.pathname === '/sw.js';
  const shouldSkip = url.pathname.includes('login') || url.pathname.includes('register');

  if (shouldSkip && !isNavigate) return;

  event.respondWith(
    (async () => {
      try {

        // 1) NAVIGÁCIE: network-first s cache fallback
        if (isNavigate) {
          try {
            const networkResponse = await fetch(event.request);
            if (networkResponse.status === 200) {
              const cache = await caches.open(CACHE_NAME);
              cache.put(event.request, networkResponse.clone());
            }
            return networkResponse;
          } catch (err) {
            const cachedResponse = await caches.match(event.request) ||
                                   await caches.match(url.pathname);
            if (cachedResponse) return cachedResponse;

            return new Response(`<!DOCTYPE html>
<html lang="sk">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Offline – WordKeeper</title>
  <style>
    body { font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; background: #f4f7fe; color: #333; text-align: center; padding: 2rem; box-sizing: border-box; }
    .icon { font-size: 4rem; margin-bottom: 1rem; }
    h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
    p { color: #666; margin-bottom: 2rem; }
    a { background: #4079ff; color: #fff; padding: 0.75rem 1.5rem; border-radius: 8px; text-decoration: none; font-weight: 600; }
  </style>
</head>
<body>
  <div class="icon">📶</div>
  <h1>Ste offline</h1>
  <p>Táto stránka nie je dostupná bez pripojenia.<br>Vráťte sa na dashboard kde sú uložené vaše dáta.</p>
  <a href="/dashboard">← Dashboard</a>
</body>
</html>`, { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
          }
        }

        // 2) MANIFEST a SW: network-first
        if (isManifest) {
          try {
            const response = await fetch(event.request);
            if (response.status === 200) {
              const cache = await caches.open(CACHE_NAME);
              cache.put(event.request, response.clone());
            }
            return response;
          } catch (err) {
            const cached = await caches.match(event.request);
            return cached || new Response('{}', { status: 503 });
          }
        }

        // 3) API REQUESTY: stale-while-revalidate s offline fallback
        if (isApi) {
          const cache = await caches.open(CACHE_NAME);
          const cachedResponse = await cache.match(event.request);

          const fetchPromise = fetch(event.request)
            .then((networkResponse) => {
              if (networkResponse && networkResponse.status === 200) {
                cache.put(event.request, networkResponse.clone());
              }
              return networkResponse;
            })
            .catch(() => {
              if (cachedResponse) return cachedResponse;

              // ✅ Fallback na prázdne dáta pre známe endpointy
              const pathname = url.pathname;

              if (pathname.includes('/api/v1/categories')) {
                // Jednotlivá kategória vs zoznam
                const isSingleCategory = /\/api\/v1\/categories\/\d+$/.test(pathname);
                if (isSingleCategory) {
                  return new Response(JSON.stringify({ error: 'offline', offline: true }), {
                    status: 200,
                    headers: { 'Content-Type': 'application/json', 'X-Offline': 'true' }
                  });
                }
                return new Response(JSON.stringify(OFFLINE_FALLBACK_DATA.categories), {
                  status: 200,
                  headers: { 'Content-Type': 'application/json', 'X-Offline': 'true' }
                });
              }

              if (pathname.includes('/api/v1/words')) {
                return new Response(JSON.stringify(OFFLINE_FALLBACK_DATA.words), {
                  status: 200,
                  headers: { 'Content-Type': 'application/json', 'X-Offline': 'true' }
                });
              }

              if (pathname.includes('/api/user/stats')) {
                return new Response(JSON.stringify(OFFLINE_FALLBACK_DATA.stats), {
                  status: 200,
                  headers: { 'Content-Type': 'application/json', 'X-Offline': 'true' }
                });
              }

              if (pathname.includes('/api/user')) {
                return new Response(JSON.stringify(OFFLINE_FALLBACK_DATA.user), {
                  status: 200,
                  headers: { 'Content-Type': 'application/json', 'X-Offline': 'true' }
                });
              }

              return new Response(JSON.stringify({ error: 'offline', offline: true }), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
              });
            });

          return cachedResponse || fetchPromise;
        }

        // 4) STATICKÉ SÚBORY: stale-while-revalidate
        if (isStatic) {
          const cache = await caches.open(CACHE_NAME);
          const cachedResponse = await cache.match(event.request);

          const fetchPromise = fetch(event.request)
            .then((networkResponse) => {
              if (networkResponse && networkResponse.status === 200) {
                cache.put(event.request, networkResponse.clone());
              }
              return networkResponse;
            })
            .catch(() => cachedResponse);

          return cachedResponse || fetchPromise;
        }

        // 5) OSTATNÉ
        return await fetch(event.request);

      } catch (error) {
        console.error('[SW] Fetch handler error:', error);
        return new Response('Service Worker error', { status: 500 });
      }
    })()
  );
});

// Messages
self.addEventListener('message', (event) => {
  if (!event.data) return;

  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data.type === 'SHOW_NOTIFICATION') {
    try {
      const title = event.data.title || 'WordKeeper';
      const options = {
        body: event.data.body || '',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/icon-192x192.png',
        tag: event.data.tag || 'wordkeeper-offline',
        renotify: true
      };
      event.waitUntil(self.registration.showNotification(title, options));
    } catch (e) { /* ignoruj */ }
  }

  // ✅ NOVÉ: Prefetch príkaz zo stránky — SW aktívne uloží slovíčka do cache
  if (event.data.type === 'PREFETCH_WORDS') {
    const { categoryIds } = event.data;
    if (!Array.isArray(categoryIds) || categoryIds.length === 0) return;

    event.waitUntil(
      caches.open(CACHE_NAME).then(async (cache) => {
        for (const id of categoryIds) {
          try {
            const url = `/api/v1/words?category_id=${id}`;
            // Preskočiť ak už máme čerstvú cache (menej ako 24h)
            const existing = await cache.match(url);
            if (existing) {
              const dateHeader = existing.headers.get('date');
              if (dateHeader) {
                const age = Date.now() - new Date(dateHeader).getTime();
                if (age < 24 * 60 * 60 * 1000) {
                  console.log(`[SW] Prefetch skip (fresh cache): category ${id}`);
                  continue;
                }
              }
            }
            const response = await fetch(url);
            if (response.status === 200) {
              await cache.put(url, response.clone());
              console.log(`[SW] Prefetched words for category ${id}`);
            }
            // Malá pauza medzi requestmi
            await new Promise(r => setTimeout(r, 200));
          } catch (e) {
            console.warn(`[SW] Prefetch failed for category ${id}:`, e);
          }
        }
        console.log('[SW] Prefetch dokončený pre všetky kategórie');
      })
    );
  }
});

console.log('[SW] Service Worker v9 loaded');
