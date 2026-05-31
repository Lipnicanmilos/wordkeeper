const CACHE_NAME = 'wordkeeper-v3';
const ASSETS_TO_CACHE = [
  '/',
  '/dashboard',
  '/login',
  '/register',
  '/test',
  '/repeat',
  '/profile',
  '/static/css/style.css',
  '/manifest.json',
  '/favicon.ico',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

// Inštalácia - cachovanie základných súborov
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting(); // Vynúti aktiváciu novej verzie hneď po inštalácii
});

// Aktivácia - vymazanie starej cache
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    })
  );
  self.clients.claim(); // Prevezme kontrolu nad všetkými klientmi okamžite
});

// Fetch stratégia - Stale-While-Revalidate
self.addEventListener('fetch', (event) => {
  // SWR používame iba pre GET požiadavky
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.match(event.request).then((cachedResponse) => {
        const fetchPromise = fetch(event.request).then((networkResponse) => {
          // Ak dostaneme platnú odpoveď, aktualizujeme cache
          if (networkResponse && networkResponse.status === 200) {
            cache.put(event.request, networkResponse.clone());
          }
          return networkResponse;
        }).catch(() => {
          // Ak sme offline a sieť zlyhá, skúsime vrátiť dashboard pre navigácie
          if (event.request.mode === 'navigate' && !cachedResponse) {
            return caches.match('/dashboard');
          }
        });

        // Vrátime cachovanú verziu okamžite (stale), zatiaľ čo fetchPromise beží na pozadí
        // Ak v cache nič nemáme, čakáme na fetchPromise (revalidate)
        return cachedResponse || fetchPromise;
      });
    })
  );
});