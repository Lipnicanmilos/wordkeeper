ahoj skontroluj moj kod
https://github.com/Lipnicanmilos/wordkeeper
PWA mozes mi ked som online ulozit vsetky categorie a slovicka do pamati
aby som offline mohol pracovat so vsetkym profil, vsetky kategorie aj tie nekliknute v online rezime
aj vsetky testy a repeaty a slovicka?


Hlavné problémy
1. test.html — žiadny offline fallback
/api/v1/words/test/start je POST — SW ho úplne ignoruje (riadok v sw.js: if (event.request.method !== 'GET') return). Keď si offline, test sa nespustí a kód ani nemá catch s fallbackom.
2. /api/v1/words/test/submit (POST) sa offline stratí
Výsledky testu sa neukložia do žiadnej fronty. Po reconnecte sa knowledge level neaktualizuje.
3. prefetchAllWords čaká na serviceWorker.controller
Pri prvom načítaní stránky (hneď po inštalácii SW) je controller ešte null — prefetch sa preskoči úplne, aj keď je fallback kód v prefetchAllWords napísaný.
4. repeat.html — offline cache funguje len pre kombináciu (categoryId + level + direction) ktorú si už raz otvoril online. Nové levely alebo kategórie bez predchádzajúcej návštevy nemajú cache.
5. Štatistiky (/api/user/stats) sa nekešujú do localStorage na profile.html — vidno len na dashboarde.

🛠 Prioritne opravy (už schválené)
✅ 1) test.html — offline fallback cez localStorage (start cache)
✅ 2) test.html — offline queue pre submit (POST) v localStorage + flush pri online reconnectu
⬜ 3) sw.js / prefetchAllWords race (controller null)
⬜ 4) repeat.html offline cache rozšíriť pre nové kombinácie bez predchádzajúcej návštevy
⬜ 5) profile.html — ukladať /api/user/stats do localStorage online, čítať offline



