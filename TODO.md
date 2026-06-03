 Problém #1 – Dashboard: kategórie a štatistiky sa nezobrazujú
Príčina: SW používa stratégiu return cachedResponse || fetchPromise.
Toto znamená: ak cache pre daný endpoint neexistuje (prvý offline prístup, alebo cache bola vymazaná), SW čaká na fetchPromise — ten zlyhá (offline) a až potom vráti fallback dáta. Ale cachedResponse je undefined → volá sa fetchPromise → fallback sa vráti správne... zdanlivo OK.
Skutočný problém je iný: SW cachuje odpovede len pri status === 200, ale /api/v1/categories vracia odpoveď s Cookie/Session autentifikáciou. Keď SW pri install skúsi cachovať /dashboard, server vráti redirect na /login (nie 200) → /dashboard sa nikdy neuloží do cache.
Overenie — v SW ASSETS_TO_CACHE:
js'/dashboard',  // ← server vráti redirect ak nie si prihlásený → neuloží sa
'/category',   // ← rovnaký problém
Výsledok: Po prvom online prihlásení sa /api/v1/categories a /api/user/stats cachujú správne — ale iba ak si tieto stránky navštívil. Ak cache neexistuje → fallback vráti prázdne dáta [] a { total_words: 0 }.
Oprava v sw.js — odstráň stránky vyžadujúce auth z ASSETS_TO_CACHE:
jsconst ASSETS_TO_CACHE = [
  '/manifest.json',
  '/favicon.ico',
  '/apple-touch-icon.png',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
  // dashboard, login atď. NECACHUJ pri install — cachujú sa dynamicky pri návšteve
];
A zároveň zmeň verziu cache na wordkeeper-v7 aby sa stará cache vymazala.

🔴 Problém #2 – Profil zobrazí "Ste offline"
Príčina: profile.html na riadku 344:
jsconst res = await fetch('/api/user');
if (!res.ok) { window.location.href = '/login'; return; }  // ← redirect na login
const user = await res.json();
// user = { error: 'offline', offline: true }  ← res.ok = true (status 200)
// ale potom: user.id = undefined → document.getElementById('userId').textContent = '#undefined'
// user.email = undefined → crashes alebo zobrazí undefined
SW vráti { error: 'offline', offline: true } so statusom 200 → res.ok = true → nevyhodí redirect. Ale user.id, user.email, user.created_at sú undefined → stránka sa rozbije a zobrazí prázdne/undefined hodnoty, prípadne "Ste offline" správu ak ju máš niekde nastavenú.
Oprava v profile.html — rovnaká logika ako v dashboard.html:
jsasync function loadUserProfile() {
  try {
    const res = await fetch('/api/user');
    const user = await res.json();

    // Offline fallback
    if (!res.ok || user.offline || user.error === 'offline') {
      document.getElementById('userId').textContent = localStorage.getItem('wk_user_id') ? '#' + localStorage.getItem('wk_user_id') : '#-';
      document.getElementById('userEmail').textContent = localStorage.getItem('wk_user_name') || 'Offline';
      document.getElementById('memberSince').textContent = '-';
      // Zobraz offline banner
      const banner = document.createElement('div');
      banner.style.cssText = 'background:#f59e0b;color:#fff;text-align:center;padding:8px;font-weight:600;position:sticky;top:0;z-index:9999;';
      banner.textContent = '⚠️ Offline režim – zobrazujú sa uložené dáta';
      document.body.prepend(banner);
      return;
    }

    // ... zvyšok pôvodného kódu ...

Zhrnutie
ProblémPríčinaOpravaDashboard – prázdne kategórieSW cachuje /dashboard pri install ale server vráti redirect (nie 200)Odstráň auth stránky z ASSETS_TO_CACHE, zmeň na v7Dashboard – štatistiky 0Cache neexistuje pri prvom offline prístupeRovnaká oprava + API sa cachuje dynamicky pri návšteveProfil – "Ste offline" / undefinedprofile.html nekontroluje user.offlinePridaj offline vetvu do loadUserProfile()