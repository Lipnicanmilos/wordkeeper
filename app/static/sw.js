const CACHE_NAME = 'lexinova-v18';
const ASSETS_TO_CACHE = [
  '/manifest.json',
  '/favicon.ico',
  '/apple-touch-icon.png',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/static/js/offline-cache.js',
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

  // Auth endpointy nikdy neinterceptujeme — OAuth flow potrebuje natívne cookie spracovanie.
  if (url.pathname.startsWith('/auth/')) {
    return;
  }

  // Iba GET cachujeme; POST/PUT/... vždy sieť.
  if (event.request.method !== 'GET') {
    event.respondWith(fetch(event.request));
    return;
  }

  // API nikdy necachujeme — vždy sieť (alebo chyba, ktorú stránka spracuje sama).
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Statické assety: cache-first.
  if (url.pathname.startsWith('/static/') || url.pathname === '/manifest.json') {
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

  // HTML stránky (navigate): network-first, pri offline servuj z cache.
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).then((response) => {
        // Úspešnú odpoveď ulož do cache pre offline použitie.
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      }).catch(async () => {
        // Offline: skús cache pre túto konkrétnu URL.
        const cached = await caches.match(event.request);
        if (cached) return cached;

        // Fallback: skús /dashboard (ak bolo cachované).
        const dashboard = await caches.match('/dashboard');
        if (dashboard) return dashboard;

        // Nič nie je v cache — zobraz offline stránku.
        return new Response(`<!DOCTYPE html><html lang="sk"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Offline – LexiNova</title>
<style>*{margin:0;box-sizing:border-box}body{font-family:Inter,sans-serif;background:#f4f7fe;
display:flex;align-items:center;justify-content:center;min-height:100vh;padding:2rem}
.card{background:#fff;border-radius:20px;padding:2.5rem;max-width:420px;width:100%;
text-align:center;box-shadow:0 8px 32px rgba(64,121,255,.1)}
h1{font-size:1.4rem;font-weight:800;color:#4079ff;margin-bottom:.75rem}
p{color:#718096;font-size:.95rem;line-height:1.6;margin-bottom:1.5rem}
a{display:inline-block;padding:.75rem 1.5rem;background:linear-gradient(135deg,#4079ff,#40ffaa);
color:#fff;text-decoration:none;border-radius:12px;font-weight:700;font-size:.9rem}</style>
</head><body><div class="card">
<h1>📡 Si offline</h1>
<p>Táto stránka nie je dostupná bez internetu.<br>
Navštív ju najprv online, aby sa uložila do cache.</p>
<a href="/dashboard">← Dashboard</a>
</div></body></html>`, {
          status: 503,
          headers: { 'Content-Type': 'text/html; charset=utf-8' }
        });
      })
    );
    return;
  }

  // Všetko ostatné: iba sieť.
  event.respondWith(fetch(event.request));
});

self.addEventListener('message', (event) => {
  if (!event.data) return;
  if (event.data.type === 'SKIP_WAITING') self.skipWaiting();
  if (event.data.type === 'SHOW_NOTIFICATION') {
    const { title, body, tag } = event.data;
    event.waitUntil(
      self.registration.showNotification(title || 'LexiNova', {
        body: body || '',
        tag: tag || 'lexinova',
        icon: '/static/icons/icon-192x192.png',
      })
    );
  }
});

console.log('[SW] Service Worker v18 loaded');
