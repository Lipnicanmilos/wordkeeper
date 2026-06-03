# WordKeeper – Offline PWA TODO

## Completed
- [x] Úprava service workeru (`app/static/sw.js`) na cacheovanie navigácií + GET requestov na `/api/**` tak, aby UI vedelo zobraziť posledné uložené dáta offline.
- [x] Offline učenie slovíčok v `app/templates/repeat.html` (cache slovíčok do localStorage + fallback offline).
- [x] Offline notifikácie (C): UI permission + SW `SHOW_NOTIFICATION` demo na `app/templates/dashboard.html`.

## Next
- [ ] Implementovať offline queue pre zápisy (POST/PUT/DELETE) do IndexedDB/localStorage.


- [ ] Po obnovení online poslať queued operácie na backend (replay) a refreshnúť UI.
- [ ] Spraviť offline editovanie level slovíčok (ak existujú endpointy na update `Word.knowledge_level`) rovnakým mechanizmom queue.
- [ ] Testovanie: Chrome DevTools → Application → Service Worker + Offline mode; overiť:
  - načítanie dashboardu offline po prvom online otvorení
  - pridanie/upravovanie/mazanie kategórie offline a následný sync po online
  - edit level slovíčka offline + sync

